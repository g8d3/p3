"""TPS Proxy — mide tokens/segundo en tiempo real.

Se interpone entre los agentes y la API de opencode.ai.
Registra tiempo, tokens, y expone métricas vía /stats.
"""

import os, json, time, http.server
from urllib.request import Request, urlopen
from collections import deque

API_KEY = os.environ.get('OPENCODE_GO_API_KEY', '')
API_URL = 'https://opencode.ai/zen/go/v1/chat/completions'
PORT = int(os.environ.get('PROXY_PORT', '9100'))

# Ventana móvil de últimos 60s para TPS
window = deque()  # cada entrada: (timestamp, completion_tokens)

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        client_req = json.loads(body)

        # Reenviar a opencode.ai
        t0 = time.time()
        req = Request(API_URL, data=body, headers={
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json',
            'User-Agent': 'tps-proxy/1.0',
        })
        r = urlopen(req, timeout=120)
        t1 = time.time()
        resp = json.loads(r.read())

        # Medir
        usage = resp.get('usage', {})
        prompt_tok = usage.get('prompt_tokens', 0)
        completion_tok = usage.get('completion_tokens', 0)
        elapsed = round(t1 - t0, 3)

        # Registrar en ventana móvil
        now = time.time()
        window.append((now, completion_tok))
        # Podar entradas > 60s
        while window and window[0][0] < now - 60:
            window.popleft()

        # Calcular TPS
        total_tok = sum(w[1] for w in window)
        tps = round(total_tok / 60, 1) if len(window) > 1 else round(completion_tok / elapsed, 1)

        # Agregar métricas a la respuesta (sin modificar la original)
        resp['_proxy'] = {
            'elapsed_s': elapsed,
            'tps_60s': tps,
            'window_samples': len(window),
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())

    def do_GET(self):
        if self.path == '/stats':
            now = time.time()
            while window and window[0][0] < now - 60:
                window.popleft()
            total_tok = sum(w[1] for w in window)
            tps = round(total_tok / 60, 1) if window else 0
            stats = {
                'tps_60s': tps,
                'tokens_60s': total_tok,
                'samples_60s': len(window),
                'agents_connected': len(agents),
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # silencioso

agents = {}  # registro de agentes que usan el proxy

if __name__ == '__main__':
    print(f'Proxy TPS en puerto {PORT} → {API_URL}')
    http.server.HTTPServer(('127.0.0.1', PORT), ProxyHandler).serve_forever()
