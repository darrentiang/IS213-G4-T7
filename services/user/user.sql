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
    ('jiayingkam0811@gmail.com', 'Alice Tan', 'cus_test_alice001'),
    ('jiayingkam0811@gmail.com', 'Bob Lim', 'cus_UFTMQiGA5lpook'),
    ('jiayingkam0811@gmail.com', 'Charlie Ng', 'cus_UFTPSV7hB0vszX');
    -- ('tiangdarren@gmail.com', 'Alice Tan', 'cus_test_alice001'),
    -- ('darrentiang0@gmail.com', 'Bob Lim', 'cus_UFTMQiGA5lpook'),
    -- ('darrentiang1@gmail.com', 'Charlie Ng', 'cus_UFTPSV7hB0vszX');
