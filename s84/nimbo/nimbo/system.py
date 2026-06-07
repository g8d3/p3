import asyncio
import json
import subprocess
import psutil

from .server import Response


PROCESS_FIELDS = [{"name": "pid", "type": "int"},
                   {"name": "name", "type": "string"},
                   {"name": "cpu_percent", "type": "float", "label": "CPU%"},
                   {"name": "memory_percent", "type": "float", "label": "MEM%"},
                   {"name": "status", "type": "string"}]


def register_system_endpoints(app):
    app._model_schema["process"] = PROCESS_FIELDS
    app._model_db["process"] = None
    app._register_models_route()

    @app.route("/api/process/schema", methods=["GET"])
    async def proc_schema(req):
        return {"name": "process", "fields": PROCESS_FIELDS}

    proc_attrs = ["pid", "name", "cpu_percent", "memory_percent", "status", "create_time"]

    @app.route("/api/system/processes", methods=["GET"])
    async def get_processes(req):
        procs = []
        for p in psutil.process_iter(proc_attrs):
            try:
                info = p.info
                if info.get("cpu_percent") is not None:
                    info["cpu_percent"] = round(info["cpu_percent"], 1)
                if info.get("memory_percent") is not None:
                    info["memory_percent"] = round(info["memory_percent"], 1)
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(procs, key=lambda x: x.get("cpu_percent", 0), reverse=True)[:50]

    @app.route("/api/system/resources", methods=["GET"])
    async def get_resources(req):
        loop = asyncio.get_event_loop()
        cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0.5))
        return {
            "cpu": cpu,
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("/")._asdict(),
            "net": psutil.net_io_counters()._asdict(),
            "uptime": psutil.boot_time(),
        }

    @app.route("/api/system/kill/<id>", methods=["POST"])
    async def kill_process(req, id):
        try:
            p = psutil.Process(int(id))
            name = p.name()
            p.terminate()
            return {"killed": int(id), "name": name}
        except psutil.NoSuchProcess:
            return Response({"error": "process not found"}, 404)
        except psutil.AccessDenied:
            return Response({"error": "access denied"}, 403)
        except Exception as e:
            return Response({"error": str(e)}, 500)

    @app.route("/api/exec", methods=["POST"])
    async def execute_command(req):
        data = req.json
        cmd = data.get("command", "")
        timeout = data.get("timeout", 30)
        if not cmd:
            return Response({"error": "no command"}, 400)
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            try: proc.kill(); await proc.wait()
            except: pass
            return {"stdout": "", "stderr": "Timed out", "returncode": -1}
        except Exception as e:
            return Response({"error": str(e)}, 500)


LOG_SCHEMA = [{"name": "source", "type": "string", "default": ""},
              {"name": "level", "type": "string", "default": "info"},
              {"name": "content", "type": "string", "default": ""},
              {"name": "time", "type": "string", "default": ""}]


def register_log_model(app):
    # Register custom routes BEFORE model CRUD to avoid <id> catch-all
    @app.route("/api/log/recent", methods=["GET"])
    async def recent_logs(req):
        all_logs = app._db.list("log")
        return all_logs[-50:]

    app._register_model(None, table="log", fields=LOG_SCHEMA)

    @app.ws_handler(topic="logs")
    async def ws_logs(ws):
        app._ws_manager.add(ws, "logs")
        while not ws.closed:
            msg = await ws.recv()
            if msg:
                try:
                    data = json.loads(msg)
                    if data.get("type") == "log":
                        entry = data.get("data", {})
                        ts = __import__("time").strftime("%H:%M:%S")
                        app._db.create("log", {
                            "source": entry.get("source", "client"),
                            "level": entry.get("level", "info"),
                            "content": entry.get("content", ""),
                            "time": ts,
                        })
                        app._db.engine._conn.execute(
                            "DELETE FROM log WHERE id NOT IN (SELECT id FROM log ORDER BY id DESC LIMIT 200)"
                        )
                        app._db.engine._conn.commit()
                        entry["time"] = ts
                        await app._ws_manager.broadcast(
                            json.dumps({"type": "log", "data": entry}),
                            topic="logs"
                        )
                except json.JSONDecodeError:
                    pass
