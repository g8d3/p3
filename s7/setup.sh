#!/bin/bash

echo "Setting up PocketBase collections..."

# Wait for PocketBase to be ready
sleep 2

echo "Setting up admin authentication..."

# Try default credentials first
echo "Trying default admin credentials..."
AUTH_RESPONSE=$(curl -X POST http://localhost:8090/api/admins/auth-with-password \
  -H "Content-Type: application/json" \
  -d '{
    "identity": "admin@example.com",
    "password": "admin123123"
  }' 2>/dev/null)

TOKEN=$(echo $AUTH_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Default credentials failed. Please enter admin credentials manually:"
  echo "Go to http://localhost:8090/_/ to see what admin users exist"
  echo "Then enter the email and password below:"

  echo -n "Admin email [admin@example.com]: "
  read ADMIN_EMAIL
  ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}

  echo -n "Admin password [admin123123]: "
  read -s ADMIN_PASSWORD
  ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123123}
  echo ""

  echo "Authenticating with: $ADMIN_EMAIL"
  AUTH_RESPONSE=$(curl -X POST http://localhost:8090/api/admins/auth-with-password \
    -H "Content-Type: application/json" \
    -d "{
      \"identity\": \"$ADMIN_EMAIL\",
      \"password\": \"$ADMIN_PASSWORD\"
    }")

  echo "Auth response: $AUTH_RESPONSE"
  TOKEN=$(echo $AUTH_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

  if [ -z "$TOKEN" ]; then
    echo "Authentication failed. Please check your credentials."
    exit 1
  fi
fi

echo "Got admin token"

# Create collections
echo "Creating collections..."

COLLECTIONS=(
  '{"name":"ai_models","type":"base","schema":[{"name":"name","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"api_key","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"api_url","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"model_id","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"owner","type":"relation","required":true,"options":{"collectionId":"_pb_users_auth_","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}}],"listRule":"@request.auth.id = owner.id","viewRule":"@request.auth.id = owner.id","createRule":"@request.auth.id != \"\"","updateRule":"@request.auth.id = owner.id","deleteRule":"@request.auth.id = owner.id"}'
  '{"name":"browsers","type":"base","schema":[{"name":"name","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"cdp_url","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"owner","type":"relation","required":true,"options":{"collectionId":"_pb_users_auth_","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}}],"listRule":"@request.auth.id = owner.id","viewRule":"@request.auth.id = owner.id","createRule":"@request.auth.id != \"\"","updateRule":"@request.auth.id = owner.id","deleteRule":"@request.auth.id = owner.id"}'
  '{"name":"data_sinks","type":"base","schema":[{"name":"name","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"type","type":"select","required":true,"options":{"maxSelect":1,"values":["webhook","s3","pocketbase","custom_api"]}},{"name":"config","type":"json","required":false,"options":{"maxSize":2000000}},{"name":"owner","type":"relation","required":true,"options":{"collectionId":"_pb_users_auth_","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}}],"listRule":"@request.auth.id = owner.id","viewRule":"@request.auth.id = owner.id","createRule":"@request.auth.id != \"\"","updateRule":"@request.auth.id = owner.id","deleteRule":"@request.auth.id = owner.id"}'
  '{"name":"scrapers","type":"base","schema":[{"name":"name","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"url","type":"url","required":true,"options":{"exceptDomains":null,"onlyDomains":null}},{"name":"ai_model","type":"relation","required":false,"options":{"collectionId":"ai_models","cascadeDelete":false,"minSelect":null,"maxSelect":1,"displayFields":null}},{"name":"browser","type":"relation","required":false,"options":{"collectionId":"browsers","cascadeDelete":false,"minSelect":null,"maxSelect":1,"displayFields":null}},{"name":"code","type":"text","required":false,"options":{"min":null,"max":null,"pattern":""}},{"name":"discovery_options","type":"json","required":false,"options":{"maxSize":2000000}},{"name":"selected_option","type":"text","required":false,"options":{"min":null,"max":null,"pattern":""}},{"name":"schedule","type":"text","required":false,"options":{"min":null,"max":null,"pattern":""}},{"name":"data_sink","type":"relation","required":false,"options":{"collectionId":"data_sinks","cascadeDelete":false,"minSelect":null,"maxSelect":1,"displayFields":null}},{"name":"owner","type":"relation","required":true,"options":{"collectionId":"_pb_users_auth_","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}}],"listRule":"@request.auth.id = owner.id","viewRule":"@request.auth.id = owner.id","createRule":"@request.auth.id != \"\"","updateRule":"@request.auth.id = owner.id","deleteRule":"@request.auth.id = owner.id"}'
  '{"name":"extraction_runs","type":"base","schema":[{"name":"scraper","type":"relation","required":true,"options":{"collectionId":"scrapers","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}},{"name":"status","type":"select","required":true,"options":{"maxSelect":1,"values":["pending","running","completed","failed"]}},{"name":"started_at","type":"date","required":false,"options":{"min":"0001-01-01 00:00:00.000Z","max":"9999-12-31 23:59:59.999Z"}},{"name":"finished_at","type":"date","required":false,"options":{"min":"0001-01-01 00:00:00.000Z","max":"9999-12-31 23:59:59.999Z"}},{"name":"steps","type":"json","required":false,"options":{"maxSize":2000000}},{"name":"output_data","type":"json","required":false,"options":{"maxSize":2000000}},{"name":"errors","type":"json","required":false,"options":{"maxSize":2000000}}],"listRule":"","viewRule":"","createRule":"","updateRule":"","deleteRule":""}'
  '{"name":"tests","type":"base","schema":[{"name":"scraper","type":"relation","required":true,"options":{"collectionId":"scrapers","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}},{"name":"name","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"code","type":"text","required":true,"options":{"min":null,"max":null,"pattern":""}},{"name":"owner","type":"relation","required":true,"options":{"collectionId":"_pb_users_auth_","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}}],"listRule":"@request.auth.id = owner.id","viewRule":"@request.auth.id = owner.id","createRule":"@request.auth.id != \"\"","updateRule":"@request.auth.id = owner.id","deleteRule":"@request.auth.id = owner.id"}'
  '{"name":"test_runs","type":"base","schema":[{"name":"test","type":"relation","required":true,"options":{"collectionId":"tests","cascadeDelete":true,"minSelect":null,"maxSelect":1,"displayFields":null}},{"name":"status","type":"select","required":true,"options":{"maxSelect":1,"values":["pass","fail"]}},{"name":"logs","type":"json","required":false,"options":{"maxSize":2000000}},{"name":"run_at","type":"date","required":false,"options":{"min":"0001-01-01 00:00:00.000Z","max":"9999-12-31 23:59:59.999Z"}}],"listRule":"","viewRule":"","createRule":"","updateRule":"","deleteRule":""}'
)

# Get list of existing collections
echo "Checking existing collections..."
existing_collections=$(curl -s http://localhost:8090/api/collections \
  -H "Authorization: Bearer $TOKEN" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)

echo "Existing collections: $existing_collections"

for collection in "${COLLECTIONS[@]}"; do
  collection_name=$(echo $collection | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
  echo "Processing collection: $collection_name"

  # Check if collection already exists
  if echo "$existing_collections" | grep -q "^$collection_name$"; then
    echo "✅ Collection $collection_name already exists, skipping..."
    continue
  fi

  echo "Creating collection: $collection_name"
  response=$(curl -X POST http://localhost:8090/api/collections \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$collection")

  if echo "$response" | grep -q '"id":'; then
    echo "✅ Created collection: $collection_name"
  else
    echo "❌ Failed to create collection: $collection_name"
    echo "Response: $response"
  fi
done

echo "Setup complete! Admin credentials: admin@example.com / admin123123"
echo "Admin UI: http://localhost:8090/_/"
echo "App: http://localhost:3000"
echo ""
echo "Note: Some collections may need to be created manually in the admin UI if they failed above."
echo "Go to http://localhost:8090/_/ > Collections to create any missing collections."