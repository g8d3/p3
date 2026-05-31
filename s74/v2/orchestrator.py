#!/usr/bin/env python3
"""s74/v2 — Orquestador mínimo. Sirve API + archivos. Versiones contienen el UI completo."""

import asyncio, json, mimetypes, os, re, shutil, sqlite3, subprocess, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path

mimetypes.add_type("text/html", ".html")

HOST, PORT = "0.0.0.0", 9879
DIR = Path(__file__).parent
DATA_DIR = DIR / "data"
VERSIONS_DIR = DIR / "versions"
LEDGER = DATA_DIR / "state.db"
AGENT = DIR / "agent.py"
BASE = VERSIONS_DIR / "base"

API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
API_BASE = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")

def now(): return datetime.now(timezone.utc).isoformat()
def vp(n): return VERSIONS_DIR / n
def live(): return (VERSIONS_DIR/"live").resolve() if (VERSIONS_DIR/"live").exists() else BASE

# ── DB ────────────────────────────────────────────────────────────

DB = None
def db():
    global DB
    if not DB:
        os.makedirs(str(LEDGER.parent), exist_ok=True)
        DB = sqlite3.connect(str(LEDGER), check_same_thread=False)
        DB.row_factory = sqlite3.Row
        DB.executescript("""
            CREATE TABLE IF NOT EXISTS versions (
                name TEXT PRIMARY KEY, task_id TEXT, description TEXT,
                created_at TEXT, parent TEXT, tags TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, description TEXT,
                status TEXT DEFAULT 'pending', version_name TEXT,
                agent_output TEXT, error TEXT, created_at TEXT,
                completed_at TEXT, human_id TEXT
            );
            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT, duration_ms INTEGER,
                tokens_input INTEGER DEFAULT 0, tokens_output INTEGER DEFAULT 0,
                success INTEGER DEFAULT 0, error TEXT, ran_at TEXT
            );
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY, value TEXT
            );
        """)
        DB.commit()
    return DB

# ── Init ──────────────────────────────────────────────────────────

def init():
    os.makedirs(str(VERSIONS_DIR), exist_ok=True)
    if not BASE.exists():
        shutil.copytree(DIR / "_template", BASE) if (DIR / "_template").exists() else BASE.mkdir(parents=True)
        (BASE / "index.html").write_text("""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>v2</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font-family:system-ui,sans-serif;font-size:14px}
.toolbar{background:#161b22;border-bottom:1px solid #30363d;padding:8px 12px;display:flex;gap:4px;align-items:center;position:sticky;top:0;z-index:100;flex-wrap:wrap}
.toolbar a,.toolbar button{color:#c9d1d9;text-decoration:none;padding:4px 10px;border:1px solid #30363d;border-radius:4px;background:#21262d;cursor:pointer;font-size:12px}
.toolbar a:hover,.toolbar button:hover{background:#30363d}
.toolbar .on{background:#58a6ff20;border-color:#58a6ff;color:#58a6ff}
.content{max-width:1200px;margin:auto;padding:16px}
h1{font-size:22px;margin-bottom:2px}
.sub{color:#8b949e;font-size:13px;margin-bottom:16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:12px}
.card h2{font-size:12px;text-transform:uppercase;color:#8b949e;margin-bottom:8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
.bar{display:grid;grid-template-columns:repeat(auto-fit,minmax(80px,1fr));gap:8px;margin-bottom:12px}
.bar-item{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px}
.bar-item .l{font-size:10px;color:#8b949e;text-transform:uppercase}
.bar-item .v{font-size:18px;font-weight:700}
.tag{display:inline-block;padding:2px 8px;border-radius:8px;font-size:10px;background:#30363d;color:#8b949e;margin:2px;border:1px solid #30363d}
.btn{padding:5px 14px;border:1px solid #30363d;border-radius:6px;cursor:pointer;background:#21262d;color:#c9d1d9;font-size:12px}
.btn-p{border-color:#58a6ff;color:#58a6ff}.btn-ok{border-color:#3fb950;color:#3fb950}.btn-no{border-color:#f85149;color:#f85149}
.task,.ver-row{padding:8px 10px;border:1px solid #30363d;border-radius:6px;margin-bottom:6px}
.ver-row{display:flex;justify-content:space-between;cursor:pointer}
.ver-row:hover{background:#ffffff08}.ver-row.on{border-color:#3fb950;background:#3fb95010}
.s{font-size:10px;padding:2px 8px;border-radius:8px;font-weight:600}
.s-w{background:#58a6ff20;color:#58a6ff}.s-r{background:#d2992220;color:#d29922}.s-a{background:#3fb95020;color:#3fb950}
.bm-row{display:grid;grid-template-columns:2fr 1fr 1fr;gap:4px;padding:3px 0;font-size:12px}
.diff-box{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:8px;max-height:200px;overflow:auto;font-family:monospace;font-size:12px;white-space:pre-wrap}
.add{color:#3fb950}.del{color:#f85149}
textarea{width:100%;padding:8px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:14px;resize:vertical;font-family:inherit}
.moda{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px;z-index:200;width:90%;max-width:460px;box-shadow:0 8px 32px #000}
.empty{color:#8b949e;font-style:italic;padding:6px 0}
.loader{display:inline-block;width:12px;height:12px;border:2px solid #30363d;border-top-color:#58a6ff;border-radius:50%;animation:s .6s linear infinite;vertical-align:middle}
@keyframes s{to{transform:rotate(360deg)}}
</style></head><body>
<div class="toolbar" id="tb"></div>
<div class="content" id="ct"></div>
<div id="modal" class="moda" style="display:none">
<h3>Nueva tarea</h3><textarea id="ti" style="min-height:60px" placeholder="Qué debería cambiar..."></textarea>
<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-p" id="sb" onclick="sendTask()">Enviar</button><button class="btn" onclick="hide('modal')">Cancelar</button><span id="ts" style="font-size:12px;color:#8b949e"></span></div></div>
<div id="rej" class="moda" style="display:none;border-color:#f85149;text-align:center">
<p style="margin-bottom:12px">¿Rechazar cambios?<br><small style="color:#8b949e">Se descartará la versión.</small></p>
<button class="btn btn-no" onclick="rej2(true)">Sí</button> <button class="btn" onclick="rej2(false)">No</button></div>
<script>
let WS_TRY=0;const WS=9878;let S={},RID='',ACTV='',WS_FAIL=false;
const ws=new WebSocket("ws://"+location.hostname+":"+WS);
ws.onmessage=e=>{S=JSON.parse(e.data);if(S.type==="state")rn()};
ws.onopen=()=>ws.send(JSON.stringify({type:"get_state"}));
ws.onclose=()=>{if(!WS_FAIL){WS_FAIL=true;setInterval(async()=>{try{const r=await fetch('/api/state');S=await r.json();rn()}catch(e){}},3000)}};
const esc=s=>{const d=document.createElement("div");d.textContent=s||"";return d.innerHTML};
const hide=i=>document.getElementById(i).style.display="none";

function rn(){
  const s=S, vv=location.pathname.split("/")[1], ac=s.active_version||"base";
  const tks=s.tasks||[], bm=s.benchmarks||[], vers=s.versions||[], vt=s.version_tags||{};
  ACTV=ac;
  // Toolbar
  document.getElementById("tb").innerHTML=
    `<a href="/base">base</a>`+
    vers.filter(v=>v.name!="base").map(v=>`<a href="/${v.name}"${vv==v.name?' class="on"':''}>${v.name}</a>`).join("")+
    `<button onclick="m('modal')">+Tarea</button>`+
    `<span style="font-size:11px;color:#8b949e;margin-left:auto">${ac}</span>`;

  // Working indicator
  const working = tks.filter(t=>t.status=="working");
  const whtml = working.length ? `<div style="padding:8px 12px;background:#58a6ff10;border:1px solid #58a6ff40;border-radius:6px;margin-bottom:12px;display:flex;align-items:center;gap:8px"><span class="loader"></span> ${working.length} agente${working.length>1?'s':''} trabajando...</div>` : "";

  // Tasks
  const it=tks.filter(t=>t.status!="approved"&&t.status!="rejected").slice(0,10).map(t=>{
    const sl={working:"s-w",reviewing:"s-r"},sn={working:"trabajando",reviewing:"revisar",failed:"error"};
    const acs=t.status=="reviewing"?`<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">
      <button class="btn btn-ok" onclick="fetch('/api/tasks/${t.id}/approve',{method:'POST'})">✓Aprobar</button>
      <button class="btn" onclick="RID='${t.id}';document.getElementById('rej').style.display='block'">✗Rechazar</button>
      <button class="btn" onclick="sd('${t.id}',this)">Diff</button></div>
      <div class="diff-box" id="d-${t.id}" style="display:none"></div>`:"";
    const tg=(vt[t.version_name]||[]).map(x=>`<span class="tag">${x}</span>`).join("");
    return `<div class="task"><div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px"><b>${esc(t.description)}</b><span class="s ${sl[t.status]||''}">${sn[t.status]||t.status}</span></div>
    <div style="font-size:11px;color:#8b949e">${t.version_name||''} ${tg}</div>${acs}</div>`;
  }).join("");

  // Versions
  const vi=vers.filter(v=>v.name!="base").map(v=>{
    const tg=(vt[v.name]||[]).map(x=>`<span class="tag">${x}</span>`).join("");
    return `<div class="ver-row ${ac==v.name?'on':''}" onclick="sw('${v.name}')">
      <div><b>${v.name}</b>${ac==v.name?' <span style="color:#3fb950;font-size:10px">activo</span>':''}
      <div style="font-size:11px;color:#8b949e">${esc(v.description||'')}</div>${tg?'<div>'+tg+'</div>':''}</div>
      <div style="font-size:11px;color:#8b949e">${(v.created_at||'').slice(0,10)}</div></div>`;
  }).join("");

  document.getElementById("ct").innerHTML=
    `<h1>${vv||'base'}</h1>
    <div class="sub">${vv=='base'?'Raíz — siempre disponible. Las versiones se crean desde tareas.':ac+' activo'}</div>
    ${whtml}
    <div class="bar">
      <div class="bar-item"><div class="l">Trabajando</div><div class="v">${tks.filter(t=>t.status=='working').length}</div></div>
      <div class="bar-item"><div class="l">Revisar</div><div class="v">${tks.filter(t=>t.status=='reviewing').length}</div></div>
      <div class="bar-item"><div class="l">Versiones</div><div class="v">${vers.length-1}</div></div>
      <div class="bar-item"><div class="l">Benchmarks</div><div class="v" id="bm-count">${bm.length}</div></div>
    </div>
    <div class="grid">
      <div class="card"><h2>Tareas</h2>${it||'<div class="empty">Sin tareas activas</div>'}</div>
      <div class="card"><h2>Versiones</h2>${vi||'<div class="empty">Crea una tarea para generar la primera versión</div>'}</div>
    </div>
    <div class="grid">
      <div class="card"><h2>Benchmarks</h2>${bm.slice(0,8).map(b=>`<div class="bm-row"><span>${b.model}</span><span>${b.duration_ms}ms</span><span>${b.tokens_input||0}/${b.tokens_output||0}</span></div>`).join("")||'<div class="empty">Sin datos</div>'}</div>
      <div class="card"><h2>Config</h2>
        <div style="display:grid;gap:6px">
          <label style="font-size:12px;color:#8b949e">Benchmarks activos</label>
          <input type="checkbox" id="c-en" onchange="saveCfg()" ${s.config?.benchmark_enabled=='1'?'checked':''}>
          <label style="font-size:12px;color:#8b949e">Intervalo (seg)</label>
          <input type="number" id="c-iv" value="${s.config?.benchmark_interval||600}" onchange="saveCfg()" style="padding:4px 8px;background:#0d1117;border:1px solid #30363d;border-radius:4px;color:#c9d1d9;font-size:13px">
        </div>
      </div>
    </div>`;
}

function m(id){document.getElementById(id).style.display='block';document.getElementById('ti')?.focus()}

async function sendTask(){
  const i=document.getElementById("ti"),d=i.value.trim();if(!d)return;
  i.disabled=true;document.getElementById("ts").textContent="enviando...";
  const r=await(await fetch("/api/tasks",{method:"POST",body:JSON.stringify({description:d})})).json();
  i.value="";document.getElementById("ts").textContent=r.ok?"ok → "+r.version:"error";i.disabled=false;
  if(r.ok)setTimeout(()=>hide('modal'),1500);
}

function rej2(ok){if(ok)fetch("/api/tasks/"+RID+"/reject",{method:"POST"});hide('rej')}

async function sd(tid,b){
  const bx=document.getElementById("d-"+tid);
  if(bx.style.display!="none"){bx.style.display="none";return}
  bx.style.display="block";const t=await(await fetch("/diff/"+tid)).text();
  bx.innerHTML=t.split("\n").map(l=>{if(l[0]=='+')return'<span class="add">'+esc(l)+'</span>';if(l[0]=='-')return'<span class="del">'+esc(l)+'</span>';return esc(l)}).join("\n")||"(sin cambios)";
}

function sw(vn){
  if(vn==ACTV)return;
  fetch("/api/versions/activate",{method:"POST",body:JSON.stringify({version:vn})}).then(()=>location.href="/"+vn);
}

async function saveCfg(){
  await fetch("/api/config",{method:"POST",body:JSON.stringify({
    benchmark_enabled:document.getElementById("c-en").checked?"1":"0",
    benchmark_interval:document.getElementById("c-iv").value||600
  }),headers:{"Content-Type":"application/json"}});
}
</script></body></html>""")
    if not (VERSIONS_DIR / "live").exists():
        (VERSIONS_DIR / "live").symlink_to("base", target_is_directory=True)

# ── Server ────────────────────────────────────────────────────────

class Server:
    def __init__(self):
        init(); self.ws = set(); self._mt = os.path.getmtime(__file__)
        # Seed config defaults
        for k, v in {"benchmark_interval":"600","benchmark_enabled":"1","benchmark_models":"", "available_models": "deepseek-v4-flash,deepseek-v4-pro,kimi-k2.6,kimi-k2.5,mimo-v2.5,minimax-m2.5"}.items():
            if not db().execute("SELECT key FROM config WHERE key=?", (k,)).fetchone():
                db().execute("INSERT INTO config (key,value) VALUES (?,?)", (k,v))
        db().commit()

    async def start(self):
        asyncio.create_task(self._watch())
        asyncio.create_task(self._benchmarks())
        await self._serve()

    async def _watch(self):
        while True:
            await asyncio.sleep(2)
            try:
                m = os.path.getmtime(__file__)
                if m > self._mt: os.execv(sys.executable, [sys.executable, __file__])
            except: pass

    async def _serve(self):
        import websockets as ws
        async def wsh(ws_):
            self.ws.add(ws_)
            try:
                async for raw in ws_:
                    m = json.loads(raw)
                    if m.get("type")=="get_state": await ws_.send(self._state())
            except: pass
            finally: self.ws.discard(ws_)

        async def htr(r, w):
            try:
                raw = await r.read(65536)
                req = raw.decode() if raw else ""
                meth = req.split(" ")[0] if req else ""
                path = req.split(" ")[1] if req else ""
                body = req.split("\r\n\r\n",1)[1] if "\r\n\r\n" in req else ""
                if "api/" in path:
                    if path=="/api/state": await self._json(w, json.loads(self._state()))
                    elif meth=="POST" and path=="/api/tasks": await self._task(w, body)
                    elif re.match(r"^/api/tasks/[^/]+/approve$",path): await self._approve(w, path.split("/")[3])
                    elif re.match(r"^/api/tasks/[^/]+/reject$",path): await self._reject(w, path.split("/")[3])
                    elif meth=="POST" and path=="/api/versions/activate": await self._activate(w, body)
                    elif path=="/api/config" and meth=="GET": await self._json(w, self._cfg())
                    elif path=="/api/config" and meth=="POST": await self._set_cfg(w, body)
                    elif re.match(r"^/api/versions/[^/]+/tags$",path) and meth=="POST": await self._tag(w, path.split("/")[3], body)
                    elif re.match(r"^/diff/",path): await self._diff(w, path.split("/")[2])
                    else: await self._json(w, {"ok":False})
                elif re.match(r"^/(base|v\d{3})(/.*)?$", path):
                    v = path.split("/")[1]; rest = "/".join(path.split("/")[2:])
                    f = vp(v) / (rest or "index.html")
                    if f.exists(): d = f.read_bytes(); w.write(f"HTTP/1.1 200 OK\r\nContent-Type: {mimetypes.guess_type(str(f))[0] or 'text/html'}\r\nContent-Length: {len(d)}\r\n\r\n".encode()); w.write(d)
                    else: w.write(b"HTTP/1.1 404\r\nContent-Length: 9\r\n\r\nnot found")
                elif path == "/":
                    l = live().name
                    d = (vp(l) / "index.html").read_bytes()
                    w.write(f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(d)}\r\n\r\n".encode()); w.write(d)
                else: w.write(b"HTTP/1.1 404\r\nContent-Length: 9\r\n\r\nnot found")
                await w.drain()
            except Exception as e:
                print(f"http: {e}")
                try: w.close()
                except: pass

        ws_s = await ws.serve(wsh, HOST, 9878)
        ht_s = await asyncio.start_server(htr, HOST, PORT)
        print(f"\n  s74/v2 → http://{HOST}:{PORT}/\n")
        await asyncio.gather(ws_s.wait_closed(), ht_s.serve_forever())

    async def _task(self, w, body):
        d = json.loads(body); desc = d.get("description","")
        if not desc: return await self._json(w, {"ok":False})
        tid = uuid.uuid4().hex[:12]
        db().execute("INSERT INTO tasks (id,description,status,created_at) VALUES (?,?,?,?)", (tid,desc,"working",now())); db().commit()
        c = live(); nums = [int(n.name[1:]) for n in VERSIONS_DIR.iterdir() if n.name.startswith("v") and n.name[1:].isdigit()]
        vn = f"v{max(nums)+1 if nums else 1:03d}"; shutil.copytree(c, vp(vn), symlinks=False)
        db().execute("INSERT INTO versions (name,task_id,description,parent,created_at) VALUES (?,?,?,?,?)", (vn,tid,desc,c.name,now())); db().commit()
        db().execute("UPDATE tasks SET version_name=? WHERE id=?", (vn,tid)); db().commit()
        await self._json(w, {"ok":True,"version":vn}); await self._bcast()
        asyncio.create_task(self._agent(tid, str(vp(vn)), desc, vn))

    async def _agent(self, tid, wp, desc, vn):
        try:
            p = await asyncio.create_subprocess_exec(sys.executable, str(AGENT), wp, desc, stdout=-1, stderr=-1, env={**os.environ})
            o, e = await asyncio.wait_for(p.communicate(), 300); out = (o.decode()+"\n"+e.decode()).strip()
            if p.returncode==0:
                db().execute("UPDATE tasks SET status='reviewing', agent_output=? WHERE id=?", (out[:2000],tid)); db().commit()
                # Auto-tag
                v = db().execute("SELECT parent FROM versions WHERE name=?", (vn,)).fetchone()
                pn = v["parent"] if v else "base"
                diff = subprocess.run(["diff","-r",str(vp(pn)),str(vp(vn))], capture_output=True, text=True).stdout[:5000]
                tags = self._auto_tag(vn, diff)
                db().execute("UPDATE versions SET tags=? WHERE name=?", (",".join(tags) if tags else "", vn)); db().commit()
            else: db().execute("UPDATE tasks SET status='failed', error=? WHERE id=?", (out[:500],tid)); db().commit()
        except asyncio.TimeoutError: db().execute("UPDATE tasks SET status='failed', error=? WHERE id=?", (tid,))
        await self._bcast()

    def _auto_tag(self, vn, diff):
        dl = diff.lower() if diff else ""; tags = set()
        if any(w in dl for w in ["color","theme","tema","css","style","dark","light"]):
            tags.add("tema")
            if "dark" in dl: tags.add("oscuro")
            if "light" in dl or "claro" in dl: tags.add("claro")
        if any(w in dl for w in ["endpoint","route","api","handler"]): tags.add("funcionalidad")
        if any(w in dl for w in ["title","texto","content","mensaje","label"]): tags.add("contenido")
        if not tags: tags.add("cambio")
        for t in tags: db().execute("INSERT OR IGNORE INTO versions SET tags=tags||?,name=? WHERE name=?", (t,",",vn))
        return tags

    async def _approve(self, w, tid):
        t = db().execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if not t or not t["version_name"]: return await self._json(w, {"ok":False})
        vn = t["version_name"]
        (VERSIONS_DIR/"live").unlink(missing_ok=True)
        (VERSIONS_DIR/"live").symlink_to(vn, target_is_directory=True)
        db().execute("UPDATE tasks SET status='approved',completed_at=? WHERE id=?", (now(),tid)); db().commit()
        await self._json(w, {"ok":True,"version":vn}); await self._bcast()

    async def _reject(self, w, tid):
        t = db().execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if not t: return await self._json(w, {"ok":False})
        vn = t["version_name"]
        db().execute("UPDATE tasks SET status='rejected',completed_at=? WHERE id=?", (now(),tid)); db().commit()
        if vn: shutil.rmtree(str(vp(vn)), ignore_errors=True)
        await self._json(w, {"ok":True}); await self._bcast()

    async def _activate(self, w, body):
        vn = json.loads(body).get("version","")
        if not vp(vn).exists(): return await self._json(w, {"ok":False})
        (VERSIONS_DIR/"live").unlink(missing_ok=True)
        (VERSIONS_DIR/"live").symlink_to(vn, target_is_directory=True)
        await self._json(w, {"ok":True,"version":vn}); await self._bcast()

    async def _tag(self, w, vn, body):
        tags = json.loads(body).get("tags",[])
        db().execute("UPDATE versions SET tags=? WHERE name=?", (",".join(tags), vn)); db().commit()
        await self._json(w, {"ok":True}); await self._bcast()

    async def _diff(self, w, tid):
        t = db().execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if not t: return await self._json(w, {"error":"not found"})
        vn = t["version_name"]; v = db().execute("SELECT parent FROM versions WHERE name=?", (vn,)).fetchone()
        pn = v["parent"] if v else "base"
        if vn and pn:
            r = subprocess.run(["diff","-r",str(vp(pn)),str(vp(vn))], capture_output=True, text=True)
            d = r.stdout[:5000] or "(sin cambios)"
        else: d = "no diff"
        w.write(f"HTTP/1.1 200\r\nContent-Type: text/plain\r\nContent-Length: {len(d)}\r\n\r\n".encode()); w.write(d.encode()); await w.drain()

    async def _set_cfg(self, w, body):
        for k,v in json.loads(body).items():
            db().execute("INSERT OR REPLACE INTO config (key,value) VALUES (?,?)", (k,str(v)))
        db().commit(); await self._json(w, {"ok":True})

    def _state(self):
        cfg = {r["key"]:r["value"] for r in db().execute("SELECT * FROM config").fetchall()}
        vers = [dict(r) for r in db().execute("SELECT * FROM versions ORDER BY created_at ASC").fetchall()]
        # Build version_tags map from versions.tags
        vt = {}
        for v in vers:
            if v.get("tags"): vt[v["name"]] = [t.strip() for t in v["tags"].split(",") if t.strip()]
        return json.dumps({
            "type":"state","active_version":live().name,
            "config": cfg,
            "versions": vers,
            "tasks":[dict(r) for r in db().execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50").fetchall()],
            "benchmarks":[dict(r) for r in db().execute("SELECT * FROM benchmarks ORDER BY ran_at DESC LIMIT 20").fetchall()],
            "version_tags": vt,
        })

    def _cfg(self):
        return {r["key"]:r["value"] for r in db().execute("SELECT * FROM config").fetchall()}

    async def _json(self, w, d):
        b = json.dumps(d).encode()
        w.write(f"HTTP/1.1 200\r\nContent-Type: application/json\r\nContent-Length: {len(b)}\r\nAccess-Control-Allow-Origin: *\r\n\r\n".encode())
        w.write(b); await w.drain()

    async def _bcast(self):
        p = self._state()
        for ws_ in list(self.ws):
            try: await ws_.send(p)
            except: self.ws.discard(ws_)

    async def _benchmarks(self):
        import httpx as hx
        while True:
            iv = int(db().execute("SELECT value FROM config WHERE key='benchmark_interval'").fetchone()[0])
            en = db().execute("SELECT value FROM config WHERE key='benchmark_enabled'").fetchone()[0]
            mc = db().execute("SELECT value FROM config WHERE key='benchmark_models'").fetchone()[0]
            if en!="1" or iv<=0: await asyncio.sleep(30); continue
            models = [m.strip() for m in mc.split(",") if m.strip()] or db().execute("SELECT value FROM config WHERE key='available_models'").fetchone()[0].split(",")
            for m in models:
                try:
                    s=time.monotonic()
                    async with hx.AsyncClient(timeout=60) as c:
                        r = await c.post(f"{API_BASE.rstrip('/')}/chat/completions", json={"model":m,"messages":[{"role":"user","content":"Say only: OK"}],"max_tokens":100}, headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json","User-Agent":"curl/8.0"})
                    d=int((time.monotonic()-s)*1000)
                    if r.status_code==200:
                        j=r.json(); ct=(j["choices"][0]["message"].get("content") or "").strip().lower()
                        db().execute("INSERT INTO benchmarks (model,duration_ms,tokens_input,tokens_output,success,ran_at) VALUES (?,?,?,?,?,?)", (m,d,j.get("usage",{}).get("prompt_tokens",0),j.get("usage",{}).get("completion_tokens",0),int(len(ct)>0),now())); db().commit()
                    else: db().execute("INSERT INTO benchmarks (model,duration_ms,success,error,ran_at) VALUES (?,?,?,?,?)", (m,d,0,f"HTTP {r.status_code}",now())); db().commit()
                except Exception as e: db().execute("INSERT INTO benchmarks (model,duration_ms,success,error,ran_at) VALUES (?,?,?,?,?)", (m,0,0,str(e)[:200],now())); db().commit()
            await self._bcast(); await asyncio.sleep(int(iv))

if __name__=="__main__":
    asyncio.run(Server().start())
