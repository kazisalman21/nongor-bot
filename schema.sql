-- Nongor Bot V3 Database Schema
-- Run this in your Neon PostgreSQL database BEFORE deploying

-- Users table (for bot users)
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table (main business data)
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id TEXT,  -- Alternative order ID if used
    customer_name TEXT,
    phone TEXT,
    product_name TEXT,
    quantity INTEGER DEFAULT 1,
    price DECIMAL(10, 2),
    total_price DECIMAL(10, 2),
    total DECIMAL(10, 2),
    status TEXT DEFAULT 'pending',  -- pending, confirmed, delivered, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(phone);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_product_name ON orders(product_name);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen DESC);

-- Sample data (optional - for testing)
INSERT INTO orders (customer_name, phone, product_name, quantity, price, total, status)
VALUES 
    ('Test Customer 1', '01711222333', 'Premium T-Shirt', 2, 500, 1000, 'delivered'),
    ('Test Customer 2', '01811333444', 'Denim Jeans', 1, 1500, 1500, 'confirmed'),
    ('Test Customer 3', '01911444555', 'Cotton Hoodie', 1, 1200, 1200, 'pending')
ON CONFLICT DO NOTHING;
