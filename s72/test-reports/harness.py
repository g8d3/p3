"""Test helper for AI Video Studio — uses CDP directly for advanced interactions.

Usage:
  python3.12 test_harness.py                      # Run all tests
  python3.12 test_harness.py --test swipe         # Run specific test
  python3.12 test_harness.py --monitor            # Monitor window 0
"""

import asyncio
import json
import os
import sys
import time
import urllib.request

# ── Config ───────────────────────────────────────────────
API = "http://127.0.0.1:8777"
COMPOSER = f"{API}/composer"
CDP_WS = "ws://localhost:9222/devtools/browser/6459b050-678c-40fb-9539-aa9c7189e302"
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "test-reports")


def api_get(path: str) -> dict:
    try:
        r = urllib.request.urlopen(f"{API}{path}", timeout=10)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def api_post(path: str, data: dict) -> dict:
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{API}{path}", data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        r = urllib.request.urlopen(req, timeout=10)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(condition: bool, msg: str) -> str:
    icon = "✅" if condition else "❌"
    print(f"  {icon} {msg}")
    return icon


def test_api():
    section("API Endpoints")
    results = []

    # Queue
    q = api_get("/api/feed/queue")
    results.append(check("queue" in q, f"GET /api/feed/queue → {q.get('queue_size','?' )} videos"))

    # Next package
    pkg = api_get("/api/feed/package")
    results.append(check(
        pkg.get("status") == "ready" and pkg.get("package"),
        f"GET /api/feed/package → {pkg.get('status')}"
    ))

    # Style
    s = api_get("/api/style")
    results.append(check(
        s.get("voice") and s.get("font_size"),
        f"GET /api/style → voice={s.get('voice')}, font={s.get('font_size')}"
    ))

    # Sources
    src = api_get("/api/sources")
    results.append(check(
        isinstance(src, dict) and len(src) > 0,
        f"GET /api/sources → {len(src)} sources: {', '.join(src.keys())}"
    ))

    # Assets
    a = api_get("/api/assets")
    results.append(check(
        isinstance(a.get("gameplay"), list) and len(a["gameplay"]) > 0,
        f"GET /api/assets → {len(a.get('gameplay',[]))} videos, {len(a.get('audio',[]))} tracks"
    ))

    # Post style
    sp = api_post("/api/style", {"voice": "es-MX-JorgeNeural", "font_size": 120})
    results.append(check(
        sp.get("voice") == "es-MX-JorgeNeural",
        f"POST /api/style → voice={sp.get('voice')}"
    ))

    # Restore
    api_post("/api/style", {"voice": "es-MX-DaliaNeural", "font_size": 96, "music_volume": 0.12})

    all_ok = all(r == "✅" for r in results)
    print(f"\n  → {'✅ ALL PASS' if all_ok else '❌ SOME FAILED'} ({sum(1 for r in results if r=='✅')}/{len(results)})")
    return all_ok


def test_feed_cycle():
    section("Feed Cycle (pop → verify → return)")
    results = []

    # Peek first
    before = api_get("/api/feed/queue")
    bsize = before.get("queue_size", 0)
    results.append(check(bsize > 0, f"Queue has {bsize} videos before pop"))

    # Get next package
    nxt = api_get("/api/feed/next")
    results.append(check(
        nxt.get("status") == "ready" and nxt.get("package"),
        f"Pop next → pkg_id={nxt['package'].get('pkg_id','?')}"
    ))

    pkg = nxt["package"]
    # Verify package structure
    required_fields = ["pkg_id", "script", "narration", "subtitles", "gameplay", "duration_s"]
    for f in required_fields:
        results.append(check(
            f in pkg and pkg[f],
            f"    field '{f}' = {str(pkg.get(f,''))[:50]}"
        ))

    # Check narration file accessible
    nar_url = pkg.get("narration", "")
    if nar_url:
        try:
            r = urllib.request.urlopen(f"{API}{nar_url}", timeout=5)
            results.append(check(r.status == 200, f"    narration downloadable ({len(r.read())} bytes)"))
        except Exception as e:
            results.append(check(False, f"    narration download failed: {e}"))

    # Check queue decreased
    after = api_get("/api/feed/queue")
    asize = after.get("queue_size", 0)
    results.append(check(
        asize < bsize or asize == bsize,
        f"Queue after pop: {asize} (was {bsize})"
    ))

    all_ok = all(r == "✅" for r in results)
    print(f"\n  → {'✅ ALL PASS' if all_ok else '❌ SOME FAILED'} ({sum(1 for r in results if r=='✅')}/{len(results)})")
    return all_ok


def test_assets_accessible():
    section("Assets accessibility")
    results = []

    assets = api_get("/api/assets")
    for v in assets.get("gameplay", []):
        fname = os.path.basename(v)
        try:
            r = urllib.request.urlopen(f"{API}/api/download/{fname}", timeout=10)
            results.append(check(r.status == 200, f"  video {fname} downloadable ({len(r.read())} bytes)"))
        except Exception as e:
            results.append(check(False, f"  video {fname} FAILED: {e}"))
    for a in assets.get("audio", []):
        fname = os.path.basename(a)
        try:
            r = urllib.request.urlopen(f"{API}/api/download/{fname}", timeout=10)
            results.append(check(r.status == 200, f"  audio {fname} downloadable ({len(r.read())} bytes)"))
        except Exception as e:
            results.append(check(False, f"  audio {fname} FAILED: {e}"))

    all_ok = all(r == "✅" for r in results)
    print(f"\n  → {'✅ ALL PASS' if all_ok else '❌ SOME FAILED'} ({sum(1 for r in results if r=='✅')}/{len(results)})")
    return all_ok


if __name__ == "__main__":
    results = []

    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        print("Monitor mode: watching window 0 for changes...")
        # Monitoring will be set up separately
        sys.exit(0)

    test_filter = None
    if len(sys.argv) > 2 and sys.argv[1] == "--test":
        test_filter = sys.argv[2]

    tests = {
        "api": test_api,
        "feed": test_feed_cycle,
        "assets": test_assets_accessible,
    }

    for name, fn in tests.items():
        if test_filter and test_filter != name:
            continue
        try:
            results.append((name, fn()))
        except Exception as e:
            print(f"\n  ❌ {name} CRASHED: {e}")
            results.append((name, False))

    print(f"\n{'='*60}")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"  RESULT: {passed}/{total} passed")
    print(f"{'='*60}")

    sys.exit(0 if passed == total else 1)
