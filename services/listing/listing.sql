CREATE DATABASE IF NOT EXISTS listing_db;
USE listing_db;
 
CREATE TABLE IF NOT EXISTS listings (
    listing_id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    listing_type VARCHAR(20) NOT NULL COMMENT 'AUCTION or FIXED',
    start_price DECIMAL(10, 2) NOT NULL,
    start_time DATETIME COMMENT 'Auction only, nullable for FIXED',
    end_time DATETIME COMMENT 'Auction only, nullable for FIXED',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE' COMMENT 'SCHEDULED, ACTIVE, CLOSED_PENDING_PAYMENT, SOLD, FAILED_NO_ELIGIBLE_BIDDER',
    winning_buyer_id INT COMMENT 'Set on auction close, nullable',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
 
-- Sample data for testing
-- INSERT INTO listings (seller_id, title, description, image_url, listing_type, start_price, status)
-- VALUES
--     (1, 'Vintage Guitar', 'A classic 1965 Fender Stratocaster', 'https://example.com/guitar.jpg', 'FIXED', 500.00, 'ACTIVE'),
--     (1, 'Rare Comic Book', 'First edition Spider-Man #1', 'https://example.com/comic.jpg', 'FIXED', 200.00, 'ACTIVE');
 