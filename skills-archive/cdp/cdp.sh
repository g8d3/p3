#!/bin/bash
# CDP Skill — Lanza Chrome con remote debugging
# Config personal: ~/.config/cdp-skill/config.sh
# Env vars (CDP_PORT, CDP_DIR, CDP_PROFILE, CDP_MODE) ganan sobre config

# Cargar config personal (usa :=, por eso va antes que env vars)
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/cdp-skill/config.sh"
[ -f "$CONFIG" ] && source "$CONFIG"

# Defaults genéricos (neutrales, ningún path personal)
PORT="${CDP_PORT:-9222}"
DIR="${CDP_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/cdp-profile}"
PROFILE="${CDP_PROFILE:-}"
MODE="${CDP_MODE:-auto}"

mkdir -p "$DIR"
pkill -f "chrome.*--remote-debugging-port=$PORT" 2>/dev/null
sleep 0.3

ARGS=(
  --user-data-dir="$DIR"
  --remote-debugging-port="$PORT"
  --no-first-run --no-default-browser-check
  --disable-features=DownloadRestrictions
)
[ -n "$PROFILE" ] && ARGS+=(--profile-directory="$PROFILE")
[ "$MODE" = headless ] && ARGS+=(--headless)
[ "$MODE" = auto ] && [ -z "$DISPLAY" ] && ARGS+=(--headless)

google-chrome "${ARGS[@]}" "$@" &>/dev/null &
disown
echo "CDP: port=$PORT dir=$DIR${PROFILE:+ profile=$PROFILE} pid=$!"
