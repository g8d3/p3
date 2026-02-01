#!/usr/bin/env python3
"""
UX exploration script that generates a CSV report of issues found.
"""

import json
import urllib.request
import urllib.error
import csv
import sys
from datetime import datetime

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


def send_key(key: str) -> bool:
    """Send a keystroke to TUI."""
    result = make_request("POST", "/keystroke", {"key": key})
    return result.get("success", False)


def get_screen() -> str:
    """Get current TUI screen text."""
    result = make_request("GET", "/screen")
    return result.get("screen", "")


def get_state() -> dict:
    """Get TUI state."""
    result = make_request("GET", "/state")
    return result.get("state", {})


def extract_visible_text(screen: str) -> list:
    """Extract visible text lines from screen (filter out escape codes)."""
    lines = screen.split("\n")
    visible_lines = []
    for line in lines:
        # Filter out ANSI escape codes
        import re
        clean_line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
        clean_line = re.sub(r'\x1b\[[0-9;]*[HfABCDsuJK]', '', clean_line)
        clean_line = re.sub(r'\x1b\][0-9;]*[^\x1b]', '', clean_line)
        clean_line = clean_line.strip()
        if clean_line:
            visible_lines.append(clean_line)
    return visible_lines


def analyze_screen(screen: str, action: str) -> list:
    """Analyze screen for issues."""
    issues = []
    visible = extract_visible_text(screen)

    # Check for help
    if 'help' not in ' '.join(visible).lower():
        issues.append({
            'action': action,
            'issue': 'No help visible on screen',
            'severity': 'high',
            'suggestion': 'Add help text or visible shortcuts'
        })

    # Check for shortcuts hints
    if 'press' not in ' '.join(visible).lower():
        issues.append({
            'action': action,
            'issue': 'No keyboard shortcuts hints',
            'severity': 'medium',
            'suggestion': 'Show available shortcuts (e.g., "Press ? for help")'
        })

    # Check for status/mode indicator
    status_indicators = ['mode', 'status', 'chat', 'provider', 'model', 'agent']
    has_status = any(ind in ' '.join(visible).lower() for ind in status_indicators)

    if not has_status and visible:
        issues.append({
            'action': action,
            'issue': 'No status/mode indicator visible',
            'severity': 'low',
            'suggestion': 'Show current mode in status bar'
        })

    return issues


def run_exploration():
    """Run full UX exploration and generate CSV report."""
    issues = []

    print("=" * 80)
    print("Terminal AI Chat App - UX Exploration")
    print("=" * 80)
    print()

    # Test cases
    test_cases = [
        ('Initial state', []),
        ('Press ? for help', ['?']),
        ('Press / for chat', ['/']),
        ('Press p for providers', ['p']),
        ('Press m for models', ['m']),
        ('Press a for agents', ['a']),
        ('Press s for sessions', ['s']),
        ('Press t for tools', ['t']),
        ('Press h for schedules', ['h']),
        ('Press enter', ['enter']),
        ('Press escape', ['escape']),
        ('Press up arrow', ['up']),
        ('Press down arrow', ['down']),
        ('Press //help (as user might try)', ['/', '/', 'h', 'e', 'l', 'p']),
        ('Press ? then ? again', ['?', '?']),
    ]

    for action, keys in test_cases:
        print(f"Testing: {action}...")
        for key in keys:
            send_key(key)

        screen = get_screen()
        visible = extract_visible_text(screen)

        if visible:
            print(f"  Screen: {visible[:100]}...")
        else:
            print(f"  Screen: EMPTY")

        # Analyze
        screen_issues = analyze_screen(screen, action)
        issues.extend(screen_issues)

        for issue in screen_issues:
            print(f"  ISSUE: {issue['issue']} ({issue['severity']})")

        print()

    # Generate CSV report
    print("=" * 80)
    print("Generating CSV Report...")
    print("=" * 80)

    # Remove duplicates based on issue text
    unique_issues = []
    seen = set()
    for issue in issues:
        key = (issue['action'], issue['issue'])
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    # Write CSV
    csv_file = '/home/vuos/code/p3/s17/ux_issues.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['severity', 'action', 'issue', 'suggestion'])
        writer.writeheader()

        # Sort by severity
        severity_order = {'high': 1, 'medium': 2, 'low': 3}
        sorted_issues = sorted(unique_issues, key=lambda x: severity_order.get(x['severity'], 4))

        for issue in sorted_issues:
            # Escape commas in fields
            for field in ['action', 'issue', 'suggestion']:
                issue[field] = issue[field].replace(',', ';')
            writer.writerow(issue)

    print(f"\nCSV report saved to: {csv_file}")
    print()

    # Summary
    high = sum(1 for i in unique_issues if i['severity'] == 'high')
    medium = sum(1 for i in unique_issues if i['severity'] == 'medium')
    low = sum(1 for i in unique_issues if i['severity'] == 'low')

    print("Summary:")
    print(f"  High severity: {high}")
    print(f"  Medium severity: {medium}")
    print(f"  Low severity: {low}")
    print(f"  Total issues: {len(unique_issues)}")
    print()

    return unique_issues


if __name__ == "__main__":
    run_exploration()
