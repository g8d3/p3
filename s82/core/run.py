#!/usr/bin/env python3
"""
run.py — Async command runner. Never blocks.

Usage:
  python3 core/run.py <command>                    # run with defaults
  python3 core/run.py --name test "sleep 5 && ls"  # named run, 30s timeout
  python3 core/run.py --name test --timeout 10 "cmd"
  python3 core/run.py --status                     # table of all runs
  python3 core/run.py --status --json              # JSON output
  python3 core/run.py --show <name>                # full details

Design: forks a child process, writes status files. Never blocks the caller.
"""
import json, os, subprocess, sys, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
RUNS_DIR = BASE / "data" / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
STATUS = BASE / "data" / "runs.json"


def _load():
    if STATUS.exists():
        return json.loads(STATUS.read_text())
    return {}

def _save(runs):
    STATUS.write_text(json.dumps(runs, indent=2, default=str))

def run(name, cmd, timeout=30):
    runs = _load()
    out_file = RUNS_DIR / f"{name}.out"
    err_file = RUNS_DIR / f"{name}.err"
    start = time.time()

    entry = {
        "name": name, "cmd": cmd[:200], "timeout": timeout,
        "started_at": datetime.now().isoformat(), "pid": None,
        "status": "running", "exit_code": None,
    }
    runs[name] = entry
    _save(runs)

    pid = os.fork()
    if pid == 0:
        # Child: run command
        try:
            with open(out_file, "w") as out, open(err_file, "w") as err:
                p = subprocess.Popen(cmd, shell=True, stdout=out, stderr=err)
                try:
                    p.wait(timeout=timeout)
                    code = p.returncode
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
                    code = -1
        except Exception as e:
            code = -2
            err_file.write_text(str(e))
        # Write result from child process
        result = {"status": "done" if code == 0 else "timeout" if code == -1 else "error",
                  "exit_code": code, "ended_at": datetime.now().isoformat(),
                  "duration_s": round(time.time() - start, 1)}
        r = _load()
        if name in r:
            r[name].update(result)
            _save(r)
        os._exit(0)
    else:
        entry["pid"] = pid
        runs[name]["pid"] = pid
        _save(runs)
        return {"ok": True, "name": name, "pid": pid, "status": "running"}


def status():
    runs = _load()
    result = []
    for name, r in sorted(runs.items(), key=lambda x: x[1].get("started_at", ""), reverse=True)[:20]:
        out_file = RUNS_DIR / f"{name}.out"
        tail = out_file.read_text().strip().split("\n")[-3:] if out_file.exists() else []
        result.append({
            "name": name, "cmd": r.get("cmd", "")[:80],
            "status": r.get("status", "?"), "exit": r.get("exit_code"),
            "dur": r.get("duration_s"), "started": str(r.get("started_at", ""))[11:19],
            "tail": "; ".join(tail)[:100],
        })
    return result


def table(records):
    if not records:
        return "(no runs)"
    cols = ["name", "status", "dur", "exit", "cmd", "tail"]
    w = {c: len(c) for c in cols}
    for r in records:
        for c in cols:
            w[c] = max(w[c], len(str(r.get(c, ""))))
    sep = "+" + "+".join("-" * (v + 2) for v in w.values()) + "+"
    h = "| " + " | ".join(c.upper().ljust(w[c]) for c in cols) + " |"
    lines = [sep, h, sep]
    for r in records:
        row = "| " + " | ".join(str(r.get(c, "")).ljust(w[c]) for c in cols) + " |"
        lines.append(row)
    lines.append(sep)
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or "--help" in args:
        print("Usage: run.py [--name X] [--timeout N] <command>")
        print("       run.py --status [--json]")
        print("       run.py --show <name>")
        sys.exit(0)

    if args[0] == "--status":
        data = status()
        if "--json" in args:
            print(json.dumps(data, indent=2, default=str))
        else:
            print(table(data))

    elif args[0] == "--show" and len(args) > 1:
        name = args[1]
        runs = _load()
        r = runs.get(name)
        if r:
            print(json.dumps(r, indent=2, default=str))
            out_file = RUNS_DIR / f"{name}.out"
            if out_file.exists():
                print(f"\n--- stdout ---")
                print(out_file.read_text()[-500:])
        else:
            print(f"Run '{name}' not found. Available: {', '.join(list(runs.keys())[:10])}")

    elif args[0] == "--clean":
        import shutil
        shutil.rmtree(RUNS_DIR)
        RUNS_DIR.mkdir()
        STATUS.unlink(missing_ok=True)
        print("Cleaned")

    else:
        name = "cmd"
        timeout = 30
        cmd_parts = []
        i = 0
        while i < len(args):
            if args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]; i += 2
            elif args[i] == "--timeout" and i + 1 < len(args):
                timeout = int(args[i + 1]); i += 2
            else:
                cmd_parts.append(args[i]); i += 1
        cmd_str = " ".join(cmd_parts)
        if not cmd_str:
            print("No command specified"); sys.exit(1)
        result = run(name, cmd_str, timeout)
        print(json.dumps(result, default=str))
