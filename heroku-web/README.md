# Employee Service Authentication UI

This is a standalone web interface for the Employee Service API authentication system.

## Local Testing

1. **Open HTML files directly in browser**:
   - Open `index.html` (login page) in your web browser
   - Open `register.html` (registration page) in your web browser
   - Update the "API Base URL" field to point to your MuleSoft API

2. **Test with Node.js server**:
   ```bash
   npm install
   npm start
   ```
   Then visit: http://localhost:3000

## Heroku Deployment

1. **Initialize Git repository** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Create Heroku app**:
   ```bash
   heroku create your-auth-app-name
   ```

3. **Deploy to Heroku**:
   ```bash
   git push heroku main
   ```

4. **Access your app**:
   ```
   https://your-auth-app-name.herokuapp.com
   ```

## Database Connection

**Yes, the HTML pages are already tied to your PostgreSQL database** through your MuleSoft API:

- When users submit the registration form, it calls `/auth/register` on your MuleSoft API
- When users submit the login form, it calls `/auth/login` on your MuleSoft API  
- Your MuleSoft API connects to PostgreSQL to validate/create users
- The API returns OAuth tokens that can be used to access protected endpoints

## Configuration

The HTML pages include an "API Base URL" field where you can:
- For local testing: Use `http://localhost:8081` (if running MuleSoft locally)
- For production: Use your CloudHub URL: `https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io`

## CORS Configuration

If you deploy the HTML pages to Heroku and your MuleSoft API to CloudHub, you may need to configure CORS in your MuleSoft application to allow cross-origin requests from your Heroku domain.

## Testing Flow

1. **Deploy your MuleSoft app** to CloudHub with the database setup
2. **Test locally**: Open the HTML files in a browser and use your CloudHub URL
3. **Deploy to Heroku**: Use the instructions above
4. **Test end-to-end**: Register a user, login, and use the token for API calls