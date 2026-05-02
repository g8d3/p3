# GLM API Performance Monitor

A Python script to measure and analyze performance metrics when connecting to the GLM model through the z.ai coding plan API.

## Features

- **Connection Time**: Measures time to establish API connection
- **Time to First Token (TTFT)**: Time from request start to first generated token
- **Time to Completion**: Total time for complete response generation
- **Throughput Metrics**: Tokens per second (TPS)
- **Statistical Analysis**: P50, P90, P95, P99 percentiles
- **Error Tracking**: Logs timeouts and API errors
- **Multiple Export Formats**: JSON and CSV for further analysis

## Installation

```bash
# Clone or download the script
cd /home/vuos/code/p3/s15

# Install dependencies
pip install requests
```

## Configuration

Set your API key as an environment variable:

```bash
export GLM_API_KEY="your-api-key-here"
```

Or modify the `API_KEY` variable in the script.

## Usage

### Mode 1: Automated Benchmark

Run a pre-defined 10-call benchmark test suite:

```bash
python glm_performance_monitor.py benchmark
```

This will:
1. Execute 10 test prompts of varying complexity
2. Measure performance for each call
3. Calculate aggregate statistics
4. Save results to `glm_performance_metrics.json` and `glm_performance_metrics.csv`

### Mode 2: Interactive Monitor

Run continuous monitoring with custom prompts:

```bash
python glm_performance_monitor.py monitor
```

Commands in monitor mode:
- Enter any prompt → Measure performance
- Type `stats` → View current statistics
- Type `save` → Save metrics to JSON
- Type `csv` → Export to CSV
- Type `exit` or `quit` → Stop monitoring

### Mode 3: Help

```bash
python glm_performance_monitor.py help
```

## Understanding the Metrics

### Core Performance Indicators

| Metric | Description | Good Performance |
|---------|-------------|------------------|
| **Time to First Token (TTFT)** | Time from request to first token generated | < 2s for simple prompts |
| **Tokens per Second (TPS)** | Generation throughput | > 50 tokens/s |
| **Connection Time** | Time to establish connection | < 1s |
| **Time to Completion** | Total response time | Varies by output size |

### Statistical Percentiles

| Percentile | Meaning | Usage |
|------------|----------|--------|
| **P50 (Median)** | Typical performance | Baseline expectation |
| **P90** | 90% of calls are faster than this | SLA target |
| **P95** | 95% of calls are faster than this | Strict SLA |
| **P99** | 99% of calls are faster than this | Tail latency optimization |

### Performance Tiers

| Tier | TTFT | TPS | Assessment |
|------|-------|-----|------------|
| **Excellent** | < 1.0s | > 100 tokens/s | Premium performance |
| **Good** | 1.0-2.0s | 50-100 tokens/s | Acceptable production performance |
| **Fair** | 2.0-4.0s | 25-50 tokens/s | Adequate for most use cases |
| **Poor** | > 4.0s | < 25 tokens/s | May need optimization |

## Output Files

### glm_performance_metrics.json

Contains:
- Generation timestamp
- Aggregated statistics (averages, percentiles)
- Individual call metrics with timestamps

### glm_performance_metrics.csv

Contains one row per API call with columns:
- timestamp
- connection_time
- time_to_first_token
- time_to_completion
- first_token_latency
- tokens_per_second
- input_tokens
- output_tokens
- total_tokens
- status
- error_message

## Use Cases

### 1. Baseline Performance Measurement

```bash
# Run benchmark before code changes
python glm_performance_monitor.py benchmark
cp glm_performance_metrics.json baseline_before.json

# Make changes to your integration
# ...

# Run benchmark after changes
python glm_performance_monitor.py benchmark
cp glm_performance_metrics.json baseline_after.json

# Compare results
python -c "
import json
with open('baseline_before.json') as f1, open('baseline_after.json') as f2:
    before = json.load(f1)['statistics']
    after = json.load(f2)['statistics']
    print(f'TTFT Change: {after[\"avg_time_to_first_token\"] - before[\"avg_time_to_first_token\"]:.4f}s')
    print(f'TPS Change: {after[\"avg_tokens_per_second\"] - before[\"avg_tokens_per_second\"]:.2f} tokens/s')
"
```

### 2. Performance Regression Testing

Add to your CI/CD pipeline:

```yaml
# .github/workflows/performance-test.yml
name: Performance Test

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run GLM Performance Benchmark
        env:
          GLM_API_KEY: ${{ secrets.GLM_API_KEY }}
        run: |
          python glm_performance_monitor.py benchmark
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: performance-metrics
          path: glm_performance_metrics.json
```

### 3. Real-time Production Monitoring

Run in production with logging:

```bash
# Start background monitor
nohup python glm_performance_monitor.py monitor > glm_monitor.log 2>&1 &

# Check real-time stats
tail -f glm_monitor.log

# Analyze historical data
python -c "
import json
import statistics

with open('glm_performance_metrics.json') as f:
    data = json.load(f)
    
# Extract hourly statistics
# ... analysis code ...
"
```

### 4. Load Testing

Test performance under concurrent load:

```bash
# Spawn multiple monitor instances in parallel
for i in {1..10}; do
    python glm_performance_monitor.py benchmark &
done

wait

# Aggregate results from all runs
# ... combine CSV files ...
```

## Troubleshooting

### Issue: Timeout Errors

```
✗ timeout: Request timed out after 30 seconds
```

**Solutions**:
- Check network connectivity
- Verify API endpoint is accessible
- Increase `timeout` parameter if needed
- Check API rate limits

### Issue: High TTFT

**Symptoms**:
```
TTFT: 5.234s | TPS: 15.2 | Output: 100 tokens
```

**Investigation**:
1. Check if using high `max_tokens` value
2. Verify network latency to API endpoint
3. Check if API is under load
4. Review prompt complexity

### Issue: Inconsistent TPS

**Symptoms**: Wide variance in tokens/second

**Investigation**:
1. Check for network fluctuations
2. Monitor API endpoint load
3. Verify stable API version
4. Check for rate limiting

## Integration Examples

### Flask Application

```python
from glm_performance_monitor import GLMAPIPerformanceMonitor

monitor = GLMAPIPerformanceMonitor(api_key="your-key")

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json['prompt']
    
    # Measure performance
    metrics = monitor.measure_performance(prompt)
    
    # Log metrics (to database, file, etc.)
    log_metrics(metrics)
    
    # Return response with performance headers
    return jsonify({
        'response': actual_response,
        'ttft': metrics.time_to_first_token,
        'tps': metrics.tokens_per_second
    })
```

### Next.js/Node.js Integration

```javascript
// Use Python script for measurement, Node.js for API calls
const { spawn } = require('child_process');

async function measureGLMPrompt(prompt) {
    const monitor = spawn('python', ['glm_performance_monitor.py', 'monitor']);
    
    monitor.stdin.write(prompt);
    
    return new Promise((resolve) => {
        monitor.stdout.on('data', (data) => {
            // Parse performance metrics
            const metrics = JSON.parse(data.toString());
            resolve(metrics);
        });
    });
}
```

## Performance Optimization Tips

Based on metrics collected:

1. **Reduce TTFT**: Minimize initial response size, optimize first token generation
2. **Increase TPS**: Stream responses, batch similar requests
3. **Reduce Connection Time**: Use connection pooling, persistent connections
4. **Optimize Prompt Engineering**: Clear, concise prompts improve generation speed

## Contributing

To add custom metrics:

```python
@dataclass
class PerformanceMetrics:
    # ... existing fields ...
    your_custom_metric: float  # Add your custom field here
    
    def calculate_custom_score(self):
        # Implement custom scoring logic
        pass
```

## License

MIT License - Use and modify freely for your projects.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review generated JSON/CSV files
3. Enable debug mode by adding `print()` statements
4. Check z.ai API documentation for changes
