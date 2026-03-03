#!/bin/bash
#
# AI Content Factory - Complete Installer
# Installs all dependencies needed for automated video creation
#

set -e

echo "============================================"
echo "  AI Content Factory - Installer"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root for apt installs
if [ "$EUID" -eq 0 ]; then
    CAN_INSTALL=true
else
    log_warn "Not running as root - will skip system packages"
    CAN_INSTALL=false
fi

# Create directories
log_info "Creating directories..."
mkdir -p ~/.config/ai-content-factory/data
mkdir -p ~/Videos/ai-content
mkdir -p ~/Videos/ai-content/assets
mkdir -p ~/bin
echo "Done!"

# Install Python packages
log_info "Installing Python packages..."
if command -v pip3 &> /dev/null; then
    pip3 install gtts pyttsx3 --quiet 2>/dev/null || log_warn "Could not install Python TTS packages"
elif command -v python3 &> /dev/null; then
    # Try ensurepip
    python3 -m ensurepip --default-pip 2>/dev/null || true
    python3 -m pip install gtts --quiet 2>/dev/null || log_warn "Could not install Python packages"
fi

# Install system packages (if root)
if [ "$CAN_INSTALL" = true ]; then
    log_info "Installing system packages..."
    
    # Core dependencies
    apt-get update -qq
    apt-get install -y -qq \
        ffmpeg \
        x11-utils \
        xvfb \
        xterm \
        Xvfb \
        2>/dev/null || log_warn "Could not install some packages"
    
    # TTS
    apt-get install -y -qq \
        espeak \
        espeak-ng \
        2>/dev/null || log_warn "Could not install TTS"
    
    # Audio
    apt-get install -y -qq \
        pulseaudio \
        libportaudio2 \
        alsa-utils \
        2>/dev/null || log_warn "Could not install audio packages"
    
    echo "Done!"
else
    log_warn "Run with sudo to install system packages"
    echo ""
    echo "To install manually, run:"
    echo "  sudo apt-get install ffmpeg xvfb Xvfb xterm espeak espeak-ng pulseaudio alsa-utils"
fi

# Check installations
echo ""
log_info "Checking installations..."

check_cmd() {
    if command -v $1 &> /dev/null; then
        echo "  ✓ $1"
    else
        echo "  ✗ $1 (not found)"
    fi
}

check_cmd ffmpeg
check_cmd espeak
check_cmd espeak-ng
check_cmd xvfb-run
check_cmd Xvfb

# Create launcher script
log_info "Creating launcher..."
cat > ~/bin/ai-content-factory << 'EOF'
#!/bin/bash
cd ~/ai_content_factory
python3 main.py "$@"
EOF
chmod +x ~/bin/ai-content-factory
echo "Created ~/bin/ai-content-factory"

# Create cron setup
log_info "Setting up cron..."
(crontab -l 2>/dev/null | grep -v "ai-content-factory"; echo "# AI Content Factory") | crontab - 2>/dev/null || true
echo "Cron ready"

# Create YouTube upload helper
log_info "Creating YouTube upload script..."
cat > ~/bin/upload-youtube << 'EOF'
#!/bin/bash
# Upload to YouTube using yt-dlp
# Usage: upload-youtube video.mp4 "Title" "Description"

VIDEO="$1"
TITLE="${2:-AI Tutorial}"
DESC="${3:-Created with AI Content Factory}"

if [ -z "$VIDEO" ]; then
    echo "Usage: upload-youtube <video.mp4> [title] [description]"
    exit 1
fi

if ! command -v yt-dlp &> /dev/null; then
    echo "Installing yt-dlp..."
    pip3 install yt-dlp
fi

# Note: You'll need to authenticate with YouTube first
# Run: yt-dlp --username oauth --password-from-stdin
# (or set up OAuth)

yt-dlp \
    --upload-file "$VIDEO" \
    --title "$TITLE" \
    --description "$DESC" \
    --privacy private \
    "$@"
EOF
chmod +x ~/bin/upload-youtube

echo ""
echo "============================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "============================================"
echo ""
echo "Quick Start:"
echo "  1. Generate topics:"
echo "     ai-content-factory --generate --niche ai"
echo ""
echo "  2. Record screen (10 seconds):"
echo "     ai-content-factory --record --duration 10"
echo ""
echo "  3. Full pipeline:"
echo "     ai-content-factory --full --niche crypto"
echo ""
echo "  4. Set up automation (runs daily):"
echo "     ai-content-factory --setup"
echo ""
echo "  5. Check status:"
echo "     ai-content-factory --status"
echo ""
echo "To enable YouTube upload:"
echo "  - Install yt-dlp: pip3 install yt-dlp"
echo "  - Or use YouTube Data API"
echo ""
