import os
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROXY_URL = os.environ.get("PROXY_URL", "http://localhost:9098")
PROXY_HEALTH = f"{PROXY_URL}/health"
PROXY_LOG = f"{PROXY_URL}/log"

GRAPH_DB = str(BASE / "data" / "agent-graph.db")
BUS_DIR = "/tmp/agent-bus"
BUS_HISTORY = f"{BUS_DIR}/history"

STUCK_AFTER = int(os.environ.get("STUCK_AFTER", "120"))  # 2min sin LLM = stuck (antes 25s, causaba falsos positivos)
IDLE_AFTER = int(os.environ.get("IDLE_AFTER", "600"))   # 10min idle before alerting peers
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))  # faster: every 5s
HELP_COOLDOWN = int(os.environ.get("HELP_COOLDOWN", "30"))  # reduced: 30s

AGENT_WINDOWS = os.environ.get("AGENT_WINDOWS", "1:worker-1,2:worker-2,3:watcher")
