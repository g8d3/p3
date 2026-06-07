import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from nimbo import App, Response

STATIC_DIR = Path(__file__).parent / "static"
app = App(__name__, static_dir=str(STATIC_DIR), db_url="sqlite:///data/agentui.db")


@app.model
class Agent:
    name: str
    status: str = "idle"
    pid: int = 0
    command: str = ""
    provider: str = "openai"


@app.model
class DataSource:
    name: str
    type: str = "sqlite"
    url: str = ""
    active: bool = True


@app.model
class Command:
    name: str
    shell: str = ""
    description: str = ""
    timeout: int = 30


@app.route("/api/commands/run/<id>", methods=["POST"])
async def run_custom_command(req, id):
    import asyncio
    cmd = app._db.read("command", id)
    if not cmd:
        return Response("", 404)
    data = req.json or {}
    shell = cmd["shell"]
    for k, v in data.items():
        shell = shell.replace("{{" + k + "}}", str(v))
    timeout = cmd.get("timeout") or 30
    try:
        proc = await asyncio.create_subprocess_shell(
            shell, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {"stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace"), "returncode": proc.returncode}
    except asyncio.TimeoutError:
        try: proc.kill(); await proc.wait()
        except: pass
        return {"stdout": "", "stderr": "Timed out", "returncode": -1}
    except Exception as e:
        return Response({"error": str(e)}, 500)


if __name__ == "__main__":
    app.serve(ws_backend="websockets", reload=True)
