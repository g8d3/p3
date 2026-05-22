#!/usr/bin/env python3
"""
Servidor unificado: sirve la PWA y reenvía llamadas API a opencode serve.

Un solo comando, un solo puerto, sin CORS, sin SSH tunnels.

Uso:
  python3 server.py                    # usa defaults: :8080 → opencode :4096
  python3 server.py --port 80          # cambia el puerto web
  python3 server.py --oc-port 4097     # opencode está en otro puerto
  python3 server.py --oc-host 10.0.0.5 # opencode en otra máquina
"""
import os, sys, json, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── config ──
WEB_PORT    = int(os.environ.get("PORT", "8080"))
OC_HOST     = os.environ.get("OC_HOST", "127.0.0.1")
OC_PORT     = int(os.environ.get("OC_PORT", "4096"))
OC_PASSWORD = os.environ.get("OPENCODE_SERVER_PASSWORD", "")
STATIC_DIR  = os.path.dirname(os.path.abspath(__file__))

def log(m):
    print(f"[oc-mobile] {m}", flush=True)

# ── proxy handler ──

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PATCH(self):
        self.route("PATCH")

    def do_DELETE(self):
        self.route("DELETE")

    def route(self, method):
        path = self.path

        # Static files (PWA)
        if path == "/" or path.startswith("/index.html") or path.startswith("/manifest.json") or path.startswith("/sw.js"):
            self.serve_static(path)
            return

        # Everything else → proxy to opencode serve
        self.proxy(method, path)

    def serve_static(self, path):
        if path == "/":
            path = "/index.html"
        filepath = STATIC_DIR + path
        if not os.path.isfile(filepath):
            self.send_error(404, "Not found")
            return
        ext = os.path.splitext(filepath)[1]
        ctype, _ = mimetypes.guess_type(filepath)
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def proxy(self, method, path):
        """Reenvía la petición a opencode serve y devuelve la respuesta."""
        target = f"http://{OC_HOST}:{OC_PORT}{path}"

        try:
            # Leer body si existe
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else None

            # Construir request
            req = Request(target, data=body, method=method)
            # Reenviar headers relevantes
            for h in ["Content-Type", "Accept"]:
                v = self.headers.get(h)
                if v:
                    req.add_header(h, v)

            # Inyectar auth automáticamente si está configurada
            auth = self.headers.get("Authorization")
            if not auth and OC_PASSWORD:
                import base64
                auth = "Basic " + base64.b64encode(b"opencode:" + OC_PASSWORD.encode()).decode()
            if auth:
                req.add_header("Authorization", auth)
            elif OC_PASSWORD:
                log(f"⚠️  OPENCODE_SERVER_PASSWORD configurada pero cliente no envió auth")

            log(f"{method} {path}")
            resp = urlopen(req, timeout=120)
            data = resp.read()
            self._send_response(resp.status, data, dict(resp.headers))

        except URLError as e:
            log(f"Proxy error: {e}")
            # HTTPError (4xx/5xx) — reenviar tal cual
            if hasattr(e, 'code') and hasattr(e, 'read'):
                data = e.read()
                self._send_response(e.code, data, dict(e.headers))
            elif hasattr(e, 'reason') and 'refused' in str(e.reason):
                self.send_error(502, f"opencode serve no está corriendo en {OC_HOST}:{OC_PORT}")
            else:
                self.send_error(502, f"Error del proxy: {e}")
        except Exception as e:
            log(f"Proxy error: {e}")
            self.send_error(502, f"Error del proxy: {e}")

    def _send_response(self, status, data, headers):
        self.send_response(status)
        ct = headers.get("Content-Type")
        if ct:
            self.send_header("Content-Type", ct)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, fmt, *args):
        # Silenciar logs de HTTP server
        pass

# ── HTTPS support ──

def ensure_cert(cert_path, key_path):
    """Genera certificado autofirmado si no existe."""
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return True
    # Intentar con openssl
    import subprocess, tempfile
    if not os.path.exists(os.path.dirname(cert_path)):
        os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    try:
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", key_path,
            "-out", cert_path,
            "-days", "3650",
            "-nodes",
            "-subj", "/CN=opencode-mobile/O=opencode/C=ES",
        ], check=True, capture_output=True)
        log(f"   Certificado autofirmado generado: {cert_path}")
        return True
    except FileNotFoundError:
        log("   ⚠️  openssl no encontrado. Instálalo o genera el cert manualmente:")
        log(f"      openssl req -x509 -newkey rsa:2048 -keyout {key_path} -out {cert_path} -days 365 -nodes -subj '/CN=opencode'")
        return False
    except subprocess.CalledProcessError:
        return False

def run_server(use_https, cert_file, key_file):
    if use_https:
        import ssl
        if not ensure_cert(cert_file, key_file):
            log("   ❌ No se pudo generar el certificado. Usando HTTP...")
            use_https = False

    if use_https:
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        server = HTTPServer(("0.0.0.0", WEB_PORT), Handler)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        proto = "https"
    else:
        server = HTTPServer(("0.0.0.0", WEB_PORT), Handler)
        proto = "http"

    log(f"✅ Servidor listo")
    log(f"   PWA:      {proto}://0.0.0.0:{WEB_PORT}")
    log(f"   API proxy → http://{OC_HOST}:{OC_PORT}")
    log(f"   Abre desde tu celular: {proto}://<IP-DEL-SERVIDOR>:{WEB_PORT}")
    if use_https:
        log(f"   ⚠️  Certificado autofirmado — el navegador mostrará advertencia,")
        log(f"       pero el micrófono funcionará. Dale en 'Avanzado → Continuar'.")
    log("")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Apagando…")
        server.server_close()

# ── main ──

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Servidor unificado opencode-mobile")
    parser.add_argument("--port", type=int, default=WEB_PORT, help="Puerto web (default: 8080)")
    parser.add_argument("--oc-host", default=OC_HOST, help="Host de opencode serve (default: 127.0.0.1)")
    parser.add_argument("--oc-port", type=int, default=OC_PORT, help="Puerto de opencode serve (default: 4096)")
    parser.add_argument("--https", action="store_true", help="Usar HTTPS (genera cert autofirmado)")
    parser.add_argument("--cert", default="cert.pem", help="Ruta al certificado (default: cert.pem)")
    parser.add_argument("--key", default="key.pem", help="Ruta a la clave privada (default: key.pem)")
    args = parser.parse_args()

    WEB_PORT = args.port
    OC_HOST = args.oc_host
    OC_PORT = args.oc_port
    CERT_FILE = os.path.join(STATIC_DIR, args.cert)
    KEY_FILE = os.path.join(STATIC_DIR, args.key)

    if not OC_PASSWORD:
        log("⚠️  OPENCODE_SERVER_PASSWORD no está configurada")
        log("   El servidor funcionará pero opencode requiere autenticación")
        log("   Exporta la variable: export OPENCODE_SERVER_PASSWORD='tu-clave'")

    run_server(args.https, CERT_FILE, KEY_FILE)