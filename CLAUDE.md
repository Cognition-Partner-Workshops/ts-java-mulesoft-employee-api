# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **MuleSoft Mule 4** application that provides an Employee Service API. The application is built using:
- Mule Runtime 4.9.6+ with Java 17
- Maven for dependency management
- PostgreSQL database for data persistence
- OAuth2 client credentials authentication
- APIKit for REST API implementation

## Build and Development Commands

### Build the application:
```bash
mvn clean compile
```

### Package the application:
```bash
mvn clean package
```

### Run tests (if MUnit tests exist):
```bash
mvn test
```

### Deploy to CloudHub 2.0:
Uses the deployment configuration in `src/main/resources/deploy_ch2.json`

## Application Architecture

### Core Components

1. **OAuth2 Authentication System**
   - Custom OAuth2 implementation using client credentials flow
   - Token validation and management using Object Store
   - Client credentials stored in PostgreSQL (`api_clients` table)

2. **Database Integration**
   - PostgreSQL configuration with environment variable placeholders
   - Tables: `api_clients`, `employee_goals`, `employee_learning`, `employee_pto`
   - Connection parameters: `${db.host}`, `${db.port}`, `${db.database}`, `${db.username}`, `${db.password}`

3. **API Endpoints**
   - Base path: `/api/*` (requires authentication)
   - Console: `/console/*` (no authentication)
   - Health check: `/health` (no authentication)
   - OAuth token: `/oauth/token` (no authentication)

### Main Flows

1. **oauth-token-flow**: Handles OAuth2 token generation
2. **validate-token-subflow**: Validates bearer tokens for protected endpoints
3. **employee-services-api-main**: Main API router with token validation
4. **health-check-flow**: Database connectivity health check

### Employee API Endpoints

All employee endpoints require OAuth2 bearer token authentication:

- `GET /{employeeId}/goals` - Retrieve employee goals
- `GET /{employeeId}/learning-status` - Get learning course status  
- `GET /{employeeId}/next-pay-date` - Get next pay date
- `GET /{employeeId}/pto/balance` - Get PTO balance
- `POST /{employeeId}/pto/schedule` - Schedule PTO time

### Error Handling

The application implements comprehensive error handling for:
- Database connectivity issues (503 Service Unavailable)
- Database query errors (500 Internal Server Error)
- Data transformation errors (500 Internal Server Error)
- OAuth token validation errors (401 Unauthorized)
- Resource not found scenarios (404 Not Found)

### Configuration

- HTTP listener runs on port 8081 by default
- Database connection uses environment variables for configuration
- APIKit configuration references the employee-services-api OAS specification
- Object Store used for in-memory token management

## Development Notes

- The application uses DataWeave 2.0 for data transformations
- Logging is implemented throughout for debugging and monitoring
- PostgreSQL driver is included for CloudHub 2.0 compatibility
- APIKit generates flows based on the OpenAPI specification
- Token expiration is set to 1 hour (3600 seconds)