CREATE TABLE users (
 user_id SERIAL PRIMARY KEY, username VARCHAR(255) UNIQUE NOT NULL,
 email VARCHAR(255) UNIQUE NOT NULL, first_name VARCHAR(255) NOT NULL,
 last_name VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 is_active BOOLEAN DEFAULT true
);
CREATE TABLE api_clients (
 client_id VARCHAR(255) PRIMARY KEY, client_secret VARCHAR(255) NOT NULL,
 user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
 access_token VARCHAR(500), expires_at TIMESTAMP, callback_url VARCHAR(500),
 refresh_token VARCHAR(500), refresh_token_expires_at TIMESTAMP,
 token_expires_at TIMESTAMP, salesforce_user_id VARCHAR(255),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 is_active BOOLEAN DEFAULT true
);
CREATE TABLE employee_goals (id SERIAL PRIMARY KEY, employee_id VARCHAR(50) NOT NULL, goal TEXT);
CREATE TABLE employee_learning (id SERIAL PRIMARY KEY, employee_id VARCHAR(50) NOT NULL, course TEXT, status TEXT);
CREATE TABLE employee_pto (employee_id VARCHAR(50) PRIMARY KEY, pto_balance NUMERIC(10,2), next_pay_date DATE);
INSERT INTO api_clients (client_id,client_secret) VALUES ('demo_client','demo_secret');
INSERT INTO employee_goals (employee_id,goal) VALUES ('EMP001','Complete Q4 Sales Target');
INSERT INTO employee_learning (employee_id,course,status) VALUES ('EMP001','Advanced Sales Techniques','In Progress');
INSERT INTO employee_pto VALUES ('EMP001',120.00,'2024-02-01');
INSERT INTO employee_goals (employee_id,goal) VALUES ('EMP002','Complete onboarding');
INSERT INTO employee_learning (employee_id,course,status) VALUES ('EMP002','Security basics','Completed');
INSERT INTO employee_pto VALUES ('EMP002',0.00,NULL), ('EMP003',40.00,'2024-02-01');
