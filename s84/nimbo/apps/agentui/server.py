import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from nimbo import App

app = App(__name__, db_url="sqlite:///data/agentui.db")


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
@app.run("shell", timeout="timeout")
class Command:
    name: str
    shell: str = ""
    description: str = ""
    timeout: int = 30


@app.system
class Process:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str


@app.log
class Log:
    source: str
    level: str
    content: str
    time: str


if __name__ == "__main__":
    app.serve(ws_backend="websockets", reload=True)
