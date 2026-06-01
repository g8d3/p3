#!/usr/bin/env python3
"""Extract one Crush session to plain text for LLM analysis."""
import json
import sqlite3
import sys

db_path = sys.argv[1]
session_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get session info
cur.execute("SELECT id, title, message_count FROM sessions ORDER BY created_at")
sessions = cur.fetchall()
if session_idx >= len(sessions):
    print(f"Solo hay {len(sessions)} sesiones (índice {session_idx})")
    sys.exit(1)

sid, title, count = sessions[session_idx]
print(f"=== SESIÓN: {title[:80]} ===")
print(f"=== ID: {sid} | {count} mensajes ===\n")

# Get messages
cur.execute(
    "SELECT datetime(created_at,'unixepoch'), role, parts FROM messages WHERE session_id = ? ORDER BY created_at",
    (sid,),
)

for ts, role, parts_json in cur.fetchall():
    try:
        parts = json.loads(parts_json)
    except json.JSONDecodeError:
        continue

    texts = []
    for p in parts:
        if p.get("type") == "text":
            t = p.get("data", {}).get("text", "")
            if t:
                texts.append(t)
        elif p.get("type") == "reasoning":
            t = p.get("data", {}).get("thinking", "")
            if t:
                texts.append(f"[razonamiento]: {t[:200]}...")
        elif p.get("type") == "tool_result":
            name = p.get("data", {}).get("name", "tool")
            content = p.get("data", {}).get("content", "")
            texts.append(f"[tool:{name}]: {str(content)[:150]}")
        elif p.get("type") == "finish":
            pass

    full_text = " | ".join(texts)
    if full_text:
        label = "USR" if role == "user" else "AST" if role == "assistant" else "TOL"
        print(f"[{ts}] {label}: {full_text[:500]}")
        print()

conn.close()
