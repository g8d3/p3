import asyncio
import json
import psutil

from .server import Response


SYSTEM_SOURCES = {
    "process": [{"name": "pid", "type": "int"},
                {"name": "name", "type": "string"},
                {"name": "cpu_percent", "type": "float", "label": "CPU%"},
                {"name": "memory_percent", "type": "float", "label": "MEM%"},
                {"name": "status", "type": "string"}],
    "mount": [{"name": "device", "type": "string"},
              {"name": "mount", "type": "string"},
              {"name": "fstype", "type": "string"},
              {"name": "usage", "type": "float", "label": "Usage%"}],
    "network": [{"name": "fd", "type": "int"},
                {"name": "family", "type": "string"},
                {"name": "type", "type": "string"},
                {"name": "laddr", "type": "string"},
                {"name": "raddr", "type": "string"},
                {"name": "status", "type": "string"}],
    "service": [{"name": "name", "type": "string"},
                {"name": "status", "type": "string"},
                {"name": "pid", "type": "int"},
                {"name": "started", "type": "string"}],
    "user": [{"name": "name", "type": "string"},
             {"name": "terminal", "type": "string"},
             {"name": "host", "type": "string"},
             {"name": "started", "type": "string"},
             {"name": "pid", "type": "int"}],
}


def infer_source(cls):
    name = cls.__name__.lower()
    if name in SYSTEM_SOURCES:
        return name
    for src in SYSTEM_SOURCES:
        if name.startswith(src):
            return src
    return "process"


def register_system_endpoints(app):
    _register_process_endpoints(app)
    _register_mount_endpoints(app)
    _register_network_endpoints(app)
    _register_service_endpoints(app)
    _register_user_endpoints(app)
    _register_resources(app)


def _register_process_endpoints(app):
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


def _register_mount_endpoints(app):
    @app.route("/api/mount", methods=["GET"])
    async def list_mounts(req):
        parts = psutil.disk_partitions()
        result = []
        for p in parts:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                usage_pct = round(usage.percent, 1)
            except (PermissionError, FileNotFoundError):
                usage_pct = 0.0
            result.append({
                "device": p.device,
                "mount": p.mountpoint,
                "fstype": p.fstype,
                "usage": usage_pct,
            })
        return result


def _register_network_endpoints(app):
    @app.route("/api/network", methods=["GET"])
    async def list_connections(req):
        conns = []
        for c in psutil.net_connections():
            try:
                conns.append({
                    "fd": c.fd or 0,
                    "family": str(c.family),
                    "type": str(c.type),
                    "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                    "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                    "status": c.status or "",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return conns[:100]


def _register_service_endpoints(app):
    @app.route("/api/service", methods=["GET"])
    async def list_services(req):
        result = []
        for s in psutil.win_service_iter() if hasattr(psutil, 'win_service_iter') else []:
            try:
                result.append({
                    "name": s.name(),
                    "status": s.status(),
                    "pid": s.pid() or 0,
                    "started": "",
                })
            except Exception:
                pass
        # On non-Windows, try reading from systemd
        if not result:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "systemctl", "list-units", "--type=service", "--all", "--no-pager",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                for line in stdout.decode().split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        result.append({
                            "name": parts[0],
                            "status": parts[3],
                            "pid": 0,
                            "started": "",
                        })
            except Exception:
                pass
        return result[:50]


def _register_user_endpoints(app):
    @app.route("/api/user", methods=["GET"])
    async def list_users(req):
        users = []
        for u in psutil.users():
            users.append({
                "name": u.name,
                "terminal": u.terminal or "",
                "host": u.host or "",
                "started": str(u.started),
                "pid": u.pid,
            })
        return users


def _register_resources(app):
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
    if "log" in app._model_schema:
        return
    app._register_log(type("Log", (), {"__annotations__": {}}))
