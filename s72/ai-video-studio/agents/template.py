import os, json, http.server, time
from urllib.request import Request, urlopen

API_KEY = os.environ.get('OPENCODE_GO_API_KEY', '')
MODEL = os.environ.get('AGENT_MODEL', 'deepseek-v4-flash')
API_URL = 'https://opencode.ai/zen/go/v1/chat/completions'

def call_llm(prompt: str) -> dict:
    payload = json.dumps({
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': 'Eres un agente de IA. Responde directamente sin razonamiento interno. Da la respuesta completa y concisa.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 2000,
    }).encode()
    t0 = time.time()
    req = Request(API_URL, data=payload, headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'User-Agent': 'agent-crush/1.0',
    })
    r = urlopen(req, timeout=120)
    t1 = time.time()
    resp = json.loads(r.read())
    usage = resp.get('usage', {})
    return {
        'content': resp['choices'][0]['message'].get('content', ''),
        'reasoning': resp['choices'][0]['message'].get('reasoning_content', '')[:300],
        'prompt_tokens': usage.get('prompt_tokens', 0),
        'completion_tokens': usage.get('completion_tokens', 0),
        'total_tokens': usage.get('total_tokens', 0),
        'time_s': round(t1 - t0, 2),
        'tps': round(usage.get('completion_tokens', 0) / (t1 - t0), 1) if (t1 - t0) > 0 else 0,
    }

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        data = json.loads(body)
        result = call_llm(data.get('task', ''))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'model': MODEL}).encode())
    def log_message(self, format, *args): pass

PORT = int(os.environ.get('AGENT_PORT', '9101'))
http.server.HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
