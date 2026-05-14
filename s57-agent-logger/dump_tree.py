#!/usr/bin/env python3
"""
Dump del árbol del monitor desde la terminal.
Muestra el mismo árbol que se ve en el TUI pero como texto.
"""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
STATUS_ICONS = {
    "active": "🟢", "in_progress": "🟡", "running": "🟡",
    "completed": "✅", "success": "✅",
    "error": "🔴", "failure": "🔴", "failed": "🔴",
    "pending": "⏳", "idle": "⚪", "warning": "⚠️",
    "cancelled": "✖️", "stopped": "⏹", "unknown": "❓",
}
LOG_ICONS = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "🔴", "DEBUG": "🔵", "CRITICAL": "💀"}

def load(name):
    p = DATA_DIR / name
    if not p.exists(): return []
    with open(p) as f: return list(csv.DictReader(f))

def si(s): return STATUS_ICONS.get(s.lower().strip(), "❓")
def li(l): return LOG_ICONS.get(l.upper().strip(), "📝")

def main():
    agents = load("agents.csv")
    tasks = load("tasks.csv")
    logs = load("logs.csv")

    # Build task tree
    by_agent = {}
    for t in tasks:
        by_agent.setdefault(t.get("agent_id",""), []).append(dict(t))
    task_tree = {}
    for aid, ats in by_agent.items():
        idx = {}
        for t in ats:
            t["children"] = []
            idx[t["task_id"]] = t
        roots = []
        for t in ats:
            p = t.get("parent_task_id","")
            if p and p in idx:
                idx[p]["children"].append(t)
            else:
                roots.append(t)
        task_tree[aid] = roots

    logs_by_t = {}
    for l in logs:
        logs_by_t.setdefault(l.get("task_id",""), []).append(l)
    errs_by_a = {}
    for l in logs:
        if l.get("level","").upper() in ("ERROR","CRITICAL"):
            errs_by_a.setdefault(l.get("agent_id",""), []).append(l)

    print("=" * 68)
    print(f"  🤖  AGENT MONITOR  —  {len(agents)} agents  {sum(1 for a in agents if a.get('status') in ('active','in_progress','running'))} active  {sum(1 for a in agents if a.get('status') in ('error','failure','failed'))} errors")
    print("=" * 68)

    for agent in agents:
        aid = agent["agent_id"]
        st = agent.get("status","?")
        icon = si(st)
        name = agent.get("name", aid)
        
        # Color tag
        if st in ("error","failure","failed"): tag = f"[ERR]"
        elif st in ("in_progress","running"): tag = f"[RUN]"
        elif st == "active": tag = f"[ACT]"
        else: tag = f"[---]"
        
        print(f"\n  {icon} {name} {tag}  role={agent.get('role','')}  model={agent.get('model','')}")

        # Errors
        errs = errs_by_a.get(aid, [])
        if errs:
            print(f"    🔴  Errors ({len(errs)}):")
            for e in errs[:3]:
                print(f"      └─ 🔴 {e.get('message','')[:90]}")
            if len(errs) > 3:
                print(f"      └─ ... y {len(errs)-3} más")

        # Tasks
        ats = task_tree.get(aid, [])
        if ats:
            print(f"    📋  Tasks:")
            for t in ats:
                print_task(t, logs_by_t, 3)
        
    print()

def print_task(t, logs_by_t, indent=0, prefix="└─"):
    icon = si(t.get("status",""))
    sp = "  " * indent
    print(f"{sp}  {prefix} {icon} {t.get('description','?')}  [{t.get('status','?')}]")
    
    tl = logs_by_t.get(t["task_id"], [])
    for l in tl[-5:]:
        lvl = l.get("level","INFO").upper()
        licon = li(lvl)
        print(f"{sp}      {licon} {l.get('message','')[:80]}")
    
    kids = t.get("children", [])
    for i, kid in enumerate(kids):
        p = "├─" if i < len(kids)-1 else "└─"
        print_task(kid, logs_by_t, indent + 1, p)

if __name__ == "__main__":
    main()
