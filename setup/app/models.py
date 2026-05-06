"""
Database Models
SQLAlchemy ORM models for customer feedback data
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class SentimentType(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    # Content
    text = Column(Text, nullable=False)

    # Input metadata (from user)
    customer_id = Column(String(100), nullable=True, index=True)
    source = Column(String(50), default="web")
    product_id = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars

    # AI results (auto-filled by Gemini)
    sentiment = Column(SQLEnum(SentimentType, name="sentiment_type", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    sentiment_respon = Column(Text, nullable=True)

    # Flags
    is_verified = Column(Boolean, default=False)
    is_spam = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_sentiment_created', 'sentiment', 'created_at'),
        Index('idx_customer_date', 'customer_id', 'created_at'),
        Index('idx_product_sentiment', 'product_id', 'sentiment'),
    )

if __name__ == "__main__":
    print("Database models loaded successfully")