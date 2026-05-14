#!/usr/bin/env python3
"""
Agent Web — Hub multi-agente con SSH, autenticación, terminal web y botones configurables.

Uso:
  python3 agent_web.py --port 8080 --host 0.0.0.0
"""
import os, json, asyncio, subprocess, argparse, logging, time, hashlib, hmac
import aiohttp.web
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("agent_web")

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "agent_config.json"

# ── Config ─────────────────────────────────────────────────────────────────
def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"web_password":"","connections":[],"agents":[],"buttons":[],"speech":{},"appearance":{}}

def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))

def check_auth(request, cfg: dict) -> bool:
    """Valida token contra web_password."""
    pw = cfg.get("web_password", "")
    if not pw: return True  # sin password = acceso libre
    token = request.headers.get("X-Auth-Token", request.query.get("token", ""))
    return hmac.compare_digest(token, hashlib.sha256(pw.encode()).hexdigest())

# ── SSH / Terminal Session ────────────────────────────────────────────────
async def run_remote(conn: dict, cmd: str, ws, agent_id: str):
    """Ejecuta un comando a través de SSH o local y envía output por WS."""
    cfg = load_config()
    agents_map = {a["id"]: a for a in cfg.get("agents", [])}
    agent = agents_map.get(agent_id, {})
    workdir = agent.get("workdir", str(BASE))
    full_cmd = f"cd {workdir} && {cmd}" if cmd != "clear" else "clear"

    if conn.get("type") == "local":
        proc = await asyncio.create_subprocess_exec(
            "bash", "-c", full_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    else:
        ssh_cmd = ["ssh"]
        if conn.get("key_path"): ssh_cmd += ["-i", conn["key_path"]]
        ssh_cmd += ["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
                    f"{conn['user']}@{conn['host']}", "-p", str(conn.get("port",22)),
                    full_cmd]
        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

    while proc.stdout and not proc.stdout.at_eof():
        line = await proc.stdout.readline()
        if not line: break
        text = line.decode("utf-8", errors="replace")
        if ws and not ws.closed:
            try: await ws.send(json.dumps({"type":"stdout","data":text,"agent":agent_id}))
            except: break

async def spawn_terminal(conn: dict, agent_id: str, ws):
    """Abre una sesión interactiva SSH o local (tmux) y la conecta al WS."""
    cfg = load_config()
    agents_map = {a["id"]: a for a in cfg.get("agents", [])}
    agent = agents_map.get(agent_id, {})
    workdir = agent.get("workdir", str(BASE))
    session_name = f"agent_{agent_id}"

    if conn.get("type") == "local":
        cmd = ["bash", "--norc", "--noprofile"]
        # Try to attach to existing tmux or create new
        tmux_cmd = ["tmux", "new-session", "-A", "-s", session_name,
                    "-c", workdir, "bash"]
        proc = await asyncio.create_subprocess_exec(
            *tmux_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "TERM": "xterm-256color"},
        )
    else:
        ssh_cmd = ["ssh", "-t"]
        if conn.get("key_path"): ssh_cmd += ["-i", conn["key_path"]]
        ssh_cmd += ["-o", "StrictHostKeyChecking=no",
                    f"{conn['user']}@{conn['host']}", "-p", str(conn.get("port",22)),
                    f"cd {workdir} && tmux new-session -A -s {session_name} 2>/dev/null || bash"]
        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

    # Reader
    async def reader():
        while proc.stdout and not proc.stdout.at_eof():
            line = await proc.stdout.readline()
            if not line: break
            text = line.decode("utf-8", errors="replace")
            if ws and not ws.closed:
                try: await ws.send(json.dumps({"type":"stdout","data":text,"agent":agent_id}))
                except: break

    read_task = asyncio.create_task(reader())
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("action") == "stdin" and proc.stdin:
                    proc.stdin.write((data.get("data","") + "\n").encode())
                    await proc.stdin.drain()
                elif data.get("action") == "resize": pass
                elif data.get("action") == "ping":
                    await ws.send(json.dumps({"type":"pong"}))
    finally:
        read_task.cancel()
        if proc: proc.terminate()

# ── Routes ────────────────────────────────────────────────────────────────
async def handle_index(request):
    pw = load_config().get("web_password", "")
    html = (BASE / "agent_web.html").read_text() if (BASE / "agent_web.html").exists() else "<h1>No HTML</h1>"
    return aiohttp.web.Response(text=html, content_type="text/html")

async def handle_auth(request):
    """Verifica contraseña y devuelve token."""
    data = await request.json()
    cfg = load_config()
    pw = cfg.get("web_password", "")
    if not pw: return aiohttp.web.json_response({"token":"open","status":"ok"})
    if hmac.compare_digest(data.get("password",""), pw):
        token = hashlib.sha256(pw.encode()).hexdigest()
        return aiohttp.web.json_response({"token":token,"status":"ok"})
    return aiohttp.web.json_response({"status":"error","msg":"Contraseña incorrecta"}, status=401)

async def handle_config_get(request):
    cfg = load_config()
    if not check_auth(request, cfg):
        return aiohttp.web.json_response({"status":"error","msg":"No autorizado"}, status=401)
    return aiohttp.web.json_response(cfg)

async def handle_config_save(request):
    cfg = load_config()
    if not check_auth(request, cfg):
        return aiohttp.web.json_response({"status":"error","msg":"No autorizado"}, status=401)
    try:
        data = await request.json()
        # Merge con config existente
        existing = load_config()
        # No sobreescribir web_password si no viene
        if "web_password" in data: existing["web_password"] = data["web_password"]
        if "connections" in data: existing["connections"] = data["connections"]
        if "agents" in data: existing["agents"] = data["agents"]
        if "buttons" in data: existing["buttons"] = data["buttons"]
        if "speech" in data: existing["speech"] = data["speech"]
        if "appearance" in data: existing["appearance"] = data["appearance"]
        save_config(existing)
        return aiohttp.web.json_response({"status":"ok"})
    except Exception as e:
        return aiohttp.web.json_response({"status":"error","msg":str(e)}, status=400)

async def handle_ws(request):
    cfg = load_config()
    if not check_auth(request, cfg):
        return aiohttp.web.WebSocketResponse()  # will close

    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)

    agent_id = request.query.get("agent", "default")
    conn_id = request.query.get("connection", "local")
    connections = {c["id"]: c for c in cfg.get("connections", [])}
    conn = connections.get(conn_id, {"type":"local"})

    await spawn_terminal(conn, agent_id, ws)
    return ws

async def handle_exec(request):
    """Ejecuta un comando (para botones) y devuelve output."""
    cfg = load_config()
    if not check_auth(request, cfg):
        return aiohttp.web.json_response({"status":"error","msg":"No autorizado"}, status=401)

    data = await request.json()
    cmd = data.get("command", "")
    connection_id = data.get("connection", "local")
    agent_id = data.get("agent", "")
    connections = {c["id"]: c for c in cfg.get("connections", [])}
    conn = connections.get(connection_id, {"type":"local"})

    # Collect output
    output_lines = []
    class FakeWS:
        async def send(self, msg):
            d = json.loads(msg)
            output_lines.append(d.get("data",""))
        @property
        def closed(self): return False

    fws = FakeWS()
    await run_remote(conn, cmd, fws, agent_id)
    return aiohttp.web.json_response({"output":"".join(output_lines),"status":"ok"})

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    app = aiohttp.web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/auth", handle_auth)
    app.router.add_get("/api/config", handle_config_get)
    app.router.add_post("/api/config", handle_config_save)
    app.router.add_post("/api/exec", handle_exec)
    app.router.add_get("/ws", handle_ws)
    static_dir = BASE / "static"
    static_dir.mkdir(exist_ok=True)
    app.router.add_static("/static/", path=str(static_dir), name="static")

    log.info(f"Agent Web en http://{args.host}:{args.port}")
    aiohttp.web.run_app(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
