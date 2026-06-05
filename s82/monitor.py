#!/usr/bin/env python3
"""monitor.py — Visualizador compacto para móvil (76 chars).

Uso:
  python3 monitor.py              # modo tail (sigue captures.jsonl)
  python3 monitor.py --last 10   # últimas 10 entradas
  python3 monitor.py --stats     # resumen del día
  python3 monitor.py --watch     # refresca cada 2s (para tmux)
"""
import json, sys, time, os, subprocess
from pathlib import Path
from datetime import datetime

DATA_LOG = Path('/home/vuos/code/p3/s82/captures.jsonl')
MAX_W = 76
CACHE = []  # entradas cargadas


# ─── Cargar entradas ─────────────────────────────────

def load(max_lines=200):
    """Carga entradas del JSONL."""
    entries = []
    try:
        with open(DATA_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
    except FileNotFoundError:
        pass
    return entries[-max_lines:]


# ─── Formateo compacto ───────────────────────────────

def fmt_time(t):
    """'2026-06-05T14:23:15' → '14:23:15'"""
    if not t:
        return '??:??:??'
    if 'T' in t:
        return t.split('T')[1][:8]
    return t[-8:]

def short_model(m):
    if not m:
        return '?'
    m = m.replace('deepseek-', 'ds-').replace('claude-', 'cl-')
    m = m.replace('gemini-', 'gm-').replace('gpt-', '')
    return m[:10]

def short_app(app):
    if not app:
        return '?'
    return app.split('.')[0][:8]

def trunc(s, n):
    s = str(s or '')
    s = s.replace('\n', ' ').replace('\r', '')
    return s[:n]

def fmt_entry(e, full=False):
    """Retorna línea de 76 chars (o más si full)."""
    t = fmt_time(e.get('t'))
    app = short_app(e.get('app'))
    model = short_model(e.get('model'))
    prompt = trunc(e.get('prompt', ''), 20)
    resp = trunc(e.get('response', ''), 20)
    tokens = e.get('tokens_out', '')
    cost = e.get('cost', '')

    if not full:
        # Compacto: 8+2+8+2+8+2+20+2+20 = 74
        line = f"{t} {app:<6} {model:<8} {prompt}"
        if resp:
            line += f" → {resp}"
        if tokens:
            line += f" {tokens}t"
        return line[:MAX_W]
    else:
        # Expandido
        lines = [
            f"  {t}  {app} → {e.get('host','')}",
            f"  modelo: {model}",
        ]
        if e.get('method'):
            lines.append(f"  {e['method']} {e.get('path','')}")
        if e.get('status'):
            lines.append(f"  {e['status']}")
        if tokens or cost:
            tok_s = f"in={e.get('tokens_in','?')} out={tokens}"
            cost_s = f" ${cost}" if cost else ''
            lines.append(f"  tokens: {tok_s}{cost_s}")
        if e.get('prompt'):
            lines.append(f"  > {trunc(e['prompt'], 60)}")
        if e.get('response'):
            lines.append(f"  < {trunc(e['response'], 60)}")
        if e.get('bytes'):
            lines.append(f"  ({e['bytes']} bytes)")
        return '\n'.join(lines)


# ─── Display ─────────────────────────────────────────

def show_last(n=15):
    entries = load()
    if not entries:
        print("(sin datos aún)")
        return
    for e in entries[-n:]:
        print(fmt_entry(e))

def show_detail(idx=-1):
    entries = load()
    if not entries:
        return
    e = entries[idx]
    print(fmt_entry(e, full=True))

def show_stats():
    entries = load(5000)
    if not entries:
        print("(sin datos)")
        return
    
    apps = {}
    models = {}
    total_cost = 0.0
    total_tokens = 0
    
    for e in entries:
        app = e.get('app', '?')
        apps[app] = apps.get(app, 0) + 1
        model = e.get('model', '?')
        models[model] = models.get(model, 0) + 1
        try:
            total_cost += float(e.get('cost', 0) or 0)
        except:
            pass
        total_tokens += int(e.get('tokens_out', 0) or 0)
    
    print(f"Total requests: {len(entries)}")
    print(f"Total tokens out: {total_tokens}")
    print(f"Total cost: ${total_cost:.4f}")
    print()
    print("Apps:")
    for app, count in sorted(apps.items(), key=lambda x: -x[1])[:10]:
        print(f"  {app:<20} {count}")
    print()
    print("Modelos:")
    for model, count in sorted(models.items(), key=lambda x: -x[1])[:10]:
        print(f"  {short_model(model):<20} {count}")


def watch(interval=2):
    """Modo watch: refresca cada interval segundos."""
    last_count = 0
    while True:
        entries = load(50)
        count = len(entries)
        os.system('clear')
        print(f"╔{'═'*74}╗")
        print(f"║  MITM  {datetime.now().strftime('%H:%M:%S')}  {count} capturados{' '*(50-len(str(count)))}║")
        print(f"╠{'═'*74}╣")
        for e in entries[-15:]:
            line = fmt_entry(e)
            print(f"║ {line:<74}║")
        print(f"╚{'═'*74}╝")
        print(f"  {DATA_LOG}  |  Ctrl+C salir")
        time.sleep(interval)


# ─── Tail ────────────────────────────────────────────

def tail():
    """Sigue el JSONL como tail -f."""
    if not DATA_LOG.exists():
        print(f"Esperando {DATA_LOG}...")
        while not DATA_LOG.exists():
            time.sleep(1)
    
    with open(DATA_LOG) as f:
        f.seek(0, 2)  # fin
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                if line:
                    try:
                        e = json.loads(line)
                        print(fmt_entry(e))
                    except:
                        pass
            else:
                time.sleep(0.5)


# ─── Main ────────────────────────────────────────────

if __name__ == '__main__':
    if '--stats' in sys.argv:
        show_stats()
    elif '--last' in sys.argv:
        try:
            n = int(sys.argv[sys.argv.index('--last') + 1])
        except:
            n = 10
        show_last(n)
    elif '--watch' in sys.argv:
        watch()
    elif '--detail' in sys.argv:
        show_detail()
    else:
        tail()
