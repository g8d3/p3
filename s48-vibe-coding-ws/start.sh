#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source ~/.zshrc

# Auto-generate SSL cert if --ssl and cert doesn't exist
if [[ "$*" == *--ssl* ]] && [ ! -f /tmp/cert.pem ]; then
  echo "Generating self-signed SSL cert..."
  openssl req -x509 -newkey rsa:2048 -keyout /tmp/key.pem -out /tmp/cert.pem \
    -days 30 -nodes -subj "/CN=100.102.52.59" 2>/dev/null
fi

echo "Starting Vibe Coding server on port ${PORT:-8765}..."
python3 server.py "$@" 2>&1 | tee -a /tmp/vibe-server.log
