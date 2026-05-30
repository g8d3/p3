"""Auto-genera guiones usando datos de tendencias + proxy LLM.

Flujo:
  1. Fetch trends de GitHub y HuggingFace
  2. Llama al proxy directamente (no worker — esto es automático del sistema)
  3. Guarda en frontend/data/current_script.json
"""

import os, sys, json, time
from urllib.request import Request, urlopen

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from backend.sources import get_all_connectors

PROXY_URL = os.environ.get('PROXY_URL', 'http://127.0.0.1:9100')
DATA_DIR = f'{BASE}/frontend/data'
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_trends() -> str:
    conns = get_all_connectors()
    parts = []
    for name, conn in conns.items():
        if not conn.enabled:
            continue
        try:
            items = conn.fetch()
            if items:
                parts.append(f'=== {name} ===')
                for it in items[:5]:
                    title = it.get('title', '?')
                    desc = str(it.get('description', ''))[:120]
                    parts.append(f'- {title}: {desc}')
        except Exception as e:
            parts.append(f'- {name}: error {e}')
    return '\n'.join(parts) if parts else '(sin datos)'

def call_proxy(prompt: str) -> str:
    payload = json.dumps({
        'model': 'deepseek-v4-flash',
        'messages': [
            {'role': 'system', 'content': 'Eres un creador de contenido para TikTok. Eres directo, conversacional, usas números como dígitos. Máximo 120 palabras.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 2000,
    }).encode()
    req = Request(f'{PROXY_URL}/chat/completions', data=payload,
        headers={'Content-Type': 'application/json'})
    r = urlopen(req, timeout=120)
    resp = json.loads(r.read())
    return resp['choices'][0]['message'].get('content', '')

def generate_script(trends: str) -> str:
    prompt = f'''Genera un guión de TikTok de 30-40 segundos basado en estos datos de tendencias de IA.
Usa números como dígitos (16% no "dieciséis por ciento").
Sé conversacional, directo. Sin introducciones ni despedidas largas.

Datos de tendencias:
{trends[:3000]}'''
    return call_proxy(prompt)

if __name__ == '__main__':
    print('Fetching trends...')
    trends = fetch_trends()
    print(f'  {len(trends)} chars de tendencias')

    print('Generating script via proxy...')
    script = generate_script(trends)

    output = {
        'script': script,
        'trends_sources': [k for k in ['github','huggingface']],
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'char_count': len(script),
    }
    path = f'{DATA_DIR}/current_script.json'
    with open(path, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'✅ Guión guardado en {path}')
    print(f'')
    print(f'{script}')
