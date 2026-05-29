"""AI Video Studio — Lanzador.

Pantalla minimalista: muestra estado de la cola y redirige al
compositor browser (ffmpeg.wasm) para ver el video.
"""

import sys, os, json, time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

import streamlit as st

st.set_page_config(page_title="AI Video Studio", layout="centered", initial_sidebar_state="collapsed")

BASE = Path(__file__).parent.parent
API = "http://127.0.0.1:8777/api"
COMPOSER_URL = "http://localhost:8777/composer"

# ── State ────────────────────────────────────────────────
for key in ("sources", "actions", "last_check", "queue_size", "pkg_status"):
    if key not in st.session_state:
        st.session_state[key] = {} if key in ("sources", "actions") else (0 if key in ("last_check","queue_size") else "unknown")


def api_get(path):
    try:
        r = urlopen(f"{API}{path}", timeout=5)
        return json.loads(r.read())
    except Exception:
        return None


def refresh():
    now = time.time()
    if now - st.session_state.last_check < 3:
        return
    st.session_state.last_check = now

    q = api_get("/feed/queue")
    st.session_state.queue_size = q.get("queue_size", 0) if q else 0

    pkg = api_get("/feed/package")
    st.session_state.pkg_status = pkg.get("status", "error") if pkg else "error"

    s = api_get("/sources")
    if s: st.session_state.sources = s

    a = api_get("/actions?limit=10")
    if a: st.session_state.actions = a.get("actions", [])


# ── UI ───────────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { max-width: 520px !important; padding-top: 2rem; }
    h1 { text-align: center; font-size: 28px; margin-bottom: 4px; }
    .sub { text-align: center; color: #888; font-size: 14px; margin-bottom: 24px; }
    .stat { text-align: center; font-size: 48px; font-weight: 700; margin: 8px 0; }
    .stat-label { text-align: center; color: #888; font-size: 13px; }
    .launch-btn {
        display: block; width: 100%; padding: 16px; font-size: 20px;
        text-align: center; background: #0af; color: #000;
        border: none; border-radius: 12px; font-weight: 700;
        text-decoration: none; margin: 20px 0;
    }
    .launch-btn:hover { background: #3cf; }
    .action-item { font-size: 12px; color: #888; padding: 2px 0; border-bottom: 1px solid #1a1a1a; }
</style>
""", unsafe_allow_html=True)

refresh()

st.markdown("<h1>🎬 AI Video Studio</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub'>Feed autónomo — composición en el navegador</p>", unsafe_allow_html=True)

# Queue status
q = st.session_state.queue_size
if q > 0:
    st.markdown(f"<div class='stat' style='color:#0f0'>{q}</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>📦 Videos listos para ver</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='stat' style='color:#ff0'>⚙️</div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-label'>Generando... (~10s por video)</div>", unsafe_allow_html=True)

# Launch button
st.markdown(f"<a href='{COMPOSER_URL}' target='_blank' class='launch-btn'>▶️ Ver siguiente video</a>", unsafe_allow_html=True)
st.caption("Se abre el compositor en el navegador — ffmpeg.wasm compone el video localmente")

# Style OSD
with st.expander("🎨 Estilo", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        font_size = st.select_slider("Tamaño fuente", [48,72,96,120,144,192], value=96)
        voice = st.selectbox("Voz", ["es-MX-DaliaNeural","es-MX-JorgeNeural","es-ES-AlvaroNeural","en-US-JennyNeural"])
    with c2:
        max_words = st.select_slider("Palabras/bloque", [2,3,4,5,6], value=5)
        music_vol = st.slider("Vol. música", 0.0, 0.5, 0.12, 0.01)

    if st.button("✅ Aplicar"):
        import urllib.request as ur
        data = json.dumps({"font_size":font_size,"max_words":max_words,"voice":voice,"music_volume":music_vol}).encode()
        req = ur.Request(f"{API}/style", data=data, headers={"Content-Type":"application/json"})
        try: ur.urlopen(req, timeout=5)
        except: pass
        st.success("Estilo actualizado")

# Sources
with st.expander("🔌 Conexiones", expanded=False):
    for name, info in st.session_state.sources.items():
        if not isinstance(info, dict): continue
        icon = "✅" if info.get("connected") else ("⏸️" if not info.get("enabled") else "❌")
        st.markdown(f"{icon} **{name}** — {info.get('last_error','ok')[:60]}")

# Actions
with st.expander("📋 Últimas acciones", expanded=False):
    for a in st.session_state.actions[:10]:
        st.markdown(f"<div class='action-item'><b>{a.get('ts','')}</b> {a.get('kind','')}: {a.get('detail','')[:80]}</div>", unsafe_allow_html=True)


# Auto-refresh
if st.button("🔄 Refrescar"):
    st.rerun()

import time as _t
_t.sleep(3)
