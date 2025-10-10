# Callback Testing and Debugging Guide

## 🐛 Enhanced Debugging Version Deployed

The latest JAR includes comprehensive logging to debug the callback issue. Here's what to test:

## 📋 Test Steps

### 1. OAuth Token Flow Test

```bash
curl -X POST http://your-api-url/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "grant_type": "client_credentials",
    "callback_url": "https://your-salesforce-org.lightning.force.com/services/apexrest/api/auth/callback/"
  }'
```

### 2. Login Flow Test

```bash
curl -X POST http://your-api-url/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password",
    "callback_url": "https://your-salesforce-org.lightning.force.com/services/apexrest/api/auth/callback/",
    "salesforce_user_id": "your_sf_user_id"
  }'
```

## 🔍 What to Look For in Logs

After testing, check the MuleSoft logs for these specific messages in sequence:

### OAuth Flow Debug Messages:
1. `"OAuth token request received"`
2. `"Raw OAuth request payload: {...}"`
3. `"OAuth request headers: {...}"`
4. `"OAuth - Extracted variables: clientId=..., callbackUrl=..."`
5. `"About to store in DB - clientId: ..., callbackUrl: ..., accessToken: ..."`
6. `"DB insert completed successfully"`
7. `"Checking callback URL: ..."`
8. `"Making callback to: ... with token: ..."`

### Login Flow Debug Messages:
1. `"User login request received"`
2. `"Raw login payload: {...}"`
3. `"Login request headers: {...}"`
4. `"Login - Extracted variables: username=..., callbackUrl=..., salesforceUserId=..."`
5. `"Login - About to update DB - clientId: ..., callbackUrl: ..., accessToken: ..."`
6. `"Login - DB update completed successfully"`
7. `"Login - Checking callback URL: ..."`
8. `"Login - Making callback to: ... with token: ..."`

## 🚨 Key Debug Points

### If callback_url is NULL in logs:
- The JSON payload is not being parsed correctly
- Check the raw payload logs to see what's actually being received
- Verify Content-Type header is `application/json`

### If callback_url shows in logs but not in database:
- There may be a database constraint issue
- Check for DB errors in logs
- Verify the `callback_url` column exists and allows NULLs

### If callback doesn't reach Salesforce:
- Check for callback error logs
- Verify the Salesforce endpoint is accessible
- Check for HTTP request failures

## 🔧 Quick Database Check

Run this SQL to see what's actually in the database:

```sql
SELECT client_id, access_token, callback_url, expires_at, created_at 
FROM api_clients 
ORDER BY created_at DESC 
LIMIT 5;
```

## 💡 Troubleshooting Tips

1. **Check Content-Type**: Ensure requests use `Content-Type: application/json`
2. **Verify JSON Format**: Use a JSON validator to check your request payload
3. **Check Log Level**: Ensure MuleSoft logging is set to INFO level
4. **Database Permissions**: Verify the API can update the callback_url column

## 🧪 Test with Hardcoded URL (Next Step)

If issues persist, we can create a version with a hardcoded callback URL to isolate whether the issue is:
- JSON parsing/variable extraction
- Database storage  
- HTTP callback execution