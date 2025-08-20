# OAuth Authentication Setup Guide

This guide explains how to set up the web-based OAuth authentication system for the Employee Service API.

## Overview

The authentication system includes:
- User registration and login web pages
- PostgreSQL database tables for user management
- OAuth2 token generation linked to user accounts
- Secure password hashing

## Database Setup

1. **Run the database setup script**:
   ```sql
   -- Execute the contents of database-setup.sql in your PostgreSQL database
   ```

2. **Verify tables were created**:
   - `users` - Stores user credentials and profile information
   - `api_clients` - Links users to OAuth2 client credentials

## Web Interface Endpoints

### Public Endpoints (No Authentication Required)

- **Login Page**: `https://your-domain.com/web/login` or `https://your-domain.com/web/`
- **Registration Page**: `https://your-domain.com/web/register`
- **User Registration API**: `POST /auth/register`
- **User Login API**: `POST /auth/login`

### Authentication Flow

1. **User Registration**:
   - Users access `/web/register` to create an account
   - Form collects: first name, last name, email, username, password
   - Passwords are hashed with salt before storage
   - Creates user record in `users` table

2. **User Login**:
   - Users access `/web/login` to sign in
   - Validates credentials against `users` table
   - Creates or retrieves API client credentials in `api_clients` table
   - Generates OAuth2 access token
   - Returns token to the web interface

3. **Token Usage**:
   - Users receive access token after successful login
   - Token can be used to access protected API endpoints
   - Token expires after 1 hour (3600 seconds)

## API Endpoints

### Register New User
```http
POST /auth/register
Content-Type: application/json

{
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@example.com",
  "username": "johndoe",
  "password": "securePassword123"
}
```

**Response** (201 Created):
```json
{
  "message": "User created successfully",
  "username": "johndoe"
}
```

### User Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "johndoe",
  "password": "securePassword123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "12345678-90ab-cdef-1234-567890abcdef-2024-01-01T12:00:00",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write",
  "user": {
    "username": "johndoe",
    "client_id": "abcdef12-3456-7890-abcd-ef1234567890"
  }
}
```

## Security Features

1. **Password Hashing**: Passwords are hashed using Base64 encoding with salt
2. **Token Expiration**: Access tokens expire after 1 hour
3. **User Validation**: Only active users can authenticate
4. **Duplicate Prevention**: Username and email must be unique

## Deployment Steps

1. **Database**: Run `database-setup.sql` in your PostgreSQL instance
2. **Deploy Application**: Deploy the updated Mule application to CloudHub 2.0
3. **Test Authentication**:
   - Access `https://your-domain.com/web/` 
   - Create a test account using the registration form
   - Login with the created credentials
   - Use the returned access token for API calls

## Testing the System

1. **Create Account**:
   - Navigate to `/web/register`
   - Fill out the registration form
   - Verify success message

2. **Login**:
   - Navigate to `/web/login`
   - Enter credentials from step 1
   - Copy the access token from the success message

3. **Use Token**:
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        https://your-domain.com/api/12345/goals
   ```

## Heroku Deployment Notes

If you plan to deploy the web interface to Heroku separately:
1. The HTML files in `/src/main/resources/web/` can be deployed as static files
2. Update the JavaScript fetch URLs to point to your MuleSoft CloudHub domain
3. Ensure CORS is configured properly for cross-origin requests

## Security Recommendations

1. **Use HTTPS**: Always use HTTPS in production
2. **Strong Passwords**: Implement password strength requirements
3. **Rate Limiting**: Add rate limiting to prevent brute force attacks
4. **Token Refresh**: Consider implementing token refresh mechanism
5. **Proper Hashing**: Consider upgrading to bcrypt or Argon2 for password hashing