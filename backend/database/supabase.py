"""
Supabase (PostgreSQL) database connection using SQLAlchemy async.
Uses Transaction Pooler for optimal connection handling.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

DATABASE_URL = os.environ.get('DATABASE_URL')

# Convert to async URL (postgresql:// -> postgresql+asyncpg://)
ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://') if DATABASE_URL else None

# Create async engine with Transaction Pooler compatible settings
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=False,
    echo=False,
    connect_args={
        "statement_cache_size": 0,  # CRITICAL: Required for transaction pooler
        "command_timeout": 30,
    }
) if ASYNC_DATABASE_URL else None

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
) if engine else None


async def get_db():
    """Dependency for getting database session."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL in .env")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def test_connection():
    """Test database connection."""
    if engine is None:
        return False, "DATABASE_URL not configured"
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)
