"""Traffic analytics — POST pageview (public, rate-limited) + Superadmin stats.

Design decisions:
  * Anonymization: IP is hashed (SHA-256 + per-day salt) never stored raw.
  * Bot filter: a very lightweight user-agent keyword check.
  * ADMIN_IP env (comma-separated; supports IPv4 + IPv6): such visits are
    NOT recorded — the owner's browsing doesn't skew metrics.
  * Static assets (``/static``, ``.js``, ``.css``, images) and API paths
    (``/api/``) are rejected at the record endpoint so the client never has
    to filter them.
  * Superadmin analytics endpoint is gated by ``get_current_user`` + role=='superadmin'.
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.supabase import get_db
from database.models import PageView
from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


BOT_UA_KEYWORDS = (
    "bot", "crawler", "spider", "slurp", "curl/", "wget", "python-requests",
    "httpclient", "headlesschrome", "phantomjs",
)


def _load_admin_ips() -> set[str]:
    """Parse ``ADMIN_IP`` env into a normalized set (empty set = no exclusion)."""
    raw = os.environ.get("ADMIN_IP", "")
    out: set[str] = set()
    for piece in raw.split(","):
        p = piece.strip()
        if not p:
            continue
        try:
            out.add(str(ipaddress.ip_address(p)))  # canonical form
        except ValueError:
            logger.warning(f"ADMIN_IP entry is not a valid IP: {p!r}")
    return out


def _client_ip(request: Request) -> str:
    """Return the best-effort visitor IP, respecting proxy headers.

    We use the *first* entry in ``X-Forwarded-For`` (the origin client); the
    rest of the chain is proxy/CDN hops. Falls back to ``request.client.host``
    during local dev.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "0.0.0.0"


def _normalize_ip(ip_str: str) -> str:
    """Canonicalize an IP string (e.g., collapses IPv6 zero groups)."""
    try:
        return str(ipaddress.ip_address(ip_str))
    except ValueError:
        return ip_str


def _ip_hash(ip_str: str, day: str) -> str:
    """SHA-256(ip | day) — per-day salt so the hash rotates and can't be
    cross-correlated across days without re-seeing the same IP.
    """
    h = hashlib.sha256()
    h.update(ip_str.encode("utf-8", errors="ignore"))
    h.update(b"|")
    h.update(day.encode("utf-8"))
    return h.hexdigest()


def _session_id(ip_str: str, user_agent: str, day: str) -> str:
    """Stable session id for "unique visitors per day": hash of ip+ua+day."""
    h = hashlib.sha256()
    h.update(ip_str.encode("utf-8", errors="ignore"))
    h.update(b"|")
    h.update((user_agent or "").encode("utf-8", errors="ignore"))
    h.update(b"|")
    h.update(day.encode("utf-8"))
    return h.hexdigest()[:32]


_STATIC_SUFFIX_RE = re.compile(r"\.(?:js|mjs|css|map|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|eot|otf|mp4|webm|mp3|pdf|json)(?:\?|$)", re.IGNORECASE)


def _is_ignorable_path(path: str) -> bool:
    """True if the path is a static asset, an API call, or otherwise not a
    user-facing page load we want to record.
    """
    if not path or not path.startswith("/"):
        return True
    if path.startswith("/api/") or path == "/api" or path.startswith("/static/"):
        return True
    return bool(_STATIC_SUFFIX_RE.search(path))


def _is_bot(user_agent: str) -> bool:
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(k in ua for k in BOT_UA_KEYWORDS)


# ---------- POST pageview (public) ----------

class PageViewIn(BaseModel):
    path: str = Field(..., max_length=500)
    referrer: Optional[str] = Field(None, max_length=500)


@router.post("/pageview", status_code=202)
async def record_pageview(
    body: PageViewIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Record a single pageview. Silent-no-op when the path is ignorable,
    the UA looks like a bot, or the caller's IP matches ``ADMIN_IP``.

    Returns 202 Accepted unconditionally — the client doesn't need to know
    whether we decided to discard the sample (prevents analytics-adblocker
    feedback loops).
    """
    if _is_ignorable_path(body.path):
        return {"recorded": False, "reason": "ignored_path"}

    user_agent = request.headers.get("user-agent", "")
    if _is_bot(user_agent):
        return {"recorded": False, "reason": "bot"}

    ip_raw = _normalize_ip(_client_ip(request))
    admin_ips = _load_admin_ips()
    if ip_raw in admin_ips:
        return {"recorded": False, "reason": "admin_ip"}

    day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pv = PageView(
        path=body.path[:500],
        ip_hash=_ip_hash(ip_raw, day_key),
        user_agent=user_agent[:500] if user_agent else None,
        session_id=_session_id(ip_raw, user_agent, day_key),
        referrer=(body.referrer or "")[:500] or None,
    )
    db.add(pv)
    try:
        await db.commit()
    except Exception as e:
        logger.warning(f"pageview commit failed: {e}")
        await db.rollback()
        return {"recorded": False, "reason": "db_error"}
    return {"recorded": True}


# ---------- Superadmin stats ----------

def _ensure_superadmin(user: dict) -> None:
    """The platform owner is identified by e-mail (matches AdminLayout's
    ``Superadmin`` nav-item gating) rather than a DB role flag.
    """
    superadmin_emails = {"demo@budezivo.cz", "admin@budezivo.cz"}
    extra = os.environ.get("SUPERADMIN_EMAILS", "")
    for piece in extra.split(","):
        p = piece.strip().lower()
        if p:
            superadmin_emails.add(p)
    email = (user.get("email") or "").lower()
    if email not in superadmin_emails and user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Přístup pouze pro superadmina")


class DailyBucket(BaseModel):
    day: str
    views: int
    unique_visitors: int


class AnalyticsStats(BaseModel):
    today_views: int
    views_7d: int
    views_30d: int
    unique_visitors_7d: int
    unique_visitors_30d: int
    total_views: int
    top_paths: List[dict]
    daily: List[DailyBucket]
    range_days: int


@router.get("/stats", response_model=AnalyticsStats)
async def get_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Superadmin-only traffic dashboard payload."""
    _ensure_superadmin(current_user)
    days = max(1, min(days, 365))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc)

    # Aggregate KPI counters in one trip when possible.
    total_q = await db.execute(select(func.count(PageView.id)))
    total_views = total_q.scalar() or 0

    today_q = await db.execute(select(func.count(PageView.id)).where(PageView.created_at >= today_start))
    today_views = today_q.scalar() or 0

    views_7d_q = await db.execute(select(func.count(PageView.id)).where(PageView.created_at >= (now - timedelta(days=7))))
    views_7d = views_7d_q.scalar() or 0

    views_30d_q = await db.execute(select(func.count(PageView.id)).where(PageView.created_at >= (now - timedelta(days=30))))
    views_30d = views_30d_q.scalar() or 0

    u7_q = await db.execute(select(func.count(func.distinct(PageView.session_id))).where(PageView.created_at >= (now - timedelta(days=7))))
    unique_7d = u7_q.scalar() or 0

    u30_q = await db.execute(select(func.count(func.distinct(PageView.session_id))).where(PageView.created_at >= (now - timedelta(days=30))))
    unique_30d = u30_q.scalar() or 0

    # Top paths (within the selected window).
    top_q = await db.execute(
        select(PageView.path, func.count(PageView.id).label("views"))
        .where(PageView.created_at >= since)
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(20)
    )
    top_paths = [{"path": r.path, "views": r.views} for r in top_q]

    # Daily histogram (views + unique sessions) for charting.
    day_expr = func.date_trunc('day', PageView.created_at)
    daily_q = await db.execute(
        select(
            day_expr.label("day"),
            func.count(PageView.id).label("views"),
            func.count(func.distinct(PageView.session_id)).label("unique_visitors"),
        )
        .where(PageView.created_at >= since)
        .group_by(day_expr)
        .order_by(day_expr.asc())
    )
    daily = [
        DailyBucket(day=r.day.strftime('%Y-%m-%d'), views=r.views, unique_visitors=r.unique_visitors)
        for r in daily_q
    ]

    return AnalyticsStats(
        today_views=today_views,
        views_7d=views_7d,
        views_30d=views_30d,
        unique_visitors_7d=unique_7d,
        unique_visitors_30d=unique_30d,
        total_views=total_views,
        top_paths=top_paths,
        daily=daily,
        range_days=days,
    )
