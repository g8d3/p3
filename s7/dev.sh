#!/bin/bash

echo "🚀 Starting AI Scraper Application (Development Mode)"
echo "======================================================"

# Check if required services are running
echo "🔍 Checking required services..."

if ! curl -s http://localhost:8090/api/health > /dev/null 2>&1; then
  echo "❌ PocketBase not running on port 8090"
  echo "   Please start PocketBase first: ./pocketbase serve --http 0.0.0.0:8090 &"
  exit 1
fi
echo "✅ PocketBase running on port 8090"

# Start the application in dev mode (auto-reload)
echo "🖥️  Starting AI Scraper application (dev mode with auto-reload)..."
echo "   Server logs: server.log"
echo "   Auto-reload enabled - changes will restart server"
echo "   Press Ctrl+C to stop"
echo ""

bun run dev