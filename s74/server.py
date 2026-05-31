#!/usr/bin/env python3
"""s74 — Orquestador mínimo. Sirve API + archivos. Versiones contienen el UI completo."""

import asyncio, json, mimetypes, os, re, shutil, sqlite3, subprocess, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path

mimetypes.add_type("text/html", ".html")

HOST, PORT = "0.0.0.0", 9878
DIR = Path(__file__).parent
DATA_DIR = DIR / "data"; VERSIONS_DIR = DIR / "versions"
LEDGER = DATA_DIR / "ledger.db"; AGENT = DIR / "agent.py"; BASE = VERSIONS_DIR / "base"

API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
BASE_URL = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")
BM_INT = int(os.environ.get("BENCHMARK_INTERVAL", "600"))
MODELS = ["deepseek-v4-flash","deepseek-v4-pro","kimi-k2.6","kimi-k2.5","mimo-v2.5","minimax-m2.5"]

def now(): return datetime.now(timezone.utc).isoformat()
def vp(n): return VERSIONS_DIR / n
def live(): return (VERSIONS_DIR/"live").resolve() if (VERSIONS_DIR/"live").exists() else BASE

DB = None
def db():
    global DB
    if not DB:
        os.makedirs(str(LEDGER.parent), exist_ok=True)
        DB = sqlite3.connect(str(LEDGER), check_same_thread=False)
        DB.row_factory = sqlite3.Row
        DB.executescript("""
            CREATE TABLE IF NOT EXISTS versions (name TEXT PRIMARY KEY, task_id TEXT, description TEXT, created_at TEXT, parent TEXT);
            CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, description TEXT, status TEXT DEFAULT 'pending', version_name TEXT, agent_output TEXT, error TEXT, created_at TEXT, completed_at TEXT, human_id TEXT);
            CREATE TABLE IF NOT EXISTS benchmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, model TEXT, duration_ms INTEGER, tokens_input INTEGER DEFAULT 0, tokens_output INTEGER DEFAULT 0, success INTEGER DEFAULT 0, error TEXT, ran_at TEXT);
            CREATE TABLE IF NOT EXISTS contributions (id INTEGER PRIMARY KEY AUTOINCREMENT, human_id TEXT, action TEXT, points INTEGER DEFAULT 1, created_at TEXT);
            CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS tag_rels (tag_a INTEGER REFERENCES tags(id), tag_b INTEGER REFERENCES tags(id), relation TEXT, PRIMARY KEY(tag_a,tag_b));
            CREATE TABLE IF NOT EXISTS version_tags (version_name TEXT REFERENCES versions(name), tag_id INTEGER REFERENCES tags(id), PRIMARY KEY(version_name,tag_id));
        """)
        DB.commit()
    return DB

def ensure_tag(name):
    name = name.strip().lower().replace(" ","-")
    r = db().execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()
    if r: return r["id"]
    db().execute("INSERT INTO tags (name) VALUES (?)", (name,)); db().commit()
    return db().execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()["id"]

def tag_version(vname, *tags):
    for t in tags:
        tid = ensure_tag(t)
        db().execute("INSERT OR IGNORE INTO version_tags (version_name, tag_id) VALUES (?,?)", (vname, tid))
    db().commit()

def auto_tag(vname, diff):
    tags, dl = set(), diff.lower() if diff else ""
    if any(w in dl for w in ["color","theme","tema","css","style","dark","light"]):
        tags.add("tema")
        if "dark" in dl: tags.add("oscuro")
        if "light" in dl or "claro" in dl: tags.add("claro")
    if any(w in dl for w in ["endpoint","route","api","handler"]): tags.add("funcionalidad")
    if any(w in dl for w in ["title","texto","content","mensaje","label"]): tags.add("contenido")
    if not tags: tags.add("cambio")
    for t in tags: tag_version(vname, t)
    return tags

def init():
    os.makedirs(str(VERSIONS_DIR), exist_ok=True)
    if not BASE.exists():
        BASE.mkdir(parents=True); (BASE/"web").mkdir()
    if not db().execute("SELECT * FROM versions").fetchone():
        db().execute("INSERT INTO versions (name,description,created_at) VALUES (?,?,?)", ("base","versión raíz",now())); db().commit()
    if not (VERSIONS_DIR/"live").exists(): (VERSIONS_DIR/"live").symlink_to("base")

class Server:
    def __init__(self):
        init(); self.ws = set(); self.last_mt = os.path.getmtime(__file__)

    async def start(self):
        asyncio.create_task(self._watch())
        asyncio.create_task(self._bm())
        await self._serve()

    async def _watch(self):
        while True:
            await asyncio.sleep(2)
            try:
                m = os.path.getmtime(__file__)
                if m > self.last_mt: os.execv(sys.executable, [sys.executable, __file__])
            except: pass

    async def _serve(self):
        import websockets
        async def wsh(ws):
            self.ws.add(ws)
            try:
                async for raw in ws:
                    m = json.loads(raw)
                    if m.get("type")=="get_state": await ws.send(self._state())
            except: pass
            finally: self.ws.discard(ws)
        async def htr(r,w):
            try:
                raw = await r.read(65536); req = raw.decode() if raw else ""; meth = req.split(" ")[0] if req else ""; path = req.split(" ")[1] if req else ""
                body = req.split("\r\n\r\n",1)[1] if "\r\n\r\n" in req else ""
                if "api/" in path:
                    if path=="/api/state": await self._json(w, json.loads(self._state()))
                    elif path=="/api/config": await self._json(w, self._cfg())
                    elif meth=="POST" and path=="/api/config": await self._set_cfg(w, body)
                    elif meth=="POST" and path=="/api/tasks": await self._new_task(w, body)
                    elif meth=="POST" and re.match(r"^/api/tasks/[^/]+/approve$",path): await self._approve(w, path.split("/")[3])
                    elif meth=="POST" and re.match(r"^/api/tasks/[^/]+/reject$",path): await self._reject(w, path.split("/")[3])
                    elif meth=="POST" and path=="/api/versions/activate": await self._activate(w, body)
                    elif meth=="POST" and re.match(r"^/api/versions/[^/]+/tags$",path): await self._tag_ver(w, path.split("/")[3], body)
                    elif re.match(r"^/api/tags/",path): await self._tags_for(w, path.split("/")[2])
                    elif path=="/api/tags": await self._json(w, {"tags":[dict(r) for r in db().execute("SELECT * FROM tags ORDER BY name").fetchall()]})
                    else: await self._json(w, {"ok":False})
                elif path=="/" or path.startswith("/base") or re.match(r"^/v\d{3}",path):
                    v = live().name if path=="/" else path.split("/")[1]
                    idx = vp(v) / "web" / "index.html"
                    if idx.exists():
                        d = idx.read_bytes(); w.write(f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(d)}\r\n\r\n".encode()); w.write(d)
                    else: w.write(b"HTTP/1.1 404\r\nContent-Length: 9\r\n\r\nnot found")
                else: w.write(b"HTTP/1.1 404\r\nContent-Length: 9\r\n\r\nnot found")
                await w.drain()
            except: pass
            finally:
                try: w.close()
                except: pass
        ws_s = await websockets.serve(wsh, HOST, 9879)
        ht_s = await asyncio.start_server(htr, HOST, PORT)
        print(f"\n  s74 • http://{HOST}:{PORT}/\n")
        await asyncio.gather(ws_s.wait_closed(), ht_s.serve_forever())

    async def _new_task(self, w, body):
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
                # Get parent version from DB
                v = db().execute("SELECT parent FROM versions WHERE name=?", (vn,)).fetchone()
                parent_name = v["parent"] if v else "base"
                diff = subprocess.run(["diff","-r",str(vp(parent_name)),str(vp(vn))], capture_output=True, text=True).stdout[:5000]
                tags = auto_tag(vn, diff)
                print(f"agent: done {tid} tags={tags}")
            else: db().execute("UPDATE tasks SET status='failed', error=? WHERE id=?", (out[:500],tid)); db().commit()
        except asyncio.TimeoutError: db().execute("UPDATE tasks SET status='failed', error='timeout' WHERE id=?", (tid,)); db().commit()
        await self._bcast()

    async def _approve(self, w, tid):
        t = db().execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        if not t or not t["version_name"]: return await self._json(w, {"ok":False})
        (VERSIONS_DIR/"live").unlink(missing_ok=True); (VERSIONS_DIR/"live").symlink_to(t["version_name"])
        db().execute("UPDATE tasks SET status='approved',completed_at=? WHERE id=?", (now(),tid)); db().commit()
        db().execute("INSERT INTO contributions (human_id,action,points,created_at) VALUES (?,?,?,?)", ("human","approve",50,now())); db().commit()
        await self._json(w, {"ok":True,"version":t["version_name"]}); await self._bcast()

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
        (VERSIONS_DIR/"live").unlink(missing_ok=True); (VERSIONS_DIR/"live").symlink_to(vn)
        db().execute("INSERT INTO contributions (human_id,action,points,created_at) VALUES (?,?,?,?)", ("human","switch",5,now())); db().commit()
        await self._json(w, {"ok":True,"version":vn}); await self._bcast()

    async def _tag_ver(self, w, vn, body):
        db().execute("DELETE FROM version_tags WHERE version_name=?", (vn,)); db().commit()
        for t in json.loads(body).get("tags",[]): tag_version(vn, t)
        await self._json(w, {"ok":True}); await self._bcast()

    async def _tags_for(self, w, vn):
        r = db().execute("SELECT t.name FROM tags t JOIN version_tags vt ON t.id=vt.tag_id WHERE vt.version_name=?", (vn,)).fetchall()
        await self._json(w, {"tags":[x["name"] for x in r]})

    async def _set_cfg(self, w, body):
        for k,v in json.loads(body).items():
            if k in ("benchmark_interval","benchmark_enabled","benchmark_models"): db().execute("INSERT OR REPLACE INTO config (key,value) VALUES (?,?)", (k,str(v)))
        db().commit(); await self._json(w, {"ok":True})

    def _state(self):
        return json.dumps({
            "type":"state","active_version":live().name,
            "versions":[dict(r) for r in db().execute("SELECT * FROM versions ORDER BY created_at ASC").fetchall()],
            "tasks":[dict(r) for r in db().execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50").fetchall()],
            "leaderboard":[dict(r) for r in db().execute("SELECT human_id,SUM(points)as total,COUNT(*)as actions FROM contributions GROUP BY human_id ORDER BY total DESC LIMIT 20").fetchall()],
            "benchmarks":[dict(r) for r in db().execute("SELECT * FROM benchmarks ORDER BY ran_at DESC LIMIT 20").fetchall()],
            "tags":[dict(r) for r in db().execute("SELECT * FROM tags ORDER BY name").fetchall()],
            "version_tags":[dict(r) for r in db().execute("SELECT vt.version_name,t.name FROM version_tags vt JOIN tags t ON vt.tag_id=t.id").fetchall()],
        })

    def _cfg(self):
        c = {r["key"]:r["value"] for r in db().execute("SELECT * FROM config").fetchall()}
        c.setdefault("benchmark_interval",str(BM_INT)); c.setdefault("benchmark_enabled","1"); c.setdefault("benchmark_models","")
        c["available_models"] = ",".join(MODELS); return c

    async def _json(self, w, d):
        b = json.dumps(d).encode(); w.write(f"HTTP/1.1 200\r\nContent-Type: application/json\r\nContent-Length: {len(b)}\r\nAccess-Control-Allow-Origin: *\r\n\r\n".encode()); w.write(b); await w.drain()

    async def _bcast(self):
        p = self._state()
        for ws in list(self.ws):
            try: await ws.send(p)
            except: self.ws.discard(ws)

    async def _bm(self):
        import httpx as hx
        while True:
            iv = int(db().execute("SELECT value FROM config WHERE key='benchmark_interval'",()).fetchone()[0] if db().execute("SELECT value FROM config WHERE key='benchmark_interval'",()).fetchone() else "600")
            en = db().execute("SELECT value FROM config WHERE key='benchmark_enabled'",()).fetchone()[0] if db().execute("SELECT value FROM config WHERE key='benchmark_enabled'",()).fetchone() else "1"
            mc = db().execute("SELECT value FROM config WHERE key='benchmark_models'",()).fetchone()[0] if db().execute("SELECT value FROM config WHERE key='benchmark_models'",()).fetchone() else ""
            if en!="1" or iv<=0: await asyncio.sleep(30); continue
            models = [m.strip() for m in mc.split(",") if m.strip()] or MODELS
            for m in models:
                try:
                    s=time.monotonic()
                    async with hx.AsyncClient(timeout=60) as c:
                        r = await c.post(f"{BASE_URL.rstrip('/')}/chat/completions", json={"model":m,"messages":[{"role":"user","content":"Say only: OK"}],"max_tokens":100}, headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json","User-Agent":"curl/8.0"})
                    d=int((time.monotonic()-s)*1000)
                    if r.status_code==200:
                        j=r.json(); ct=(j["choices"][0]["message"].get("content") or "").strip().lower()
                        ok=len(ct)>0
                        db().execute("INSERT INTO benchmarks (provider,model,duration_ms,tokens_input,tokens_output,success,ran_at) VALUES (?,?,?,?,?,?,?)", ("opencode-go",m,d,j.get("usage",{}).get("prompt_tokens",0),j.get("usage",{}).get("completion_tokens",0),int(ok),now())); db().commit()
                    else: db().execute("INSERT INTO benchmarks (provider,model,duration_ms,success,error,ran_at) VALUES (?,?,?,?,?,?)", ("opencode-go",m,d,0,f"HTTP {r.status_code}",now())); db().commit()
                except Exception as e: db().execute("INSERT INTO benchmarks (provider,model,duration_ms,success,error,ran_at) VALUES (?,?,?,?,?,?)", ("opencode-go",m,0,0,str(e)[:200],now())); db().commit()
            await self._bcast(); await asyncio.sleep(iv)

init()
Server.ws = set()
if __name__=="__main__":
    asyncio.run(Server().start())
