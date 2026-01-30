# GLM Performance Monitoring - Quick Start Guide

## Files Created

| File | Purpose |
|------|----------|
| `glm_performance_monitor.py` | Main Python script for measuring GLM API performance |
| `run_glm_monitor.sh` | Bash wrapper with interactive menu |
| `README_glm_performance_monitor.md` | Comprehensive documentation |

## Quick Start

### Step 1: Set API Key

```bash
export GLM_API_KEY="your-api-key-here"
```

### Step 2: Run Quick Test

```bash
./run_glm_monitor.sh
```

Select option 5 for a quick single-prompt test.

### Step 3: Run Full Benchmark

```bash
./run_glm_monitor.sh
```

Select option 1 to run 10 automated tests.

## Direct Python Usage

```bash
# Run benchmark
python glm_performance_monitor.py benchmark

# Run interactive monitor
python glm_performance_monitor.py monitor
```

## Key Metrics Measured

| Metric | Good | Needs Improvement |
|---------|-------|------------------|
| **TTFT** (Time to First Token) | < 2s | > 4s |
| **TPS** (Tokens per Second) | > 50 | < 25 |
| **Connection Time** | < 0.5s | > 1s |
| **Success Rate** | > 95% | < 90% |

## Output Files Generated

After running, you'll get:

1. **glm_performance_metrics.json** - Detailed statistics including:
   - Average, median, P50, P90, P95, P99 latencies
   - Throughput metrics (tokens/second)
   - Success rate

2. **glm_performance_metrics.csv** - Per-call data for analysis in Excel/Google Sheets

## Troubleshooting

### Error: "No metrics file found"
Run benchmark or monitor first to generate data.

### Error: Timeout
Check:
- Network connectivity
- API endpoint availability
- Firewall settings

### Error: API key not set
Make sure to export:
```bash
export GLM_API_KEY="your-key-here"
```

## Performance Optimization Checklist

Based on metrics:

- [ ] TTFT consistently under 2s
- [ ] TPS consistently above 50 tokens/s
- [ ] Success rate above 95%
- [ ] Connection time under 0.5s
- [ ] P95 latency under 3s

## Continuous Monitoring Setup

For production monitoring:

```bash
# Start background monitor
nohup python glm_performance_monitor.py monitor > /tmp/glm_monitor.log 2>&1 &

# Save PID
echo $! > /tmp/glm_monitor.pid

# Stop when needed
kill $(cat /tmp/glm_monitor.pid)
```

## CI/CD Integration

Add to GitHub Actions workflow:

```yaml
name: GLM Performance Test

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        run: pip install requests
      - name: Run Benchmark
        env:
          GLM_API_KEY: ${{ secrets.GLM_API_KEY }}
        run: |
          python glm_performance_monitor.py benchmark
      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: performance-results
          path: glm_performance_metrics.*
```

## Next Steps

1. ✅ Run initial benchmark to establish baseline
2. 📊 Review JSON/CSV output to understand current performance
3. 🔍 Identify bottlenecks based on metrics
4. 🚀 Implement optimizations
5. 📈 Re-run benchmark to measure improvements
6. 📈 Set up continuous monitoring in production

## Support

For detailed documentation, see `README_glm_performance_monitor.md`
