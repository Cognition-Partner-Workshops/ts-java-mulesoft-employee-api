# Salesforce Named Credentials Integration Tests

## 🎯 **New Architecture Overview**

The API has been updated to work with Salesforce Named Credentials:

### **✅ Changes Made:**

1. **Database Schema Updated** - Added refresh token support
2. **Login Endpoint Modified** - Returns synchronous tokens
3. **Refresh Token Endpoint Created** - New `/auth/refresh-token` endpoint
4. **Web Page Updated** - PostMessage integration for Salesforce popups
5. **CORS Headers Added** - Proper Salesforce domain support

---

## 📋 **Test Plan**

### **Test 1: Database Schema Update**

First, run the database migration:

```sql
-- Run this in your PostgreSQL database
\i database-setup.sql
```

**Expected Result:** New columns added to `api_clients` table:
- `refresh_token`
- `refresh_token_expires_at`
- `token_expires_at`
- `salesforce_user_id`
- `created_at`
- `updated_at`
- `is_active`

### **Test 2: Updated Login Endpoint**

**Test URL:** `POST /auth/login`

**Test Request:**
```json
{
  "username": "redacted_user",
  "password": "REDACTED_PASSWORD",
  "userId": "005XXXXXXXXXXXXXXX"
}
```

**Expected Response:**
```json
{
  "access_token": "72aea7c8-ce2e-4aac-9b2c-20bb9462bd70-2025-08-16T...",
  "refresh_token": "refresh_a1b2c3d4-e5f6-7890-abcd-ef1234567890-2025-08-16T...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "005XXXXXXXXXXXXXXX",
  "client_id": "redacted_client_id",
  "scope": "read write"
}
```

### **Test 3: New Refresh Token Endpoint**

**Test URL:** `POST /auth/refresh-token`

**Test Request:**
```json
{
  "refresh_token": "refresh_a1b2c3d4-e5f6-7890-abcd-ef1234567890-2025-08-16T..."
}
```

**Expected Response:**
```json
{
  "access_token": "new-access-token-here...",
  "refresh_token": "new-refresh-token-here...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### **Test 4: Web Page Salesforce Integration**

**Test URL:** `https://your-api.com/web/login?userId=005XXXXXXXXXXXXXXX`

**Expected Behavior:**
1. Page shows "Connecting your Salesforce account to Employee Services"
2. After successful login, sends postMessage to parent window:
   ```javascript
   {
     type: 'API_AUTH_SUCCESS',
     token: 'access_token_here',
     refresh_token: 'refresh_token_here',
     userId: '005XXXXXXXXXXXXXXX',
     client_id: 'client_id_here',
     expires_in: 3600
   }
   ```
3. Popup window closes automatically

### **Test 5: CORS Headers**

**Test:** Make requests from `https://yourorg.salesforce.com`

**Expected Headers in Response:**
```
Access-Control-Allow-Origin: https://*.salesforce.com
Access-Control-Allow-Methods: POST, GET, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### **Test 6: Token Validation**

**Test URL:** `GET /api/employee/123/goals`

**Test Headers:**
```
Authorization: Bearer your-access-token-here
```

**Expected Result:** API call succeeds with Bearer token authentication

---

## 🧪 **Manual Testing Commands**

### **Login Test:**
```bash
curl -X POST "https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "redacted_user",
    "password": "REDACTED_PASSWORD",
    "userId": "005XXXXXXXXXXXXXXX"
  }'
```

### **Refresh Token Test:**
```bash
curl -X POST "https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/auth/refresh-token" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "REFRESH_TOKEN_FROM_LOGIN_RESPONSE"
  }'
```

### **Protected API Test:**
```bash
curl -X GET "https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/api/employee/123/goals" \
  -H "Authorization: Bearer ACCESS_TOKEN_FROM_LOGIN_RESPONSE"
```

---

## 🔍 **Database Verification**

After running tests, check the database:

```sql
-- Check token storage
SELECT 
  client_id, 
  access_token, 
  refresh_token, 
  salesforce_user_id,
  token_expires_at,
  refresh_token_expires_at,
  is_active,
  created_at,
  updated_at
FROM api_clients 
WHERE salesforce_user_id = '005XXXXXXXXXXXXXXX'
ORDER BY updated_at DESC;
```

---

## 🚀 **Salesforce Named Credentials Setup**

In Salesforce, create a Named Credential with:

1. **URL:** `https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io`
2. **Identity Type:** `Named Principal`
3. **Authentication Protocol:** `OAuth 2.0`
4. **OAuth Flow:** `Authorization Code`
5. **Scope:** `read write`
6. **Authorization Endpoint:** `https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/web/login`
7. **Token Endpoint:** `https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/auth/login`
8. **Token Refresh Endpoint:** `https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/auth/refresh-token`

---

## ✅ **Success Criteria**

- ✅ Login returns refresh tokens
- ✅ Refresh endpoint generates new tokens
- ✅ Web page sends postMessage to Salesforce
- ✅ CORS headers allow Salesforce domains
- ✅ Database stores all new fields
- ✅ Token validation works for API calls