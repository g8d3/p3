#!/bin/bash
# Quick setup and run script for API Benchmark

echo "🚀 Setting up API Benchmark Environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if required environment variables are set
if [ -z "$ZAI_API_KEY" ]; then
    echo "❌ ZAI_API_KEY environment variable is not set."
    echo "Please run: export ZAI_API_KEY='your_zai_api_key'"
    exit 1
fi

if [ -z "$OPENCODE_GO_API_KEY" ]; then
    echo "❌ OPENCODE_GO_API_KEY environment variable is not set."
    echo "Please run: export OPENCODE_GO_API_KEY='your_opencode_go_api_key'"
    exit 1
fi

# Install required Python packages
echo "📦 Installing required packages..."
pip3 install -r requirements.txt 2>/dev/null || pip3 install requests

# Make the benchmark script executable
chmod +x api_benchmark.py

# Run the benchmark
echo "🎯 Starting API Benchmark..."
echo "This will test all available models and generate performance metrics."
echo "Please wait... This may take a few minutes."
echo ""

python3 api_benchmark.py

echo ""
echo "✅ Benchmark completed! Check the generated JSON file for detailed results."