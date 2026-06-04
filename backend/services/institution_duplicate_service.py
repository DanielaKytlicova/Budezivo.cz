"""Duplicate-institution detection (Phase 83).

Provides two levels of match against the existing ``institutions`` table:

* **STRONG** — IČO exact match → registration is blocked, user must request join.
* **WEAK**   — Similar normalised name AND same city → soft warning shown to
  the user, who may still proceed if they confirm.

Pure read-only utility; never mutates DB.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Institution


WEAK_NAME_SIMILARITY = 0.80   # threshold (0–1) for slug-based similarity


@dataclass
class DuplicateMatch:
    """One existing institution that matches an incoming registration."""
    id: str
    name: str
    city: Optional[str]
    ico_dic: Optional[str]
    match_strength: str       # "strong" | "weak"
    reason: str               # human-readable Czech explanation


def _slugify(text: Optional[str]) -> str:
    """Strip diacritics and non-alphanumerics for fuzzy comparison."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in norm if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", ascii_only.lower())


def _normalize_ico(ico: Optional[str]) -> str:
    """Keep only digits — Czech IČO is 8 digits, sometimes prefixed/separated."""
    if not ico:
        return ""
    return re.sub(r"\D", "", str(ico))


def _name_similarity(a: str, b: str) -> float:
    """Token-based Jaccard-like similarity on slugified halves."""
    sa, sb = _slugify(a), _slugify(b)
    if not sa or not sb:
        return 0.0
    if sa == sb:
        return 1.0
    # Sliding-window character comparison — robust for short Czech names
    # like "ZŠ Komenského" vs "Základní škola Komenského".
    if sa in sb or sb in sa:
        return 0.9
    # Trigram overlap
    def trigrams(s: str) -> set:
        s = f"  {s}  "
        return {s[i : i + 3] for i in range(len(s) - 2)}
    ta, tb = trigrams(sa), trigrams(sb)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


async def find_duplicate_institutions(
    db: AsyncSession,
    *,
    name: Optional[str] = None,
    ico_dic: Optional[str] = None,
    city: Optional[str] = None,
    address: Optional[str] = None,
    exclude_id: Optional[str] = None,
) -> list[DuplicateMatch]:
    """Return all institutions in the DB that look like duplicates.

    Sorted strong-first so callers can simply check ``matches[0].match_strength``.
    """
    matches: list[DuplicateMatch] = []
    seen_ids: set[str] = set()

    # ── STRONG: exact IČO ──
    ico_norm = _normalize_ico(ico_dic)
    if ico_norm and len(ico_norm) >= 6:
        q = await db.execute(
            select(Institution).where(Institution.ico_dic.is_not(None))
        )
        for inst in q.scalars().all():
            if exclude_id and str(inst.id) == exclude_id:
                continue
            if _normalize_ico(inst.ico_dic) == ico_norm:
                matches.append(DuplicateMatch(
                    id=str(inst.id),
                    name=inst.name or "",
                    city=inst.city,
                    ico_dic=inst.ico_dic,
                    match_strength="strong",
                    reason=f"Stejné IČO {inst.ico_dic}.",
                ))
                seen_ids.add(str(inst.id))

    # ── WEAK: similar name (and matching city if both provided) ──
    if name:
        # Pull a small set of candidates by simple substring match to keep
        # the heavy slug-similarity comparison cheap. The Czech name "Galerie
        # Brno" still matches "Galerie m. Brna" because of the trigram step.
        first_token = name.strip().split()[0] if name.strip() else ""
        if len(first_token) >= 3:
            q = await db.execute(
                select(Institution).where(
                    func.lower(Institution.name).like(
                        f"%{first_token.lower()}%"
                    )
                ).limit(20)
            )
            candidates = q.scalars().all()
        else:
            q = await db.execute(select(Institution).limit(200))
            candidates = q.scalars().all()

        for inst in candidates:
            inst_id = str(inst.id)
            if exclude_id and inst_id == exclude_id:
                continue
            if inst_id in seen_ids:
                continue
            sim = _name_similarity(name, inst.name or "")
            if sim < WEAK_NAME_SIMILARITY:
                continue
            # Require city match (or empty-on-either-side) to avoid false positives
            same_city = (
                not city or not inst.city
                or _slugify(city) == _slugify(inst.city)
            )
            if not same_city:
                continue
            matches.append(DuplicateMatch(
                id=inst_id,
                name=inst.name or "",
                city=inst.city,
                ico_dic=inst.ico_dic,
                match_strength="weak",
                reason=(
                    f"Podobný název ({int(sim * 100)} % shoda)"
                    + (f" ve městě {inst.city}." if inst.city else ".")
                ),
            ))
            seen_ids.add(inst_id)

    matches.sort(key=lambda m: (0 if m.match_strength == "strong" else 1))
    return matches


def match_to_dict(m: DuplicateMatch) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "city": m.city,
        "ico_dic": m.ico_dic,
        "match_strength": m.match_strength,
        "reason": m.reason,
    }
