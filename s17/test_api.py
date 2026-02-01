#!/usr/bin/env python3
"""
Test client for AI agents to interact with Terminal AI Chat App.

This allows AI agents to:
- Send keystrokes to the TUI
- Read screen output
- Discover UX issues naturally

Usage:
    python test_api.py --help
    python test_api.py --health
    python test_api.py --tui-screen
    python test_api.py --tui-state
    python test_api.py --tui-key --key p
    python test_api.py --tui-keys --keys "p,m,a,enter"
"""

import argparse
import json
import urllib.request
import urllib.error
import sys

API_BASE = "http://localhost:8080"


def make_request(method: str, path: str, data: dict = None) -> dict:
    """Make HTTP request to API server."""
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(url, method=method, headers=headers)
    if data:
        req.data = json.dumps(data).encode()

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e}"}


def cmd_health():
    """Check API health."""
    result = make_request("GET", "/health")
    print(json.dumps(result, indent=2))


def cmd_list_providers():
    """List all providers."""
    result = make_request("GET", "/providers")
    print(json.dumps(result, indent=2))


def cmd_list_models():
    """List all models."""
    result = make_request("GET", "/models")
    print(json.dumps(result, indent=2))


def cmd_list_agents():
    """List all agents."""
    result = make_request("GET", "/agents")
    print(json.dumps(result, indent=2))


def cmd_list_sessions():
    """List all sessions."""
    result = make_request("GET", "/sessions")
    print(json.dumps(result, indent=2))


def cmd_create_session(name: str, provider: str, model: str, agent: str = None):
    """Create a new session."""
    data = {
        "name": name,
        "provider_name": provider,
        "model_name": model
    }
    if agent:
        data["agent_id"] = agent
    result = make_request("POST", "/sessions", data)
    print(json.dumps(result, indent=2))
    return result.get("id")


def cmd_get_session(session_id: str):
    """Get session details with messages."""
    result = make_request("GET", f"/sessions/{session_id}")
    print(json.dumps(result, indent=2))


def cmd_chat(session_id: str, message: str):
    """Send chat message and get response."""
    data = {
        "session_id": session_id,
        "message": message
    }
    result = make_request("POST", "/chat", data)
    print(json.dumps(result, indent=2))


def cmd_stats():
    """Get performance statistics."""
    result = make_request("GET", "/stats")
    print(json.dumps(result, indent=2))


def cmd_api_logs():
    """Get recent API logs."""
    result = make_request("GET", "/api-logs")
    print(json.dumps(result, indent=2))


def cmd_tui_screen():
    """Get current TUI screen text."""
    result = make_request("GET", "/screen")
    if "error" in result:
        print(f"Error: {result['error']}")
        return False
    print("=" * 80)
    print("TUI SCREEN OUTPUT")
    print("=" * 80)
    print(result.get("screen", ""))
    print("=" * 80)
    return True


def cmd_tui_state():
    """Get current TUI state."""
    result = make_request("GET", "/state")
    print(json.dumps(result, indent=2))
    return "error" not in result


def cmd_tui_key(key: str):
    """Send a keystroke to the TUI."""
    result = make_request("POST", "/keystroke", {"key": key})
    print(json.dumps(result, indent=2))
    return result.get("success", False)


def cmd_tui_keys(keys: str, delay: float = 0.1):
    """Send multiple keystrokes to the TUI."""
    key_list = [k.strip() for k in keys.split(",")]
    result = make_request("POST", "/keystrokes", {"keys": key_list, "delay": delay})
    print(json.dumps(result, indent=2))
    return all(r.get("success", False) for r in result.get("results", []))


def cmd_run_tests():
    """Run comprehensive tests and report results."""
    print("=" * 60)
    print("Terminal AI Chat App - Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Health Check", lambda: make_request("GET", "/health")),
        ("List Providers", lambda: make_request("GET", "/providers")),
        ("List Models", lambda: make_request("GET", "/models")),
        ("List Agents", lambda: make_request("GET", "/agents")),
        ("List Sessions", lambda: make_request("GET", "/sessions")),
        ("TUI Screen", lambda: make_request("GET", "/screen")),
        ("TUI State", lambda: make_request("GET", "/state")),
    ]

    results = []
    for name, test_fn in tests:
        print(f"Testing: {name}...", end=" ", flush=True)
        try:
            result = test_fn()
            if "error" in result:
                print(f"FAIL - {result['error']}")
                results.append((name, False, result["error"]))
            else:
                print("PASS")
                results.append((name, True, None))
        except Exception as e:
            print(f"ERROR - {e}")
            results.append((name, False, str(e)))

    print()
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    passed = sum(1 for _, p, _ in results if p)
    failed = len(results) - passed
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print()

    if failed > 0:
        print("Failed tests:")
        for name, _, error in results:
            if error:
                print(f"  - {name}: {error}")

    return failed == 0


def cmd_ux_exploration():
    """
    Explore TUI UX by sending keystrokes and analyzing screen output.
    This simulates how a human would discover the interface.
    """
    print("=" * 60)
    print("TUI UX Exploration - AI Agent Style")
    print("=" * 60)
    print()
    print("Simulating human exploration of the terminal interface...")
    print()

    exploration_steps = [
        ("Initial screen", []),
        ("Press '?' for help", ["?"]),
        ("Press '/' for chat", ["/"]),
        ("Press 'p' for providers", ["p"]),
        ("Press 'm' for models", ["m"]),
        ("Press 'a' for agents", ["a"]),
        ("Press 's' for sessions", ["s"]),
        ("Press 't' for tools", ["t"]),
        ("Press 'h' for schedules", ["h"]),
        ("Press 'enter'", ["enter"]),
        ("Press 'escape'", ["escape"]),
        ("Press arrow keys", ["up", "down", "left", "right"]),
        ("Press 'q' to quit", ["q"]),
    ]

    all_screens = []

    for description, keys in exploration_steps:
        print(f"Step: {description}")
        if keys:
            for key in keys:
                result = make_request("POST", "/keystroke", {"key": key})
                print(f"  Sent key '{key}': {result.get('success', 'N/A')}")
                if not result.get("success", False):
                    print(f"    Failed: {result.get('error', 'Unknown error')}")

        screen_result = make_request("GET", "/screen")
        screen = screen_result.get("screen", "")
        if screen:
            lines = screen.split("\n")
            non_empty = [l for l in lines if l.strip()]
            print(f"  Screen has {len(non_empty)} non-empty lines")
            if len(non_empty) > 0:
                print(f"  First line: {non_empty[0][:60]}...")
            all_screens.append((description, screen))
        print()

    print("=" * 60)
    print("UX Analysis Summary")
    print("=" * 60)
    print()

    issues = []

    for description, screen in all_screens:
        if not screen.strip():
            issues.append(f"{description}: Empty screen")
        elif "error" in screen.lower() or "fail" in screen.lower():
            issues.append(f"{description}: Error message found")

    if issues:
        print("Potential UX issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("No obvious UX issues detected from screen analysis")

    print()
    print("Full screen captures saved for analysis:")
    for i, (description, _) in enumerate(all_screens[:5]):
        print(f"  {i+1}. {description}")
    print()
    print("AI Agent can now analyze these screens to find UX problems!")

    return len(issues) == 0


def main():
    parser = argparse.ArgumentParser(
        description="AI Agent Test Client for Terminal AI Chat App",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Check if API is running
    python test_api.py --health

    # List all resources
    python test_api.py --providers
    python test_api.py --models
    python test_api.py --agents

    # TUI Control (for AI agent testing)
    python test_api.py --tui-screen           # Get current screen
    python test_api.py --tui-state            # Get TUI state
    python test_api.py --tui-key --key p      # Send 'p' key
    python test_api.py --tui-keys --keys "p,m,a,enter"  # Send multiple keys

    # Create a session and chat
    python test_api.py --session --name "test" --provider openai --model "GPT-4"
    python test_api.py --chat --session-id "<id>" --message "Hello!"

    # Run tests
    python test_api.py --test

    # AI UX exploration (simulates human testing)
    python test_api.py --explore
        """
    )

    parser.add_argument("--health", action="store_true", help="Check API health")
    parser.add_argument("--providers", action="store_true", help="List providers")
    parser.add_argument("--models", action="store_true", help="List models")
    parser.add_argument("--agents", action="store_true", help="List agents")
    parser.add_argument("--sessions", action="store_true", help="List sessions")
    parser.add_argument("--session", action="store_true", help="Create a session")
    parser.add_argument("--name", help="Session name for --session")
    parser.add_argument("--provider", help="Provider name for --session")
    parser.add_argument("--model", help="Model name for --session")
    parser.add_argument("--agent", help="Agent name for --session")
    parser.add_argument("--chat", action="store_true", help="Send chat message")
    parser.add_argument("--session-id", help="Session ID for --chat")
    parser.add_argument("--message", help="Message to send for --chat")
    parser.add_argument("--stats", action="store_true", help="Get performance stats")
    parser.add_argument("--logs", action="store_true", help="Get API logs")
    parser.add_argument("--test", action="store_true", help="Run test suite")
    parser.add_argument("--explore", action="store_true", help="AI UX exploration")
    parser.add_argument("--tui-screen", action="store_true", help="Get TUI screen text")
    parser.add_argument("--tui-state", action="store_true", help="Get TUI state")
    parser.add_argument("--tui-key", action="store_true", help="Send keystroke to TUI")
    parser.add_argument("--key", help="Key to send (for --tui-key)")
    parser.add_argument("--tui-keys", action="store_true", help="Send multiple keystrokes")
    parser.add_argument("--keys", help="Comma-separated keys (for --tui-keys)")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between keystrokes")

    args = parser.parse_args()

    if not any([args.health, args.providers, args.models, args.agents,
                args.sessions, args.session, args.chat, args.stats, args.logs,
                args.test, args.explore, args.tui_screen, args.tui_state,
                args.tui_key, args.tui_keys]):
        parser.print_help()
        return

    if args.health:
        cmd_health()
    elif args.providers:
        cmd_list_providers()
    elif args.models:
        cmd_list_models()
    elif args.agents:
        cmd_list_agents()
    elif args.sessions:
        cmd_list_sessions()
    elif args.session:
        if not args.name or not args.provider or not args.model:
            print("Error: --name, --provider, and --model required for --session")
            return
        cmd_create_session(args.name, args.provider, args.model, args.agent)
    elif args.chat:
        if not args.session_id or not args.message:
            print("Error: --session-id and --message required for --chat")
            return
        cmd_chat(args.session_id, args.message)
    elif args.stats:
        cmd_stats()
    elif args.logs:
        cmd_api_logs()
    elif args.test:
        cmd_run_tests()
    elif args.explore:
        cmd_ux_exploration()
    elif args.tui_screen:
        cmd_tui_screen()
    elif args.tui_state:
        cmd_tui_state()
    elif args.tui_key:
        if not args.key:
            print("Error: --key required for --tui-key")
            return
        cmd_tui_key(args.key)
    elif args.tui_keys:
        if not args.keys:
            print("Error: --keys required for --tui-keys")
            return
        cmd_tui_keys(args.keys, args.delay)


if __name__ == "__main__":
    main()
