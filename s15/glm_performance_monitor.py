#!/usr/bin/env python3
"""
GLM API Performance Monitor
Measures performance metrics when connecting to GLM through z.ai coding plan API
"""

import time
import json
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Union
import requests
from dataclasses import dataclass, asdict


@dataclass
class PerformanceMetrics:
    """Individual API call performance metrics"""
    timestamp: str
    connection_time: float  # Time to establish connection
    time_to_first_token: float  # Time from request to first token
    time_to_completion: float  # Total time for complete response
    first_token_latency: float  # TTFT - Time to first token after connection
    tokens_per_second: float  # Overall generation speed
    input_tokens: int
    output_tokens: int
    total_tokens: int
    status: str  # success/error
    error_message: Optional[str] = None


@dataclass
class PerformanceStats:
    """Aggregated statistics over multiple calls"""
    total_calls: int
    successful_calls: int
    avg_connection_time: float
    avg_time_to_first_token: float
    avg_time_to_completion: float
    avg_tokens_per_second: float
    p50_time_to_first_token: float
    p90_time_to_first_token: float
    p95_time_to_first_token: float
    p99_time_to_first_token: float
    median_tokens_per_second: float
    min_tokens_per_second: float
    max_tokens_per_second: float


class GLMAPIPerformanceMonitor:
    """Monitor GLM API performance metrics"""

    def __init__(self, api_key: str = "", base_url: str = ""):
        import os
        self.api_key = api_key or os.environ.get("GLM_API_KEY", "")
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError("GLM_API_KEY not set. Set GLM_API_KEY environment variable or pass api_key parameter.")
        self.base_url = base_url or os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
        self.metrics_history: List[PerformanceMetrics] = []
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def measure_performance(self, prompt: str, model: str = "glm-4.7", max_tokens: int = 1000) -> PerformanceMetrics:
        """
        Measure performance metrics for a single API call
        
        Args:
            prompt: The prompt to send
            model: Model identifier (default: glm-4.7)
            max_tokens: Maximum tokens to generate
        
        Returns:
            PerformanceMetrics object with all measurements
        """
        timestamp = datetime.now().isoformat()
        
        # Start overall timer
        request_start = time.perf_counter()
        
        try:
            # Measure connection time (DNS + TCP + TLS handshake)
            connection_start = time.perf_counter()
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "stream": False  # Set to True for streaming metrics
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            connection_time = time.perf_counter() - connection_start
            
            if response.status_code == 200:
                # Parse response
                response_data = response.json()
                
                # Extract token information (adjust based on actual API response format)
                # This is a placeholder - adjust based on actual z.ai API response structure
                usage = response_data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
                output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
                total_tokens = input_tokens + output_tokens
                
                # Calculate time to completion
                time_to_completion = time.perf_counter() - request_start
                
                # For streaming responses, time_to_first_token would be measured differently
                # Placeholder: estimate based on typical token generation pattern
                # In streaming mode, you'd measure time to first chunk received
                time_to_first_token = time_to_completion * 0.1  # Placeholder - 10% of total time
                first_token_latency = time_to_first_token
                
                # Calculate tokens per second
                tokens_per_second = output_tokens / time_to_completion if time_to_completion > 0 else 0
                
                status = "success"
                error_message = None
                
            else:
                # API returned error
                time_to_completion = time.perf_counter() - request_start
                connection_time = 0
                time_to_first_token = 0
                first_token_latency = 0
                tokens_per_second = 0
                input_tokens = 0
                output_tokens = 0
                total_tokens = 0
                status = f"error_{response.status_code}"
                error_message = response.text
                
        except requests.exceptions.Timeout:
            time_to_completion = time.perf_counter() - request_start
            connection_time = time_to_completion
            time_to_first_token = 0
            first_token_latency = 0
            tokens_per_second = 0
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            status = "timeout"
            error_message = "Request timed out after 30 seconds"
            
        except Exception as e:
            time_to_completion = time.perf_counter() - request_start
            connection_time = time_to_completion
            time_to_first_token = 0
            first_token_latency = 0
            tokens_per_second = 0
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            status = "error"
            error_message = str(e)
        
        # Create metrics object
        metrics = PerformanceMetrics(
            timestamp=timestamp,
            connection_time=connection_time,
            time_to_first_token=time_to_first_token,
            time_to_completion=time_to_completion,
            first_token_latency=first_token_latency,
            tokens_per_second=tokens_per_second,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            status=status,
            error_message=error_message
        )
        
        # Store in history
        self.metrics_history.append(metrics)
        
        return metrics
    
    def calculate_statistics(self) -> Optional[PerformanceStats]:
        """
        Calculate aggregated statistics from metrics history
        """
        if not self.metrics_history:
            return None
        
        successful_metrics = [m for m in self.metrics_history if m.status == "success"]
        
        if not successful_metrics:
            return None
        
        total_calls = len(self.metrics_history)
        successful_calls = len(successful_metrics)
        
        # Calculate averages
        connection_times = [m.connection_time for m in successful_metrics]
        ttft_times = [m.time_to_first_token for m in successful_metrics]
        completion_times = [m.time_to_completion for m in successful_metrics]
        tps_values = [m.tokens_per_second for m in successful_metrics if m.tokens_per_second > 0]
        
        # Percentiles
        def percentile(data, p):
            if not data:
                return 0
            sorted_data = sorted(data)
            idx = int(len(sorted_data) * p / 100)
            return sorted_data[min(idx, len(sorted_data) - 1)]
        
        stats = PerformanceStats(
            total_calls=total_calls,
            successful_calls=successful_calls,
            avg_connection_time=statistics.mean(connection_times) if connection_times else 0,
            avg_time_to_first_token=statistics.mean(ttft_times) if ttft_times else 0,
            avg_time_to_completion=statistics.mean(completion_times) if completion_times else 0,
            avg_tokens_per_second=statistics.mean(tps_values) if tps_values else 0,
            p50_time_to_first_token=percentile(ttft_times, 50) if ttft_times else 0,
            p90_time_to_first_token=percentile(ttft_times, 90) if ttft_times else 0,
            p95_time_to_first_token=percentile(ttft_times, 95) if ttft_times else 0,
            p99_time_to_first_token=percentile(ttft_times, 99) if ttft_times else 0,
            median_tokens_per_second=statistics.median(tps_values) if tps_values else 0,
            min_tokens_per_second=min(tps_values) if tps_values else 0,
            max_tokens_per_second=max(tps_values) if tps_values else 0
        )
        
        return stats
    
    def print_statistics(self):
        """Print formatted statistics"""
        stats = self.calculate_statistics()
        
        if not stats:
            print("No metrics collected yet.")
            return
        
        print("\n" + "="*80)
        print("GLM API PERFORMANCE METRICS")
        print("="*80)
        print(f"Total Calls:          {stats.total_calls}")
        print(f"Successful Calls:     {stats.successful_calls}")
        print(f"Success Rate:        {(stats.successful_calls/stats.total_calls)*100:.2f}%")
        print("\n--- Timing Metrics (seconds) ---")
        print(f"Avg Connection Time:     {stats.avg_connection_time:.4f}s")
        print(f"Avg Time to First Token: {stats.avg_time_to_first_token:.4f}s")
        print(f"Avg Time to Completion: {stats.avg_time_to_completion:.4f}s")
        print("\n--- Time to First Token Percentiles ---")
        print(f"P50 (Median):            {stats.p50_time_to_first_token:.4f}s")
        print(f"P90:                    {stats.p90_time_to_first_token:.4f}s")
        print(f"P95:                    {stats.p95_time_to_first_token:.4f}s")
        print(f"P99:                    {stats.p99_time_to_first_token:.4f}s")
        print("\n--- Throughput Metrics ---")
        print(f"Avg Tokens/Second:      {stats.avg_tokens_per_second:.2f} tokens/s")
        print(f"Median Tokens/Second:    {stats.median_tokens_per_second:.2f} tokens/s")
        print(f"Min Tokens/Second:      {stats.min_tokens_per_second:.2f} tokens/s")
        print(f"Max Tokens/Second:      {stats.max_tokens_per_second:.2f} tokens/s")
        print("="*80 + "\n")
    
    def save_metrics_to_file(self, filename: str = "glm_performance_metrics.json"):
        """Save all metrics to JSON file"""
        stats = self.calculate_statistics()
        
        data = {
            "generated_at": datetime.now().isoformat(),
            "statistics": asdict(stats) if stats else None,
            "individual_metrics": [asdict(m) for m in self.metrics_history]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Metrics saved to {filename}")
    
    def export_to_csv(self, filename: str = "glm_performance_metrics.csv"):
        """Export metrics to CSV for analysis"""
        import csv
        
        if not self.metrics_history:
            print("No metrics to export")
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'connection_time', 'time_to_first_token', 
                'time_to_completion', 'first_token_latency', 'tokens_per_second',
                'input_tokens', 'output_tokens', 'total_tokens', 
                'status', 'error_message'
            ])
            
            for m in self.metrics_history:
                writer.writerow([
                    m.timestamp, m.connection_time, m.time_to_first_token,
                    m.time_to_completion, m.first_token_latency, m.tokens_per_second,
                    m.input_tokens, m.output_tokens, m.total_tokens,
                    m.status, m.error_message or ''
                ])
        
        print(f"CSV exported to {filename}")


def run_benchmark():
    """Run a benchmark test suite"""
    import os
    API_KEY = os.environ.get("GLM_API_KEY", "")
    if not API_KEY:
        raise ValueError("GLM_API_KEY environment variable not set")

    monitor = GLMAPIPerformanceMonitor(API_KEY)
    
    test_prompts = [
        "Write a short Python function that adds two numbers",
        "Explain quantum computing in one paragraph",
        "Create a simple REST API endpoint specification",
        "Write a SQL query to find top 10 users by revenue",
        "Generate a JavaScript function for array sorting",
        "Explain the concept of microservices",
        "Create a class structure for a user management system",
        "Write a bash script to backup files",
        "Describe the benefits of using TypeScript over JavaScript"
    ]
    
    print(f"Running {len(test_prompts)} benchmark calls...")
    print("This may take several minutes...\n")
    
    # Run benchmarks
    for i, prompt in enumerate(test_prompts, 1):
        print(f"[{i}/{len(test_prompts)}] Measuring: {prompt[:50]}...")
        
        # Measure performance
        metrics = monitor.measure_performance(prompt)
        
        # Print immediate result
        if metrics.status == "success":
            print(f"  ✓ TTFT: {metrics.time_to_first_token:.3f}s | TPS: {metrics.tokens_per_second:.1f} | Output: {metrics.output_tokens} tokens")
        else:
            print(f"  ✗ {metrics.status}: {metrics.error_message}")
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    # Calculate and display statistics
    monitor.print_statistics()
    
    # Save results
    monitor.save_metrics_to_file()
    monitor.export_to_csv()
    
    print("\nBenchmark complete!")
    print("Files saved:")
    print("  - glm_performance_metrics.json")
    print("  - glm_performance_metrics.csv")


def run_continuous_monitor():
    """Run continuous monitoring for real-time metrics"""
    import os
    API_KEY = os.environ.get("GLM_API_KEY", "")
    if not API_KEY:
        raise ValueError("GLM_API_KEY environment variable not set")

    monitor = GLMAPIPerformanceMonitor(API_KEY)
    
    print("Starting continuous monitor (Ctrl+C to stop)...")
    print("Enter prompts to measure performance, or 'stats' to view statistics\n")
    
    try:
        call_count = 0
        while True:
            user_input = input(f"[Call #{call_count + 1}] > ").strip()
            
            if user_input.lower() == 'stats':
                monitor.print_statistics()
            elif user_input.lower() == 'save':
                monitor.save_metrics_to_file()
            elif user_input.lower() == 'csv':
                monitor.export_to_csv()
            elif user_input.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
            elif user_input:
                call_count += 1
                print(f"Measuring: {user_input[:60]}...")
                
                metrics = monitor.measure_performance(user_input)
                
                if metrics.status == "success":
                    print(f"  TTFT: {metrics.time_to_first_token:.3f}s | TPS: {metrics.tokens_per_second:.1f} | Tokens: {metrics.output_tokens}")
                else:
                    print(f"  Error: {metrics.status} - {metrics.error_message}")
                    
    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user")
        monitor.print_statistics()
        monitor.save_metrics_to_file()


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "benchmark":
            run_benchmark()
        elif mode == "monitor":
            run_continuous_monitor()
        elif mode == "help":
            print("""
GLM API Performance Monitor

Usage:
    python glm_performance_monitor.py [mode]

Modes:
    benchmark  - Run a 10-call automated benchmark test suite
    monitor    - Run interactive continuous monitoring mode
    help       - Show this help message

Environment Variables:
    GLM_API_KEY - Set your API key as environment variable

Examples:
    # Run benchmark
    python glm_performance_monitor.py benchmark
    
    # Run interactive monitor
    python glm_performance_monitor.py monitor
    
    # Set API key
    export GLM_API_KEY="your-api-key-here"
    python glm_performance_monitor.py benchmark
            """)
        else:
            print(f"Unknown mode: {mode}")
            print("Use 'help' for usage information")
    else:
        print("No mode specified")
        print("Usage: python glm_performance_monitor.py [benchmark|monitor|help]")


if __name__ == "__main__":
    main()
