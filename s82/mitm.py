#!/usr/bin/env python3
"""
mitm.py — Proxy MITM transparente v3.
Intercepta TODO tráfico HTTPS usando iptables REDIRECT.
Lee ClientHello manualmente para extraer SNI, luego usa MemoryBIO
para el handshake TLS con el certificado correcto.

Uso:
  bash gen-ca.sh
  sudo python3 mitm.py --install-ca
  sudo python3 mitm.py --iptables-add
  sudo python3 mitm.py          # corre como root
  sudo python3 mitm.py --iptables-del
"""

import ssl, socket, struct, threading, logging, sys, os, json, hashlib, subprocess
import traceback, resource
from datetime import datetime
from pathlib import Path

# ─── Config ──────────────────────────────────────────
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8443
BASE = Path('/home/vuos/code/p3/s82')
CA_CERT = BASE / 'certs/ca.crt'
CA_KEY = BASE / 'certs/ca.key'
SERVER_KEY = BASE / 'certs/server.key'
CERT_CACHE = BASE / 'certs/cache'
LOG_FILE = BASE / 'mitm.log'
DATA_LOG = BASE / 'captures.jsonl'
SOCK_TIMEOUT = 60
BUF_SIZE = 65536
SO_ORIGINAL_DST = 80

# ─── Resource limits ────────────────────────────────
MAX_CONCURRENT = 50          # max conexiones simultáneas
RAM_WARN_PCT = 80            # alerta si RAM usada > 80%
_start_time = datetime.now()
_conn_semaphore = threading.BoundedSemaphore(MAX_CONCURRENT)

def resource_baseline():
    """Retorna (ram_total_mb, ram_used_mb, ram_pct, cpu_count, ulimit_n)."""
    import resource
    mem = {}
    with open('/proc/meminfo') as f:
        for line in f:
            k, v = line.split(':')
            mem[k.strip()] = int(v.strip().split()[0]) // 1024  # KB→MB
    total = mem.get('MemTotal', 0)
    available = mem.get('MemAvailable', 0)
    used = total - available
    pct = (used / total * 100) if total else 0
    cpu = os.cpu_count() or 1
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        ulimit_n = soft
    except:
        ulimit_n = 1024
    return total, used, pct, cpu, ulimit_n


# ─── Logging ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger()


# =====================================================================
# CERTIFICADOS DINÁMICOS
# =====================================================================

def generate_cert(hostname):
    """Genera (o cachea) un certificado para hostname firmado por nuestra CA."""
    safe = hashlib.sha256(hostname.encode()).hexdigest()[:16]
    cert_path = CERT_CACHE / f"{safe}.crt"
    if cert_path.exists():
        return str(cert_path)

    cnf = CERT_CACHE / f"{safe}.cnf"
    csr = CERT_CACHE / f"{safe}.csr"

    cnf.write_text(f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no
[req_distinguished_name]
CN = {hostname}
[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = {hostname}
""")

    subprocess.run(['openssl', 'req', '-new', '-key', str(SERVER_KEY),
                    '-out', str(csr), '-config', str(cnf)], capture_output=True)
    subprocess.run(['openssl', 'x509', '-req', '-in', str(csr),
                    '-CA', str(CA_CERT), '-CAkey', str(CA_KEY),
                    '-CAcreateserial', '-out', str(cert_path),
                    '-days', '365', '-sha256',
                    '-extfile', str(cnf), '-extensions', 'v3_req'], capture_output=True)

    cnf.unlink(missing_ok=True)
    csr.unlink(missing_ok=True)
    return str(cert_path)


# =====================================================================
# PARSEADOR SNI (TLS ClientHello raw)
# =====================================================================

def parse_sni(data):
    """Extrae SNI del TLS ClientHello."""
    try:
        if len(data) < 5:
            return None
        pos = 5
        if pos + 4 > len(data):
            return None
        pos += 4  # handshake type(1) + length(3)
        pos += 2  # ClientVersion
        pos += 32  # Random
        if pos >= len(data):
            return None
        pos += 1 + data[pos]  # Session ID
        if pos + 2 > len(data):
            return None
        cs_len = struct.unpack('!H', data[pos:pos+2])[0]
        pos += 2 + cs_len  # Cipher Suites
        if pos >= len(data):
            return None
        pos += 1 + data[pos]  # Compression
        if pos + 2 > len(data):
            return None
        ext_len = struct.unpack('!H', data[pos:pos+2])[0]
        pos += 2
        ext_end = pos + ext_len
        while pos + 4 <= ext_end:
            ext_type = struct.unpack('!H', data[pos:pos+2])[0]
            ext_len = struct.unpack('!H', data[pos+2:pos+4])[0]
            pos += 4
            if ext_type == 0:  # SNI
                pos += 2  # sni list length
                if pos < len(data):
                    name_type = data[pos]
                    pos += 1
                    if name_type == 0:  # host_name
                        name_len = struct.unpack('!H', data[pos:pos+2])[0]
                        pos += 2
                        return data[pos:pos+name_len].decode('utf-8', errors='replace')
            pos += ext_len
    except Exception:
        pass
    return None


def get_original_dst(sock):
    try:
        dst = sock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
        port = struct.unpack('!H', dst[2:4])[0]
        ip = socket.inet_ntoa(dst[4:8])
        return ip, port
    except Exception:
        return None, None


# =====================================================================
# MANEJADOR TLS CON MEMORYBIO
# =====================================================================

def tls_server_handshake(raw_conn, cert_path, key_path):
    """
    Hace handshake TLS del lado servidor usando MemoryBIO.
    raw_conn: socket TCP (ya leyó ClientHello)
    cert_path: certificado para presentar
    key_path: clave privada

    Retorna: (ssl_object, hostname_detectado)
    El ssl_object soporta .read(n) y .write(data) como un socket.
    """
    # Leer ClientHello del socket (o ya lo tenemos?)
    # En nuestro caso, NO lo hemos leído — lo leemos aquí
    hello = raw_conn.recv(BUF_SIZE)
    if not hello:
        return None, None

    sni = parse_sni(hello)

    # Crear contexto con el cert correcto
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    ctx.set_alpn_protocols(['http/1.1'])

    bio_in = ssl.MemoryBIO()
    bio_out = ssl.MemoryBIO()
    obj = ctx.wrap_bio(bio_in, bio_out, server_side=True)

    # Inyectar ClientHello
    bio_in.write(hello)

    # Handshake loop
    while True:
        try:
            obj.do_handshake()
            break
        except ssl.SSLWantReadError:
            # Enviar datos pendientes al cliente
            pending = bio_out.read()
            if pending:
                raw_conn.sendall(pending)
            # Leer más datos del cliente
            data = raw_conn.recv(BUF_SIZE)
            if not data:
                return None, sni
            bio_in.write(data)
        except ssl.SSLWantWriteError:
            pending = bio_out.read()
            if pending:
                raw_conn.sendall(pending)

    # Drenar bio_out
    pending = bio_out.read()
    if pending:
        raw_conn.sendall(pending)

    return obj, sni


# =====================================================================
# HTTP I/O SOBRE SSLObject
# =====================================================================

class TlsBIO:
    """Wrapper sobre SSLObject + MemoryBIO + socket TCP.
    Proporciona interfaz tipo socket (read/write) para SSLObject."""
    def __init__(self, ssl_obj, sock, bio_out):
        self.obj = ssl_obj
        self.sock = sock
        self.bio_out = bio_out

    def read(self, n=BUF_SIZE):
        """Lee datos descifrados (hasta n bytes)."""
        out = b''
        # Primero: si hay datos descifrados pendientes, leerlos
        try:
            out += self.obj.read(n)
        except ssl.SSLWantReadError:
            pass

        if out:
            return out

        # No hay datos descifrados: leer del socket, pasar a SSL
        data = self.sock.recv(BUF_SIZE)
        if not data:
            return b''

        # Escribir datos cifrados al BIO de entrada
        self.obj.write(b'')  # hack: forzar flush
        # Necesitamos pasar los datos al bio_in
        # Pero SSLObject no nos deja acceder a bio_in directamente
        # ...
        # Enfoque: usar obj.read() que internamente lee del bio_in
        # Pero ¿cómo metemos datos al bio_in?
        # 
        # PROBLEMA: SSLObject envuelve bio_in internamente.
        # No podemos escribir en bio_in directamente.
        # La API correcta es: obj.read() intenta descifrar datos
        # del bio_in. Pero si bio_in está vacío, lanza SSLWantReadError.
        # Necesitamos escribir en bio_in antes de leer.
        #
        # Con MemoryBIO explícito podemos hacer:
        # bio_in.write(data_cifrada)
        # obj.read()  # descifra lo que pusimos
        #
        # PERO con SSLObject creado por wrap_bio, los bio_in/bio_out
        # están encapsulados. No podemos acceder a ellos.
        #
        # Solución: NO usar TlsBIO. Usar bio_in/bio_out directamente.
        return b''  # FIXME


# =====================================================================
# LECTURA HTTP CON BUFFERING (usando SSLObject.read())
# =====================================================================

def http_read_line(ssl_obj, sock, bio_in, bio_out):
    """Lee una línea de HTTP desde SSLObject (con MemoryBIO)."""
    line = b''
    while not line.endswith(b'\n'):
        ch = _read_decrypted(ssl_obj, sock, bio_in, bio_out, 1)
        if not ch:
            break
        line += ch
    return line


def _read_decrypted(ssl_obj, sock, bio_in, bio_out, n):
    """
    Lee n bytes descifrados.
    bio_in/bio_out son los MemoryBIO.
    sock es el socket TCP.
    ssl_obj es el SSLObject.
    """
    try:
        return ssl_obj.read(n)
    except ssl.SSLWantReadError:
        # SSL quiere leer datos cifrados del bio_in
        # Leer del socket y meter en bio_in
        data = sock.recv(BUF_SIZE)
        if not data:
            return b''
        bio_in.write(data)
        # Enviar datos de salida SSL al socket
        out = bio_out.read()
        if out:
            sock.sendall(out)
        # Intentar leer de nuevo
        try:
            return ssl_obj.read(n)
        except ssl.SSLWantReadError:
            return b''


def _write_encrypted(ssl_obj, sock, bio_out, data):
    """Escribe datos descifrados, los cifra y los envía al socket."""
    try:
        ssl_obj.write(data)
    except ssl.SSLWantWriteError:
        pass
    # Los datos cifrados están en bio_out
    out = bio_out.read()
    if out:
        sock.sendall(out)


# =====================================================================
# HANDLER PRINCIPAL
# =====================================================================

def handle(conn, addr):
    conn.settimeout(SOCK_TIMEOUT)

    try:
        # ── 0. Leer primeros bytes para detectar modo ──
        first_bytes = conn.recv(BUF_SIZE)
        if not first_bytes:
            return

        # ¿CONNECT? (forward proxy mode)
        if first_bytes.startswith(b'CONNECT '):
            log.info(f"\n🔗 {addr[0]} → [CONNECT proxy]")
            line, _, _ = first_bytes.partition(b'\r\n')
            parts = line.split(b' ')
            if len(parts) >= 2:
                hostport = parts[1].decode()
                target = hostport.split(':')[0]
                port = int(hostport.split(':')[1]) if ':' in hostport else 443
            else:
                return

            # Responder 200 Connection Established
            conn.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')

            # Ahora el cliente envía TLS ClientHello por el túnel
            hello = conn.recv(BUF_SIZE)
            if not hello:
                return

            sni = parse_sni(hello) or target
            log.info(f"    CONNECT → {target}:{port} (SNI: {sni})")

        else:
            # ── Transparent MITM (via iptables) ──
            hello = first_bytes
            sni = parse_sni(hello)
            orig_ip, orig_port = get_original_dst(conn)
            target = sni or orig_ip or 'unknown'

            log.info(f"\n🔗 {addr[0]} → {target}")
            if sni:
                log.info(f"    SNI: {sni}")

        # ── Generar certificado para hostname ──
        cert_path = generate_cert(target)

        # ── 3. Handshake TLS con MemoryBIO ──
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_path, str(SERVER_KEY))
        ctx.set_alpn_protocols(['h2', 'http/1.1'])
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2

        bio_in = ssl.MemoryBIO()
        bio_out = ssl.MemoryBIO()
        ssl_obj = ctx.wrap_bio(bio_in, bio_out, server_side=True)

        # Inyectar ClientHello que ya leímos
        bio_in.write(hello)

        # Handshake loop
        while True:
            try:
                ssl_obj.do_handshake()
                break
            except ssl.SSLWantReadError:
                out = bio_out.read()
                if out:
                    conn.sendall(out)
                data = conn.recv(BUF_SIZE)
                if not data:
                    return
                bio_in.write(data)
            except ssl.SSLWantWriteError:
                out = bio_out.read()
                if out:
                    conn.sendall(out)

        out = bio_out.read()
        if out:
            conn.sendall(out)

        log.info(f"    ✓ TLS handshake OK")

        # ── 4. Leer HTTP request ──
        method, path, headers, body = read_http(ssl_obj, conn, bio_in, bio_out)
        if not method:
            # Intentar leer qué datos llegaron
            try:
                raw_dump = ssl_obj.read(200)
            except:
                pass
            return

        log.info(f"  >>> {method} {path}")
        for h in ['content-type', 'authorization', 'x-api-key', 'user-agent']:
            if h in headers:
                v = mask(headers[h]) if h in ('authorization', 'x-api-key') else headers[h]
                log.info(f"      {h}: {v}")
        if body:
            log.info(f"      Body ({len(body)} bytes):\n{fmt_body(body)}")

        # ── 5. Conectar al destino real ──
        host = headers.get('host', target)
        real = socket.create_connection((host, 443), timeout=SOCK_TIMEOUT)
        # Cliente TLS — básico pero compatible
        cli_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        cli_ctx.load_default_certs()
        tls_real = cli_ctx.wrap_socket(real, server_hostname=sni or host)
        tls_real.settimeout(SOCK_TIMEOUT)

        # ── 6. Reenviar request al real ──
        req = f"{method} {path} HTTP/1.1\r\n".encode()
        for k, v in headers.items():
            if k.lower() != 'host':
                req += f"{k}: {v}\r\n".encode()
        req += f"Host: {host}\r\n".encode()
        req += b'\r\n' + body

        tls_real.sendall(req)

        # ── 7. Leer response y enviar al cliente ──
        resp = read_http_response(tls_real)
        if not resp:
            return
        status_line, rhdrs, resp_body = resp

        # Log
        log.info(f"  <<< {status_line}")
        for h in ['content-type', 'content-length']:
            if h in rhdrs:
                log.info(f"      {h}: {rhdrs[h]}")

        # Reconstruir y enviar response al cliente
        resp_raw = f"HTTP/1.1 {status_line.split(' ', 1)[-1]}\r\n".encode() if ' ' in status_line else (status_line.encode() + b'\r\n')
        for k, v in rhdrs.items():
            resp_raw += f"{k}: {v}\r\n".encode()
        resp_raw += b'\r\n' + resp_body

        # Escribir al cliente via SSL
        ssl_obj.write(resp_raw)
        out = bio_out.read()
        if out:
            conn.sendall(out)

        # ── 8. Logging del body ──
        if resp_body:
            log_response_content(rhdrs.get('content-type', ''), resp_body, log)

        # ── 9. Si es streaming, seguir leyendo ──
        if rhdrs.get('content-type', '').startswith('text/event-stream'):
            try:
                while True:
                    chunk = tls_real.read(BUF_SIZE)
                    if not chunk:
                        break
                    ssl_obj.write(chunk)
                    out = bio_out.read()
                    if out:
                        conn.sendall(out)
                    log_stream_chunk(chunk, log)
            except (socket.timeout, ssl.SSLEOFError):
                pass

        tls_real.close()
        log.info(f"  ✓ ({len(resp_body)} bytes)")

        # ── JSONL para el monitor ──
        try:
            body_str = body.decode('utf-8', errors='replace') if body else ''
            req_data = json.loads(body_str) if body_str.startswith('{') else {}
            resp_str = resp_body.decode('utf-8', errors='replace') if resp_body else ''
            resp_data = json.loads(resp_str) if resp_str.startswith('{') else {}

            # Extraer modelo y prompt
            model = (req_data.get('model', '') or
                     headers.get('x-model', ''))
            prompt = ''
            messages = req_data.get('messages', [])
            for m in messages:
                if isinstance(m, dict) and m.get('role') in ('user', 'human') and m.get('content'):
                    prompt = m['content'][:200]
                    break

            # Extraer respuesta
            response = ''
            if 'choices' in resp_data:
                for c in resp_data['choices']:
                    if 'message' in c:
                        response = c['message'].get('content', '')[:500]
                    elif 'delta' in c:
                        response = c['delta'].get('content', '')[:500]
            elif 'content' in resp_data:
                for b in resp_data['content']:
                    if isinstance(b, dict) and b.get('text'):
                        response = b['text'][:500]

            tokens_in = None
            tokens_out = None
            cost = None
            usage = resp_data.get('usage', {})
            if usage:
                tokens_in = usage.get('prompt_tokens')
                tokens_out = usage.get('completion_tokens')
                if 'cost' in resp_data:
                    cost = resp_data['cost']

            capture = {
                't': datetime.now().isoformat(),
                'app': target,
                'host': headers.get('host', ''),
                'model': model,
                'method': method,
                'path': path,
                'status': status_line[:50] if status_line else '',
                'prompt': prompt[:100],
                'response': response[:200],
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'cost': cost,
                'bytes': len(resp_body),
            }
            with open(DATA_LOG, 'a') as f:
                f.write(json.dumps(capture) + '\n')
        except Exception:
            pass

    except ssl.SSLError as e:
        # Intentar identificar dónde ocurrió el error SSL
        import sys
        tb = sys.exc_info()[2]
        frames = []
        while tb:
            frames.append(tb.tb_frame.f_code.co_name)
            tb = tb.tb_next
        import traceback as tb2
        tb_lines = tb2.format_exception(type(e), e, e.__traceback__)
        ssl_lineno = '?'
        for l in tb_lines:
            if 'mitm.py' in l and ', line ' in l:
                ssl_lineno = l.split('line ')[1].split(',')[0]
                break
        log.error(f"  SSL (line {ssl_lineno}): {e}")
    except socket.timeout:
        log.warning(f"  ⏱ timeout")
    except ConnectionRefusedError:
        log.error(f"  ✗ conexión rechazada")
    except Exception as e:
        log.error(f"  ✗ {type(e).__name__}: {e}")
        for l in traceback.format_exc().split('\n')[:5]:
            log.error(f"    {l}")
    finally:
        try:
            conn.close()
        except:
            pass


# =====================================================================
# LECTURA HTTP helpers
# =====================================================================

def read_http(ssl_obj, sock, bio_in, bio_out):
    """Lee HTTP request completo usando SSLObject + MemoryBIO."""
    # Status line
    line = b''
    while not line.endswith(b'\n'):
        ch = _tls_read(ssl_obj, sock, bio_in, bio_out, 1)
        if not ch:
            return None, None, {}, b''
        line += ch

    first = line.split(b' ')
    method = first[0].decode('utf-8', errors='replace') if len(first) > 0 else None
    path = first[1].decode('utf-8', errors='replace') if len(first) > 1 else None

    # Headers
    head_block = b''
    while b'\r\n\r\n' not in head_block:
        ch = _tls_read(ssl_obj, sock, bio_in, bio_out, 1)
        if not ch:
            break
        head_block += ch

    headers = {}
    for ln in head_block.split(b'\r\n'):
        if b':' in ln:
            k, v = ln.split(b':', 1)
            headers[k.decode().strip().lower()] = v.decode().strip()

    cl = int(headers.get('content-length', 0) or 0)
    body = b''
    while len(body) < cl:
        chunk = _tls_read(ssl_obj, sock, bio_in, bio_out, cl - len(body))
        if not chunk:
            break
        body += chunk

    return method, path, headers, body


def read_http_response(tls_sock):
    """Lee HTTP response de un socket TLS estándar con buffering."""
    buf = b''

    def _fill():
        nonlocal buf
        while True:
            chunk = tls_sock.read(BUF_SIZE)
            if not chunk:
                return
            buf += chunk
            # Leer al menos lo que necesitamos para headers
            if b'\r\n\r\n' in buf:
                return

    def _read_until(marker):
        nonlocal buf
        while marker not in buf:
            chunk = tls_sock.read(BUF_SIZE)
            if not chunk:
                break
            buf += chunk
        idx = buf.find(marker)
        if idx < 0:
            data = buf
            buf = b''
            return data
        end = idx + len(marker)
        data = buf[:end]
        buf = buf[end:]
        return data

    def _read_n(n):
        nonlocal buf
        while len(buf) < n:
            chunk = tls_sock.read(BUF_SIZE)
            if not chunk:
                break
            buf += chunk
        data = buf[:n]
        buf = buf[n:]
        return data

    def _read_all():
        nonlocal buf
        out = buf
        buf = b''
        while True:
            chunk = tls_sock.read(BUF_SIZE)
            if not chunk:
                break
            out += chunk
        return out

    # Status line
    line = _read_until(b'\r\n')
    if not line:
        return None
    status = line.decode('utf-8', errors='replace').strip()

    # Headers
    head_block = _read_until(b'\r\n\r\n')

    headers = {}
    for ln in head_block.split(b'\r\n'):
        if b':' in ln:
            k, v = ln.split(b':', 1)
            headers[k.decode().strip().lower()] = v.decode().strip()

    # Body
    is_chunked = headers.get('transfer-encoding', '').lower() == 'chunked'
    cl = int(headers.get('content-length', 0) or 0)

    body = b''
    if is_chunked:
        while True:
            line = _read_until(b'\r\n')
            if not line:
                break
            try:
                size = int(line.strip(), 16)
            except:
                body += line
                break
            body += line
            if size == 0:
                body += _read_n(2)
                break
            body += _read_n(size + 2)
    elif cl > 0:
        body = _read_n(cl)
    else:
        body = _read_all()

    return status, headers, body


def _tls_read(ssl_obj, sock, bio_in, bio_out, n):
    """Lee datos descifrados del SSLObject, alimentando bio_in desde el socket."""
    try:
        data = ssl_obj.read(n)
        if data:
            return data
    except ssl.SSLWantReadError:
        pass

    # SSL quiere leer más datos cifrados
    data = sock.recv(BUF_SIZE)
    if not data:
        return b''
    bio_in.write(data)

    # Enviar datos de salida SSL
    out = bio_out.read()
    if out:
        sock.sendall(out)

    try:
        return ssl_obj.read(n)
    except ssl.SSLWantReadError:
        return b''


# =====================================================================
# LOGGING helpers
# =====================================================================

def fmt_body(body):
    try:
        s = body.decode('utf-8')
        try:
            s = json.dumps(json.loads(s), indent=2, ensure_ascii=False)
        except:
            pass
        return s[:2000]
    except:
        return f'({len(body)} bytes bin)'


def mask(val):
    return val[:12] + '...' if len(val) > 12 else val


def log_response_content(ct, body, log):
    if 'text/event-stream' in ct:
        for ln in body.decode('utf-8', errors='replace').split('\n'):
            ln = ln.strip()
            if ln.startswith('data: '):
                payload = ln[6:]
                if payload == '[DONE]':
                    log.info(f"      [DONE]")
                else:
                    _log_ai_chunk(payload, log)
    elif 'application/json' in ct:
        try:
            data = json.loads(body)
            if 'choices' in data:
                for c in data['choices']:
                    if 'message' in c:
                        content = c['message'].get('content', '')
                        if content:
                            log.info(f"      ✦ {content[:500]}")
            if 'content' in data:
                for block in data['content']:
                    if isinstance(block, dict) and block.get('text'):
                        log.info(f"      ✦ {block['text'][:500]}")
        except:
            pass


def log_stream_chunk(chunk, log):
    txt = chunk.decode('utf-8', errors='replace')
    for ln in txt.split('\n'):
        ln = ln.strip()
        if ln.startswith('data: '):
            payload = ln[6:]
            if payload == '[DONE]':
                log.info(f"      [DONE]")
            else:
                _log_ai_chunk(payload, log)


def _log_ai_chunk(payload, log):
    try:
        obj = json.loads(payload)
        for c in obj.get('choices', []):
            d = c.get('delta', {})
            content = d.get('content', '')
            if content:
                log.info(f"      ✦ {content}")
    except:
        log.info(f"      data: {payload[:200]}")


# =====================================================================
# MAIN
# =====================================================================

def main():
    for f in [CA_CERT, CA_KEY, SERVER_KEY]:
        if not f.exists():
            log.error(f"Falta: {f}. Ejecuta: bash gen-ca.sh")
            sys.exit(1)

    CERT_CACHE.mkdir(parents=True, exist_ok=True)

    # Resource baseline
    total_mb, used_mb, pct, cpu, ulimit_n = resource_baseline()
    max_th = min(MAX_CONCURRENT, max(1, ulimit_n // 20))
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  MITM Proxy Transparente v3                ║")
    log.info(f"║  RAM: {used_mb}/{total_mb}MB ({pct:.0f}%)")
    log.info(f"║  CPU: {cpu} cores")
    log.info(f"║  FD:  {ulimit_n} (máx {max_th} conexiones)")
    log.info(f"║  Puerto: {LISTEN_PORT}")
    log.info(f"║  Datos: {DATA_LOG}")
    log.info("╚══════════════════════════════════════════════╝")

    # Socket dual-stack: acepta IPv4 e IPv6
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(('::', LISTEN_PORT))
    sock.listen(100)
    sock.settimeout(None)

    while True:
        try:
            client, addr = sock.accept()

            # Check resources each accept
            _, _, ram_pct, _, _ = resource_baseline()
            if ram_pct > RAM_WARN_PCT:
                log.warning(f"⚠ RAM al {ram_pct:.0f}% — reinicia o revisa")

            # Rate limit: acquire semaphore (non-blocking with timeout)
            if not _conn_semaphore.acquire(blocking=True, timeout=0.5):
                log.warning("⏱ Muchas conexiones, descartando")
                client.close()
                continue

            def _wrapper(c, a):
                try:
                    handle(c, a)
                finally:
                    _conn_semaphore.release()

            t = threading.Thread(target=_wrapper, args=(client, addr), daemon=True)
            t.start()
        except Exception as e:
            log.error(f"Accept: {e}")


if __name__ == '__main__':
    if '--install-ca' in sys.argv:
        subprocess.run(['sudo', 'cp', str(CA_CERT),
                       '/usr/local/share/ca-certificates/mitm-ca.crt'])
        subprocess.run(['sudo', 'update-ca-certificates'])
        print("✓ CA instalada en sistema")

    elif '--iptables-add' in sys.argv:
        # === Puerto 443 (tráfico HTTPS directo) ===
        # IPv4
        subprocess.run([
            'sudo', 'iptables', '-t', 'nat', '-A', 'OUTPUT',
            '-p', 'tcp', '--dport', '443',
            '!', '-d', '127.0.0.0/8',
            '-m', 'owner', '!', '--uid-owner', 'root',
            '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
        ])
        # IPv6
        subprocess.run([
            'sudo', 'ip6tables', '-t', 'nat', '-A', 'OUTPUT',
            '-p', 'tcp', '--dport', '443',
            '!', '-d', '::1/128',
            '-m', 'owner', '!', '--uid-owner', 'root',
            '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
        ])
        # === Puerto 8080 (forward proxy CONNECT) ===
        subprocess.run([
            'sudo', 'iptables', '-t', 'nat', '-A', 'OUTPUT',
            '-p', 'tcp', '--dport', '8080',
            '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
        ])
        print("✓ Reglas agregadas: 443 (HTTPS) + 8080 (proxy CONNECT)")

    elif '--iptables-del' in sys.argv:
        # === Puerto 443 ===
        # IPv4
        r = subprocess.run([
            'sudo', 'iptables', '-t', 'nat', '-D', 'OUTPUT',
            '-p', 'tcp', '--dport', '443',
            '!', '-d', '127.0.0.0/8',
            '-m', 'owner', '!', '--uid-owner', 'root',
            '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
        ], capture_output=True)
        if r.returncode != 0:
            subprocess.run([
                'sudo', 'iptables', '-t', 'nat', '-D', 'OUTPUT',
                '-p', 'tcp', '--dport', '443',
                '!', '-d', '127.0.0.0/8',
                '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
            ])
        # IPv6
        r6 = subprocess.run([
            'sudo', 'ip6tables', '-t', 'nat', '-D', 'OUTPUT',
            '-p', 'tcp', '--dport', '443',
            '!', '-d', '::1/128',
            '-m', 'owner', '!', '--uid-owner', 'root',
            '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
        ], capture_output=True)
        if r6.returncode != 0:
            subprocess.run([
                'sudo', 'ip6tables', '-t', 'nat', '-D', 'OUTPUT',
                '-p', 'tcp', '--dport', '443',
                '!', '-d', '::1/128',
                '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
            ])
        # === Puerto 8080 ===
        subprocess.run([
            'sudo', 'iptables', '-t', 'nat', '-D', 'OUTPUT',
            '-p', 'tcp', '--dport', '8080',
            '-j', 'REDIRECT', '--to-port', str(LISTEN_PORT)
        ], capture_output=True)
        print("✓ Reglas eliminadas")

    elif '--iptables-list' in sys.argv:
        print("=== IPv4 nat OUTPUT ===")
        subprocess.run(['sudo', 'iptables', '-t', 'nat', '-L', 'OUTPUT', '-n', '--line-numbers'])
        print("=== IPv6 nat OUTPUT ===")
        subprocess.run(['sudo', 'ip6tables', '-t', 'nat', '-L', 'OUTPUT', '-n', '--line-numbers'])

    else:
        main()
