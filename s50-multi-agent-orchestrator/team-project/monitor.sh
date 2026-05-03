#!/usr/bin/env bash
set -euo pipefail

# Real-time monitor for agent team
# Usage: ./monitor.sh
# Press Ctrl+C to exit, or type agent name to interrupt it

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDS_DIR="$PROJECT_DIR/.pids"
LOGS_DIR="$PROJECT_DIR/.logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

trap 'echo -e "\n${YELLOW}Monitor stopped${NC}"; exit 0' INT

watch_logs() {
    while true; do
        clear
        echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║         🤖 AGENT TEAM MONITOR                   ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
        echo ""

        for name in html css js tests docs; do
            local pid_file="$PIDS_DIR/${name}.pid"
            local log_file="$LOGS_DIR/${name}.log"

            if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
                echo -e "  ${GREEN}●${NC} ${BLUE}$name${NC} [running]"
            elif [[ -f "$log_file" ]] && grep -q "\[DONE\]" "$log_file" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} ${BLUE}$name${NC} [done]"
            else
                echo -e "  ${YELLOW}○${NC} ${BLUE}$name${NC} [idle]"
            fi

            # Show last 2 lines of log
            if [[ -f "$log_file" ]]; then
                tail -2 "$log_file" 2>/dev/null | while IFS= read -r line; do
                    # Truncate long lines
                    echo -e "    ${line:0:70}"
                done
            fi
            echo ""
        done

        echo -e "${CYAN}──────────────────────────────────────────────────${NC}"
        echo -e "  ${YELLOW}Commands:${NC}"
        echo -e "    Type agent name (html/css/js/tests/docs) to interrupt"
        echo -e "    Type 'all' to stop all"
        echo -e "    Ctrl+C to exit monitor"
        echo -e "${CYAN}──────────────────────────────────────────────────${NC}"

        # Check for user input (non-blocking)
        read -t 2 -r input || true
        case "${input:-}" in
            html|css|js|tests|docs)
                ./launch.sh stop-one "$input"
                sleep 1
                ;;
            all)
                ./launch.sh stop
                sleep 1
                ;;
        esac
    done
}

watch_logs
