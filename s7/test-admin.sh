#!/bin/bash

echo "Testing admin authentication..."

AUTH_RESPONSE=$(curl -X POST http://localhost:8090/api/admins/auth-with-password \
  -H "Content-Type: application/json" \
  -d '{
    "identity": "admin@example.com",
    "password": "admin123123"
  }')

echo "Response: $AUTH_RESPONSE"

TOKEN=$(echo $AUTH_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
  echo "✅ Admin authentication successful!"
else
  echo "❌ Admin authentication failed. Please create admin at http://localhost:8090/_/"
fi