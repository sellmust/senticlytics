"""
Database Seeding Script
Load sample data dari HuggingFace dataset ke database
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from datasets import load_dataset
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.database import SessionLocal, sync_engine, create_all_tables

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATASET_NAME = "jakartaresearch/google-play-review"
SAMPLE_SIZE = 100  # Number of samples to load (adjust as needed)
BATCH_SIZE = 50

# Helper Functions
def create_tables():
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        create_all_tables()
        logger.info("✓ Tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        raise

def load_dataset_from_huggingface():
    """Load dataset dari HuggingFace"""
    try:
        logger.info(f"Loading dataset: {DATASET_NAME}")
        dataset = load_dataset(DATASET_NAME, trust_remote_code=True)
        
        # Get train split
        train_data = dataset['train']
        logger.info(f"✓ Dataset loaded. Total rows: {len(train_data)}")
        
        # Convert to DataFrame
        df = train_data.to_pandas()
        logger.info(f"✓ Converted to DataFrame. Shape: {df.shape}")
        
        # Show columns
        logger.info(f"Columns: {list(df.columns)}")
        
        return df.head(SAMPLE_SIZE)
        
    except Exception as e:
        logger.error(f"❌ Error loading dataset: {str(e)}")
        raise

def map_sentiment(rating):
    """Map rating ke sentiment"""
    if rating >= 4:
        return "positive"
    elif rating == 3:
        return "neutral"
    else:
        return "negative"

def seed_database(db: Session, df):
    """Seed database dengan data dari DataFrame"""
    try:
        logger.info(f"Seeding {len(df)} records to database...")
        
        from backend.models import Feedback
        
        inserted_count = 0
        error_count = 0
        
        for idx, row in df.iterrows():
            try:
                # Extract data from row
                text = str(row.get('text', ''))[:500] if 'text' in row else ""
                rating = int(row.get('rating', 3)) if 'rating' in row else 3
                sentiment = row.get('sentiment', map_sentiment(rating))
                
                # Map sentiment value if it's numeric
                if isinstance(sentiment, int):
                    sentiment = ['negative', 'neutral', 'positive'][sentiment]
                
                sentiment = sentiment.lower()
                if sentiment not in ['positive', 'neutral', 'negative']:
                    sentiment = map_sentiment(rating)
                
                # Create feedback record
                feedback = Feedback(
                    text=text,
                    sentiment=sentiment,
                    rating=rating,
                    source="huggingface_dataset",
                    category=row.get('domain', 'general'),
                    language="en",
                    word_count=len(text.split()),
                    sentiment_confidence=0.85,  # Dataset confidence
                    created_at=datetime.utcnow() - timedelta(days=(idx % 30)),  # Spread over 30 days
                    is_verified=True
                )
                
                db.add(feedback)
                inserted_count += 1
                
                # Batch commit
                if inserted_count % BATCH_SIZE == 0:
                    db.commit()
                    logger.info(f"  Committed {inserted_count} records...")
                    
            except Exception as e:
                error_count += 1
                logger.warning(f"❌ Error processing row {idx}: {str(e)}")
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        logger.info(f"✓ Seeding complete!")
        logger.info(f"  Inserted: {inserted_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info(f"  Success rate: {(inserted_count/(inserted_count+error_count)*100):.1f}%")
        
        return inserted_count, error_count
        
    except Exception as e:
        logger.error(f"❌ Error during seeding: {str(e)}")
        db.rollback()
        raise

def get_database_stats(db: Session):
    """Get database statistics after seeding"""
    try:
        from backend.models import Feedback
        from sqlalchemy import func
        
        total = db.query(func.count(Feedback.id)).scalar()
        
        sentiment_counts = db.query(
            Feedback.sentiment,
            func.count(Feedback.id)
        ).group_by(Feedback.sentiment).all()
        
        avg_rating = db.query(func.avg(Feedback.rating)).scalar()
        
        logger.info("\n=== Database Statistics ===")
        logger.info(f"Total feedbacks: {total}")
        logger.info("Sentiment distribution:")
        for sentiment, count in sentiment_counts:
            percentage = (count / total * 100) if total > 0 else 0
            logger.info(f"  - {sentiment}: {count} ({percentage:.1f}%)")
        logger.info(f"Average rating: {avg_rating:.2f}" if avg_rating else "No ratings")
        logger.info("=" * 25)
        
    except Exception as e:
        logger.warning(f"Could not get stats: {str(e)}")

# Main Execution
def main():
    """Main seeding function"""
    try:
        logger.info("=" * 50)
        logger.info("Starting Database Seeding")
        logger.info("=" * 50)
        
        # Step 1: Create tables
        logger.info("\n[1/4] Creating database tables...")
        create_tables()
        
        # Step 2: Load dataset
        logger.info("\n[2/4] Loading dataset from HuggingFace...")
        df = load_dataset_from_huggingface()
        
        # Step 3: Seed database
        logger.info(f"\n[3/4] Seeding database with {len(df)} records...")
        db = SessionLocal()
        inserted, errors = seed_database(db, df)
        
        # Step 4: Get stats
        logger.info("\n[4/4] Getting database statistics...")
        get_database_stats(db)
        
        logger.info("\n✅ Seeding completed successfully!")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ Seeding failed: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)