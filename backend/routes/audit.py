"""
Audit Log routes and helper.
Logs admin actions and provides read access for audit trail.
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from core.security import get_current_user
from database.supabase import get_db
from database.models import AuditLog

router = APIRouter(prefix="/audit-log", tags=["AuditLog"])
logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    *,
    institution_id: str,
    user_id: str,
    user_email: str = "",
    action: str,
    entity_type: str,
    entity_id: str = None,
    details: dict = None,
    ip_address: str = None,
):
    """Helper to create an audit log entry. Fire-and-forget."""
    try:
        entry = AuditLog(
            institution_id=institution_id,
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address,
        )
        db.add(entry)
        await db.commit()
    except Exception as e:
        logger.warning(f"Audit log write failed: {e}")


@router.get("")
async def get_audit_logs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
):
    """Get paginated audit log for institution."""
    institution_id = current_user["institution_id"]

    q = select(AuditLog).where(AuditLog.institution_id == institution_id)
    count_q = select(func.count(AuditLog.id)).where(AuditLog.institution_id == institution_id)

    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
        count_q = count_q.where(AuditLog.entity_type == entity_type)
    if action:
        q = q.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    q = q.order_by(desc(AuditLog.created_at)).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    logs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": str(log.id),
                "user_email": log.user_email,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
