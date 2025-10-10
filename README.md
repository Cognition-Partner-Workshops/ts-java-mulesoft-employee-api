# Employee Service API

> A secure MuleSoft-based REST API for managing employee information including goals, learning status, pay dates, and PTO management.

## 🎯 Project Overview

The Employee Service API is a **MuleSoft Mule 4** application that provides a comprehensive set of RESTful endpoints for accessing and managing employee-related data. The API implements OAuth2 client credentials authentication and integrates with a PostgreSQL database for data persistence.

## ✨ Key Features

- **OAuth2 Security**: Client credentials flow with token-based authentication
- **Employee Goals**: Retrieve and track employee goal progress
- **Learning Management**: Access employee learning course status and progress
- **Payroll Integration**: Get next pay date information
- **PTO Management**: Check balances and schedule paid time off
- **Health Monitoring**: Built-in health check endpoint for monitoring database connectivity
- **API Console**: Interactive API documentation and testing interface
- **CloudHub 2.0 Ready**: Configured for deployment to Salesforce's CloudHub 2.0 platform

## 🏗️ Technical Architecture

### Technology Stack

- **Runtime**: Mule Runtime 4.9.6+ with Java 17
- **Build Tool**: Maven
- **Database**: PostgreSQL
- **Authentication**: OAuth2 Client Credentials
- **API Framework**: APIKit with OpenAPI Specification
- **Storage**: Object Store for token management

### Core Components

1. **OAuth2 Authentication System**
   - Custom OAuth2 implementation using client credentials flow
   - Token validation and management using Object Store
   - Client credentials stored securely in PostgreSQL (`api_clients` table)
   - Token expiration: 1 hour (3600 seconds)

2. **Database Integration**
   - PostgreSQL connection with environment variable configuration
   - Database tables:
     - `api_clients` - OAuth client credentials
     - `employee_goals` - Employee goal tracking
     - `employee_learning` - Learning course progress
     - `employee_pto` - PTO balances and requests

3. **API Endpoints**
   - **Protected**: `/api/*` (requires OAuth2 bearer token)
   - **Public**: `/console/*` (API documentation)
   - **Public**: `/health` (health check)
   - **Public**: `/oauth/token` (token generation)

### Main Flows

- **oauth-token-flow**: Handles OAuth2 token generation and validation
- **validate-token-subflow**: Validates bearer tokens for protected endpoints
- **employee-services-api-main**: Main API router with token validation
- **health-check-flow**: Database connectivity health check

## 📡 API Endpoints

### Authentication

#### Get OAuth Token
```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET
```

**Response:**
```json
{
  "access_token": "your-access-token",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Employee Endpoints

All employee endpoints require OAuth2 bearer token authentication:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

#### Get Employee Goals
```http
GET /api/{employeeId}/goals
```

#### Get Learning Status
```http
GET /api/{employeeId}/learning-status
```

#### Get Next Pay Date
```http
GET /api/{employeeId}/next-pay-date
```

#### Get PTO Balance
```http
GET /api/{employeeId}/pto/balance
```

#### Schedule PTO
```http
POST /api/{employeeId}/pto/schedule
Content-Type: application/json

{
  "startDate": "2025-10-15",
  "endDate": "2025-10-19",
  "hours": 40
}
```

### System Endpoints

#### Health Check
```http
GET /health
```

#### API Console
```http
GET /console/
```

## 🚀 Installation & Deployment

### Prerequisites

- Java 17 or higher
- Maven 3.8+
- PostgreSQL database
- MuleSoft Anypoint Platform account (for CloudHub deployment)
- Anypoint CLI or Studio (optional)

### Environment Configuration

Set the following environment variables or configure them in your deployment properties:

```properties
db.host=your-database-host
db.port=5432
db.database=your-database-name
db.username=your-database-username
db.password=your-database-password
```

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd employee-service-api
   ```

2. **Build the application**
   ```bash
   mvn clean compile
   ```

3. **Package the application**
   ```bash
   mvn clean package
   ```

4. **Run tests** (if MUnit tests exist)
   ```bash
   mvn test
   ```

5. **Deploy locally**
   - Import the project into Anypoint Studio
   - Configure database connection parameters
   - Run the application
   - Access the API at `http://localhost:8081`

### CloudHub 2.0 Deployment

The application includes a deployment configuration file at `src/main/resources/deploy_ch2.json`.

**Deploy using Anypoint CLI:**
```bash
anypoint-cli-v4 runtime-mgr:cloudhub2:application:deploy \
  --config-file src/main/resources/deploy_ch2.json
```

## 🗄️ Database Setup

### Required Tables

#### api_clients
```sql
CREATE TABLE api_clients (
    client_id VARCHAR(255) PRIMARY KEY,
    client_secret VARCHAR(255) NOT NULL,
    client_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### employee_goals
```sql
CREATE TABLE employee_goals (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    goal_title VARCHAR(255) NOT NULL,
    goal_description TEXT,
    target_date DATE,
    progress INTEGER DEFAULT 0,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### employee_learning
```sql
CREATE TABLE employee_learning (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    course_status VARCHAR(50),
    completion_percentage INTEGER DEFAULT 0,
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### employee_pto
```sql
CREATE TABLE employee_pto (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    pto_balance DECIMAL(10,2) DEFAULT 0,
    accrual_rate DECIMAL(10,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Sample Data

```sql
-- Insert sample OAuth client
INSERT INTO api_clients (client_id, client_secret, client_name)
VALUES ('demo_client', 'demo_secret', 'Demo Application');

-- Insert sample employee data
INSERT INTO employee_goals (employee_id, goal_title, progress, status)
VALUES ('EMP001', 'Complete Q4 Sales Target', 75, 'In Progress');

INSERT INTO employee_learning (employee_id, course_name, course_status, completion_percentage)
VALUES ('EMP001', 'Advanced Sales Techniques', 'In Progress', 60);

INSERT INTO employee_pto (employee_id, pto_balance, accrual_rate)
VALUES ('EMP001', 120.00, 8.00);
```

## 🔒 Security

- **OAuth2 Authentication**: All API endpoints (except `/oauth/token`, `/health`, and `/console/*`) require valid OAuth2 bearer tokens
- **Token Expiration**: Access tokens expire after 1 hour
- **Database Security**: Credentials stored securely using environment variables
- **Client Credentials**: Stored hashed in PostgreSQL
- **HTTPS**: Recommended for production deployments

## 🧪 Testing

### Manual Testing with cURL

1. **Get an access token:**
```bash
curl -X POST http://localhost:8081/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=demo_client&client_secret=demo_secret"
```

2. **Call a protected endpoint:**
```bash
curl -X GET http://localhost:8081/api/EMP001/goals \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

3. **Check health:**
```bash
curl http://localhost:8081/health
```

### Automated Testing

Run MUnit tests (if configured):
```bash
mvn test
```

## 📊 Error Handling

The application implements comprehensive error handling:

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| Database connectivity issues | 503 Service Unavailable | Database is unreachable |
| Database query errors | 500 Internal Server Error | Query execution failed |
| Data transformation errors | 500 Internal Server Error | Data mapping failed |
| Invalid/expired token | 401 Unauthorized | Authentication failed |
| Resource not found | 404 Not Found | Employee/resource doesn't exist |
| Invalid request | 400 Bad Request | Malformed request data |

## 📝 Configuration

### HTTP Listener
- **Default Port**: 8081
- **Base Path**: `/`
- **Protocol**: HTTP (HTTPS recommended for production)

### Database Connection
Configuration uses environment variable placeholders:
- `${db.host}` - Database host
- `${db.port}` - Database port (typically 5432)
- `${db.database}` - Database name
- `${db.username}` - Database username
- `${db.password}` - Database password

### APIKit
- References the employee-services-api OpenAPI Specification
- Auto-generates flows based on OAS definitions
- Provides built-in API Console

### Object Store
- Used for in-memory token management
- Stores active OAuth tokens with expiration

## 🔧 Customization

### Adding New Endpoints

1. Update the OpenAPI specification in `src/main/resources/api/`
2. Regenerate APIKit flows or add manual flow implementations
3. Add corresponding database queries if needed
4. Update this README with new endpoint documentation

### Modifying Token Expiration

Edit the token expiration time in the OAuth flow:
```xml
<set-variable value="3600" variableName="expiresIn"/>
```

### Adding New Database Tables

1. Create the table in PostgreSQL
2. Add corresponding flows and queries in the Mule configuration
3. Update the database setup section in this README

## 📋 Project Structure

```
employee-service-api/
├── src/
│   ├── main/
│   │   ├── mule/
│   │   │   └── employee-services-api.xml    # Main Mule configuration
│   │   └── resources/
│   │       ├── api/                          # OpenAPI specifications
│   │       ├── application.properties        # Application properties
│   │       └── deploy_ch2.json              # CloudHub 2.0 deployment config
├── pom.xml                                   # Maven configuration
├── mule-artifact.json                        # Mule artifact descriptor
├── CLAUDE.md                                 # AI assistant guidance
├── AUTHENTICATION_SETUP.md                   # Auth setup documentation
└── README.md                                 # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-endpoint`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add new endpoint for employee reviews'`)
6. Push to the branch (`git push origin feature/new-endpoint`)
7. Create a Pull Request

## 📄 License

This project is provided as-is for demonstration and educational purposes.

## 🆘 Support & Troubleshooting

### Common Issues

**Database Connection Failed:**
- Verify database credentials and connection parameters
- Check network connectivity to the database
- Ensure PostgreSQL is running and accessible

**OAuth Token Invalid:**
- Check that client credentials exist in the `api_clients` table
- Verify the token hasn't expired (1-hour lifetime)
- Ensure the Authorization header is properly formatted

**API Returns 404:**
- Verify the employee ID exists in the database
- Check the endpoint URL matches the API specification
- Review application logs for routing issues

**Health Check Fails:**
- Database may be unavailable or credentials incorrect
- Check application logs for specific error messages
- Verify environment variables are properly set

### Logging

The application implements comprehensive logging throughout all flows for debugging and monitoring. Check CloudHub logs or local console output for detailed error messages.

## 📞 Additional Resources

- [MuleSoft Documentation](https://docs.mulesoft.com/)
- [APIKit Documentation](https://docs.mulesoft.com/apikit/)
- [OAuth2 Client Credentials Flow](https://oauth.net/2/grant-types/client-credentials/)
- [CloudHub 2.0 Documentation](https://docs.mulesoft.com/cloudhub-2/)

---

**Built with MuleSoft Mule 4** | **Powered by PostgreSQL** | **Secured with OAuth2**

_Last updated: October 2025_
