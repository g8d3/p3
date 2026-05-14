#!/bin/bash
# pi-termux.sh — Lanzar pi con fix Termux
# Redirige al wrapper global
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PI_TERMUX_FIX=1
export NODE_OPTIONS="--import $DIR/pi-termux.mjs${NODE_OPTIONS:+ $NODE_OPTIONS}"
exec pi "$@"
