#!/bin/bash
# AI Content Factory - Quick Start Script

set -e

echo "=========================================="
echo "AI Content Factory - Setup"
echo "=========================================="

# Create config directory
mkdir -p ~/.config/ai-content-factory/data

# Create output directories
mkdir -p ~/Videos/ai-content
mkdir -p ~/Videos/ai-content/assets

# Install Python dependencies (optional - using stdlib)
echo "Checking dependencies..."

if ! command -v ffmpeg &> /dev/null; then
    echo "ERROR: ffmpeg not found. Install with:"
    echo "  sudo apt install ffmpeg"
    exit 1
fi

echo "  ✓ ffmpeg"

# Optional: Install yt-dlp for easier YouTube uploads
if ! command -v yt-dlp &> /dev/null; then
    echo "  ⚠ yt-dlp not found (optional - for YouTube uploads)"
    echo "    Install: pip install yt-dlp"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Quick Start:"
echo "  1. Generate topics:"
echo "     cd ai_content_factory && python3 main.py --generate --niche ai"
echo ""
echo "  2. Record content:"
echo "     cd ai_content_factory && python3 main.py --record --duration 60"
echo ""
echo "  3. Process video:"
echo "     cd ai_content_factory && python3 main.py --process"
echo ""
echo "  4. Upload:"
echo "     cd ai_content_factory && python3 main.py --upload youtube"
echo ""
echo "  5. Full pipeline:"
echo "     cd ai_content_factory && python3 main.py --full --niche ai"
echo ""
echo "  6. Set up automation:"
echo "     cd ai_content_factory && python3 main.py --setup"
echo ""
echo "  7. Check status:"
echo "     cd ai_content_factory && python3 main.py --status"
