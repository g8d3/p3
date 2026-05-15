#!/usr/bin/env python3
"""
obs-web.py — Panel web táctil para OBS Studio vía WebSocket

Uso:  python3 obs-web.py
Luego abre http://localhost:8080 desde tu navegador (en el celular, la IP de esta máquina)
"""

import asyncio
import json
import os
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote_plus

import simpleobsws

OBS_WS = "ws://127.0.0.1:4455"
OBS_PASS = "SFT16WlCaNoupRwt"


def do_obs(method, data=None):
    """Synchronous wrapper for OBS calls. Creates fresh loop + connection each call."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_do_obs(method, data))
    finally:
        loop.close()


async def _do_obs(method, data=None):
    ws = simpleobsws.WebSocketClient(url=OBS_WS, password=OBS_PASS)
    await ws.connect()
    try:
        await ws.wait_until_identified()
        req = simpleobsws.Request(method, data or {})
        resp = await ws.call(req)
        if not resp.ok():
            return {"error": str(resp.responseData)}
        return resp.responseData or {}
    finally:
        await ws.disconnect()


# ─── HTTP Handler ────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silencioso

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/" or path == "":
            self._send_html(HTML)
        elif path == "/api/scenes":
            try:
                data = do_obs("GetSceneList")
                scenes = data.get("scenes", [])
                current = data.get("currentProgramSceneName", "")
                self._send_json({"scenes": [s["sceneName"] for s in scenes], "current": current})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif path.startswith("/api/sources/"):
            scene = unquote_plus(path.split("/api/sources/")[1])
            try:
                data = do_obs("GetSceneItemList", {"sceneName": scene})
                items = data.get("sceneItems", [])
                srcs = []
                for item in items:
                    srcs.append({
                        "id": item.get("sceneItemId"),
                        "name": item.get("sourceName"),
                        "enabled": item.get("sceneItemEnabled", True),
                        "transform": item.get("sceneItemTransform", {}),
                    })
                self._send_json({"sources": srcs})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        elif path == "/api/status":
            try:
                v = do_obs("GetVersion")
                self._send_json({"connected": True, "version": v.get("obsVersion", "?")})
            except:
                self._send_json({"connected": False})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        try:
            if path == "/api/command":
                method = data.get("method", "")
                params = data.get("params", {})
                result = do_obs(method, params)
                self._send_json(result)

            elif path == "/api/switch-scene":
                result = do_obs("SetCurrentProgramScene", {"sceneName": data["scene"]})
                self._send_json(result)

            elif path == "/api/set-transform":
                result = do_obs("SetSceneItemTransform", {
                    "sceneName": data["scene"],
                    "sceneItemId": data["itemId"],
                    "sceneItemTransform": data["transform"],
                })
                self._send_json(result)

            elif path == "/api/delete-source":
                result = do_obs("RemoveInput", {"inputName": data["name"]})
                self._send_json(result)

            elif path == "/api/move-source":
                result = do_obs("SetSceneItemIndex", {
                    "sceneName": data["scene"],
                    "sceneItemId": data["itemId"],
                    "sceneItemIndex": data["index"],
                })
                self._send_json(result)

            elif path == "/api/toggle-source":
                result = do_obs("SetSceneItemEnabled", {
                    "sceneName": data["scene"],
                    "sceneItemId": data["itemId"],
                    "sceneItemEnabled": data["enabled"],
                })
                self._send_json(result)

            elif path == "/api/screenshot":
                shot = f"/tmp/obs-shot-{int(time.time())}.png"
                r = subprocess.run(["import", "-display", ":99", "-window", "root", shot],
                                   capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    self._send_json({"ok": True, "file": shot})
                else:
                    self._send_json({"error": r.stderr}, 500)

            elif path == "/api/start-recording":
                result = do_obs("StartRecord")
                self._send_json(result)

            elif path == "/api/stop-recording":
                result = do_obs("StopRecord")
                self._send_json(result)

            elif path == "/api/create-scene":
                result = do_obs("CreateScene", {"sceneName": data["name"]})
                self._send_json(result)

            elif path == "/api/delete-scene":
                result = do_obs("RemoveScene", {"sceneName": data["name"]})
                self._send_json(result)

            elif path == "/api/chat":
                msg = data.get("message", "")
                # Try as direct command first
                parts = msg.strip().split(" ", 1)
                if parts[0][0].isupper():
                    method = parts[0]
                    params = {}
                    if len(parts) > 1:
                        try:
                            params = json.loads(parts[1])
                        except:
                            params = {"raw": parts[1]}
                    result = do_obs(method, params)
                    self._send_json({"type": "command", "result": result})
                else:
                    # Call opencode AI
                    try:
                        r = subprocess.run(
                            ["opencode", "run",
                             "You are an OBS WebSocket API assistant. "
                             "The user asks: " + msg + ". "
                             "Respond with ONLY the OBS WebSocket command in format: MethodName {\\\"param\\\":\\\"value\\\"}. "
                             "If unclear, ask for clarification briefly.",
                             "--model", "opencode-go/mimo-v2.5"],
                            capture_output=True, text=True, timeout=15,
                        )
                        reply = r.stdout.strip() or r.stderr.strip() or "(no response)"
                        self._send_json({"type": "ai", "reply": reply[:500]})
                    except Exception as e:
                        self._send_json({"type": "error", "reply": str(e)})
            else:
                self._send_json({"error": "not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)


# ─── HTML Frontend ───────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>OBS Control</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #0f0f23; color: #e0e0e0; padding: 10px; }
h1 { font-size: 18px; margin: 8px 0; text-align: center; color: #7aa2f7; }
.status { text-align: center; font-size: 13px; padding: 6px; border-radius: 8px; margin-bottom: 10px; }
.status.ok { background: #1a3a1a; color: #9ece6a; }
.status.err { background: #3a1a1a; color: #f7768e; }

.section { margin-bottom: 12px; }
.section-title { font-size: 14px; font-weight: 600; color: #a9b1d6; margin-bottom: 6px; padding-left: 2px; }

.btn-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.btn { 
    padding: 12px 16px; border: none; border-radius: 10px; 
    font-size: 15px; font-weight: 500; cursor: pointer; 
    touch-action: manipulation; min-height: 48px;
    display: flex; align-items: center; justify-content: center;
    flex: 1 1 auto; min-width: 60px;
    transition: transform 0.1s, opacity 0.1s;
}
.btn:active { transform: scale(0.96); opacity: 0.8; }

.btn-scene { background: #1a1b2e; color: #c0caf5; border: 1px solid #3b4261; }
.btn-scene.active { background: #3b4261; border-color: #7aa2f7; color: #7aa2f7; font-weight: 700; }

.btn-source { background: #1a1b2e; color: #c0caf5; border: 1px solid #3b4261; width: 100%; justify-content: space-between; }
.btn-source .name { flex: 1; text-align: left; }
.btn-source .badge { font-size: 12px; color: #565f89; }

.btn-action { background: #2f3a5c; color: #c0caf5; border: 1px solid #4a5580; }
.btn-danger { background: #4a1a1a; color: #f7768e; border: 1px solid #6a2a2a; }
.btn-success { background: #1a3a1a; color: #9ece6a; border: 1px solid #2a5a2a; }
.btn-primary { background: #2a3a7a; color: #7aa2f7; border: 1px solid #3a4a9a; }

.transform-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }

.cmd-row { display: flex; gap: 6px; margin-top: 6px; }
.cmd-row input { 
    flex: 1; padding: 12px; border-radius: 10px; border: 1px solid #3b4261; 
    background: #1a1b2e; color: #e0e0e0; font-size: 15px;
}

#chat-box { 
    background: #1a1b2e; border: 1px solid #3b4261; border-radius: 10px; 
    padding: 10px; height: 120px; overflow-y: auto; font-size: 13px; margin-bottom: 6px;
}
.chat-msg { margin-bottom: 4px; }
.chat-ai { color: #9ece6a; }
.chat-cmd { color: #7dcfff; }
.chat-user { color: #c0caf5; }

.source-item { margin-bottom: 4px; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #3b4261; border-radius: 2px; }
</style>
</head>
<body>

<h1>🎬 OBS Control</h1>
<div id="status" class="status err">Conectando...</div>

<div class="section">
    <div class="section-title">📂 Escenas</div>
    <div id="scenes" class="btn-grid"></div>
</div>

<div class="section">
    <div class="section-title">⚡ Acciones rápidas</div>
    <div class="btn-grid">
        <button class="btn btn-action" onclick="api('start-recording')">⏺ Grabar</button>
        <button class="btn btn-action" onclick="api('stop-recording')">⏹ Parar</button>
        <button class="btn btn-action" onclick="doScreenshot()">📷 Captura</button>
    </div>
</div>

<div class="section">
    <div class="section-title">📐 Posición (presets)</div>
    <div class="transform-grid" id="transform-btns">
        <button class="btn btn-primary" onclick="setTransform('center')">🎯 Centrar</button>
        <button class="btn btn-primary" onclick="setTransform('left_half')">◀ Mitad Izq</button>
        <button class="btn btn-primary" onclick="setTransform('right_half')">Mitad Der ▶</button>
        <button class="btn btn-primary" onclick="setTransform('top_half')">▲ Mitad Sup</button>
        <button class="btn btn-primary" onclick="setTransform('bottom_half')">Mitad Inf ▼</button>
        <button class="btn btn-primary" onclick="setTransform('fullscreen')">⛶ Full</button>
        <button class="btn btn-primary" onclick="setTransform('corner_top_left')">Esq Sup-Izq</button>
        <button class="btn btn-primary" onclick="setTransform('corner_top_right')">Esq Sup-Der</button>
        <button class="btn btn-primary" onclick="setTransform('corner_bot_left')">Esq Inf-Izq</button>
    </div>
</div>

<div class="section" id="sources-section" style="display:none">
    <div class="section-title">📹 Fuentes</div>
    <div id="sources"></div>
</div>

<div class="section">
    <div class="section-title">📟 Comando directo</div>
    <div class="cmd-row">
        <input id="cmd-input" placeholder="GetVersion, SetCurrentProgramScene...">
        <button class="btn btn-success" style="flex:0 0 auto;padding:12px 20px" onclick="sendCommand()">▶</button>
    </div>
    <div id="cmd-result" style="font-size:12px;color:#565f89;margin-top:4px"></div>
</div>

<div class="section">
    <div class="section-title">💬 Chat IA</div>
    <div id="chat-box"></div>
    <div class="cmd-row">
        <input id="chat-input" placeholder="centra el título arriba a la derecha">
        <button class="btn btn-primary" style="flex:0 0 auto;padding:12px 20px" onclick="sendChat()">▶</button>
    </div>
</div>

<script>
// ─── State ───
let currentScene = "";
let currentItemId = 0;

const TRANSFORMS = {
    center: {positionX:960, positionY:540, alignment:5},
    left_half: {positionX:320, positionY:540, alignment:5, width:640, height:1080},
    right_half: {positionX:1600, positionY:540, alignment:5, width:640, height:1080},
    top_half: {positionX:960, positionY:270, alignment:5, width:1280, height:540},
    bottom_half: {positionX:960, positionY:810, alignment:5, width:1280, height:540},
    fullscreen: {positionX:0, positionY:0, width:1920, height:1080},
    corner_top_left: {positionX:0, positionY:0, width:640, height:360},
    corner_top_right: {positionX:1280, positionY:0, width:640, height:360},
    corner_bot_left: {positionX:0, positionY:720, width:640, height:360},
    corner_bot_right: {positionX:1280, positionY:720, width:640, height:360},
};

// ─── API ───
async function api(path, data = {}) {
    try {
        const r = await fetch('/api/' + path, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data),
        });
        return await r.json();
    } catch(e) {
        document.getElementById('status').className = 'status err';
        document.getElementById('status').textContent = '❌ Error de conexión';
        return {error: e.message};
    }
}

async function apiGet(path) {
    try {
        const r = await fetch(path);
        return await r.json();
    } catch(e) {
        return {error: e.message};
    }
}

// ─── Scenes ───
async function loadScenes() {
    const data = await apiGet('/api/scenes');
    if (data.error) return;
    const div = document.getElementById('scenes');
    div.innerHTML = '';
    data.scenes.forEach(name => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-scene' + (name === data.current ? ' active' : '');
        btn.textContent = name;
        btn.onclick = () => switchScene(name);
        div.appendChild(btn);
    });
    currentScene = data.current;
}

async function switchScene(name) {
    await api('switch-scene', {scene: name});
    currentScene = name;
    loadScenes();
    loadSources();
}

// ─── Sources ───
async function loadSources() {
    if (!currentScene) return;
    const data = await apiGet('/api/sources/' + encodeURIComponent(currentScene));
    if (data.error || !data.sources) return;
    const div = document.getElementById('sources');
    div.innerHTML = '';
    document.getElementById('sources-section').style.display = 'block';
    data.sources.forEach((src, i) => {
        const item = document.createElement('div');
        item.className = 'source-item';
        const btn = document.createElement('button');
        btn.className = 'btn btn-source';
        btn.innerHTML = `<span class="name">${src.enabled ? '👁' : '🚫'} ${src.name}</span> <span class="badge">#${src.id}</span>`;
        btn.onclick = () => selectSource(src, data.sources);
        item.appendChild(btn);

        // Buttons row
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:4px;margin-top:4px';
        const mkBtn = (text, cls, cb) => {
            const b = document.createElement('button');
            b.className = 'btn ' + cls;
            b.textContent = text;
            b.style.cssText = 'padding:8px 12px;font-size:13px;min-height:36px';
            b.onclick = cb;
            row.appendChild(b);
        };
        mkBtn('⬆', 'btn-action', () => moveSource(src.id, Math.max(0, i-1)));
        mkBtn('⬇', 'btn-action', () => moveSource(src.id, Math.min(data.sources.length-1, i+1)));
        mkBtn(src.enabled ? '🙈' : '👁', 'btn-action', () => toggleSource(src.id, !src.enabled));
        mkBtn('✕', 'btn-danger', () => deleteSource(src.name));
        item.appendChild(row);
        div.appendChild(item);
    });
}

function selectSource(src, all) {
    currentItemId = src.id;
    // Highlight selected
    document.querySelectorAll('.btn-source').forEach(b => b.style.borderColor = '');
    event.currentTarget.style.borderColor = '#7aa2f7';
    document.getElementById('cmd-result').textContent = 
        `Seleccionado: ${src.name} | X:${src.transform?.positionX?.toFixed(0)||'?'} Y:${src.transform?.positionY?.toFixed(0)||'?'}`;
}

function setTransform(name) {
    const t = TRANSFORMS[name];
    if (!t || !currentItemId || !currentScene) return;
    api('set-transform', {scene: currentScene, itemId: currentItemId, transform: t});
    document.getElementById('cmd-result').textContent = `✅ ${name} aplicado`;
    setTimeout(loadSources, 500);
}

async function moveSource(id, newIndex) {
    await api('move-source', {scene: currentScene, itemId: id, index: newIndex});
    loadSources();
}

async function toggleSource(id, enabled) {
    await api('toggle-source', {scene: currentScene, itemId: id, enabled});
    loadSources();
}

async function deleteSource(name) {
    await api('delete-source', {name});
    loadSources();
}

// ─── Quick Actions ───
async function doScreenshot() {
    const r = await api('screenshot');
    document.getElementById('cmd-result').textContent = r.ok ? '📷 Screenshot tomada' : '❌ ' + (r.error || 'error');
}

function sendCommand() {
    const input = document.getElementById('cmd-input');
    const text = input.value.trim();
    if (!text) return;
    const parts = text.split(' ', 1);
    const method = parts[0];
    let params = {};
    if (text.includes('{')) {
        try { params = JSON.parse(text.slice(text.indexOf('{'))); } catch(e) {}
    }
    api('command', {method, params}).then(r => {
        document.getElementById('cmd-result').textContent = '✅ ' + JSON.stringify(r).slice(0, 200);
    });
}

// ─── Chat ───
function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    const box = document.getElementById('chat-box');
    box.innerHTML += `<div class="chat-msg chat-user">🧑: ${msg}</div>`;
    input.value = '';
    box.scrollTop = box.scrollHeight;

    fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg}),
    })
    .then(r => r.json())
    .then(data => {
        if (data.type === 'command') {
            box.innerHTML += `<div class="chat-msg chat-cmd">🤖: Comando ejecutado → ${JSON.stringify(data.result).slice(0,200)}</div>`;
        } else if (data.type === 'ai') {
            box.innerHTML += `<div class="chat-msg chat-ai">🤖: ${data.reply}</div>`;
            // Try to find OBS command in reply and auto-fill it
            const match = data.reply.match(/[A-Z]\w+\s*\{.*\}/);
            if (match) document.getElementById('cmd-input').value = match[0];
        } else {
            box.innerHTML += `<div class="chat-msg chat-ai">❌: ${data.reply || data.error}</div>`;
        }
        box.scrollTop = box.scrollHeight;
    });
}

// ─── Poll status ───
async function poll() {
    try {
        const r = await fetch('/api/status');
        const data = await r.json();
        const s = document.getElementById('status');
        if (data.connected) {
            s.className = 'status ok';
            s.textContent = '● Conectado — OBS ' + (data.version || '');
        } else {
            s.className = 'status err';
            s.textContent = '❌ Desconectado de OBS WebSocket';
        }
    } catch(e) {
        document.getElementById('status').className = 'status err';
        document.getElementById('status').textContent = '❌ Servidor no responde';
    }
}

// ─── Init ───
async function init() {
    await poll();
    await loadScenes();
    if (currentScene) await loadSources();
    setInterval(poll, 3000);
    setInterval(() => { loadScenes(); if(currentScene) loadSources(); }, 5000);
}
init();
</script>
</body>
</html>
"""

# ─── Server ──────────────────────────────────────────────────────

def run():
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print("🌐 OBS Web Panel: http://localhost:8080")
    print("   Desde tu celular: http://100.102.52.59:8080")
    print("   (junto con VNC en 100.102.52.59:5900)")
    print("   Ctrl+C para detener")
    server.serve_forever()


if __name__ == "__main__":
    run()
