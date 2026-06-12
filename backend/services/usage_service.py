"""
Usage metrics tracking — aggregated, institution-level, GDPR-safe.
Tracks feature usage counts for product analytics.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_, func
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


NEAR_LIMIT_THRESHOLD = 0.8  # 80 % → show "blížíte se limitu" banner


def _quota_block(used: int, limit: int) -> dict:
    """Build a single quota descriptor. limit == -1 means unlimited."""
    unlimited = limit is None or limit < 0
    if unlimited:
        return {
            "used": used, "limit": -1, "unlimited": True,
            "percent": 0, "remaining": None, "near_limit": False, "over_limit": False,
        }
    percent = int(round((used / limit) * 100)) if limit > 0 else 100
    return {
        "used": used,
        "limit": limit,
        "unlimited": False,
        "percent": min(percent, 999),
        "remaining": max(0, limit - used),
        "near_limit": used >= limit * NEAR_LIMIT_THRESHOLD and used < limit,
        "over_limit": used >= limit,
    }


async def get_plan_quota_usage(
    db: AsyncSession, institution_id: str, plan: str, plan_status: str = "active"
) -> dict:
    """Soft-limit usage snapshot: current programs + this-month bookings vs plan
    limits. SOFT only — never blocks; drives UI banners + upgrade prompts.

    `enforced=False` documents that hard enforcement is intentionally deferred
    (architecture-ready: flip to True post-pilot to start blocking).
    """
    from database.models import Program, Reservation
    from services.plan_service import get_plan_limits

    limits = get_plan_limits(plan, plan_status)

    programs_used = (await db.execute(
        select(func.count(Program.id)).where(and_(
            Program.institution_id == institution_id,
            Program.status != 'archived',
        ))
    )).scalar() or 0

    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    bookings_used = (await db.execute(
        select(func.count(Reservation.id)).where(and_(
            Reservation.institution_id == institution_id,
            Reservation.status != 'cancelled',
            Reservation.created_at >= month_start,
        ))
    )).scalar() or 0

    return {
        "plan": plan,
        "plan_status": plan_status,
        "enforced": False,
        "period": now.strftime("%Y-%m"),
        "programs": _quota_block(programs_used, limits.get("programs_limit", -1)),
        "bookings_month": _quota_block(bookings_used, limits.get("bookings_monthly_limit", -1)),
    }
