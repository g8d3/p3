"""Visibility & Logging Infrastructure.

Every error, API call failure, and unexpected response gets logged here
with timestamps and context.  Logs are written to logs/ directory and
also tee'd to stderr so I (Crush) can see them in real-time.
"""
from __future__ import annotations
import sys
import os
import json
import time
import traceback
from pathlib import Path
from functools import wraps
from typing import Callable, Any

LOG_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"studio_{time.strftime('%Y%m%d')}.log"


def log(level: str, source: str, message: str, data: Any = None) -> None:
    """Write a structured log entry (→ file + stderr)."""
    entry = {
        "ts": time.strftime("%H:%M:%S"),
        "level": level,
        "source": source,
        "message": message,
    }
    if data is not None:
        entry["data"] = str(data)[:500]  # truncate
    line = json.dumps(entry, ensure_ascii=False)
    # File
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    # stderr (visible to Crush)
    print(f"[{entry['ts']}] {level} {source}: {message}", file=sys.stderr)


def api_call(url: str, method: str = "GET", **kwargs) -> dict | list | str | None:
    """Safe API call with logging. Returns parsed JSON or None."""
    import urllib.request, urllib.error, json as j
    log("DEBUG", "api", f"{method} {url}")
    try:
        if method == "GET":
            r = urllib.request.urlopen(url, timeout=kwargs.get("timeout", 10))
        elif method == "POST":
            data = kwargs.get("data")
            req = urllib.request.Request(url, data=data.encode() if isinstance(data, str) else data,
                headers={"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=kwargs.get("timeout", 10))
        else:
            return None
        body = r.read().decode()
        if r.status >= 400:
            log("ERROR", "api", f"HTTP {r.status} from {url}", body[:300])
            return None
        try:
            return j.loads(body)
        except j.JSONDecodeError:
            log("WARN", "api", f"Non-JSON response from {url}", body[:200])
            return body
    except Exception as e:
        log("ERROR", "api", f"Failed {url}", str(e))
        return None


def safe_get(d: dict, key: str, default=None):
    """dict.get() that won't crash if d isn't a dict."""
    if isinstance(d, dict):
        return d.get(key, default)
    log("WARN", "safe_get", f"Expected dict, got {type(d).__name__}", str(d)[:200])
    return default


# ── Patch: log unhandled exceptions in Streamlit ──────────
_original_excepthook = sys.excepthook
def _excepthook(typ, val, tb):
    log("CRITICAL", "unhandled", str(val), "".join(traceback.format_tb(tb)))
    if _original_excepthook:
        _original_excepthook(typ, val, tb)
sys.excepthook = _excepthook
