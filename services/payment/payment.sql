DROP DATABASE IF EXISTS payment_db;
CREATE DATABASE IF NOT EXISTS payment_db;
USE payment_db

CREATE TABLE payment(
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    buyer_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    stripe_charge_id VARCHAR(255) DEFAULT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP    
);