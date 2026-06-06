import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from nimbo import App

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


if __name__ == "__main__":
    app.serve(ws_backend="websockets", reload=True)
