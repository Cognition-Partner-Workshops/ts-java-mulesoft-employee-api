# Heroku Web App Deployment Guide - Named Credentials Support

## ✅ **What Was Updated**

Your Heroku web app (`heroku-web/index.html`) has been updated to support Salesforce Named Credentials with:

### **New Features Added:**
- ✅ **Refresh token support** - Now sends refresh_token to Salesforce
- ✅ **Enhanced postMessage** - Sends complete token data including user_id, client_id, expires_in
- ✅ **Better error handling** - Proper error messages to Salesforce
- ✅ **Popup cancellation handling** - Notifies Salesforce if user closes popup
- ✅ **Salesforce context detection** - Shows appropriate messaging when opened from Salesforce

## 🚀 **Deploy to Heroku**

### **Step 1: Navigate to Heroku folder**
```bash
cd "/path/to/your/project/heroku-web"
```

### **Step 2: Deploy to Heroku**
```bash
# Initialize git repo if not already done
git init

# Add Heroku remote if not already added
heroku git:remote -a partnerapiwebauth

# Add and commit changes
git add .
git commit -m "Update for Salesforce Named Credentials support with refresh tokens"

# Deploy to Heroku
git push heroku main
```

## 🎯 **Updated Authentication Flow**

### **What Happens Now:**
1. **Salesforce opens popup**: `https://your-heroku-app.herokuapp.com/?userId=005XXXXXXXXXXXXXXX`
2. **User enters credentials** on Heroku web page
3. **Web page calls MuleSoft API**: `POST /auth/login` with userId
4. **MuleSoft returns tokens**: access_token, refresh_token, user_id, client_id, expires_in
5. **Web page sends postMessage to Salesforce**:
   ```javascript
   {
     type: 'API_AUTH_SUCCESS',
     token: 'access_token_here',
     refresh_token: 'refresh_token_here', 
     userId: '005XXXXXXXXXXXXXXX',
     client_id: 'mulesoft_client_id',
     expires_in: 3600
   }
   ```
6. **Popup closes automatically**

## 📋 **What You Need to Deploy**

### **1. Deploy Database Changes**
Run the SQL migration first:
```sql
\i database-setup.sql
```

### **2. Deploy MuleSoft API**
Deploy the updated JAR to CloudHub:
- `employee-service-api-1.0.0-SNAPSHOT-mule-application.jar`

### **3. Deploy Heroku Web App**
Deploy the updated web app (instructions above)

## 🔧 **Testing**

### **Test the updated flow:**

1. **Direct web page test**:
   ```
   https://your-heroku-app.herokuapp.com/?userId=005XXXXXXXXXXXXXXX
   ```

2. **Check the response** - Should show "Connecting your Salesforce account to Employee Services"

3. **Login and verify** - Should send complete token data via postMessage

## ✅ **Updated PostMessage Format**

Your Heroku app now sends this enhanced data to Salesforce:

```javascript
// Success message
{
  type: 'API_AUTH_SUCCESS',
  token: 'access_token_here',
  refresh_token: 'refresh_token_here',
  userId: '005Ka000001pgh7IAA', 
  client_id: 'client_id_from_mulesoft',
  expires_in: 3600
}

// Error message  
{
  type: 'API_AUTH_ERROR',
  error: 'Authentication failed: error_message'
}

// Cancellation message
{
  type: 'API_AUTH_CANCELLED', 
  error: 'Authentication window was closed'
}
```

## 🎉 **Benefits**

- ✅ **Keep existing Heroku URL** - No Salesforce config changes needed
- ✅ **Enhanced token data** - Full Named Credentials support
- ✅ **Better error handling** - Proper Salesforce integration
- ✅ **Refresh token support** - Long-term authentication

Your existing Salesforce Named Credential will work perfectly with these updates! 🚀