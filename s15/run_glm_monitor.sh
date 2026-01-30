#!/bin/bash
# GLM Performance Monitor - Quick Start Script
# Wrapper for glm_performance_monitor.py

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if API key is set
if [ -z "$GLM_API_KEY" ]; then
    echo -e "${RED}Error: GLM_API_KEY environment variable not set${NC}"
    echo -e "${YELLOW}Please set your API key:${NC}"
    echo ""
    echo "  export GLM_API_KEY=\"your-api-key-here\""
    echo ""
    echo "Or edit glm_performance_monitor.py and set API_KEY directly"
    exit 1
fi

# Display menu
echo -e "${GREEN}GLM API Performance Monitor${NC}"
echo ""
echo "Select mode:"
echo "  1) Run automated benchmark (10 test prompts)"
echo "  2) Start interactive monitor"
echo "  3) View saved statistics"
echo "  4) Export metrics to CSV"
echo "  5) Quick performance test (single prompt)"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo -e "${GREEN}Running benchmark...${NC}"
        python glm_performance_monitor.py benchmark
        ;;
    2)
        echo -e "${GREEN}Starting interactive monitor${NC}"
        echo "Commands: stats | save | csv | exit"
        python glm_performance_monitor.py monitor
        ;;
    3)
        echo ""
        if [ -f "glm_performance_metrics.json" ]; then
            echo -e "${GREEN}Performance Statistics:${NC}"
            python -c "
import json
with open('glm_performance_metrics.json') as f:
    data = json.load(f)
if data.get('statistics'):
    stats = data['statistics']
    print(f'  Total Calls:          {stats[\"total_calls\"]}')
    print(f'  Success Rate:          {(stats[\"successful_calls\"]/stats[\"total_calls\"])*100:.1f}%')
    print(f'  Avg TTFT:             {stats[\"avg_time_to_first_token\"]:.3f}s')
    print(f'  Avg TPS:              {stats[\"avg_tokens_per_second\"]:.1f} tokens/s')
    print(f'  P50 TTFT:             {stats[\"p50_time_to_first_token\"]:.3f}s')
    print(f'  P90 TTFT:             {stats[\"p90_time_to_first_token\"]:.3f}s')
    print(f'  P95 TTFT:             {stats[\"p95_time_to_first_token\"]:.3f}s')
    print(f'  P99 TTFT:             {stats[\"p99_time_to_first_token\"]:.3f}s')
"
        else
            echo -e "${RED}No metrics file found. Run benchmark or monitor first.${NC}"
        fi
        ;;
    4)
        echo -e "${GREEN}Exporting to CSV...${NC}"
        python glm_performance_monitor.py
        # The script will export when called with proper arguments
        echo "Use python glm_performance_monitor.py with proper arguments to export"
        ;;
    5)
        echo -e "${GREEN}Running quick test...${NC}"
        python -c "
from glm_performance_monitor import GLMAPIPerformanceMonitor
import os

monitor = GLMAPIPerformanceMonitor(api_key=os.environ['GLM_API_KEY'])
metrics = monitor.measure_performance('What is 2+2?')

if metrics.status == 'success':
    print(f'  Status: {metrics.status}')
    print(f'  TTFT: {metrics.time_to_first_token:.3f}s')
    print(f'  TPS: {metrics.tokens_per_second:.1f} tokens/s')
    print(f'  Tokens: {metrics.output_tokens} output, {metrics.input_tokens} input')
else:
    print(f'  Error: {metrics.error_message}')
"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Done!${NC}"
