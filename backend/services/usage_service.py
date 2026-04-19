"""
Usage metrics tracking — aggregated, institution-level, GDPR-safe.
Tracks feature usage counts for product analytics.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UsageMetric

logger = logging.getLogger(__name__)


async def track_usage(db: AsyncSession, institution_id: str, feature_key: str, metadata: dict = None):
    """Increment usage counter for a feature. Upsert pattern."""
    try:
        result = await db.execute(
            select(UsageMetric).where(and_(
                UsageMetric.institution_id == institution_id,
                UsageMetric.feature_key == feature_key,
            ))
        )
        metric = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if metric:
            metric.usage_count = (metric.usage_count or 0) + 1
            metric.last_used_at = now
            if metadata:
                existing = metric.metadata_json or {}
                existing.update(metadata)
                metric.metadata_json = existing
        else:
            metric = UsageMetric(
                institution_id=institution_id,
                feature_key=feature_key,
                usage_count=1,
                first_used_at=now,
                last_used_at=now,
                metadata_json=metadata or {},
            )
            db.add(metric)

        await db.commit()
    except Exception as e:
        logger.warning(f"Usage tracking failed for {feature_key}: {e}")
        await db.rollback()


async def get_institution_usage(db: AsyncSession, institution_id: str) -> list:
    """Get all usage metrics for an institution."""
    result = await db.execute(
        select(UsageMetric).where(UsageMetric.institution_id == institution_id)
        .order_by(UsageMetric.usage_count.desc())
    )
    metrics = result.scalars().all()
    return [
        {
            "feature_key": m.feature_key,
            "usage_count": m.usage_count,
            "first_used_at": m.first_used_at.isoformat() if m.first_used_at else None,
            "last_used_at": m.last_used_at.isoformat() if m.last_used_at else None,
        }
        for m in metrics
    ]
