const express = require('express');
const path = require('path');
const axios = require('axios');

const app = express();
const port = process.env.PORT || 3000;

// Middleware to parse JSON and URL-encoded data
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files
app.use(express.static(__dirname));

// Route for root to serve login page with URL parameters
app.get('/', (req, res) => {
    const { userId, clientId } = req.query;
    
    // Read the HTML file and inject the parameters
    const fs = require('fs');
    let html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    
    // Inject userId and clientId into hidden form fields
    if (userId && clientId) {
        // Find the form and inject hidden fields before the submit button
        html = html.replace(
            /<button type="submit" class="login-btn">Sign In<\/button>/,
            `<input type="hidden" id="clientId" name="clientId" value="${clientId}">
            <input type="hidden" id="salesforceUserId" name="salesforceUserId" value="${userId}">
            <button type="submit" class="login-btn">Sign In</button>`
        );
        
        // Also inject JavaScript variables for the client to use
        html = html.replace(
            '</head>',
            `<script>
            window.salesforceConfig = {
                userId: '${userId}',
                clientId: '${clientId}'
            };
            </script>
            </head>`
        );
    }
    
    res.send(html);
});

// Route for login page
app.get('/login', (req, res) => {
    const { userId, clientId } = req.query;
    
    // Read the HTML file and inject the parameters
    const fs = require('fs');
    let html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    
    // Inject userId and clientId into hidden form fields
    if (userId && clientId) {
        html = html.replace(
            '<button type="submit" class="login-btn">Sign In</button>',
            `<input type="hidden" id="clientId" name="clientId" value="${clientId}">
            <input type="hidden" id="salesforceUserId" name="salesforceUserId" value="${userId}">
            <button type="submit" class="login-btn">Sign In</button>`
        );
    }
    
    res.send(html);
});

// POST route for handling authentication
app.post('/authenticate', async (req, res) => {
    console.log('Authentication request received:', req.body);
    const { username, password, clientId, salesforceUserId } = req.body;
    
    console.log('Extracted fields:', { 
        username: username ? 'provided' : 'missing', 
        password: password ? 'provided' : 'missing', 
        clientId: clientId || 'missing',
        salesforceUserId: salesforceUserId || 'missing'
    });
    
    // Validate required fields
    if (!username || !password || !clientId) {
        console.log('Validation failed - missing required fields');
        return res.status(400).json({
            error: "invalid_request",
            error_description: "Missing required fields: username, password, and clientId"
        });
    }
    
    try {
        // Call your Mule API for authentication
        const apiUrl = process.env.API_BASE_URL || 'https://employee-api-jtx6w5.5sc6y6-2.usa-e2.cloudhub.io';
        
        const authResponse = await axios.post(`${apiUrl}/auth/login`, {
            username: username,
            password: password,
            clientId: clientId,
            userId: salesforceUserId
        });
        
        if (authResponse.data.access_token) {
            // Return JSON response like the original working version
            // Let the client-side JavaScript handle postMessage
            res.json({
                access_token: authResponse.data.access_token,
                refresh_token: authResponse.data.refresh_token || '',
                user_id: authResponse.data.user_id || salesforceUserId,
                clientId: clientId
            });
        } else {
            throw new Error('Authentication failed - no access token received');
        }
        
    } catch (error) {
        console.error('Authentication error:', error.response?.data || error.message);
        
        const errorMessage = error.response?.data?.error_description || 
                             error.response?.data?.error || 
                             error.message || 
                             'Authentication failed';
        
        // Send error HTML page with postMessage
        const errorHtml = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .error-container {
                    background: white;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 400px;
                }
                .error-message {
                    color: #e74c3c;
                    margin-bottom: 1rem;
                }
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-message">
                    <h2>❌ Authentication Failed</h2>
                    <p>${errorMessage.replace(/'/g, "\\'")}</p>
                    <p><small>This window will close automatically...</small></p>
                </div>
            </div>
            <script>
                console.log('=== ERROR PAGE LOADED ===');
                
                const errorData = {
                    type: 'API_AUTH_ERROR',
                    error: ${JSON.stringify(errorMessage)},
                    timestamp: new Date().toISOString()
                };
                
                console.log('Sending error postMessage:', errorData);
                
                if (window.opener && !window.opener.closed) {
                    // Send to multiple origins for reliability
                    const targetOrigins = [
                        '*',
                        'https://trailsignup-c73971618265f0.lightning.force.com'
                    ];
                    
                    targetOrigins.forEach(origin => {
                        try {
                            window.opener.postMessage(errorData, origin);
                            console.log('Error postMessage sent to origin:', origin);
                        } catch (error) {
                            console.error('Failed to send error to origin:', origin, error);
                        }
                    });
                    
                    setTimeout(() => {
                        window.close();
                    }, 3000);
                } else {
                    console.log('No window opener for error page');
                    setTimeout(() => {
                        window.history.back();
                    }, 3000);
                }
            </script>
        </body>
        </html>`;
        
        res.status(400).send(errorHtml);
    }
});

// Simple test route that immediately sends postMessage
app.get('/test-simple', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head><title>Simple Test</title></head>
        <body>
            <h2>Simple PostMessage Test</h2>
            <p>This should send a message and close immediately</p>
            <script>
                console.log('Simple test page loaded');
                if (window.opener) {
                    var message = {
                        type: 'API_AUTH_SUCCESS',
                        token: 'test-token-123',
                        userId: 'test-user',
                        clientId: 'test-client'
                    };
                    window.opener.postMessage(message, '*');
                    console.log('Message sent:', message);
                    setTimeout(() => window.close(), 2000);
                } else {
                    console.log('No window opener');
                }
            </script>
        </body>
        </html>
    `);
});

// Test route to verify postMessage works
app.get('/test-postmessage', (req, res) => {
    const { userId, clientId } = req.query;
    
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>PostMessage Test</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 2rem;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .test-container {
                    background: white;
                    color: #333;
                    padding: 2rem;
                    border-radius: 10px;
                    max-width: 500px;
                    margin: 0 auto;
                }
                button {
                    background: #667eea;
                    color: white;
                    border: none;
                    padding: 1rem 2rem;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 1rem;
                    margin: 0.5rem;
                }
                button:hover {
                    background: #5a6fd8;
                }
            </style>
        </head>
        <body>
            <div class="test-container">
                <h2>🧪 PostMessage Test</h2>
                <p><strong>User ID:</strong> ${userId || 'Not provided'}</p>
                <p><strong>Client ID:</strong> ${clientId || 'Not provided'}</p>
                
                <button onclick="sendTestSuccess()">Send Success Message</button>
                <button onclick="sendTestError()">Send Error Message</button>
                <button onclick="closeWindow()">Close Window</button>
                
                <div id="log" style="margin-top: 1rem; background: #f5f5f5; padding: 1rem; border-radius: 5px; font-family: monospace; font-size: 0.9rem;"></div>
            </div>
            
            <script>
                const log = document.getElementById('log');
                
                function addLog(message) {
                    log.innerHTML += new Date().toLocaleTimeString() + ': ' + message + '<br>';
                    console.log(message);
                }
                
                addLog('Test page loaded');
                addLog('Window opener exists: ' + !!window.opener);
                
                function sendTestSuccess() {
                    const testData = {
                        type: 'API_AUTH_SUCCESS',
                        token: 'test-token-' + Date.now(),
                        refresh_token: 'test-refresh-' + Date.now(),
                        userId: '${userId || 'test-user-123'}',
                        clientId: '${clientId || 'test-client-456'}',
                        timestamp: new Date().toISOString()
                    };
                    
                    addLog('Sending SUCCESS message: ' + JSON.stringify(testData, null, 2));
                    
                    if (window.opener) {
                        try {
                            window.opener.postMessage(testData, '*');
                            addLog('SUCCESS postMessage sent to *');
                            
                            // Also try specific Salesforce domain
                            window.opener.postMessage(testData, 'https://trailsignup-c73971618265f0.lightning.force.com');
                            addLog('SUCCESS postMessage sent to Salesforce domain');
                        } catch (error) {
                            addLog('ERROR sending postMessage: ' + error.message);
                        }
                    } else {
                        addLog('ERROR: No window opener available');
                    }
                }
                
                function sendTestError() {
                    const errorData = {
                        type: 'API_AUTH_ERROR',
                        error: 'Test error message',
                        timestamp: new Date().toISOString()
                    };
                    
                    addLog('Sending ERROR message: ' + JSON.stringify(errorData, null, 2));
                    
                    if (window.opener) {
                        try {
                            window.opener.postMessage(errorData, '*');
                            addLog('ERROR postMessage sent');
                        } catch (error) {
                            addLog('ERROR sending postMessage: ' + error.message);
                        }
                    } else {
                        addLog('ERROR: No window opener available');
                    }
                }
                
                function closeWindow() {
                    addLog('Attempting to close window...');
                    try {
                        window.close();
                    } catch (error) {
                        addLog('Could not close window: ' + error.message);
                    }
                }
            </script>
        </body>
        </html>
    `);
});

// Route for register page
app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, 'register.html'));
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.listen(port, () => {
    console.log(`Employee Service Auth UI running on port ${port}`);
});