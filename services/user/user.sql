DROP DATABASE IF EXISTS user_db;
CREATE DATABASE IF NOT EXISTS user_db;
USE user_db;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    stripe_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (email, name, stripe_id) VALUES
    ('alice@example.com', 'Alice Tan', 'cus_test_alice001'),
    ('bob@example.com', 'Bob Lim', 'cus_test_bob002'),
    ('charlie@example.com', 'Charlie Ng', 'cus_test_charlie003');
