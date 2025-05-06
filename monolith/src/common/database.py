import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.common.config import get_settings

# SQLAlchemy models base class
Base = declarative_base()

# Create async engine
settings = get_settings()
async_engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def init_db():
    """Initialize database when application starts."""
    try:
        # Create tables if they don't exist
        # This is for development only. In production, use migrations
        logging.info("Creating database tables if they don't exist...")
        async with async_engine.begin() as conn:
            # For development only - in production use migrations
            if settings.DEBUG:
                await conn.run_sync(Base.metadata.create_all)
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize database: {str(e)}")
        raise

async def close_db():
    """Close database connections when application shuts down."""
    try:
        logging.info("Closing database connections...")
        await async_engine.dispose()
        logging.info("Database connections closed")
    except Exception as e:
        logging.error(f"Failed to close database connections: {str(e)}")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for dependency injection."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()

# For synchronous code if needed (rarely used)
def get_sync_db():
    """Get a synchronous database session. Use with caution, only when necessary."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session

    # Extract synchronous URL from async URL
    # Example: postgresql+asyncpg:// -> postgresql://
    sync_url = str(settings.DATABASE_URL).replace("+asyncpg", "")
    
    sync_engine = create_engine(
        sync_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
