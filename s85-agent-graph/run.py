#!/usr/bin/env python3
"""
run.py — Safe command executor for agents.
Runs command with hard timeout, logs to graph. Never blocks forever.
Usage: python3 run.py --timeout 5 --name "test" "sleep 10"
"""
import argparse, os, subprocess, sys, time
from pathlib import Path

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(BASE))
from graph.core import Graph

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--name", default="cmd")
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.cmd:
        print("run.py --timeout N --name X -- <command>")
        sys.exit(1)

    cmd_str = " ".join(args.cmd)
    g = Graph(str(BASE / "data" / "agent-graph.db"))
    g.set_agent("run")

    timed_out = False
    exit_code = 0
    stdout = stderr = ""

    print(f"⏱  {args.name}: {cmd_str[:120]}", flush=True)

    with g.op(args.name, timeout_s=args.timeout):
        try:
            r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=args.timeout)
            exit_code = r.returncode
            stdout = r.stdout.strip()[-300:] if r.stdout else ""
            stderr = r.stderr.strip()[-300:] if r.stderr else ""
            if stdout: print(stdout, flush=True)
            if stderr and exit_code != 0: print(f"! {stderr}", flush=True)
            print(f"→ {'ok' if exit_code==0 else 'fail'} (exit={exit_code})", flush=True)
            g.add_node("artifact", f"run-{args.name[:20]}",
                {"command": cmd_str, "status": "ok" if exit_code==0 else "fail",
                 "exit": exit_code, "stdout": stdout, "stderr": stderr}, agent_id="run")
        except subprocess.TimeoutExpired:
            timed_out = True
            print(f"💥 TIMEOUT ({args.timeout}s)", flush=True)
            g.add_node("error", f"timeout: {args.name}",
                {"command": cmd_str, "timeout_s": args.timeout}, agent_id="run")
        except Exception as e:
            print(f"💥 {e}", flush=True)
            exit_code = 1

    # exit AFTER the 'with' block so the op is properly closed
    sys.exit(124 if timed_out else exit_code)

if __name__ == "__main__":
    main()
