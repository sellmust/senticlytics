"""
Database Configuration
SQLAlchemy setup and database connection management
"""

import os
import logging
from typing import Generator
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv
from sqlalchemy import text
from backend.models import Base

# Load Environment Variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://feedbackuser:feedbackpass@localhost:5432/feedback_db'
)

# Handle Async Database URL
if DATABASE_URL.startswith('postgresql://'):
    ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Pool Configuration
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 20))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', 10))
DB_POOL_RECYCLE = 3600
DB_ECHO = os.getenv('DB_ECHO', 'False').lower() == 'true'

# Async Engine (for FastAPI)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=DB_ECHO,
    poolclass=pool.NullPool,  # NullPool untuk async
    pool_pre_ping=True,
    connect_args={
        'server_settings': {
            'application_name': 'customer_feedback_intelligence',
            'jit': 'off'
        },
        'timeout': 30
    }
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Sync Engine (for scripts and CLI tools)
SYNC_DATABASE_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://').replace('postgresql+asyncpg://', 'postgresql://')
if 'asyncpg' in SYNC_DATABASE_URL:
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace('+asyncpg', '')
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=DB_ECHO,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={
        'application_name': 'customer_feedback_intelligence'
    }
)

# Sync Session Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Async Database Functions
async def get_db() -> Generator[AsyncSession, None, None]:
    """
    Dependency for FastAPI endpoints
    Provides database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            await session.close()

async def init_db():
    """
    Initialize database tables
    Create all tables defined in Base metadata
    """
    try:
        logger.info("Initializing database...")
        
        async with async_engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✓ All tables created successfully")
            
            # Add check constraints if needed
            await conn.run_sync(add_check_constraints)
            
        logger.info("✓ Database initialization complete")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}", exc_info=True)
        raise

def add_check_constraints(connection):
    """Add check constraints to tables"""
    try:
        # Example Constraints
        constraints = [
            "ALTER TABLE feedback ADD CONSTRAINT check_rating CHECK (rating BETWEEN 1 AND 5)",
            "ALTER TABLE feedback ADD CONSTRAINT check_sentiment_confidence CHECK (sentiment_confidence BETWEEN 0 AND 1)",
            "ALTER TABLE analytics_snapshot ADD CONSTRAINT check_satisfaction CHECK (customer_satisfaction BETWEEN 0 AND 100)",
        ]
        
        for constraint in constraints:
            try:
                connection.execute(constraint)
            except Exception as e:
                # Constraint might already exist
                logger.debug(f"Constraint already exists or error: {str(e)}")
                
    except Exception as e:
        logger.warning(f"Could not add constraints: {str(e)}")

# Sync Database Functions
def get_sync_db() -> Generator[Session, None, None]:
    """
    Synchronous database session provider
    For scripts and CLI tools
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()

def create_all_tables():
    """Create all database tables (synchronous)"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=sync_engine)
        logger.info("✓ All tables created")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        raise

def drop_all_tables():
    """Drop all database tables (synchronous) - USE WITH CAUTION"""
    try:
        logger.warning("⚠ Dropping all database tables...")
        Base.metadata.drop_all(bind=sync_engine)
        logger.info("✓ All tables dropped")
    except Exception as e:
        logger.error(f"❌ Error dropping tables: {str(e)}")
        raise

# Connection Testing
async def test_connection() -> bool:
    """Test async database connection"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

def test_sync_connection() -> bool:
    """Test sync database connection"""
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

# Database Statistics
async def get_db_stats() -> dict:
    """Get database statistics"""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text
        
        result = await session.execute(text("""
            SELECT 
                schemaname, tablename, 
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """))
        
        stats = []
        for row in result:
            stats.append({
                'table': row[1],
                'size': row[2]
            })
        
        return {'tables': stats}

# Cleanup
async def close_db():
    """Close database connections"""
    try:
        await async_engine.dispose()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")

# Export
__all__ = [
    'async_engine',
    'AsyncSessionLocal',
    'sync_engine',
    'SessionLocal',
    'get_db',
    'get_sync_db',
    'init_db',
    'test_connection',
    'test_sync_connection',
    'create_all_tables',
    'drop_all_tables',
    'get_db_stats',
    'close_db'
]