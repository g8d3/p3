#!/usr/bin/env python3
"""
test_cycle.py — Test the full cooperative cycle end-to-end.

Simulates proxy data with a stuck agent, runs helperd,
verifies the help message is sent and recorded.
"""
import json, os, sys, time, urllib.request
from pathlib import Path

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(BASE))
from core.helperd import Helperd, write_bus_message, append_log
from core.graph import Graph
from core.config import PROXY_HEALTH

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} {detail}")

def simulate_stuck_agent():
    """Register a fake stuck agent in the proxy by posting to /agent/register."""
    import urllib.request
    data = json.dumps({"agent": "worker-test", "pid": 99999, "host": "test"}).encode()
    req = urllib.request.Request(
        f"http://localhost:9098/agent/register",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=5)


print("=== Cooperative Cycle Test ===\n")

# 1. Graph setup
g = Graph()
g.register_agent("worker-test", {"type": "test", "window": 99})
g.register_agent("peer-test", {"type": "test", "window": 98})
check("Graph: agents registered",
      len(g.query_nodes(type="agent")) >= 2)

# 2. Write a help message to bus
write_bus_message("peer-test", "[TEST] Can you check worker-test?", trace_id="test-help-1")
bus_file = list((Path("/tmp/agent-bus") / "peer-test" / "in").glob("helperd-*"))
check("Bus: help message written to peer inbox", len(bus_file) > 0)

# 3. Record help in graph
eid = g.add_relationship("helperd", "helped", "worker-test",
                          {"note": "Test help", "reason": "stuck"})
edges = g.get_edges(type="helped")
check("Graph: help relationship recorded", len(edges) > 0)

# 4. Test find_peer_to_help
from core.helperd import find_peer_to_help
fake_agents = {
    "worker-test": {"last_s": 60, "never_active": False, "idle": True},
    "peer-test": {"last_s": 2, "never_active": False, "idle": False},
}
peer = find_peer_to_help("worker-test", fake_agents)
check("Helperd: finds nearest active peer", peer == "peer-test")

# 5. Simulate the reflex
h = Helperd()
h.help_history["worker-test"] = []
h._reflex_help("worker-test", fake_agents, "stuck", 60)
check("Helperd: reflex sends help", len(h.help_history.get("worker-test", [])) > 0)
if h.help_history.get("worker-test"):
    check("Helperd: help has peer", h.help_history["worker-test"][0]["peer"] == "peer-test")
    check("Helperd: help has reason", h.help_history["worker-test"][0]["reason"] == "stuck")

# 6. Test cooldown
h.last_help["worker-test"] = time.time()
was_sent = h._on_cooldown("worker-test")
check("Helperd: cooldown works", was_sent == True)

# 7. Save & load acks
h._save_acks()
h2 = Helperd()
check("Helperd: acks persist across restarts",
      "worker-test" in h2.help_history)

# 8. Test resolution detection
fake_agents["worker-test"]["last_s"] = 5
fake_agents["worker-test"]["never_active"] = False
h._check_resolved_helps(fake_agents)
all_resolved = all(h.get("resolved") for h in h.help_history.get("worker-test", []))
check("Helperd: marks resolved when agent recovers", all_resolved)

# 9. Test proxy health endpoint
try:
    data = json.loads(urllib.request.urlopen(PROXY_HEALTH, timeout=5).read())
    check("Proxy: health endpoint responds", "agents" in data)
except Exception as e:
    check("Proxy: health endpoint", False, str(e))

# 10. Test dashboard APIs
for endpoint in ["/api/team", "/api/helps", "/api/graph", "/api/log"]:
    try:
        resp = urllib.request.urlopen(f"http://localhost:9093{endpoint}", timeout=5)
        data = json.loads(resp.read())
        check(f"Dashboard: {endpoint} responds", True)
    except Exception as e:
        check(f"Dashboard: {endpoint}", False, str(e))

print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")

# Cleanup test data
g.delete_node("worker-test")
g.delete_node("peer-test")
for e in g.get_edges():
    if e["source_id"] in ("helperd", "watcher"):
        g.delete_edge(e["id"])
g.close()
