#!/usr/bin/env python3
"""
proxymon.py — MITM proxy con soporte de streaming.
Intercepta tráfico HTTPS de crush y muestra requests/responses en claro.
"""

import ssl, socket, threading, logging, sys, os, json, traceback
from datetime import datetime

# ─── Config ──────────────────────────────────────────
LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 8443
UPSTREAM_HOST = 'opencode.ai'
UPSTREAM_PORT = 443
BASE = '/home/vuos/code/p3/s82'
CA_CERT = f'{BASE}/certs/ca.crt'
CA_KEY = f'{BASE}/certs/ca.key'
SERVER_CERT = f'{BASE}/certs/server.crt'
SERVER_KEY = f'{BASE}/certs/server.key'
LOG_FILE = '/tmp/proxymon.log'
SOCK_TIMEOUT = 15

# ─── Logging ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger()

# ─── TLS ─────────────────────────────────────────────
def make_server_ctx():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(SERVER_CERT, SERVER_KEY)
    ctx.set_alpn_protocols(['http/1.1'])
    return ctx

def make_client_ctx():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_default_certs()
    ctx.set_alpn_protocols(['http/1.1'])
    return ctx

# ─── HTTP helpers ────────────────────────────────────
def recv_line(sock):
    """Lee una línea (hasta \\n)."""
    data = b''
    while not data.endswith(b'\n'):
        ch = sock.recv(1)
        if not ch:
            break
        data += ch
    return data

def recv_headers(sock):
    """Lee headers HTTP hasta \\r\\n\\r\\n."""
    data = b''
    while b'\r\n\r\n' not in data:
        data += recv_line(sock)
        if not data:
            break
    head, sep, _ = data.partition(b'\r\n\r\n')
    return head + sep

def recv_n(sock, n):
    """Lee exactamente n bytes."""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data

def parse_request(data):
    """Parsea HTTP request: (method, path, dict_headers, body_bytes)."""
    head, sep, body = data.partition(b'\r\n\r\n')
    lines = head.split(b'\r\n')
    first = lines[0].split(b' ')
    if len(first) < 2:
        return None, None, {}, b''
    method = first[0].decode('utf-8', errors='replace')
    path = first[1].decode('utf-8', errors='replace')
    headers = {}
    for line in lines[1:]:
        if b':' in line:
            k, v = line.split(b':', 1)
            headers[k.decode('utf-8', errors='replace').strip().lower()] = \
                v.decode('utf-8', errors='replace').strip()
    return method, path, headers, body

# ─── Logging formatters ──────────────────────────────
def trunc_json(s, maxlen=3000):
    if len(s) <= maxlen:
        return s
    return s[:maxlen] + f'\n    ... (truncado, {len(s)} bytes totales)'

def format_body(body):
    try:
        s = body.decode('utf-8')
        try:
            s = json.dumps(json.loads(s), indent=2, ensure_ascii=False)
        except:
            pass
        return trunc_json(s)
    except:
        return f'({len(body)} bytes binarios)'

def mask_auth(val):
    return val[:15] + '...' if len(val) > 15 else val

# ─── Handler ─────────────────────────────────────────
def handle(conn, addr):
    log.info(f"\n🔗 {addr[0]}:{addr[1]}")
    conn.settimeout(SOCK_TIMEOUT)

    try:
        # 1. Leer request HTTP completa
        raw = b''
        while b'\r\n\r\n' not in raw:
            chunk = conn.recv(65536)
            if not chunk:
                log.warning("  (sin datos)")
                return
            raw += chunk

        method, path, headers, body_rest = parse_request(raw)
        if not method:
            log.warning("  (request inválido)")
            return

        # Leer body si content-length indica más datos
        cl = int(headers.get('content-length', 0))
        body = body_rest
        if cl > len(body):
            body += recv_n(conn, cl - len(body))

        # Mostrar request
        log.info(f">>> {method} {path}")
        for h in ['content-type', 'authorization', 'user-agent']:
            if h in headers:
                v = mask_auth(headers[h]) if h == 'authorization' else headers[h]
                log.info(f"    {h}: {v}")
        if body:
            log.info(f"    Body ({len(body)} bytes):\n{format_body(body)}")

        # 2. Conectar al upstream
        log.info("    → upstream...")
        up = socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT), timeout=SOCK_TIMEOUT)
        up_tls = make_client_ctx().wrap_socket(up, server_hostname=UPSTREAM_HOST)
        up_tls.settimeout(SOCK_TIMEOUT)
        log.info("    ✓ conectado")

        # 3. Reconstruir request para upstream
        new_hdrs = {k: v for k, v in headers.items() if k != 'host'}
        new_hdrs['Host'] = UPSTREAM_HOST
        new_hdrs['Accept-Encoding'] = 'identity'  # nada de compresión
        req = f"{method} {path} HTTP/1.1\r\n".encode()
        for k, v in new_hdrs.items():
            req += f"{k}: {v}\r\n".encode()
        req += b'\r\n' + body

        up_tls.sendall(req)

        # 4. Leer response headers del upstream
        resp_head = b''
        while b'\r\n\r\n' not in resp_head:
            chunk = up_tls.recv(65536)
            if not chunk:
                break
            resp_head += chunk

        hp, _, rest = resp_head.partition(b'\r\n\r\n')
        rlines = hp.split(b'\r\n')
        status = rlines[0].decode('utf-8', errors='replace')
        rhdrs = {}
        for line in rlines[1:]:
            if b':' in line:
                k, v = line.split(b':', 1)
                rhdrs[k.decode('utf-8', errors='replace').strip().lower()] = \
                    v.decode('utf-8', errors='replace').strip()
        is_stream = rhdrs.get('content-type', '').startswith('text/event-stream')
        is_chunked = rhdrs.get('transfer-encoding', '').lower() == 'chunked'

        log.info(f"<<< {status}")
        for h in ['content-type', 'content-length']:
            if h in rhdrs:
                log.info(f"    {h}: {rhdrs[h]}")

        # 5. Reenviar response headers
        conn.sendall(hp + b'\r\n\r\n')

        # 6. Reenviar body con logging
        def forward(start_data):
            nonlocal rest
            buf = start_data
            if rest:
                buf = rest
                rest = b''
            
            if is_chunked:
                # Ya empezamos con `rest` que puede contener parte del chunk
                # Stream chunked
                buffer = buf
                while True:
                    # Buscar \r\n en el buffer
                    if b'\r\n' not in buffer:
                        chunk = up_tls.recv(65536)
                        if not chunk:
                            break
                        buffer += chunk
                    line, sep, buffer = buffer.partition(b'\r\n')
                    if not line:
                        continue
                    try:
                        size = int(line.strip(), 16)
                    except:
                        break
                    conn.sendall(line + b'\r\n')
                    if size == 0:
                        conn.sendall(b'\r\n')
                        break
                    # Leer chunk data + \r\n
                    need = size + 2
                    while len(buffer) < need:
                        chunk = up_tls.recv(65536)
                        if not chunk:
                            break
                        buffer += chunk
                    data = buffer[:size]
                    conn.sendall(buffer[:need])
                    buffer = buffer[need:]
                    if is_stream:
                        try:
                            txt = data.decode('utf-8', errors='replace')
                            for ln in txt.split('\n'):
                                ln = ln.strip()
                                if ln.startswith('data: ') and ln != 'data: [DONE]':
                                    payload = ln[6:]
                                    try:
                                        obj = json.loads(payload)
                                        for c in obj.get('choices', []):
                                            d = c.get('delta', {})
                                            content = d.get('content', '')
                                            if content:
                                                log.info(f"    ✦ {content}")
                                    except:
                                        log.info(f"    data: {payload[:200]}")
                                elif ln == 'data: [DONE]':
                                    log.info("    [DONE]")
                        except:
                            pass
            else:
                # No chunked - leer content-length o hasta cerrar
                cl_resp = int(rhdrs.get('content-length', 0))
                if cl_resp > 0:
                    remaining = cl_resp - len(buf)
                    while remaining > 0:
                        chunk = up_tls.recv(min(65536, remaining))
                        if not chunk:
                            break
                        conn.sendall(chunk)
                        remaining -= len(chunk)

        forward(rest)

        # Seguir leyendo chunks hasta cerrar (para chunked incompleto)
        if is_chunked:
            while True:
                try:
                    chunk = up_tls.recv(65536)
                    if not chunk:
                        break
                    # Buscar chunks en el buffer (simplificado)
                    conn.sendall(chunk)
                    if is_stream:
                        try:
                            txt = chunk.decode('utf-8', errors='replace')
                            for ln in txt.split('\n'):
                                ln = ln.strip()
                                if ln.startswith('data: ') and ln != 'data: [DONE]':
                                    log.info(f"    ✦ {ln[6:][:200]}")
                        except:
                            pass
                except socket.timeout:
                    break

        up_tls.close()
        log.info("    ✓ completo")

    except ssl.SSLError as e:
        log.error(f"SSL: {e}")
    except socket.timeout:
        log.warning("    ⏱ timeout")
    except ConnectionRefusedError:
        log.error(f"    ✗ conexión rechazada a {UPSTREAM_HOST}:{UPSTREAM_PORT}")
    except Exception as e:
        log.error(f"    ✗ {type(e).__name__}: {e}")
        for line in traceback.format_exc().split('\n')[:5]:
            log.error(f"      {line}")
    finally:
        try:
            conn.close()
        except:
            pass

# ─── Main ────────────────────────────────────────────
def main():
    for f in [CA_CERT, CA_KEY, SERVER_CERT, SERVER_KEY]:
        if not os.path.exists(f):
            log.error(f"Falta: {f}. Ejecuta ./setup-mon.sh")
            sys.exit(1)

    ctx = make_server_ctx()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    sock.listen(10)
    sock.settimeout(None)  # bloqueante

    log.info(f"🚀 Proxy en https://{LISTEN_HOST}:{LISTEN_PORT}")
    log.info(f"    → {UPSTREAM_HOST}:{UPSTREAM_PORT}")
    log.info(f"    → log: {LOG_FILE}")
    log.info(f"")
    log.info(f"SSL_CERT_FILE={CA_CERT} \\")
    log.info(f"OPENCODE_GO_BASE_URL=https://{LISTEN_HOST}:{LISTEN_PORT}/zen/go/v1/ \\")
    log.info("─" * 60)

    while True:
        try:
            client, addr = sock.accept()
            tls = ctx.wrap_socket(client, server_side=True)
            t = threading.Thread(target=handle, args=(tls, addr), daemon=True)
            t.start()
        except ssl.SSLError as e:
            log.error(f"SSL handshake: {e}")
            try: client.close()
            except: pass
        except Exception as e:
            log.error(f"Accept: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    main()
