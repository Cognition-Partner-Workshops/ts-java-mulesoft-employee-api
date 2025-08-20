-- Database setup script for Employee Service API Authentication
-- Run this script in your PostgreSQL database

-- Create users table for storing user credentials
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create index on username for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Update api_clients table to link to users and store tokens (if not already present)
ALTER TABLE api_clients 
ADD COLUMN IF NOT EXISTS user_id INTEGER,
ADD COLUMN IF NOT EXISTS access_token VARCHAR(255),
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP,
ADD CONSTRAINT fk_api_clients_user_id 
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

-- Create index on user_id in api_clients
CREATE INDEX IF NOT EXISTS idx_api_clients_user_id ON api_clients(user_id);

-- Add callback_url column to api_clients table for Salesforce callback integration
ALTER TABLE api_clients 
ADD COLUMN IF NOT EXISTS callback_url VARCHAR(500);

-- Add new columns for Named Credentials and refresh token support
ALTER TABLE api_clients 
ADD COLUMN IF NOT EXISTS refresh_token VARCHAR(500),
ADD COLUMN IF NOT EXISTS refresh_token_expires_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS salesforce_user_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Create index on salesforce_user_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_api_clients_salesforce_user_id ON api_clients(salesforce_user_id);

-- Create index on refresh_token for faster lookups
CREATE INDEX IF NOT EXISTS idx_api_clients_refresh_token ON api_clients(refresh_token);

-- Update trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_api_clients_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_api_clients_updated_at 
    BEFORE UPDATE ON api_clients 
    FOR EACH ROW 
    EXECUTE FUNCTION update_api_clients_updated_at();