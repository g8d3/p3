#!/bin/bash
# Quick configuration script for API Benchmark

echo "🚀 API Benchmark Configuration"
echo "=============================="

# Check if environment variables are set
if [ -z "$ZAI_API_KEY" ]; then
    echo "❌ ZAI_API_KEY is not set."
    echo "Please enter your ZAI API key:"
    read -r zai_key
    export ZAI_API_KEY="$zai_key"
    echo "✅ ZAI_API_KEY configured"
else
    echo "✅ ZAI_API_KEY is already configured"
fi

if [ -z "$OPENCODE_GO_API_KEY" ]; then
    echo "❌ OPENCODE_GO_API_KEY is not set."
    echo "Please enter your OpenCode GO API key:"
    read -r opencode_key
    export OPENCODE_GO_API_KEY="$opencode_key"
    echo "✅ OPENCODE_GO_API_KEY configured"
else
    echo "✅ OPENCODE_GO_API_KEY is already configured"
fi

# Create .env file for persistence
echo "Creating .env file..."
cat > .env << EOF
ZAI_API_KEY=$ZAI_API_KEY
OPENCODE_GO_API_KEY=$OPENCODE_GO_API_KEY
EOF

echo "✅ Environment variables saved to .env file"

# Check if Python is available
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 is available"
    
    # Install requirements if needed
    if ! python3 -c "import requests" &> /dev/null; then
        echo "📦 Installing required packages..."
        pip3 install requests
    else
        echo "✅ Required packages are already installed"
    fi
    
    # Ask if user wants to run benchmark now
    echo ""
    echo "Would you like to run the benchmark now? (y/n)"
    read -r run_now
    
    if [[ "$run_now" =~ ^[Yy]$ ]]; then
        echo "🎯 Starting API Benchmark..."
        python3 api_benchmark.py
    else
        echo "📋 You can run the benchmark later with:"
        echo "   python3 api_benchmark.py"
        echo ""
        echo "💡 Tip: You can also run:"
        echo "   source .env  # To load environment variables"
        echo "   ./run_benchmark.sh  # To run the benchmark with setup"
    fi
else
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    echo "   Then run: python3 api_benchmark.py"
fi