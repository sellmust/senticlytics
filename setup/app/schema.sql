-- Database Schema for Customer Feedback Intelligence Platform
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enums
CREATE TYPE sentiment_type AS ENUM ('positive', 'neutral', 'negative');

-- Feedback Table
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    customer_id VARCHAR(100),
    source VARCHAR(50) DEFAULT 'web',
    product_id VARCHAR(100),
    category VARCHAR(100),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    sentiment sentiment_type NOT NULL,
    sentiment_respon TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    is_spam BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_feedback_sentiment    ON feedback(sentiment);
CREATE INDEX idx_feedback_created_at   ON feedback(created_at DESC);
CREATE INDEX idx_feedback_customer_id  ON feedback(customer_id);
CREATE INDEX idx_feedback_product_id   ON feedback(product_id);
CREATE INDEX idx_feedback_category     ON feedback(category);
CREATE INDEX idx_feedback_rating       ON feedback(rating);
CREATE INDEX idx_sentiment_created     ON feedback(sentiment, created_at);
CREATE INDEX idx_customer_date         ON feedback(customer_id, created_at);
CREATE INDEX idx_product_sentiment     ON feedback(product_id, sentiment);

-- Full-text search
CREATE INDEX idx_feedback_text_search ON feedback USING gin(to_tsvector('english', text));

-- Views
CREATE VIEW v_sentiment_summary AS
SELECT
    DATE(created_at) as date,
    sentiment,
    COUNT(*) as count,
    ROUND(AVG(rating)::numeric, 2) as avg_rating
FROM feedback
GROUP BY DATE(created_at), sentiment;

CREATE VIEW v_category_performance AS
SELECT
    category,
    COUNT(*) as total_feedbacks,
    SUM(CASE WHEN sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN sentiment = 'neutral'  THEN 1 ELSE 0 END) as neutral_count,
    SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count,
    ROUND(AVG(rating)::numeric, 2) as avg_rating
FROM feedback
WHERE category IS NOT NULL
GROUP BY category
ORDER BY total_feedbacks DESC;

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_feedback_timestamp
BEFORE UPDATE ON feedback
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

COMMENT ON TABLE feedback IS 'Main table for customer feedback with AI sentiment analysis';
COMMENT ON COLUMN feedback.sentiment IS 'Auto-classified by Gemini: positive, neutral, negative';
COMMENT ON COLUMN feedback.sentiment_respon IS 'Auto-generated personalized response by Gemini';