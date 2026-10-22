-- Base schema required before database-setup.sql can be applied.
-- database-setup.sql only ALTERs api_clients (and creates users), so the
-- pre-existing tables documented in README.md are recreated here for CI.

CREATE TABLE IF NOT EXISTS api_clients (
    client_id VARCHAR(255) PRIMARY KEY,
    client_secret VARCHAR(255) NOT NULL,
    client_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employee_goals (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    goal_title VARCHAR(255) NOT NULL,
    goal_description TEXT,
    target_date DATE,
    progress INTEGER DEFAULT 0,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employee_learning (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    course_status VARCHAR(50),
    completion_percentage INTEGER DEFAULT 0,
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employee_pto (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    pto_balance DECIMAL(10,2) DEFAULT 0,
    accrual_rate DECIMAL(10,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
