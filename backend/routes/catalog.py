"""
Public B2B catalog "Programy pro školy" — read-only endpoints.

Reuses existing `programs` table. Programs are opted-in via `is_in_catalog`
toggle on each program (admin-controlled). No duplication.
"""
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.supabase import get_db

router = APIRouter(prefix="/public/catalog", tags=["Public Catalog"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


# ---- Helpers ----

# Map UI-friendly age slugs to DB values (programs.age_group + programs.target_groups)
AGE_SLUG_MAP = {
    "ms":   ["ms_3_6"],
    "zs1":  ["zs1_7_12"],
    "zs2":  ["zs2_12_15"],
    "ss":   ["ss_14_18", "gym_14_18"],
}

ALL_AGE_GROUPS = ["ms_3_6", "zs1_7_12", "zs2_12_15", "ss_14_18", "gym_14_18"]


def _age_label(code: str) -> str:
    return {
        "ms_3_6":     "MŠ",
        "zs1_7_12":   "1. stupeň ZŠ",
        "zs2_12_15":  "2. stupeň ZŠ",
        "ss_14_18":   "SŠ",
        "gym_14_18":  "Gymnázium",
        "adults":     "Dospělí",
        "all":        "Všechny věky",
    }.get(code or "", code or "")


def _row_to_card(row) -> Dict[str, Any]:
    """Convert DB row (dict) → public card payload (no internal fields, no _id)."""
    target_groups = row.get("target_groups") or []
    if not target_groups and row.get("age_group"):
        target_groups = [row["age_group"]]
    subject_tags = row.get("subject_tags") or []

    return {
        "id":           str(row["id"]),
        "name":         row.get("name_cs") or row.get("name_en") or "",
        "description":  (row.get("description_cs") or row.get("description_en") or "")[:240],
        "duration":     row.get("duration") or 60,
        "min_capacity": row.get("min_capacity"),
        "max_capacity": row.get("max_capacity"),
        "price":        row.get("price") or 0.0,
        "pricing_info": row.get("pricing_info"),
        "image_url":    row.get("image_url"),
        "age_groups":   target_groups,
        "age_labels":   [_age_label(t) for t in target_groups],
        "categories":   subject_tags,
        "institution": {
            "id":   str(row["institution_id"]),
            "name": row.get("institution_name") or "",
            "city": row.get("institution_city") or "",
        },
        "created_at":   row["created_at"].isoformat() if row.get("created_at") else None,
        "reservation_count": int(row.get("reservation_count") or 0),
    }


# ---- Routes ----

@router.get("")
@limiter.limit("60/minute")
async def list_catalog(
    request: Request,
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = Query(None, description="Filter by institution city (icontains)"),
    age: Optional[str] = Query(None, description="Age slug: ms | zs1 | zs2 | ss"),
    category: Optional[str] = Query(None, description="Subject tag (icontains)"),
    q: Optional[str] = Query(None, description="Free text in name/description"),
    sort: str = Query("popular", description="popular | newest"),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List public catalog programs with filters. Only `is_in_catalog=TRUE` programs."""
    where = [
        "p.is_in_catalog = TRUE",
        "p.deleted_at IS NULL",
        "p.is_published = TRUE",
        "p.status = 'active'",
        "i.deleted_at IS NULL",
    ]
    params: Dict[str, Any] = {}

    if city:
        where.append("LOWER(i.city) LIKE :city")
        params["city"] = f"%{city.lower().strip()}%"

    if age:
        codes = AGE_SLUG_MAP.get(age.lower())
        if codes:
            # Match either single age_group or any code in target_groups (json) — cast to jsonb for ?| operator
            where.append(
                "(p.age_group = ANY(:age_codes) OR (p.target_groups)::jsonb ?| :age_codes)"
            )
            params["age_codes"] = codes

    if category:
        where.append("EXISTS (SELECT 1 FROM unnest(p.subject_tags) tag WHERE LOWER(tag) LIKE :cat)")
        params["cat"] = f"%{category.lower().strip()}%"

    if q:
        where.append("(LOWER(p.name_cs) LIKE :q OR LOWER(p.description_cs) LIKE :q)")
        params["q"] = f"%{q.lower().strip()}%"

    order_sql = "p.created_at DESC" if sort == "newest" else "reservation_count DESC NULLS LAST, p.created_at DESC"

    sql = f"""
        SELECT
            p.id, p.institution_id, p.name_cs, p.name_en, p.description_cs, p.description_en,
            p.duration, p.min_capacity, p.max_capacity, p.price, p.pricing_info,
            p.image_url, p.age_group, p.target_groups, p.subject_tags, p.created_at,
            i.name AS institution_name, i.city AS institution_city,
            COALESCE(rc.cnt, 0) AS reservation_count
        FROM programs p
        JOIN institutions i ON i.id = p.institution_id
        LEFT JOIN (
            SELECT program_id, COUNT(*) AS cnt FROM reservations
            WHERE status IN ('confirmed','pending_approval','done','approved')
            GROUP BY program_id
        ) rc ON rc.program_id = p.id
        WHERE {" AND ".join(where)}
        ORDER BY {order_sql}
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    try:
        result = await db.execute(text(sql), params)
        rows = [dict(r._mapping) for r in result.fetchall()]
    except Exception as e:
        logger.exception("catalog list failed")
        raise HTTPException(status_code=500, detail=f"Catalog query failed: {e}")

    # Total count (for pagination)
    count_sql = f"""
        SELECT COUNT(*) FROM programs p
        JOIN institutions i ON i.id = p.institution_id
        WHERE {" AND ".join(where)}
    """
    count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
    total = (await db.execute(text(count_sql), count_params)).scalar() or 0

    # Distinct cities & categories from currently-public programs (for filter UI)
    facets = await db.execute(text(
        """
        SELECT
            COALESCE(NULLIF(TRIM(i.city), ''), '') AS city,
            p.subject_tags
        FROM programs p
        JOIN institutions i ON i.id = p.institution_id
        WHERE p.is_in_catalog = TRUE AND p.deleted_at IS NULL AND p.is_published = TRUE
              AND p.status = 'active' AND i.deleted_at IS NULL
        """
    ))
    cities = set()
    cats = set()
    for r in facets.fetchall():
        c = (r._mapping.get("city") or "").strip()
        if c:
            cities.add(c)
        for t in (r._mapping.get("subject_tags") or []):
            if t:
                cats.add(str(t).strip())

    return {
        "items": [_row_to_card(r) for r in rows],
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "facets": {
            "cities":     sorted(cities, key=lambda s: s.lower()),
            "categories": sorted(cats, key=lambda s: s.lower()),
            "age_groups": [
                {"slug": "ms",  "label": "MŠ"},
                {"slug": "zs1", "label": "1. stupeň ZŠ"},
                {"slug": "zs2", "label": "2. stupeň ZŠ"},
                {"slug": "ss",  "label": "SŠ / gymnázium"},
            ],
        },
    }


@router.get("/{program_id}")
@limiter.limit("60/minute")
async def get_catalog_detail(
    program_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Detail of a single public catalog program."""
    sql = """
        SELECT
            p.id, p.institution_id, p.name_cs, p.name_en, p.description_cs, p.description_en,
            p.duration, p.min_capacity, p.max_capacity, p.price, p.pricing_info,
            p.image_url, p.age_group, p.target_groups, p.subject_tags, p.created_at,
            i.name AS institution_name, i.city AS institution_city, i.address AS institution_address,
            COALESCE(rc.cnt, 0) AS reservation_count
        FROM programs p
        JOIN institutions i ON i.id = p.institution_id
        LEFT JOIN (
            SELECT program_id, COUNT(*) AS cnt FROM reservations
            WHERE status IN ('confirmed','pending_approval','done','approved')
            GROUP BY program_id
        ) rc ON rc.program_id = p.id
        WHERE p.id = :pid
          AND p.is_in_catalog = TRUE
          AND p.deleted_at IS NULL
          AND p.is_published = TRUE
          AND p.status = 'active'
          AND i.deleted_at IS NULL
        LIMIT 1
    """
    result = await db.execute(text(sql), {"pid": program_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Program nenalezen v katalogu")
    d = dict(row._mapping)
    card = _row_to_card(d)
    # Detail extras
    card["description_full"] = d.get("description_cs") or d.get("description_en") or ""
    card["institution"]["address"] = d.get("institution_address") or ""
    return card
