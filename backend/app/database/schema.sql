-- Wealth Management Database Schema

CREATE DATABASE IF NOT EXISTS wealth_management;
USE wealth_management;

-- 1. Account Types
CREATE TABLE IF NOT EXISTS account_types (
    type_id INT AUTO_INCREMENT PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL,
    interest_rate DECIMAL(5, 4) DEFAULT 0.00
);

-- 2. Users
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    risk_profile ENUM('Conservative', 'Moderate', 'Aggressive') DEFAULT 'Moderate',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Accounts
CREATE TABLE IF NOT EXISTS accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_type_id INT NOT NULL,
    balance DECIMAL(15, 2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    status ENUM('Active', 'Closed', 'Frozen') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (account_type_id) REFERENCES account_types(type_id)
);

-- 4. Advisors
CREATE TABLE IF NOT EXISTS advisors (
    advisor_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100),
    management_fee_bps INT DEFAULT 100 -- basis points
);

-- 5. Advisor-Client Mapping
CREATE TABLE IF NOT EXISTS advisor_client_mapping (
    mapping_id INT AUTO_INCREMENT PRIMARY KEY,
    advisor_id INT NOT NULL,
    user_id INT NOT NULL,
    assignment_date DATE,
    FOREIGN KEY (advisor_id) REFERENCES advisors(advisor_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 6. Transactions
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    category ENUM('Deposit', 'Withdrawal', 'Transfer', 'Dividend', 'Fee') NOT NULL,
    description VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- 7. Portfolio Holdings
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    holding_id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    ticker_symbol VARCHAR(10) NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    purchase_price DECIMAL(15, 2) NOT NULL,
    current_price DECIMAL(15, 2) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- Add some indexes for performance
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_account_user ON accounts(user_id);
CREATE INDEX idx_transaction_account ON transactions(account_id);
CREATE INDEX idx_holding_ticker ON portfolio_holdings(ticker_symbol);
