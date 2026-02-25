"""
MongoDB client connection.
This module will be replaced with Supabase connection after migration.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import MONGO_URL, DB_NAME

_client = None
_db = None


def get_mongodb_client() -> AsyncIOMotorClient:
    """Get or create MongoDB client singleton."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URL)
    return _client


def get_database():
    """Get database instance."""
    global _db
    if _db is None:
        client = get_mongodb_client()
        _db = client[DB_NAME]
    return _db


async def close_mongodb_connection():
    """Close MongoDB connection on shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
