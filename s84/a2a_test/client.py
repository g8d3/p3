#!/usr/bin/env python3
"""
A2A Test Client — orchestrates test scenarios against A2A agents.

Usage:
    python3 client.py <alpha_url> <beta_url>
    python3 client.py http://localhost:9001 http://localhost:9002
"""

import json
import sys
import time
import urllib.request
import urllib.error

# ── HTTP helpers ──

def a2a_post(url: str, body: dict) -> dict:
    """Send JSON-RPC-ish POST to A2A endpoint."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": {"code": e.code, "body": e.read().decode()[:200]}}
    except Exception as e:
        return {"error": str(e)}

def a2a_get(url: str) -> dict:
    """GET from A2A endpoint."""
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": {"code": e.code, "body": e.read().decode()[:200]}}
    except Exception as e:
        return {"error": str(e)}

def get_agent_card(url: str) -> dict:
    """Fetch Agent Card from /.well-known/agent.json"""
    return a2a_get(f"{url.rstrip('/')}/.well-known/agent.json")

def send_message(url: str, text: str, context_id: str = "") -> dict:
    """Send a message to an A2A agent."""
    body = {
        "message": {
            "role": "user",
            "parts": [{"text": text}],
            "messageId": f"msg-{int(time.time())}"
        }
    }
    if context_id:
        body["message"]["contextId"] = context_id
    return a2a_post(f"{url.rstrip('/')}/message:send", body)

def get_task(url: str, task_id: str) -> dict:
    """Get task status by ID."""
    return a2a_get(f"{url.rstrip('/')}/tasks/{task_id}")

def cancel_task(url: str, task_id: str) -> dict:
    """Cancel a task."""
    return a2a_post(f"{url.rstrip('/')}/tasks/{task_id}:cancel", {})

def list_tasks(url: str) -> list:
    """List all tasks on an agent."""
    result = a2a_get(f"{url.rstrip('/')}/tasks")
    if "result" in result:
        return result["result"]
    return []


# ── Test Scenarios ──

def test_agent_discovery(alpha_url: str, beta_url: str):
    """Test 1: Agent Card discovery."""
    print("\n" + "="*70)
    print("TEST 1: Agent Discovery (Agent Cards)")
    print("="*70)

    for name, url in [("Alpha", alpha_url), ("Beta", beta_url)]:
        card = get_agent_card(url)
        if "name" in card:
            print(f"  ✅ {name}: found '{card['name']}'")
            print(f"     Skills: {[s['name'] for s in card.get('skills', [])]}")
            print(f"     URL: {card.get('url')}")
            print(f"     Capabilities: {json.dumps(card.get('capabilities', {}))}")
        else:
            print(f"  ❌ {name}: no Agent Card — {card.get('error', 'unknown')}")
    print()


def test_basic_task(alpha_url: str):
    """Test 2: Basic task execution (send → poll → complete)."""
    print("="*70)
    print("TEST 2: Basic Task Execution")
    print("="*70)

    result = send_message(alpha_url, "What is the weather like today?")
    if "error" in result:
        print(f"  ❌ Send failed: {result['error']}")
        return None, None

    task = result.get("result", result)
    tid = task.get("id", "unknown")
    print(f"  ✅ Task created: {tid[:20]}...")
    print(f"     Initial state: {task['status']['state']}")

    # Poll until complete
    for i in range(10):
        time.sleep(0.5)
        task = get_task(alpha_url, tid)
        state = task.get("status", {}).get("state", "unknown") if "result" not in task else task["result"]["status"]["state"]
        if "result" in task:
            state = task["result"]["status"]["state"]
            print(f"     Poll {i+1}: {state}")
            if state == "completed":
                artifacts = task["result"].get("artifacts", [])
                for art in artifacts:
                    for part in art.get("parts", []):
                        if "text" in part:
                            print(f"  ✅ Response: {part['text'][:150]}...")
                return tid, task["result"]
        else:
            print(f"     Poll {i+1}: {state}")

    print("  ⚠️  Task did not complete in time")
    return tid, None


def test_cancellation(alpha_url: str):
    """Test 3: Task cancellation."""
    print("\n" + "="*70)
    print("TEST 3: Task Cancellation")
    print("="*70)

    # Send a task
    result = send_message(alpha_url, "Write a very long report about everything")
    task = result.get("result", result)
    tid = task.get("id", "unknown")
    print(f"  ✅ Task created: {tid[:20]}...")

    # Cancel it immediately
    time.sleep(0.3)
    cancel_result = cancel_task(alpha_url, tid)
    print(f"  Cancel response state: {cancel_result.get('result', cancel_result).get('status', {}).get('state', '?')}")

    # Verify cancelled state
    time.sleep(0.5)
    task = get_task(alpha_url, tid)
    if "result" in task:
        state = task["result"]["status"]["state"]
        print(f"  ✅ Task state after cancellation: {state}")
        if state == "canceled":
            print("  ✅ Cancellation successful!")
        else:
            print(f"  ⚠️  Unexpected state: {state}")
    else:
        print(f"  ⚠️  Could not verify: {task}")


def test_quality_gate_limitation(beta_url: str):
    """Test 4: Beta's custom quality check + note that A2A lacks this."""
    print("\n" + "="*70)
    print("TEST 4: Quality Gate (custom, NOT in A2A spec)")
    print("="*70)

    # Good input
    result = send_message(beta_url, "Review this code: def foo(): pass")
    task = result.get("result", result)
    tid = task.get("id", "unknown")
    time.sleep(1.5)
    task = get_task(beta_url, tid)
    if "result" in task:
        state = task["result"]["status"]["state"]
        arts = task["result"].get("artifacts", [])
        text = arts[0]["parts"][0]["text"] if arts else ""
        if "PASSED" in text or "approved" in text.lower():
            print(f"  ✅ Good input approved (state: {state})")
        print(f"     Response: {text[:120]}...")

    # Problematic input
    result = send_message(beta_url, "This code has a bug that needs fixing")
    task = result.get("result", result)
    tid = task.get("id", "unknown")
    time.sleep(1.5)
    task = get_task(beta_url, tid)
    if "result" in task:
        state = task["result"]["status"]["state"]
        arts = task["result"].get("artifacts", [])
        text = arts[0]["parts"][0]["text"] if arts else ""
        if "FAILED" in text or "rejected" in text.lower():
            print(f"  ✅ Bad input flagged (state: {state})")
        print(f"     Response: {text[:120]}...")

    print("\n  ⚠️  KEY FINDING: A2A has NO standard quality gate.")
    print("     The 'state' is 'completed' in both cases — the protocol")
    print("     doesn't distinguish between 'completed successfully'")
    print("     and 'completed with issues found'.")
    print("     Quality is buried in the artifact text, not in the state machine.")


def test_agent_card_based_discovery(alpha_url: str, beta_url: str):
    """Test 5: One agent discovers another via Agent Card."""
    print("\n" + "="*70)
    print("TEST 5: Cross-Agent Discovery")
    print("="*70)

    alpha_card = get_agent_card(alpha_url)
    beta_card = get_agent_card(beta_url)

    print(f"  Alpha discovers Beta:")
    print(f"     Name: {beta_card.get('name')}")
    print(f"     Skills: {[s['name'] for s in beta_card.get('skills', [])]}")
    print(f"     URL: {beta_card.get('url')}")

    # Check if Alpha's skills mention delegation
    alpha_skills = [s['name'] for s in alpha_card.get('skills', [])]
    if 'delegate' in [s.lower() for s in alpha_skills]:
        print(f"  ✅ Alpha CAN delegate based on skill matching")
    else:
        print(f"  ⚠️  Alpha doesn't advertise delegation — would need out-of-band logic")

    print("\n  ⚠️  LIMITATION: A2A Agent Cards describe capabilities but")
    print("     don't include quality criteria, acceptance tests, or")
    print("     expected output validation. That's all out-of-band.")


def test_context_sessions(alpha_url: str):
    """Test 6: Multi-turn conversation via contextId."""
    print("\n" + "="*70)
    print("TEST 6: Multi-turn Context (contextId)")
    print("="*70)

    session_id = f"session-{int(time.time())}"

    # Turn 1
    r1 = send_message(alpha_url, "My name is Alice", session_id)
    t1 = r1.get("result", r1)
    print(f"  Turn 1 task: {t1.get('id', '?')[:20]}")
    time.sleep(1)

    # Turn 2 — same contextId
    r2 = send_message(alpha_url, "What's my name?", session_id)
    t2 = r2.get("result", r2)
    print(f"  Turn 2 task: {t2.get('id', '?')[:20]}")

    time.sleep(1)
    task = get_task(alpha_url, t2.get("id", ""))
    if "result" in task:
        arts = task["result"].get("artifacts", [])
        text = arts[0]["parts"][0]["text"] if arts else ""
        if "Alice" in text:
            print(f"  ✅ Context preserved! Agent remembers 'Alice'")
        else:
            print(f"  ⚠️  Context NOT used (or agent doesn't track)")
        print(f"     Response: {text[:150]}...")

    print("\n  ⚠️  NOTE: A2A has contextId but doesn't mandate context")
    print("     storage or retrieval. It's up to the agent implementation.")


def test_no_quality_in_state_machine():
    """Test 7: Show that A2A state machine has no quality dimension."""
    print("\n" + "="*70)
    print("TEST 7: A2A State Machine — Missing Quality Dimension")
    print("="*70)

    print("""
  A2A Task States:
    submitted → working → completed  ✅ (success)
                        → failed      ❌ (error)
                        → canceled    🛑 (user-initiated stop)
                        → rejected    🚫 (server refused)
                        → input-required  (needs more info)
                        → auth-required   (needs auth)

  MISSING from the state machine:
    → pending-review      (work done, needs validation)     🔍
    → needs-revision      (checker rejected, go back)       🔄
    → escalated           (human intervention needed)       ⚠️
    → quality-approved    (passed all gates)                ✅

  A2A's design assumption: agents are opaque and trustworthy.
  Quality is implicitly assumed, never checked at the protocol level.
    """)


def test_list_tasks(alpha_url: str):
    """Test 8: List tasks."""
    print("\n" + "="*70)
    print("TEST 8: List Tasks")
    print("="*70)
    tasks = list_tasks(alpha_url)
    if isinstance(tasks, list):
        print(f"  Alpha has {len(tasks)} task(s):")
        for t in tasks:
            print(f"    - {t.get('id', '?')[:20]}... → {t.get('status', {}).get('state', '?')}")
    else:
        print(f"  Tasks: {tasks}")


# ── Main ──

def main():
    alpha_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9001"
    beta_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:9002"

    print(f"Alpha agent URL: {alpha_url}")
    print(f"Beta agent URL:  {beta_url}")

    # Wait for servers to be ready
    for url, name in [(alpha_url, "Alpha"), (beta_url, "Beta")]:
        for i in range(10):
            try:
                card = get_agent_card(url)
                if "name" in card:
                    print(f"  {name} ready (card found)")
                    break
            except:
                pass
            time.sleep(0.5)
        else:
            print(f"  ❌ {name} not reachable. Start agents first!")
            sys.exit(1)

    # Run tests
    test_agent_discovery(alpha_url, beta_url)
    test_basic_task(alpha_url)
    test_cancellation(alpha_url)
    test_quality_gate_limitation(beta_url)
    test_agent_card_based_discovery(alpha_url, beta_url)
    test_context_sessions(alpha_url)
    test_no_quality_in_state_machine()
    test_list_tasks(alpha_url)

    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
