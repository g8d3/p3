#!/bin/bash

# Manual test script with hardcoded values to verify logic
echo "=== Testing Environment Variable Logic ==="

source .env
echo "✓ Environment loaded:"
echo "  URL: $TARGET_URL"
echo "  Field: $DOC_FIELD" 
echo "  Value: $DOC_VALUE"
echo "  Port: $CDP_PORT"

# Test function
a() { agent-browser --cdp "$CDP_PORT" "$@"; }

echo "Testing browser connection..."
if a eval "console.log('Test connection')" >/dev/null 2>&1; then
    echo "✓ Browser connection successful"
else
    echo "✗ Browser connection failed"
    exit 1
fi

echo "Testing navigation..."
a open "$TARGET_URL"
a wait --load networkidle
a find label "$DOC_FIELD" fill "$DOC_VALUE"
a screenshot test_env_result.png

echo "✓ Test completed - check test_env_result.png"