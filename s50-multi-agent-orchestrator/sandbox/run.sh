#!/usr/bin/env bash
set -euo pipefail

# sandbox - run any command in an isolated Docker container
# Usage: sandbox [--net] [--write] [--root] <cmd> [args...]
#
# Options:
#   --net     Enable host networking (default: isolated)
#   --write   Make project dir writable (implies --root in rootless Docker)
#   --root    Run as root inside container
#
# Examples:
#   sandbox echo hello
#   sandbox --net curl https://example.com
#   sandbox --write touch newfile.txt
#   sandbox bash

IMAGE="sandbox-base"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(pwd)"

NET="none"
MOUNT_FLAGS="readonly"
USER_FLAG="--user $(id -u):$(id -g)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --net)   NET="host"; shift ;;
        --write) MOUNT_FLAGS=""; USER_FLAG="--user root"; shift ;;
        --root)  USER_FLAG="--user root"; shift ;;
        --)      shift; break ;;
        -*)      echo "Unknown option: $1" >&2; exit 1 ;;
        *)       break ;;
    esac
done

[[ $# -eq 0 ]] && { echo "Usage: sandbox [--net] [--write] [--root] <cmd> [args...]" >&2; exit 1; }

if ! docker image inspect "$IMAGE" &>/dev/null; then
    echo "Building sandbox image (one-time)..." >&2
    docker build -t "$IMAGE" -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR" >&2
fi

exec docker run --rm -i \
    --network "$NET" \
    --memory 4g \
    --cpus 2 \
    $USER_FLAG \
    --mount "type=bind,source=$PROJECT_DIR,target=/workspace${MOUNT_FLAGS:+,$MOUNT_FLAGS}" \
    --workdir /workspace \
    "$IMAGE" "$@"
