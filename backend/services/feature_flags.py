"""
Feature flag service for pilot features.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import FeatureFlag


async def is_feature_enabled(db: AsyncSession, key: str, institution_id: str) -> bool:
    """Check if a feature is enabled for a given institution."""
    result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.key == key)
    )
    flag = result.scalar_one_or_none()
    if not flag:
        return False
    # Global enable check
    if flag.enabled:
        return True
    # Whitelist check
    allowed = flag.allowed_institution_ids or []
    return institution_id in allowed
