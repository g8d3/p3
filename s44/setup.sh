#!/usr/bin/env bash
# =============================================================================
# Content Agent — One-Command Setup
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════╗"
echo "║     Content Agent — Setup                    ║"
echo "╚══════════════════════════════════════════════╝"

# --- 1. Python virtual environment ---
echo ""
echo "[1/5] Python virtual environment..."
if [ ! -d ".venv" ]; then
    uv venv .venv
    echo "  ✓ Created .venv"
else
    echo "  ✓ .venv already exists"
fi

source .venv/bin/activate
uv pip install edge-tts moviepy Pillow pyyaml mutagen 2>&1 | tail -1
echo "  ✓ Dependencies installed"

# --- 2. Generate SFX library ---
echo ""
echo "[2/5] Generating SFX library..."
python pipeline/sfx.py
echo "  ✓ SFX library ready"

# --- 3. Create output directories ---
echo ""
echo "[3/5] Creating directories..."
mkdir -p output logs assets/music assets/memes assets/sfx
echo "  ✓ Directories ready"

# --- 4. Test TTS ---
echo ""
echo "[4/5] Testing TTS..."
if [ -n "${CHUTES_API_TOKEN:-}" ]; then
    source .venv/bin/activate
    python -c "
from pipeline.tts import generate_speech
try:
    path = generate_speech('Content Agent online. Ready to create.', backend='kokoro', output_path='/tmp/setup_test.wav')
    print(f'  ✓ Kokoro TTS works: {path}')
except Exception as e:
    print(f'  ⚠ Kokoro TTS failed: {e}')
    print('  - Will use edge-tts fallback')
" 2>&1
else
    echo "  ⚠ CHUTES_API_TOKEN not set — will use edge-tts as fallback"
fi

# --- 5. Test import ---
echo ""
echo "[5/5] Verifying imports..."
source .venv/bin/activate
python -c "
from agent.script_gen import create_content_plan
from pipeline.assemble import VideoAssembler
from pipeline.sfx import get_sfx_map
from agent.personality import get_persona_prompt
print('  ✓ All imports verified')
print(f'  ✓ SFX library: {len(get_sfx_map())} effects')
print(f'  ✓ Persona prompt: {len(get_persona_prompt())} chars')
" 2>&1

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Setup Complete!                             ║"
echo "║                                              ║"
echo "║  Run:  source .venv/bin/activate             ║"
echo "║  Run:  python run.py --dry-run               ║"
echo "║  Run:  python run.py                         ║"
echo "║  Run:  python run.py --schedule              ║"
echo "╚══════════════════════════════════════════════╝"
