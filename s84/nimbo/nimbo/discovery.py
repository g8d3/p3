import psutil


AGENT_WHITELIST = {"tmux", "opencode", "python3", "crush", "node", "bash", "zsh"}


def default_discovery():
    agents = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "create_time"]):
        try:
            info = p.info
            name = (info.get("name") or "").lower()
            if not any(w in name for w in AGENT_WHITELIST):
                continue
            agents.append({
                "agent_id": f"{info['name']}-{info['pid']}",
                "pid": info["pid"],
                "cpu": round(info.get("cpu_percent", 0) or 0, 1),
                "mem_pct": round(info.get("memory_percent", 0) or 0, 1),
                "window": info.get("name", ""),
                "status": "active",
                "last_active": __import__("time").time(),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return agents
