#!/bin/bash

# Login Flow Test Script
# Replace the placeholders below with your actual values

API_URL="https://your-app-name.cloudhub.io"  # Replace with your actual API URL
USERNAME="your_username"                     # Replace with existing username from your database
PASSWORD="your_password"                     # Replace with the password for that user
SALESFORCE_USER_ID="your_sf_user_id"         # Replace with your Salesforce user ID (optional)

echo "Testing Login Flow with Callback..."
echo "API URL: $API_URL"
echo "Username: $USERNAME"
echo ""

curl -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"password\": \"$PASSWORD\",
    \"callback_url\": \"https://your-salesforce-org.lightning.force.com/services/apexrest/api/auth/callback/\",
    \"salesforce_user_id\": \"$SALESFORCE_USER_ID\"
  }" \
  --verbose

echo ""
echo "✅ Login test completed. Check the logs for debug messages!"