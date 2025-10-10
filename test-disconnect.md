# Test Disconnect Endpoint

## Endpoint Details
- **URL**: `/api/disconnect`
- **Method**: `POST`
- **Authentication**: None required (Salesforce will call this)
- **Content-Type**: `application/json`

## Request Format
```json
{
  "userId": "005XXXXXXXXXXXXXXX",
  "clientId": "your_client_id_here"
}
```

## Response Formats

### Success Response (200)
```json
{
  "status": "success",
  "message": "API connection disconnected successfully",
  "userId": "005XXXXXXXXXXXXXXX",
  "clientId": "your_client_id_here",
  "timestamp": "2025-08-17T16:30:00Z"
}
```

### Not Found Response (404)
```json
{
  "status": "not_found",
  "message": "No active API connection found for this user",
  "userId": "005XXXXXXXXXXXXXXX", 
  "clientId": "your_client_id_here",
  "timestamp": "2025-08-17T16:30:00Z"
}
```

### Error Response (400)
```json
{
  "error": "invalid_request",
  "error_description": "Missing required fields: userId and clientId"
}
```

## Test Commands

### Test with valid data:
```bash
curl -X POST "https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/api/disconnect" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "005XXXXXXXXXXXXXXX",
    "clientId": "your_actual_client_id"
  }'
```

### Test with missing data:
```bash
curl -X POST "https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/api/disconnect" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "005Ka000001pgh7IAA"
  }'
```

### Test with non-existent user:
```bash
curl -X POST "https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io/api/disconnect" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "nonexistent",
    "clientId": "nonexistent"
  }'
```

## Database Changes

The endpoint performs this SQL update:
```sql
UPDATE api_clients 
SET is_active = false, 
    updated_at = CURRENT_TIMESTAMP
WHERE salesforce_user_id = :salesforceUserId 
  AND client_id = :clientId 
  AND is_active = true
```

## Salesforce Integration

Once deployed, Salesforce can call this endpoint when users disconnect:

1. **User clicks "Disconnect API"** in Salesforce
2. **Salesforce updates** local custom setting `Is_Active__c = false`
3. **Salesforce calls** your `/api/disconnect` endpoint
4. **Your API updates** database to mark user as inactive
5. **Both systems synchronized** ✅

## CORS Support

The endpoint includes CORS headers to allow Salesforce domains:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: POST, GET, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization`