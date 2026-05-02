#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec opencode run "@REINDEX.md"
