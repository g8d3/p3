import asyncio
import json
import mimetypes
import os
import traceback
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .db import Database, DBPool
from .ws_base import WSManager
from .ws import NativeWSConnection, accept_key


class Request:
    def __init__(self, method, path, headers, body, query):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query = query
        self._json = None

    @property
    def json(self):
        if self._json is None and self.body:
            self._json = json.loads(self.body)
        return self._json

    @property
    def form(self):
        if self.body and self.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            return parse_qs(self.body.decode())
        return {}


class Response:
    def __init__(self, body="", status=200, content_type="text/plain"):
        self.body = body
        self.status = status
        self.content_type = content_type

    def to_bytes(self):
        if isinstance(self.body, (dict, list)):
            data = json.dumps(self.body, default=str, ensure_ascii=False)
            self.content_type = "application/json"
        elif isinstance(self.body, str):
            data = self.body
        elif isinstance(self.body, bytes):
            data = self.body
            if self.content_type == "text/plain":
                self.content_type = "application/octet-stream"
        else:
            data = str(self.body)

        if isinstance(data, str):
            data = data.encode("utf-8")

        status_text = {200: "OK", 201: "Created", 204: "No Content",
                       400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed",
                       500: "Internal Server Error"}.get(self.status, "OK")

        header = (
            f"HTTP/1.1 {self.status} {status_text}\r\n"
            f"Content-Type: {self.content_type}\r\n"
            f"Content-Length: {len(data)}\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
            f"Access-Control-Allow-Headers: Content-Type\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
        ).encode()
        return header + data


class App:
    def __init__(self, name, static_dir=None, db_url=None):
        self.name = name
        self._routes = []
        self._models = {}
        self._model_schema = {}
        self._model_db = {}
        self._api_handlers = {}
        self._ws_manager = WSManager()
        self._server_instance = None
        self._framework_static = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
        self._static_dir = static_dir or self._framework_static
        self._pool = DBPool()
        self._ws_handlers = {}
        self._restart_count = 0
        if db_url:
            self._pool.add("default", db_url)

    @property
    def _db(self):
        return self._pool.get("default")

    def db(self, *args):
        if len(args) == 1:
            self._pool.add("default", args[0])
            return self._pool.get("default")
        elif len(args) == 2:
            return self._pool.add(args[0], args[1])

    @staticmethod
    def run(field, **opts):
        def wrapper(cls):
            cls.__nimbo_run__ = {"field": field, **opts}
            return cls
        return wrapper

    @staticmethod
    def system(api="/api/system/processes", id="pid", refresh=5):
        def wrapper(cls):
            cls.__nimbo_system__ = {"api": api, "id": id, "refresh": refresh}
            return cls
        return wrapper

    @staticmethod
    def log(cls=None):
        if cls is None:
            return lambda c: App._setup_log(c)
        return App._setup_log(cls)

    @staticmethod
    def _setup_log(cls):
        cls.__nimbo_log__ = True
        return cls

    @staticmethod
    def action(name=None):
        def wrapper(method):
            method.__nimbo_action__ = name or method.__name__
            return method
        return wrapper

    def model(self, cls=None, **kwargs):
        if cls is None:
            def wrapper(c):
                return self._register_model(c, **kwargs)
            return wrapper
        return self._register_model(cls, **kwargs)

    def _register_model(self, cls, table=None, fields=None, db="default", run=None):
        name = table or cls.__name__.lower()
        if fields is None:
            fields = []
            for attr, typ in cls.__annotations__.items():
                if attr.startswith("_"):
                    continue
                default = getattr(cls, attr, None)
                ftype = "string"
                if typ is int: ftype = "int"
                elif typ is float: ftype = "float"
                elif typ is bool: ftype = "bool"
                fields.append({"name": attr, "type": ftype, "default": default})

        self._model_schema[name] = fields
        self._models[name] = cls
        self._model_db[name] = db

        syscfg = getattr(cls, '__nimbo_system__', None)
        if syscfg:
            @self.route(f"/api/{name}/schema", methods=["GET"])
            async def sys_schema(req, _n=name):
                return {"name": _n, "fields": self._model_schema[_n]}
        else:
            self._auto_crud(name, db)

        self._register_models_route()

        # Auto-generate run action from @app.model(run=...), @app.run, or runnable()
        runcfg = getattr(cls, '__nimbo_run__', None)
        run = run or runcfg.get("field") if runcfg else None
        if not run:
            run = getattr(cls, '__nimbo_runnable__', None) and next(iter(cls.__nimbo_runnable__))
        if run:
            route_path = f"/api/{name}/run/<id>"
            _runcfg = runcfg or (getattr(cls, '__nimbo_runnable__', None) or {}).get(run, {})
            @self.route(route_path, methods=["POST"])
            async def run_handler(req, id, _run=run, _name=name, _runcfg=_runcfg):
                db = self._pool.get(self._model_db.get(_name, "default"))
                if not db:
                    return Response("no db", 500)
                item = db.read(_name, id)
                if not item:
                    return Response("", 404)
                shell = item.get(_run, "")
                if not shell:
                    return {"stdout": "", "stderr": "no command", "returncode": -1}
                timeout_field = _runcfg.get("timeout", "timeout") if isinstance(_runcfg, dict) else "timeout"
                timeout = item.get(timeout_field, 30) or 30
                try:
                    proc = await asyncio.create_subprocess_shell(
                        shell, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                    _name2 = _name
                    log_db = self._pool.get(self._model_db.get("log", "default"))
                    if log_db and "log" in self._model_schema:
                        ts = __import__("time").strftime("%H:%M:%S")
                        log_db.create("log", {"source": _name2, "level": "info", "content": f"{_name2} #{id} ran", "time": ts})
                        log_db.engine._conn.execute("DELETE FROM log WHERE id NOT IN (SELECT id FROM log ORDER BY id DESC LIMIT 200)")
                        log_db.engine._conn.commit()
                    return {"stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace"), "returncode": proc.returncode}
                except asyncio.TimeoutError:
                    try: proc.kill(); await proc.wait()
                    except: pass
                    return {"stdout": "", "stderr": "Timed out", "returncode": -1}

        # Register action endpoints from decorated methods
        for attr_name in dir(cls):
            method = getattr(cls, attr_name)
            action_name = getattr(method, '__nimbo_action__', None)
            if action_name:
                route_path = f"/api/{name}/{action_name}/<id>"
                @self.route(route_path, methods=["POST"])
                async def action_handler(req, id, _method=method, _name=name):
                    db = self._pool.get(self._model_db.get(_name, "default"))
                    if not db:
                        return Response("no db", 500)
                    item = db.read(_name, id)
                    if not item:
                        return Response("", 404)
                    try:
                        result = _method(item)
                        if asyncio.iscoroutine(result):
                            result = await result
                        return result if result is not None else {"ok": True}
                    except Exception as e:
                        return Response({"error": str(e)}, 500)

        return cls

    def _auto_crud(self, name, db_name="default"):
        base = f"/api/{name}"

        def _db():
            return self._pool.get(db_name) or self._pool.get("default")

        def _log(level, text):
            """Write to the log model if it exists (avoid recursion)."""
            if name == "log":
                return
            log_db = self._pool.get(self._model_db.get("log", "default"))
            if log_db and "log" in self._model_schema:
                ts = __import__("time").strftime("%H:%M:%S")
                log_db.create("log", {"source": name, "level": level, "content": text, "time": ts})
                log_db.engine._conn.execute("DELETE FROM log WHERE id NOT IN (SELECT id FROM log ORDER BY id DESC LIMIT 200)")
                log_db.engine._conn.commit()

        @self.route(f"{base}/schema", methods=["GET"])
        async def get_schema(req):
            return {"name": name, "fields": self._model_schema[name]}

        @self.route(f"{base}", methods=["GET"])
        async def list_all(req):
            return _db().list(name)

        @self.route(f"{base}", methods=["POST"])
        async def create_one(req):
            result = _db().create(name, req.json)
            _log("info", f"{name} created #{result.get('id','?')}")
            return result

        @self.route(f"{base}/<id>", methods=["GET"])
        async def read_one(req, id):
            result = _db().read(name, id)
            if not result:
                return Response("", 404)
            return result

        @self.route(f"{base}/<id>", methods=["PUT"])
        async def update_one(req, id):
            result = _db().update(name, id, req.json)
            if not result:
                return Response("", 404)
            _log("info", f"{name} #{id} updated")
            return result

        @self.route(f"{base}/<id>", methods=["DELETE"])
        async def delete_one(req, id):
            result = _db().delete(name, id)
            if not result:
                return Response("", 404)
            _log("warn", f"{name} #{id} deleted")
            return result

    @property
    def model_names(self):
        return list(self._model_schema.keys())

    def route(self, path, methods=None):
        if methods is None:
            methods = ["GET"]

        def wrapper(handler):
            self._routes.append((path, methods, handler))
            return handler
        return wrapper

    def browser_api(self, name=None):
        def wrapper(handler):
            api_name = name or handler.__name__
            self._api_handlers[api_name] = handler
            return handler
        return wrapper

    def ws_handler(self, topic=""):
        def wrapper(handler):
            self._ws_handlers[topic] = handler
            return handler
        return wrapper

    def _match_route(self, method, path):
        for route_path, methods, handler in self._routes:
            if method not in methods:
                continue
            pattern = route_path.replace("<id>", "([^/]+)").replace("<path>", "(.+)")
            import re
            m = re.match(f"^{pattern}$", path)
            if m:
                return handler, list(m.groups())
        return None, None

    async def _handle_ws_upgrade(self, reader, writer, path, ws_key):
        accept = accept_key(ws_key)
        writer.write((
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        ).encode())
        await writer.drain()

        ws = NativeWSConnection(reader, writer)
        if path == "/__nimbo/livereload":
            self._ws_manager.add(ws, "__nimbo_livereload")
            await ws.send(json.dumps({"type":"version","v":self._restart_count}))
            while not ws.closed:
                await asyncio.sleep(1)
            return
        for topic, handler in self._ws_handlers.items():
            self._ws_manager.add(ws, topic)
            await handler(ws)
            return
        self._ws_manager.add(ws)

    async def _handle_http(self, reader, writer):
        try:
            raw = b""
            while True:
                chunk = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=30)
                raw += chunk
                if b"\r\n\r\n" in raw:
                    break

            header_part, _, rest = raw.partition(b"\r\n\r\n")
            lines = header_part.decode("utf-8", errors="replace").split("\r\n")
            if not lines or not lines[0]:
                writer.close()
                return

            request_line = lines[0]
            parts = request_line.split(" ")
            if len(parts) < 2:
                writer.close()
                return
            method = parts[0].upper()
            url_path = parts[1]

            headers = {}
            content_length = 0
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()
                    if k.lower() == "content-length":
                        content_length = int(v.strip())

            if method in ("POST", "PUT") and content_length > 0:
                body = rest
                while len(body) < content_length:
                    chunk = await asyncio.wait_for(reader.read(65536), timeout=30)
                    if not chunk:
                        break
                    body += chunk
            else:
                body = rest

            parsed = urlparse(url_path)
            path = parsed.path
            query = parse_qs(parsed.query)

            # WebSocket upgrade
            if headers.get("upgrade", "").lower() == "websocket":
                ws_key = headers.get("sec-websocket-key", "")
                if ws_key:
                    await self._handle_ws_upgrade(reader, writer, path, ws_key)
                return

            req = Request(method, path, headers, body, query)

            if method == "OPTIONS":
                writer.write(Response("", 204).to_bytes())
                await writer.drain()
                writer.close()
                return

            handler, args = self._match_route(method, path)
            if handler:
                try:
                    result = await handler(req, *args) if args else await handler(req)
                    if isinstance(result, Response):
                        resp = result
                    else:
                        resp = Response(result)
                except Exception as e:
                    traceback.print_exc()
                    resp = Response({"error": str(e)}, 500)
            else:
                resp = await self._serve_static(path)

            writer.write(resp.to_bytes())
            await writer.drain()

        except (asyncio.TimeoutError, ConnectionError, BrokenPipeError):
            pass
        except Exception as e:
            traceback.print_exc()
            try:
                writer.write(Response({"error": str(e)}, 500).to_bytes())
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        file_path = self._static_dir + path
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            file_path = self._framework_static + path
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return Response("Not Found", 404)
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            if path == "/index.html":
                scripts = []
                if self._model_schema:
                    resources_json = json.dumps(self.model_names)
                    scripts.append(f'<script>window.__NIMBO_RESOURCES__={resources_json};</script>')
                    cfgs = {}
                    for nm, cls in self._models.items():
                        cls_obj = cls if isinstance(cls, type) else None
                        sc = getattr(cls_obj, '__nimbo_system__', None) if cls_obj else None
                        lc = getattr(cls_obj, '__nimbo_log__', False) if cls_obj else None
                        rc = getattr(cls_obj, '__nimbo_run__', None) if cls_obj else None
                        cfg = {}
                        if sc:
                            cfg.update({"api": sc["api"], "id": sc["id"], "refresh": sc["refresh"]*1000, "noCreate": True, "noEdit": True, "fields": self._model_schema[nm]})
                        if lc:
                            cfg.update({"refresh": 3000, "noCreate": True, "noEdit": True, "fields": self._model_schema[nm]})
                        if rc:
                            cfg.setdefault("actions", []).append({"label": "▶", "class": "btn-primary", "handlerTemplate": "run"})
                        if cfg:
                            cfgs[nm] = cfg
                    if cfgs:
                        scripts.append(f'<script>window.__NIMBO_CONFIGS__={json.dumps(cfgs)};</script>')
                if getattr(self, '_ws_backend', None) == "websockets" and hasattr(self, '_ws_lib_backend'):
                    ws_port = self._ws_lib_backend.ws_port
                    scripts.append(f'<script>window.__NIMBO_WS_PORT__={ws_port};</script>')
                if os.environ.get("NIMBO_RELOAD_CHILD"):
                    scripts.append(
                        '<script>(function(){'
                        'var p=location.protocol==="https:"?"wss:":"ws:",'
                        'h=location.host,'
                        'v=-1;'
                        'function lr(){'
                        'var w=new WebSocket(p+"//"+h+"/__nimbo/livereload");'
                        'w.onmessage=function(e){'
                        'try{var d=JSON.parse(e.data);'
                        'if(d.type==="version"){'
                        'if(v>=0&&d.v!==v)location.reload();'
                        'v=d.v;}}catch(e){}};'
                        'w.onclose=function(){setTimeout(lr,2000);};'
                        '}'
                        'lr();'
                        '})();</script>'
                    )
                if scripts:
                    data = data.replace(b"</head>", "\n".join(scripts).encode() + b"</head>")
            ctype, _ = mimetypes.guess_type(file_path)
            return Response(data, content_type=ctype or "application/octet-stream")
        except Exception:
            return Response("Not Found", 404)

    def _register_models_route(self):
        if not hasattr(self, '_models_route_registered'):
            @self.route("/api/models", methods=["GET"])
            async def list_models(req):
                return self.model_names
            self._models_route_registered = True

    def _register_livereload(self):
        if not hasattr(self, '_livereload_registered'):
            self._ws_manager = WSManager()
            self._livereload_registered = True

    def _get_watched_files(self):
        files = []
        dirs = set()
        import sys
        script = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else None
        if script and os.path.isfile(script):
            dirs.add(os.path.dirname(script))
        if self._static_dir and os.path.isdir(self._static_dir):
            dirs.add(self._static_dir)
        if self._framework_static and os.path.isdir(self._framework_static):
            dirs.add(self._framework_static)
        fw_pkg = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        if os.path.isdir(fw_pkg):
            dirs.add(fw_pkg)
        for d in dirs:
            for root, _, fnames in os.walk(d):
                for f in fnames:
                    if f.endswith(('.py', '.js', '.css', '.html')):
                        files.append(os.path.join(root, f))
        return files

    def _watch_while_running(self, process):
        import time
        watched = self._get_watched_files()
        mtimes = {}
        for f in watched:
            try:
                mtimes[f] = os.path.getmtime(f)
            except OSError:
                pass
        while process.poll() is None:
            time.sleep(1)
            changed = None
            for f in watched:
                try:
                    mt = os.path.getmtime(f)
                    if f in mtimes and mt != mtimes[f]:
                        changed = f
                except OSError:
                    pass
            if changed:
                # Debounce: wait for file to be stable for 2 seconds
                time.sleep(2)
                try:
                    mt2 = os.path.getmtime(changed)
                    if mt2 == mtimes.get(changed):
                        continue  # Was a temp change, reverted
                except OSError:
                    pass
                # Check if still changed from original
                try:
                    if os.path.getmtime(changed) != mtimes[changed]:
                        return changed
                except OSError:
                    pass
        return None

    def _run_with_reload(self, host, port):
        import subprocess, sys, time
        script = os.path.abspath(sys.argv[0])
        if not script or not os.path.isfile(script):
            print("[nimbo] reload: could not find script, running without reload")
            self.serve(host, port)
            return
        env = os.environ.copy()
        env["NIMBO_RELOAD_CHILD"] = "1"
        ver = 0
        print(f"[nimbo] hot reload on {host}:{port} (watching .py, .js, .css, .html)")
        while True:
            ver += 1
            env["NIMBO_VERSION"] = str(ver)
            p = subprocess.Popen([sys.executable, script] + sys.argv[1:], env=env)
            changed = self._watch_while_running(p)
            if changed:
                print(f"[nimbo] change: {os.path.basename(changed)}, restarting...")
            p.kill()
            p.wait()
            time.sleep(0.5)

    def serve(self, host="0.0.0.0", port=8080, reload=False, ws_backend="native", system=True):
        if reload and not os.environ.get("NIMBO_RELOAD_CHILD"):
            self._run_with_reload(host, port)
            return

        if self._model_schema and self._pool.get("default") is None:
            self._pool.add("default", "sqlite:///data/nimbo.db")

        by_db = {}
        for mname, db_name in self._model_db.items():
            by_db.setdefault(db_name, {})[mname] = self._model_schema[mname]
        if by_db:
            self._pool.migrate_all(by_db)

        self._register_models_route()
        self._ws_backend = ws_backend
        self._restart_count = int(os.environ.get("NIMBO_VERSION", "0"))
        if system:
            from .system import register_system_endpoints, register_log_model
            register_system_endpoints(self)
            if self._pool.get("default"):
                register_log_model(self)

        async def start():
            if ws_backend == "websockets":
                from .ws_websockets import WebsocketsBackend
                bk = WebsocketsBackend(self)
                self._ws_lib_backend = bk
                ws_port = await bk.start(host, port)
                print(f"nimbo  WS {host}:{ws_port} (websockets)")
            self._server_instance = await asyncio.start_server(
                self._handle_http, host, port
            )
            print(f"nimbo  HTTP {host}:{port}")
            async with self._server_instance:
                await self._server_instance.serve_forever()

        try:
            asyncio.run(start())
        except KeyboardInterrupt:
            self._pool.close_all()
            if hasattr(self, '_ws_lib_backend'):
                asyncio.run(self._ws_lib_backend.close())
