import asyncio
import json
import psutil

from .server import Response


PROCESS_FIELDS = [{"name": "pid", "type": "int"},
                   {"name": "name", "type": "string"},
                   {"name": "cpu_percent", "type": "float", "label": "CPU%"},
                   {"name": "memory_percent", "type": "float", "label": "MEM%"},
                   {"name": "status", "type": "string"}]


def register_system_endpoints(app):
    proc_attrs = ["pid", "name", "cpu_percent", "memory_percent", "status", "create_time"]

    @app.route("/api/process", methods=["GET"])
    async def list_processes(req):
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

    @app.route("/api/process/<id>", methods=["DELETE"])
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

    @app.route("/api/resources", methods=["GET"])
    async def get_resources(req):
        loop = asyncio.get_event_loop()
        cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0.5))
        mem = psutil.virtual_memory()
        return {
            "cpu": cpu,
            "memory": {"percent": mem.percent, "total": mem.total, "available": mem.available},
            "disk": {"percent": psutil.disk_usage("/").percent},
            "net": {"bytes_sent": psutil.net_io_counters().bytes_sent, "bytes_recv": psutil.net_io_counters().bytes_recv},
        }


LOG_SCHEMA = [{"name": "source", "type": "string", "default": ""},
              {"name": "level", "type": "string", "default": "info"},
              {"name": "content", "type": "string", "default": ""},
              {"name": "time", "type": "string", "default": ""}]


def register_log_model(app):
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
