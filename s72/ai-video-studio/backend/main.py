"""AI Video Studio — FastAPI Backend."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from backend.config import CONFIG
from backend.sources import get_all_connectors, get_status_all
from backend.renderer import start_render, get_job, list_jobs
from backend.feed import (
    start_background_refresh,
    pop_next_package,
    peek_next_package,
    get_queue_status,
    get_actions,
    get_style,
    update_style,
    fetch_all_trends,
    generate_script,
    _log_action,
)

app = FastAPI(title="AI Video Studio", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Startup ──────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    # Start background filler AND immediately generate first packages
    start_background_refresh()
    # Give it a head start — generate first package synchronously
    import asyncio
    from backend.feed import _generate_one_package, _package_queue, _queue_lock
    try:
        pkg = await _generate_one_package()
        if pkg:
            async with _queue_lock:
                _package_queue.append(pkg)
            _log_action("system", "First package generated on startup")
    except Exception as e:
        _log_action("system", f"Startup generation: {e}")
    _log_action("system", "Backend started — feed engine (browser compositing)")


# ── Source endpoints ─────────────────────────────────────

@app.get("/api/sources")
async def api_sources_status():
    """Get status of all data source connectors with API key info."""
    status = get_status_all()
    cfg = CONFIG.sources
    for name, info in status.items():
        if name in cfg:
            info["api_key"] = cfg[name].api_key
    return status


@app.get("/api/sources/{name}/fetch")
async def api_source_fetch(name: str):
    conns = get_all_connectors()
    if name not in conns:
        raise HTTPException(404, f"Unknown source: {name}")
    items = conns[name].fetch()
    return {"source": name, "items": items, "count": len(items)}


@app.get("/api/sources/{name}/status")
async def api_source_status(name: str):
    conns = get_all_connectors()
    if name not in conns:
        raise HTTPException(404, f"Unknown source: {name}")
    return conns[name].status()


# ── Render endpoints (manual use only — feed no usa ffmpeg) ──

class RenderRequest(BaseModel):
    script: str
    voice: str = "es-MX-DaliaNeural"
    gameplay: Optional[str] = None
    music: Optional[str] = None
    font_size: int = 96
    max_words: int = 5
    music_volume: float = 0.12
    video_bitrate: str = "8M"


@app.post("/api/render")
async def api_render(req: RenderRequest, background: BackgroundTasks):
    job_id = await start_render(req.model_dump())
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/render/{job_id}")
async def api_render_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "stage": job.stage,
        "duration_s": job.duration_s,
        "error": job.error,
        "created_at": job.created_at,
        "output_path": job.output_path,
    }


@app.get("/api/render/{job_id}/download")
async def api_render_download(job_id: str):
    job = get_job(job_id)
    if not job or not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(404, "Output not found")
    return FileResponse(job.output_path, media_type="video/mp4",
                        filename=f"{job_id}.mp4")


@app.get("/api/jobs")
async def api_list_jobs():
    return {"jobs": list_jobs()}


# ── Assets endpoints ─────────────────────────────────────

@app.get("/api/assets")
async def api_assets():
    gp_dir = Path(CONFIG.assets_dir) / "gameplay"
    au_dir = Path(CONFIG.assets_dir) / "audio"
    gameplay = [str(f.relative_to(CONFIG.assets_dir))
                for f in gp_dir.glob("*.mp4")] if gp_dir.exists() else []
    audio = [str(f.relative_to(CONFIG.assets_dir))
             for f in au_dir.glob("*.mp3")] if au_dir.exists() else []
    return {"gameplay": gameplay, "audio": audio}


# ── Feed / Package endpoints ─────────────────────────────

@app.get("/api/feed/next")
async def api_feed_next():
    """Pop the next component package from the queue.
    Returns raw component URLs for browser compositing."""
    pkg = await pop_next_package()
    if pkg:
        return {"status": "ready", "package": _pkg_to_response(pkg)}
    _log_action("feed", "Queue empty")
    return {"status": "generating", "package": None}


@app.get("/api/feed/peek")
async def api_feed_peek():
    """Peek at next package without consuming."""
    pkg = peek_next_package()
    return {"status": "ready" if pkg else "empty", "package": _pkg_to_response(pkg) if pkg else None}


@app.get("/api/feed/package")
async def api_feed_package():
    """Get next package (same as peek but with full component URLs)."""
    pkg = peek_next_package()
    if pkg:
        return {"status": "ready", "package": _pkg_to_response(pkg)}
    return {"status": "generating", "package": None}


@app.get("/api/feed/queue")
async def api_feed_queue():
    q = get_queue_status()
    return {"queue_size": len(q), "queue": q}


@app.post("/api/feed/generate")
async def api_feed_generate():
    _log_action("feed", "Manual generation triggered")
    return {"status": "triggered"}


def _pkg_to_response(pkg: dict) -> dict:
    """Convert internal package to API response with download URLs."""
    def _url(path: str) -> str:
        if not path or not os.path.exists(path):
            return ""
        return f"/api/download/{os.path.basename(path)}"
    return {
        "pkg_id": pkg["pkg_id"],
        "script": pkg.get("script", ""),
        "narration": _url(pkg.get("narration_path", "")),
        "subtitles": _url(pkg.get("subtitle_path", "")),
        "gameplay": _url(pkg.get("gameplay_path", "")),
        "music": _url(pkg.get("music_path", "")),
        "duration_s": pkg.get("duration_s"),
        "voice": pkg.get("voice", CONFIG.default_voice),
        "font_size": pkg.get("font_size", CONFIG.subtitle_font_size),
    }


# ── Style / OSD ─────────────────────────────────────────

class StyleUpdate(BaseModel):
    font_size: Optional[int] = None
    max_words: Optional[int] = None
    voice: Optional[str] = None
    music_volume: Optional[float] = None
    video_bitrate: Optional[str] = None


@app.get("/api/style")
async def api_style_get():
    return get_style()


@app.post("/api/style")
async def api_style_update(data: StyleUpdate):
    updated = update_style(**data.model_dump(exclude_none=True))
    return updated


# ── Actions ──────────────────────────────────────────────

@app.get("/api/actions")
async def api_actions(limit: int = 20):
    return {"actions": get_actions(limit)}


# ── Config / API keys ────────────────────────────────────

class SourceConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    enabled: Optional[bool] = None

class ConfigUpdate(BaseModel):
    sources: dict[str, SourceConfigUpdate] = {}


@app.get("/api/config")
async def api_config_get():
    """Get current configuration (API keys masked)."""
    cfg = CONFIG.sources
    result = {}
    for name, sc in cfg.items():
        key = sc.api_key
        masked = key[:6] + "..." + key[-4:] if len(key) > 12 else ("set" if key else "")
        result[name] = {
            "api_key": key,
            "api_key_masked": masked,
            "enabled": sc.enabled,
            "rate_limit_rpm": sc.rate_limit_rpm,
        }
    return {"sources": result}


@app.post("/api/config")
async def api_config_update(data: ConfigUpdate):
    """Update API keys and source settings."""
    from backend.sources import get_all_connectors
    cfg = CONFIG.sources
    conns = get_all_connectors()
    for name, update in data.sources.items():
        if name in cfg:
            if update.api_key is not None:
                cfg[name].api_key = update.api_key
                if name in conns:
                    conns[name].api_key = update.api_key
            if update.enabled is not None:
                cfg[name].enabled = update.enabled
    _log_action("config", f"Updated {len(data.sources)} source(s)")
    return {"status": "ok", "updated": list(data.sources.keys())}


# ── Download individual files ────────────────────────────

@app.get("/api/download/{filename}")
async def api_download(filename: str):
    """Serve a file from output or assets directory."""
    paths = [
        os.path.join(CONFIG.output_dir, filename),
        os.path.join(CONFIG.assets_dir, "gameplay", filename),
        os.path.join(CONFIG.assets_dir, "audio", filename),
    ]
    for path in paths:
        if os.path.exists(path):
            # CORS headers for ffmpeg.wasm
            return FileResponse(path, filename=filename,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cross-Origin-Embedder-Policy": "require-corp",
                    "Cross-Origin-Opener-Policy": "same-origin",
                })
    raise HTTPException(404, "File not found")


# ── Compositor page ──────────────────────────────────────

@app.get("/composer", response_class=HTMLResponse)
async def composer_page():
    """Serve the in-browser ffmpeg.wasm compositor."""
    html_path = os.path.join(os.path.dirname(__file__), "composer.html")
    if os.path.exists(html_path):
        return HTMLResponse(open(html_path).read(),
            headers={
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
            })
    return HTMLResponse("<h1>Compositor no disponible</h1>")


@app.get("/player", response_class=HTMLResponse)
async def player_page():
    """Redirect to composer."""
    html_path = os.path.join(os.path.dirname(__file__), "composer.html")
    if os.path.exists(html_path):
        return HTMLResponse(open(html_path).read(),
            headers={
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
            })
    return HTMLResponse("<h1>Player no disponible</h1>")


# ── Static files ─────────────────────────────────────────

assets_dir = Path(CONFIG.assets_dir)
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

ffmpeg_wasm_dir = Path(os.path.dirname(__file__)) / "ffmpeg-wasm"
if ffmpeg_wasm_dir.exists():
    app.mount("/ffmpeg-wasm", StaticFiles(directory=str(ffmpeg_wasm_dir)), name="ffmpeg-wasm")


# ── Visibility / Status ──────────────────────────────────

@app.get("/api/status")
async def api_status():
    """Full system status: disk, cache, queue, files."""
    import shutil
    
    # Disk usage
    out_dir = Path(CONFIG.output_dir)
    out_files = list(out_dir.glob("*")) if out_dir.exists() else []
    out_size = sum(f.stat().st_size for f in out_files if f.is_file())
    
    assets = Path(CONFIG.assets_dir)
    gp_files = list((assets / "gameplay").glob("*")) if (assets / "gameplay").exists() else []
    au_files = list((assets / "audio").glob("*")) if (assets / "audio").exists() else []
    
    # Cache files
    data_dir = Path(CONFIG.data_dir)
    cache_files = list(data_dir.glob("*_cache.json")) if data_dir.exists() else []
    
    return {
        "version": "0.2.0",
        "queue_size": len(get_queue_status()),
        "output_files": len(out_files),
        "output_size_mb": round(out_size / 1024 / 1024, 1),
        "gameplay_assets": len(gp_files),
        "audio_assets": len(au_files),
        "cache_files": len(cache_files),
        "disk_usage_mb": round(sum(f.stat().st_size for f in out_files + gp_files + au_files if f.is_file()) / 1024 / 1024, 1),
    }


@app.post("/api/cleanup")
async def api_cleanup(keep: int = 5):
    """Delete old output files, keep only the N most recent packages."""
    out_dir = Path(CONFIG.output_dir)
    if not out_dir.exists():
        return {"deleted": 0}
    
    # Group files by package (narration + subs belong to same package)
    packages: dict[str, list[Path]] = {}
    for f in out_dir.iterdir():
        if not f.is_file():
            continue
        # Extract package id from filename (e.g., "abc123_narration.mp3" → "abc123")
        parts = f.stem.split("_")
        pkg_id = parts[0] if len(parts) > 1 and parts[1] in ("narration", "subtitles") else f.stem
        packages.setdefault(pkg_id, []).append(f)
    
    # Sort by modification time (oldest first)
    sorted_pkgs = sorted(packages.items(), key=lambda x: max(p.stat().st_mtime for p in x[1]))
    
    to_delete = sorted_pkgs[:-keep] if len(sorted_pkgs) > keep else []
    count = 0
    for pkg_id, files in to_delete:
        for f in files:
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
    
    _log_action("cleanup", f"Deleted {count} files ({len(to_delete)} packages)")
    return {"deleted": count, "remaining_packages": len(sorted_pkgs) - len(to_delete)}


# ── Dev error upload (browser → server) ──────────────────

class BrowserError(BaseModel):
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    timestamp: Optional[str] = None

_browser_errors: list[dict] = []
MAX_BROWSER_ERRORS = 200

@app.post("/api/dev/error")
async def api_dev_error(data: BrowserError):
    """Receive browser-side errors for Crush visibility."""
    entry = data.model_dump()
    entry["_received"] = time.strftime("%H:%M:%S")
    _browser_errors.append(entry)
    if len(_browser_errors) > MAX_BROWSER_ERRORS:
        _browser_errors[:] = _browser_errors[-MAX_BROWSER_ERRORS:]
    _log_action("browser_error", f"JS: {data.message[:120]}")
    return {"ok": True}

@app.get("/api/dev/errors")
async def api_dev_errors():
    """Get all browser errors reported."""
    return {"count": len(_browser_errors), "errors": list(reversed(_browser_errors))[:50]}


# ── Health ───────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}
