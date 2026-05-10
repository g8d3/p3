#!/usr/bin/env python3
"""
Monitor en vivo para el dashboard web.
Captura el output de los panes tmux + reportes JSON
y escribe reportes/live.json cada 2 segundos.
"""
import json
import os
import subprocess
import time
import re
from datetime import datetime

# Detectar sesión tmux actual y proyecto
SESION = os.environ.get("TMUX_SESSION", "")
if not SESION:
    # Intentar detectar la sesión actual
    sesion_out = subprocess.run(
        ["tmux", "display-message", "-p", "#S"],
        capture_output=True, text=True, timeout=3
    )
    SESION = sesion_out.stdout.strip() if sesion_out.returncode == 0 else "video"

PROJECT_DIR = os.getcwd()
REPORTES_DIR = os.path.join(PROJECT_DIR, "reportes")
LIVE_FILE = os.path.join(REPORTES_DIR, "live.json")

# Agentes predefinidos + el orquestador (esta instancia de pi)
AGENTES = [
    {"ventana": 0, "nombre": "Orquestador", "icono": "🎮", "archivo": None},  # Esta instancia de pi
    {"ventana": 1, "nombre": "Director", "icono": "🎬", "archivo": "director.json"},
    {"ventana": 2, "nombre": "GrupoA-Remotion", "icono": "🎞️", "archivo": "remotion.json"},
    {"ventana": 3, "nombre": "GrupoB-AI", "icono": "🤖", "archivo": "aigen.json"},
    {"ventana": 4, "nombre": "GrupoC-Audio", "icono": "🔊", "archivo": "audio.json"},
    {"ventana": 5, "nombre": "GrupoD-Shorts", "icono": "⚡", "archivo": "shorts.json"},
    {"ventana": 6, "nombre": "GrupoE-Editor", "icono": "✂️", "archivo": "editor.json"},
    {"ventana": 7, "nombre": "Quality", "icono": "✅", "archivo": "quality.json"},
]

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return r.stdout
    except:
        return ""

def capture_tmux_pane(ventana, lines=15):
    """Captura las últimas N líneas de un panel tmux"""
    out = run_cmd(f"tmux capture-pane -t {SESION}:{ventana} -p -S -{lines} 2>/dev/null")
    return out.split('\n') if out else []

def get_window_name(ventana):
    return run_cmd(f"tmux display-message -t {SESION}:{ventana} -p '#W' 2>/dev/null").strip()

def get_context_bar(ventana):
    """Extrae la barra de contexto de pi (tokens, costo, etc)"""
    out = run_cmd(f"tmux capture-pane -t {SESION}:{ventana} -p 2>/dev/null")
    # Buscar la barra de estado tipo: ↑3.6k ↓833 R7.7k $0.001 0.6%/1.0M
    for line in out.split('\n'):
        m = re.search(r'(↑[\d.]+k.*?R[\d.]+k.*?\$[\d.]+.*?\d+%?/[\d.]+M)', line)
        if m:
            return m.group(1)
    return ""

def extract_actions(lines):
    """Extrae acciones relevantes (comandos, herramientas, resultados)"""
    actions = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('─') or line == '~':
            continue
        # Detectar tipo de línea
        tipo = "info"
        if re.search(r'(error|fallo|fracas|failed|error)', line, re.I):
            tipo = "error"
        elif re.search(r'(completado|listo|terminado|hecho|✅|done|complete|success)', line, re.I):
            tipo = "done"
        elif re.search(r'(bash|read|write|edit|tool|herramienta|ejecutando|generando|creando|renderizando|analizando|buscando|instalando|descargando)', line, re.I):
            tipo = "action"
        elif re.search(r'(thinking|pensando|analizando|considerando)', line, re.I):
            tipo = "thinking"
        actions.append({"text": line[:120], "tipo": tipo})
    return actions[-10:]  # últimas 10

def load_report(archivo):
    path = os.path.join(REPORTES_DIR, archivo)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except:
            return None
    return None

def check_file(path):
    """Verifica si un archivo existe"""
    full = os.path.join(PROJECT_DIR, path)
    return os.path.exists(full)

def count_renders():
    renders_dir = os.path.join(PROJECT_DIR, "output/renders")
    if os.path.isdir(renders_dir):
        return len([f for f in os.listdir(renders_dir) if f.endswith(('.mp4', '.wav'))])
    return 0

def build_live():
    live = {
        "timestamp": datetime.now().isoformat(),
        "timestamp_human": datetime.now().strftime("%H:%M:%S"),
        "agentes": [],
        "archivos": {
            "escenas_yaml": check_file("templates/escenas.yaml"),
            "final_mp4": check_file("output/final.mp4"),
            "renders": count_renders()
        },
        "tareas_recientes": []
    }
    
    all_tasks = []
    
    for ag in AGENTES:
        ventana = ag["ventana"]
        nombre = ag["nombre"]
        
        # Capturar tmux
        pane_lines = capture_tmux_pane(ventana)
        context = get_context_bar(ventana)
        actions = extract_actions(pane_lines)
        
        # Cargar reporte (si tiene archivo)
        report = load_report(ag["archivo"]) if ag.get("archivo") else None
        
        # Determinar estado REAL del agente
        # 1. ocioso = pi abierto, chat vacío, esperando mensaje (0 tokens)
        # 2. trabajando = pi procesando (thinking/tool calls activas)
        # 3. completado = reporte escrito y sin actividad
        # 4. esperando = pi no ha arrancado aún
        
        tiene_reporte = report is not None
        tiene_contexto = bool(context)
        
        # Detectar actividad en tiempo real
        # Buscar spinners de pi (indicadores de que está pensando/trabajando)
        texto_pane = '\n'.join(pane_lines) if pane_lines else ''
        spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏', 'Thinking', 'Working']
        tiene_spinner = any(s in texto_pane for s in spinners)
        
        # Buscar indicadores de tool calls activas
        tiene_tool_call = any('tool_execution' in l or 'bash' in l.lower() or 'read' in l.lower() for l in pane_lines)
        
        # Buscar si el chat está vacío (pantalla de editor de pi)
        # Señal: líneas de separador '─' seguidas de '~' y el prompt
        chat_vacio = False
        ultimas_5 = '\n'.join(pane_lines[-5:] if pane_lines else [])
        if '────────────────────' in ultimas_5 and '~' in ultimas_5:
            chat_vacio = True
        # Si no hay actividades ni spinners, probablemente está ocioso
        if tiene_contexto and not tiene_spinner and not tiene_tool_call:
            # Pero solo si no hay acciones recientes relevantes
            tiene_acciones_recientes = len(actions) > 0 and any(a['tipo'] in ('action', 'thinking') for a in actions)
            if not tiene_acciones_recientes:
                chat_vacio = True
        
        if tiene_reporte and not tiene_spinner and not tiene_tool_call:
            estado = "completado"
        elif chat_vacio:
            estado = "ocioso"
        elif tiene_spinner or tiene_tool_call:
            estado = "trabajando"
        elif tiene_contexto:
            estado = "ocioso"
        else:
            estado = "esperando"
        
        resumen = report.get("resumen", "") if report else ""
        metricas = report.get("metricas", {}) if report else {}
        variaciones = report.get("variaciones", []) if report else []
        resultados = report.get("resultados", []) if report else []
        
        # Extraer última tarea
        ultima_tarea = ""
        duracion_ultima = ""
        if actions:
            ultima_tarea = actions[-1]["text"]
        if report:
            ultima_tarea = report.get("resumen", ultima_tarea)
        
        agente_data = {
            "ventana": ventana,
            "nombre": nombre,
            "icono": ag["icono"],
            "estado": estado,
            "contexto": context,
            "resumen": resumen,
            "ultima_tarea": ultima_tarea,
            "acciones": actions,
            "variaciones": len(variaciones),
            "errores": len(report.get("errores", [])) if report else 0,
            "metricas": metricas
        }
        live["agentes"].append(agente_data)
        
        # Tareas recientes desde las acciones
        for i, act in enumerate(actions):
            all_tasks.append({
                "tarea": act["text"],
                "agente": nombre,
                "tipo": act["tipo"],
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "orden": len(all_tasks) + i
            })
    
    # Ordenar tareas por orden inverso (más recientes primero)
    all_tasks.reverse()
    live["tareas_recientes"] = all_tasks[:50]  # últimas 50
    
    return live

def main():
    os.makedirs(REPORTES_DIR, exist_ok=True)
    print(f"📡 Monitor en vivo iniciado → {LIVE_FILE}")
    print("   Ctrl+C para detener")
    
    while True:
        try:
            live = build_live()
            with open(LIVE_FILE, 'w') as f:
                json.dump(live, f, indent=2, ensure_ascii=False)
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n⏹️  Monitor detenido")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
