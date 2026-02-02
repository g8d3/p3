#!/usr/bin/env python3
"""AI Agent UX Exploration Script for Terminal AI Chat App.

This script tests the TUI by sending keystrokes via the API and capturing
screen output to identify UX issues.
"""

import requests
import time
import sys
import argparse

BASE = "http://localhost:8080"

def get_screen():
    """Get current TUI screen."""
    try:
        r = requests.get(f"{BASE}/screen", timeout=2)
        return r.json().get("screen", "")
    except:
        return ""

def get_state():
    """Get TUI state."""
    try:
        r = requests.get(f"{BASE}/state", timeout=2)
        return r.json()
    except:
        return {"mode": "unknown", "running": False}

def send_key(key):
    """Send a keystroke to TUI."""
    try:
        r = requests.post(f"{BASE}/keystroke", json={"key": key}, timeout=2)
        return r.json()
    except Exception as e:
        return {"accepted": False, "error": str(e)}

def send_keys(keys, delay=0.1):
    """Send multiple keystrokes with delay."""
    results = []
    for key in keys:
        result = send_key(key)
        results.append((key, result))
        time.sleep(delay)
    return results

def capture_screen_after(action_name, keys, delay=0.2):
    """Execute action and capture screen."""
    print(f"\n{'='*60}")
    print(f"ACTION: {action_name}")
    print(f"KEYS: {keys}")
    print('='*60)

    results = send_keys(keys, delay)
    for key, result in results:
        print(f"  {key}: {result}")

    time.sleep(0.3)
    screen = get_screen()
    state = get_state()

    print(f"\nSTATE: {state}")
    print(f"\nSCREEN ({len(screen)} chars):")
    print("-" * 40)
    print(screen[:2000] if len(screen) > 2000 else screen)
    print("-" * 40)

    return screen, state

def test_help_discovery():
    """Test help discoverability."""
    print("\n" + "="*60)
    print("TEST: Help Discovery")
    print("="*60)

    issues = []

    screen = get_screen()
    if "?" not in screen and "help" not in screen.lower():
        issues.append("No help hint visible on initial screen")

    capture_screen_after("Press '?' for help", ["?"])
    screen = get_screen()
    if "help" not in screen.lower() and "shortcut" not in screen.lower():
        issues.append("'?' key doesn't show help")

    return issues

def test_chat_mode():
    """Test chat mode functionality."""
    print("\n" + "="*60)
    print("TEST: Chat Mode")
    print("="*60)

    issues = []

    capture_screen_after("Go to chat mode (/)", ["/"])

    capture_screen_after("Type message", ["H", "e", "l", "l", "o", "enter"])

    screen = get_screen()
    if "Hello" not in screen and "hello" not in screen:
        issues.append("Message not appearing in chat")

    return issues

def test_navigation_shortcuts():
    """Test navigation shortcuts."""
    print("\n" + "="*60)
    print("TEST: Navigation Shortcuts")
    print("="*60)

    issues = []
    shortcuts = [
        ("p", "Providers"),
        ("m", "Models"),
        ("a", "Agents"),
        ("s", "Sessions"),
        ("t", "Tools"),
        ("h", "Schedules"),
    ]

    for key, name in shortcuts:
        screen_before = get_screen()
        state_before = get_state()

        capture_screen_after(f"Press '{key}' for {name}", [key])

        state = get_state()
        if state.get("mode", "").lower() != name.lower():
            issues.append(f"'{key}' doesn't navigate to {name} mode")

        capture_screen_after("Back to chat (/)", ["/"])

    return issues

def test_keyboard_feedback():
    """Test visual feedback for key presses."""
    print("\n" + "="*60)
    print("TEST: Keyboard Feedback")
    print("="*60)

    issues = []

    capture_screen_after("Press random key 'x'", ["x"])
    screen = get_screen()

    state = get_state()
    if not state.get("running"):
        issues.append("TUI not running")

    return issues

def test_error_handling():
    """Test error handling."""
    print("\n" + "="*60)
    print("TEST: Error Handling")
    print("="*60)

    issues = []

    result = send_key("invalid_key_12345")
    if result.get("accepted") and "not supported" not in str(result):
        pass

    return issues

def test_api_endpoints():
    """Test API endpoints."""
    print("\n" + "="*60)
    print("TEST: API Endpoints")
    print("="*60)

    issues = []

    endpoints = [
        "/health",
        "/providers",
        "/models",
        "/agents",
        "/sessions",
        "/tools",
        "/schedules",
        "/stats",
        "/state",
    ]

    for endpoint in endpoints:
        try:
            r = requests.get(f"{BASE}{endpoint}", timeout=2)
            if r.status_code != 200:
                issues.append(f"Endpoint {endpoint} returned {r.status_code}")
        except Exception as e:
            issues.append(f"Endpoint {endpoint} failed: {e}")

    return issues

def test_crud_operations():
    """Test CRUD operations via API."""
    print("\n" + "="*60)
    print("TEST: CRUD Operations")
    print("="*60)

    issues = []

    provider_data = {
        "name": "Test Provider",
        "provider_type": "openai",
        "api_key": "test-key",
        "base_url": "https://api.openai.com"
    }

    try:
        r = requests.post(f"{BASE}/providers", json=provider_data, timeout=2)
        if r.status_code != 200:
            issues.append(f"Create provider failed: {r.status_code}")
        else:
            print("  ✓ Provider created")

        r = requests.get(f"{BASE}/providers", timeout=2)
        if r.status_code == 200:
            providers = r.json().get("providers", [])
            print(f"  ✓ Found {len(providers)} providers")
        else:
            issues.append("Failed to list providers")

    except Exception as e:
        issues.append(f"CRUD test failed: {e}")

    return issues

def run_exploration():
    """Run full UX exploration."""
    print("="*60)
    print("Terminal AI Chat App - AI Agent UX Exploration")
    print("="*60)
    print(f"API Server: {BASE}")

    state = get_state()
    if not state.get("running"):
        print("\n⚠ TUI not running. Start with: python app.py")
        print("  Or run API only: python app.py --api --port 8080")
        return []

    all_issues = []

    test_functions = [
        ("Help Discovery", test_help_discovery),
        ("Chat Mode", test_chat_mode),
        ("Navigation Shortcuts", test_navigation_shortcuts),
        ("Keyboard Feedback", test_keyboard_feedback),
        ("Error Handling", test_error_handling),
        ("API Endpoints", test_api_endpoints),
        ("CRUD Operations", test_crud_operations),
    ]

    for name, test_func in test_functions:
        try:
            issues = test_func()
            all_issues.extend(issues)
        except Exception as e:
            print(f"\n✗ {name} test failed: {e}")
            all_issues.append(f"{name} test failed: {e}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if all_issues:
        print(f"\n{len(all_issues)} potential UX issues found:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\n✓ No UX issues found!")

    print("\nRecommendations based on common UX issues:")
    print("  1. Display keyboard shortcuts on initial screen")
    print("  2. Show current mode in status bar")
    print("  3. Provide visual feedback for all key presses")
    print("  4. Make help discoverable (press ? or show hints)")
    print("  5. Include example commands or usage hints")

    return all_issues

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Agent UX Exploration Script")
    parser.add_argument("--test", action="store_true", help="Run quick test")
    parser.add_argument("--explore", action="store_true", help="Run full exploration")
    args = parser.parse_args()

    if args.test or args.explore or len(sys.argv) == 1:
        issues = run_exploration()
        sys.exit(0 if not issues else 1)
