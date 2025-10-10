# Step-by-Step Testing Commands

## Step 2: Execute Tests

### Step 2A: Test OAuth Flow

**Replace these values:**
- `YOUR_API_URL` - Your CloudHub URL (e.g., `https://employee-service-api.us-e2.cloudhub.io`)
- `YOUR_CLIENT_ID` - An existing client_id from your api_clients table
- `YOUR_CLIENT_SECRET` - The corresponding client_secret

```bash
curl -X POST "YOUR_API_URL/oauth/token" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET", 
    "grant_type": "client_credentials",
    "callback_url": "https://your-salesforce-org.lightning.force.com/services/apexrest/api/auth/callback/"
  }' \
  --verbose
```

### Step 2B: Test Login Flow

**Replace these values:**
- `https://your-mulesoft-api.cloudhub.io` - Your CloudHub URL
- `your_username` - An existing username from your users table
- `your_password_here` - The password for that user
- `005XXXXXXXXXXXXXXX` - Your Salesforce user ID (optional)

```bash
curl -X POST "https://your-mulesoft-api.cloudhub.io/auth/login" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password_here",
    "callback_url": "https://your-salesforce-org.lightning.force.com/services/apexrest/api/auth/callback/",
    "salesforce_user_id": "005XXXXXXXXXXXXXXX"
  }' \
  --verbose
```

## Step 3: Check Logs

After running each test, go to **Anypoint Platform → Runtime Manager → Your App → Logs**.

Look for these debug messages in order:

### OAuth Flow Logs to Look For:
1. ✅ `"OAuth token request received"`
2. ✅ `"Raw OAuth request payload: {...}"`
3. ✅ `"OAuth - Extracted variables: clientId=..., callbackUrl=..."`
4. ✅ `"About to store in DB - clientId: ..., callbackUrl: ..., accessToken: ..."`
5. ✅ `"Checking callback URL: ..."`
6. ✅ `"Making callback to: ... with token: ..."`

### Login Flow Logs to Look For:
1. ✅ `"User login request received"`
2. ✅ `"Raw login payload: {...}"`
3. ✅ `"Login - Extracted variables: username=..., callbackUrl=..."`
4. ✅ `"Login - About to update DB - clientId: ..., callbackUrl: ..."`
5. ✅ `"Login - Checking callback URL: ..."`
6. ✅ `"Login - Making callback to: ... with token: ..."`

## What to Report Back

Please tell me:

1. **Which test did you run?** (OAuth or Login)
2. **What was the HTTP response?** (200, 401, 500, etc.)
3. **Which debug messages appeared in the logs?**
4. **Which debug messages were missing?**
5. **Any error messages in the logs?**

This will tell us exactly where the issue is occurring! 🔍