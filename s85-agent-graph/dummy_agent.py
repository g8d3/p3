#!/usr/bin/env python3
"""dummy_agent.py — Agent de prueba que se queda dormido 120s para probar el watchdog."""
import time, sys
print(f"[dummy] PID={sys.argv[1] if len(sys.argv)>1 else '?'} durmiendo 120s...")
sys.stdout.flush()
time.sleep(120)
print("[dummy] despierto")
