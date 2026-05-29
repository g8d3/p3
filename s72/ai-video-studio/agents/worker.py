"""Worker agent — lee tareas de inbox/, las ejecuta via proxy, escribe resultados en outbox/."""

import os, json, time, sys
from urllib.request import Request, urlopen

PROXY_URL = os.environ.get('PROXY_URL', 'http://127.0.0.1:9100')
AGENT_ID = os.environ.get('AGENT_ID', 'worker1')
BASE = os.path.dirname(os.path.abspath(__file__))
INBOX = f'{BASE}/inbox/{AGENT_ID}'
OUTBOX = f'{BASE}/outbox/{AGENT_ID}'
LOG = f'{BASE}/logs/{AGENT_ID}.log'

os.makedirs(INBOX, exist_ok=True)
os.makedirs(OUTBOX, exist_ok=True)

def log(msg):
    with open(LOG, 'a') as f:
        f.write(f'{time.strftime("%H:%M:%S")} {msg}\n')

def call_proxy(prompt: str) -> dict:
    payload = json.dumps({
        'model': 'deepseek-v4-flash',
        'messages': [
            {'role': 'system', 'content': 'Eres un agente de IA auxiliar. Responde directo y conciso.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 2000,
    }).encode()
    req = Request(f'{PROXY_URL}/chat/completions', data=payload, headers={
        'Content-Type': 'application/json',
    })
    r = urlopen(req, timeout=120)
    return json.loads(r.read())

def process_task(task_path: str):
    with open(task_path) as f:
        task = json.load(f)
    task_id = task.get('id', 'unknown')
    prompt = task.get('task', '')
    log(f'inicio {task_id}')

    try:
        resp = call_proxy(prompt)
        content = resp['choices'][0]['message'].get('content', '')
        proxy_meta = resp.get('_proxy', {})
        result = {
            'id': task_id,
            'content': content,
            'proxy': proxy_meta,
            'status': 'done',
        }
    except Exception as e:
        result = {'id': task_id, 'error': str(e), 'status': 'failed'}

    # Escribir resultado
    out_path = f'{OUTBOX}/{task_id}.json'
    with open(out_path, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f'fin {task_id} → {out_path}')
    os.remove(task_path)  # limpiar tarea

# Loop principal
log(f'Worker {AGENT_ID} iniciado. Proxy: {PROXY_URL}')
while True:
    tasks = sorted(os.listdir(INBOX))
    for t in tasks:
        if t.endswith('.json'):
            process_task(f'{INBOX}/{t}')
    time.sleep(2)
