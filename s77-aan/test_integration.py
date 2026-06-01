#!/usr/bin/env python3
"""Integration tests for AAN server: API, SSE concurrency, and page load."""
import json
import time
import urllib.request
import urllib.error

BASE = "http://localhost:9091"


def test(label, condition, detail=""):
    status = "✅" if condition else "❌"
    print(f"  {status} {label}" + (f" ({detail})" if detail else ""))
    if not condition:
        errors.append(label)


def fetch(path, method="GET", body=None):
    url = f"{BASE}{path}"
    if method == "GET":
        req = urllib.request.Request(url)
    else:
        data = json.dumps(body).encode() if body else b"{}"
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(req, timeout=10)


errors = []
total_start = time.time()

# 1. Main page loads
print("\n1. Main page")
t = time.time()
r = fetch("/")
html = r.read().decode()
test("200 OK", r.status == 200, f"{time.time()-t:.2f}s")
test("Has EventSource", "EventSource" in html)
test("No setInterval", "setInterval" not in html)
test("Mobile viewport", 'initial-scale=1' in html)
test("Has version list container", "version-list" in html)

# 2. API works
print("\n2. API endpoints")
t = time.time()
r = fetch("/api/versions")
data = json.loads(r.read())
test("List versions", "versions" in data, f"{time.time()-t:.2f}s")

# 3. SSE does not block API (the bug we had)
print("\n3. SSE concurrency test")
# Open SSE connection in a thread
import threading
sse_ok = [True]

def sse_client():
    try:
        r = fetch("/api/events", "GET")
        # Read one event
        chunk = r.read(100)
        if not chunk:
            sse_ok[0] = False
    except Exception:
        sse_ok[0] = False

sse_thread = threading.Thread(target=sse_client, daemon=True)
sse_thread.start()
time.sleep(0.5)  # Let SSE connect

# While SSE is connected, make API requests
concurrent_ok = True
for i in range(3):
    try:
        t = time.time()
        r = fetch("/api/versions")
        dt = time.time() - t
        test(f"API during SSE #{i+1}", r.status == 200, f"{dt:.2f}s")
        if dt > 2:
            concurrent_ok = False
    except Exception as e:
        test(f"API during SSE #{i+1}", False, str(e))
        concurrent_ok = False

test("Concurrent SSE+API works", concurrent_ok)

# 4. Create + promote
print("\n4. Create and promote version")
r = fetch("/api/versions", "POST", {"message": "integration test", "created_by": "test"})
v = json.loads(r.read())
test("Version created", "id" in v, v["id"])

r = fetch(f"/api/versions/{v['id']}/live", "POST")
test("Version promoted", r.status == 200)

# 5. Tags
print("\n5. Tags")
fetch("/api/tags", "POST", {"name": "test-tag"})
r = fetch(f"/api/versions/{v['id']}/tags", "POST", {"tag": "test-tag"})
test("Tag added to version", r.status == 200)
r = fetch(f"/api/versions/{v['id']}/tags")
tags = json.loads(r.read())
test("Tag persists", any(t.get("name") == "test-tag" or t == "test-tag" for t in tags.get("tags", [])))

# Summary
print(f"\n{'='*40}")
total = time.time() - total_start
if errors:
    print(f"❌ {len(errors)} failures: {', '.join(errors)}")
else:
    print(f"✅ All tests passed ({total:.1f}s)")
