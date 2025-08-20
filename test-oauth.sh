#!/bin/bash

# OAuth Token Flow Test Script
# Replace the placeholders below with your actual values

API_URL="https://your-app-name.cloudhub.io"  # Replace with your actual API URL
CLIENT_ID="your_client_id"                   # Replace with existing client_id from your database
CLIENT_SECRET="your_client_secret"           # Replace with existing client_secret from your database

echo "Testing OAuth Token Flow with Callback..."
echo "API URL: $API_URL"
echo "Client ID: $CLIENT_ID"
echo ""

curl -X POST "$API_URL/oauth/token" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{
    \"client_id\": \"$CLIENT_ID\",
    \"client_secret\": \"$CLIENT_SECRET\",
    \"grant_type\": \"client_credentials\",
    \"callback_url\": \"https://redacted-org.lightning.force.com/services/apexrest/api/auth/callback/\"
  }" \
  --verbose

echo ""
echo "✅ OAuth test completed. Check the logs for debug messages!"