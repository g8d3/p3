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
        self._namespaces = {}
        self._ns_registry = {}
        self._log_models = set()
        self._proxy_backends = {}
        self._proxy_configs = {}
        self._model_redirect = {}
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

    def namespace(self, cls_or_name=None, name=None):
        if isinstance(cls_or_name, type):
            # @app.namespace  (without args)
            return self._register_namespace(cls_or_name, name)
        # @app.namespace("name")  (with string arg as name)
        ns = cls_or_name or name
        return lambda c: self._register_namespace(c, ns)

    def _register_namespace(self, cls, name=None):
        ns = name or cls.__name__.lower()
        cls.__nimbo_namespace__ = ns
        self._namespaces[ns] = cls
        self._ns_registry[id(cls)] = ns
        qual_prefix = cls.__qualname__ + '.'
        to_fix = []
        for mn, mc in list(self._models.items()):
            qn = getattr(mc, '__qualname__', '')
            if qn.startswith(qual_prefix):
                to_fix.append((mn, mc))
        for old_name, mc in to_fix:
            base = getattr(mc, '__nimbo_base_name__', old_name.split('/')[-1])
            full_ns = self._resolve_namespace_prefix(mc) or ns
            new_name = f"{full_ns}/{base}"
            # If old_name != new_name, rename model resources
            if old_name != new_name:
                self._model_schema[new_name] = self._model_schema.pop(old_name)
                self._models[new_name] = self._models.pop(old_name)
                self._model_db[new_name] = self._model_db.pop(old_name)
                mc.__nimbo_full_name__ = new_name
                # Update all redirects that pointed to old_name to point to new_name
                for k, v in list(self._model_redirect.items()):
                    if v == old_name:
                        self._model_redirect[k] = new_name
                self._model_redirect[old_name] = new_name
                old_prefix = self._route_base(old_name)
                new_prefix = f"/{new_name}"
                self._routes[:] = [
                    (p.replace(old_prefix, new_prefix, 1), m, h)
                    if p.startswith(old_prefix) else (p, m, h)
                    for (p, m, h) in self._routes
                ]
        return cls

    def _resolve_namespace_prefix(self, cls):
        qualname = getattr(cls, '__qualname__', cls.__name__)
        parts = qualname.split('.')
        if len(parts) <= 1:
            return ""
        # Find registered namespace classes by matching qualname parts
        prefixes = []
        for ns_name, ns_cls in self._namespaces.items():
            ns_qual = getattr(ns_cls, '__qualname__', ns_cls.__name__)
            if qualname.startswith(ns_qual + '.'):
                prefixes.append(ns_name)
        # Sort by qualname depth to get correct order
        prefixes.sort(key=lambda ns: self._namespaces[ns].__qualname__.count('.') if hasattr(self._namespaces[ns], '__qualname__') else 0)
        if not prefixes:
            return ""
        # Reconstruct full prefix path in qualname order
        result_parts = []
        for ns_name, ns_cls in sorted(
            self._namespaces.items(),
            key=lambda kv: (getattr(kv[1], '__qualname__', kv[1].__name__).count('.'), kv[0])
        ):
            ns_qual = getattr(ns_cls, '__qualname__', ns_cls.__name__)
            if qualname.startswith(ns_qual + '.'):
                result_parts.append(ns_name)
        return '/'.join(result_parts)

    @staticmethod
    def run(field, **opts):
        def wrapper(cls):
            cls.__nimbo_run__ = {"field": field, **opts}
            return cls
        return wrapper

    def system(self, cls_or_src=None, api=None, id="pid", refresh=5, kill=True):
        if cls_or_src is None:
            # @app.system  (no args, no class)
            return lambda c: self._register_system(c, api=api, id=id, refresh=refresh, kill=kill)
        if isinstance(cls_or_src, type):
            # @app.system  (with class, no parens)
            return self._register_system(cls_or_src, api=api, id=id, refresh=refresh, kill=kill)
        # @app.system("mount")  (with string source arg)
        src = cls_or_src
        return lambda c: self._register_system(c, api=src or api, id=id, refresh=refresh, kill=kill)

    def _register_system(self, cls, api=None, id="pid", refresh=5, kill=True):
        from .system import infer_source, SYSTEM_SOURCES
        source = api or infer_source(cls)
        default_fields = SYSTEM_SOURCES.get(source, [])
        user_fields = []
        for attr, typ in cls.__annotations__.items():
            if attr.startswith("_"):
                continue
            default = getattr(cls, attr, None)
            ftype = "string"
            if typ is int: ftype = "int"
            elif typ is float: ftype = "float"
            elif typ is bool: ftype = "bool"
            user_fields.append({"name": attr, "type": ftype, "default": default})
        merged = {f["name"]: f for f in default_fields}
        for f in user_fields:
            if f["name"] not in merged:
                merged[f["name"]] = f
        cls.__nimbo_system__ = {"api": source, "id": id, "refresh": refresh, "kill": kill if source == "process" else False}
        cls.__annotations__ = {}
        self._register_model(cls, table=source, fields=list(merged.values()))

    def proxy(self, cls=None, port=None, upstream=None, api_key=None, api_key_env=None, discovery=None):
        if cls is None:
            return lambda c: self._register_proxy(c, port=port, upstream=upstream, api_key=api_key, api_key_env=api_key_env, discovery=discovery)
        return self._register_proxy(cls, port=port, upstream=upstream, api_key=api_key, api_key_env=api_key_env, discovery=discovery)

    def _register_proxy(self, cls, port=None, upstream=None, api_key=None, api_key_env=None, discovery=None):
        from .proxy import infer_provider, PROXY_DEFAULT_FIELDS, KNOWN_PROVIDERS

        base_name = cls.__name__.lower()
        provider = infer_provider(base_name)

        resolved_upstream = upstream
        if not resolved_upstream and provider:
            resolved_upstream = KNOWN_PROVIDERS[provider]["upstream"]

        resolved_api_key_env = api_key_env
        if not resolved_api_key_env and provider:
            resolved_api_key_env = KNOWN_PROVIDERS[provider]["api_key_env"]

        user_fields = []
        for attr, typ in cls.__annotations__.items():
            if attr.startswith("_"):
                continue
            default = getattr(cls, attr, None)
            ftype = "string"
            if typ is int: ftype = "int"
            elif typ is float: ftype = "float"
            elif typ is bool: ftype = "bool"
            user_fields.append({"name": attr, "type": ftype, "default": default})

        merged = {f["name"]: f for f in PROXY_DEFAULT_FIELDS}
        for f in user_fields:
            if f["name"] not in merged:
                merged[f["name"]] = f

        cls.__nimbo_proxy__ = True
        # Act as namespace so nested models inherit route prefix
        self._register_namespace(cls, base_name)
        self._proxy_configs[base_name] = {
            "cls": cls,
            "port": port,
            "upstream": resolved_upstream,
            "api_key": api_key,
            "api_key_env": resolved_api_key_env,
            "discovery": discovery,
            "provider": provider,
            "fields": list(merged.values()),
        }

        self._register_model(cls, table=base_name, fields=list(merged.values()))
        # Register agent list route at /{proxy_name} (without /api/ prefix)
        @self.route(f"/{base_name}", methods=["GET"])
        async def proxy_agent_list(req, _pn=base_name):
            db = self._pool.get(self._model_db.get(_pn, "default"))
            if db:
                return db.list(_pn.split('/')[-1])
            return []
        return cls



    def log(self, cls=None):
        if cls is None:
            return lambda c: self._register_log(c)
        return self._register_log(cls)

    def _register_log(self, cls):
        cls.__nimbo_log__ = True
        base_name = cls.__name__.lower()
        ns_prefix = self._resolve_namespace_prefix(cls)
        model_name = f"{ns_prefix}/{base_name}" if ns_prefix else base_name
        route = self._route_base(model_name)

        log_fields = []
        for attr, typ in cls.__annotations__.items():
            if attr.startswith("_"):
                continue
            default = getattr(cls, attr, None)
            ftype = "string"
            if typ is int: ftype = "int"
            elif typ is float: ftype = "float"
            elif typ is bool: ftype = "bool"
            log_fields.append({"name": attr, "type": ftype, "default": default})

        if not log_fields:
            log_fields = [{"name": "source", "type": "string", "default": ""},
                          {"name": "level", "type": "string", "default": "info"},
                          {"name": "content", "type": "string", "default": ""},
                          {"name": "time", "type": "string", "default": ""}]

        self._model_schema[model_name] = log_fields
        self._models[model_name] = cls
        self._model_db[model_name] = "default"
        self._log_models.add(model_name)
        self._auto_crud(model_name, route, tbl=base_name, db_name="default")
        return cls

    @staticmethod
    def action(name=None):
        if callable(name):
            name.__nimbo_action__ = name.__name__
            return name
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

    def _resolve_model_name(self, name):
        seen = set()
        while name in self._model_redirect and name not in seen:
            seen.add(name)
            name = self._model_redirect[name]
        return name

    def _route_base(self, model_name):
        """Build the route prefix for a model.
        Namespaced models: /{namespace}/{model}
        Non-namespaced:   /api/{model}
        """
        if '/' in model_name:
            return f"/{model_name}"
        return f"/api/{model_name}"

    def _register_model(self, cls, table=None, fields=None, db="default", run=None):
        base_name = table or cls.__name__.lower()
        ns_prefix = self._resolve_namespace_prefix(cls)
        qual = getattr(cls, '__qualname__', cls.__name__)
        if table:
            model_name = base_name
        elif ns_prefix:
            model_name = f"{ns_prefix}/{base_name}"
        else:
            model_name = qual.replace('.', '_').replace('<', '').replace('>', '').lower()  # temp key to avoid collisions
        cls.__nimbo_temp_key__ = model_name
        cls.__nimbo_base_name__ = base_name
        if fields is None:
            fields = []
            for attr, typ in cls.__annotations__.items():
                if attr.startswith("_") or attr == "id":
                    continue
                default = getattr(cls, attr, None)
                ftype = "string"
                if typ is int: ftype = "int"
                elif typ is float: ftype = "float"
                elif typ is bool: ftype = "bool"
                fields.append({"name": attr, "type": ftype, "default": default})

        self._model_schema[model_name] = fields
        self._models[model_name] = cls
        self._model_db[model_name] = db

        route = self._route_base(model_name)

        syscfg = getattr(cls, '__nimbo_system__', None)
        if syscfg:
            @self.route(f"{route}/schema", methods=["GET"])
            async def sys_schema(req, _n=model_name):
                mn = self._resolve_model_name(_n)
                return {"name": mn, "fields": self._model_schema[mn]}
        else:
            self._auto_crud(model_name, route, base_name, db)

        self._register_models_route()

        runcfg = getattr(cls, '__nimbo_run__', None)
        if runcfg:
            run = run or runcfg.get("field")
        if not run:
            run = getattr(cls, '__nimbo_runnable__', None) and next(iter(cls.__nimbo_runnable__))
        if run:
            route_path = f"{route}/run/<id>"
            _runcfg = runcfg or (getattr(cls, '__nimbo_runnable__', None) or {}).get(run, {})
            @self.route(route_path, methods=["POST"])
            async def run_handler(req, id, _run=run, _mn=model_name, _runcfg=_runcfg):
                db = self._pool.get(self._model_db.get(_mn, "default"))
                if not db:
                    return Response("no db", 500)
                item = db.read(_mn.split('/')[-1], id)
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
                    for log_name in self._log_models:
                        log_schema = self._model_schema.get(log_name, [])
                        log_fields = {f["name"] for f in log_schema}
                        if not {"source", "level", "content", "time"}.issubset(log_fields):
                            continue
                        log_db = self._pool.get(self._model_db.get(log_name, "default"))
                        if log_db:
                            ts = __import__("time").strftime("%H:%M:%S")
                            log_db.create(log_name.split('/')[-1], {"source": _mn, "level": "info", "content": f"{_mn} #{id} ran", "time": ts})
                            log_db.engine._conn.execute(f"DELETE FROM {log_name.split('/')[-1]} WHERE id NOT IN (SELECT id FROM {log_name.split('/')[-1]} ORDER BY id DESC LIMIT 200)")
                            log_db.engine._conn.commit()
                    return {"stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace"), "returncode": proc.returncode}
                except asyncio.TimeoutError:
                    try: proc.kill(); await proc.wait()
                    except: pass
                    return {"stdout": "", "stderr": "Timed out", "returncode": -1}

        for attr_name in dir(cls):
            method = getattr(cls, attr_name)
            action_name = getattr(method, '__nimbo_action__', None)
            if action_name:
                route_path = f"{route}/{action_name}/<id>"
                @self.route(route_path, methods=["POST"])
                async def action_handler(req, id, _method=method, _mn=model_name):
                    db = self._pool.get(self._model_db.get(_mn, "default"))
                    if not db:
                        return Response("no db", 500)
                    item = db.read(_mn.split('/')[-1], id)
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

    def _auto_crud(self, model_name, route, tbl=None, db_name="default"):
        if tbl is None:
            tbl = model_name.split('/')[-1]

        def _db():
            return self._pool.get(db_name) or self._pool.get("default")

        def _log(level, text):
            if tbl == "log":
                return
            for log_name in self._log_models:
                log_schema = self._model_schema.get(log_name, [])
                log_fields = {f["name"] for f in log_schema}
                if not {"source", "level", "content", "time"}.issubset(log_fields):
                    continue
                log_db = self._pool.get(self._model_db.get(log_name, "default"))
                if log_db:
                    ts = __import__("time").strftime("%H:%M:%S")
                    log_db.create(log_name.split('/')[-1], {"source": model_name, "level": level, "content": text, "time": ts})
                    log_db.engine._conn.execute(f"DELETE FROM {log_name.split('/')[-1]} WHERE id NOT IN (SELECT id FROM {log_name.split('/')[-1]} ORDER BY id DESC LIMIT 200)")
                    log_db.engine._conn.commit()

        @self.route(f"{route}/schema", methods=["GET"])
        async def get_schema(req, _mn=model_name):
            mn = self._resolve_model_name(_mn)
            return {"name": mn, "fields": self._model_schema[mn]}

        @self.route(route, methods=["GET"])
        async def list_all(req):
            result = _db().list(tbl)
            raw_limit = req.query.get("limit", [None])[0]
            if raw_limit is not None:
                try:
                    result = result[:int(raw_limit)]
                except (ValueError, TypeError):
                    pass
            raw_offset = req.query.get("offset", [None])[0]
            if raw_offset is not None:
                try:
                    result = result[int(raw_offset):]
                except (ValueError, TypeError):
                    pass
            raw_sort = req.query.get("sort", [None])[0]
            if raw_sort is not None:
                desc = raw_sort.startswith("-")
                field = raw_sort[1:] if desc else raw_sort
                try:
                    result = sorted(result, key=lambda x: (x.get(field) or 0), reverse=desc)
                except Exception:
                    pass
            for key, vals in req.query.items():
                if key in ("limit", "offset", "sort"):
                    continue
                if vals:
                    result = [r for r in result if r.get(key) == vals[0]]
            return result

        @self.route(route, methods=["POST"])
        async def create_one(req):
            result = _db().create(tbl, req.json)
            _log("info", f"{model_name} created #{result.get('id','?')}")
            return result

        @self.route(f"{route}/<id>", methods=["GET"])
        async def read_one(req, id):
            result = _db().read(tbl, id)
            if not result:
                return Response("", 404)
            return result

        @self.route(f"{route}/<id>", methods=["PUT"])
        async def update_one(req, id):
            result = _db().update(tbl, id, req.json)
            if not result:
                return Response("", 404)
            _log("info", f"{model_name} #{id} updated")
            return result

        @self.route(f"{route}/<id>", methods=["DELETE"])
        async def delete_one(req, id):
            result = _db().delete(tbl, id)
            if not result:
                return Response("", 404)
            _log("warn", f"{model_name} #{id} deleted")
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

    async def _forward_proxy(self, method, path, headers, body, pname, pcfg):
        upstream = pcfg.get("upstream")
        if not upstream:
            return Response("no upstream configured", 502)
        api_key = None
        if pcfg.get("api_key"):
            api_key = pcfg["api_key"]
        elif pcfg.get("api_key_env"):
            api_key = os.environ.get(pcfg["api_key_env"])
        if not api_key:
            env_var = f"{pcfg['cls'].__name__.upper()}_API_KEY"
            api_key = os.environ.get(env_var)
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                upstream_path = path[len(pname) + 2:]
                upstream_url = upstream.rstrip("/") + "/" + upstream_path.lstrip("/")
                req_headers = {k: v for k, v in headers.items()
                               if k.lower() not in ("host", "content-length", "transfer-encoding")}
                if api_key:
                    auth_header = "Authorization"
                    if "openai" in upstream.lower():
                        req_headers[auth_header] = f"Bearer {api_key}"
                    elif "anthropic" in upstream.lower():
                        req_headers["x-api-key"] = api_key
                    else:
                        req_headers[auth_header] = f"Bearer {api_key}"
                async with session.request(
                    method, upstream_url,
                    headers=req_headers,
                    data=body if method in ("POST", "PUT") else None,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    resp_body = await resp.read()
                    resp_headers = dict(resp.headers)
                    # Mark agents as active if present
                    agent_id = resp_headers.get("x-agent-id", "unknown")
                    ph = self._proxy_backends.get(pname)
                    if ph and hasattr(ph, "_agents") and agent_id in ph._agents:
                        ph._agents[agent_id]["last_active"] = __import__("time").time()
                        ph._agents[agent_id]["status"] = "active"
                    # Log the call
                    for log_name in self._log_models:
                        log_schema = self._model_schema.get(log_name, [])
                        log_fields = {f["name"] for f in log_schema}
                        if not {"source", "level", "content", "time"}.issubset(log_fields):
                            continue
                        log_db = self._pool.get(self._model_db.get(log_name, "default"))
                        if log_db:
                            ts = __import__("time").strftime("%H:%M:%S")
                            log_db.create(log_name.split('/')[-1], {
                                "source": pname, "level": "info",
                                "content": f"{method} {upstream_path} → {resp.status}",
                                "time": ts,
                            })
                            log_db.engine._conn.execute(
                                f"DELETE FROM {log_name.split('/')[-1]} WHERE id NOT IN (SELECT id FROM {log_name.split('/')[-1]} ORDER BY id DESC LIMIT 200)"
                            )
                            log_db.engine._conn.commit()
                    ctype = resp_headers.get("content-type", "application/octet-stream")
                    return Response(resp_body, status=resp.status, content_type=ctype)
        except Exception as e:
            return Response({"error": f"proxy error: {str(e)}"}, 502)

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
                # Try proxy forwarding for inline proxies
                resp = None
                for pname, pcfg in self._proxy_configs.items():
                    if not pcfg.get("port") and path.startswith(f"/{pname}/"):
                        resp = await self._forward_proxy(method, path, headers, body, pname, pcfg)
                        break
                if resp is None:
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
                    resources_json = json.dumps([n.split('/')[-1] for n in self.model_names])
                    scripts.append(f'<script>window.__NIMBO_RESOURCES__={resources_json};</script>')
                    cfgs = {}
                    for nm, cls in self._models.items():
                        cls_obj = cls if isinstance(cls, type) else None
                        sc = getattr(cls_obj, '__nimbo_system__', None) if cls_obj else None
                        lc = getattr(cls_obj, '__nimbo_log__', False) if cls_obj else None
                        rc = getattr(cls_obj, '__nimbo_run__', None) if cls_obj else None
                        pc = getattr(cls_obj, '__nimbo_proxy__', None) if cls_obj else None
                        route = self._route_base(nm)
                        res_name = nm.split('/')[-1]
                        cfg = {}
                        if sc:
                            cfg.update({"api": route, "id": sc["id"], "refresh": sc["refresh"]*1000, "noCreate": True, "noEdit": True, "kill": sc.get("kill", True)})
                        elif lc:
                            cfg.update({"api": route, "refresh": 3000, "noCreate": True, "noEdit": True})
                        elif pc:
                            cfg.update({"api": route, "refresh": 10000, "noCreate": True, "noEdit": True})
                        else:
                            cfg.update({"api": route})
                        if rc:
                            cfg.setdefault("actions", []).append({"label": "▶", "class": "btn-primary", "handlerTemplate": "run"})
                        cfg["fields"] = self._model_schema[nm]
                        cfgs[res_name] = cfg
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
            tbl = mname.split('/')[-1]
            by_db.setdefault(db_name, {})[tbl] = self._model_schema[mname]
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

            # Start proxy backends
            for pname, pcfg in self._proxy_configs.items():
                proxy_port = pcfg.get("port")
                if proxy_port:
                    from .proxy import ProxyBackend
                    pb = ProxyBackend(self, pcfg, pname)
                    self._proxy_backends[pname] = pb
                    await pb.start(host, proxy_port)
                    print(f"nimbo  PROXY {pname} {host}:{proxy_port}")
                else:
                    from .proxy import ProxyInlineHandler
                    handler = ProxyInlineHandler(self, pcfg, pname)
                    self._proxy_backends[pname] = handler
                    asyncio.create_task(handler.start_discovery())
                    print(f"nimbo  PROXY {pname} (inline)")

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
            for pb in self._proxy_backends.values():
                asyncio.run(pb.close())
            if hasattr(self, '_ws_lib_backend'):
                asyncio.run(self._ws_lib_backend.close())
