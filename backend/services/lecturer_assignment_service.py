"""
Automatic main-lecturer assignment for new reservations.
Chooses the best available lecturer (main mode only) for a program+slot.
Training-mode ("náslech") lecturers are never selected as the main lecturer.
"""
import logging
import uuid
from datetime import date as date_type, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from database.models import User, Program, Reservation
from services.collision_service import (
    check_lecturer_available_for_block,
    check_availability_blocks,
    time_blocks_overlap,
)

logger = logging.getLogger(__name__)

SOURCE_DEFAULT = "default_program"
SOURCE_AUTO = "auto_suggest"
SOURCE_MANUAL = "manual_admin"
SOURCE_UNASSIGNED = "unassigned"


async def _load_eligible_lecturer_pool(db: AsyncSession, program: Program) -> tuple[list[User], int]:
    """Candidate pool filtered to active + main-mode. Also enrich with lecturers whose
    `supported_program_ids` explicitly include this program, and exclude lecturers whose
    `learning_program_ids` include this program (they are trainees for this program).
    Returns (main_mode_candidates, total_configured_count)."""
    candidate_ids: list[str] = []
    if program.assigned_lecturer_id:
        candidate_ids.append(str(program.assigned_lecturer_id))
    for lid in (program.collision_lecturer_ids or []):
        if lid and lid not in candidate_ids:
            candidate_ids.append(str(lid))

    # Also include lecturers that claim this program in supported_program_ids
    pid_str = str(program.id)
    extra_rows = await db.execute(
        select(User).where(and_(
            User.institution_id == program.institution_id,
            User.status == "active",
            User.lecturer_mode == "main",
            User.deleted_at.is_(None),
            User.supported_program_ids.contains([pid_str]),
        ))
    )
    for u in extra_rows.scalars().all():
        if str(u.id) not in candidate_ids:
            candidate_ids.append(str(u.id))

    if not candidate_ids:
        return [], 0

    rows = await db.execute(
        select(User).where(and_(
            User.id.in_([uuid.UUID(x) for x in candidate_ids]),
            User.institution_id == program.institution_id,
            User.status == "active",
            User.lecturer_mode == "main",
            User.deleted_at.is_(None),
        ))
    )
    by_id = {str(u.id): u for u in rows.scalars().all()}
    # Exclude lecturers who listed this program as a learning one (trainees for this program)
    ordered = [
        by_id[cid] for cid in candidate_ids
        if cid in by_id and pid_str not in (by_id[cid].learning_program_ids or [])
    ]
    return ordered, len(candidate_ids)


async def _lecturer_load(db: AsyncSession, lecturer_id: uuid.UUID, institution_id: uuid.UUID) -> int:
    """Count lecturer's non-cancelled reservations in the last 7 days — lower = better."""
    since = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    r = await db.execute(
        select(func.count(Reservation.id)).where(and_(
            Reservation.institution_id == institution_id,
            Reservation.assigned_lecturer_id == lecturer_id,
            Reservation.status != "cancelled",
            Reservation.date >= since,
        ))
    )
    return int(r.scalar() or 0)


async def _has_same_lecturer_collision(
    db: AsyncSession, lecturer_id: uuid.UUID, institution_id: uuid.UUID,
    date: str, time_block: str, duration: int,
) -> bool:
    """Check whether the lecturer already has an overlapping reservation on that date."""
    r = await db.execute(
        select(Reservation).where(and_(
            Reservation.institution_id == institution_id,
            Reservation.date == date,
            Reservation.status != "cancelled",
            Reservation.assigned_lecturer_id == lecturer_id,
        ))
    )
    for other in r.scalars().all():
        # Need other program duration
        op = await db.execute(select(Program.duration).where(Program.id == other.program_id))
        other_duration = op.scalar_one_or_none() or 60
        if time_blocks_overlap(time_block, duration, other.time_block, other_duration):
            return True
    return False


async def pick_main_lecturer(
    db: AsyncSession,
    institution_id: str,
    program: Program,
    date: str,
    time_block: str,
) -> dict:
    """
    Returns a dict describing the chosen main lecturer:
      {
        "lecturer_id": str | None,
        "lecturer_name": str | None,
        "source": "default_program" | "auto_suggest" | "unassigned",
        "reason": str   # human-readable Czech reason
      }
    If no program-level lecturer candidates exist (pool empty) -> source='unassigned', lecturer_id=None, reason explains.
    If pool exists but NONE is available -> returns None (caller should reject booking).
    """
    inst_uuid = uuid.UUID(institution_id)
    duration = program.duration or 60

    pool, configured_count = await _load_eligible_lecturer_pool(db, program)
    if not pool:
        if configured_count == 0:
            # Program has no lecturers configured at all — allow booking unassigned
            return {
                "lecturer_id": None,
                "lecturer_name": None,
                "source": SOURCE_UNASSIGNED,
                "reason": "Program nemá přiřazené žádné lektory v nastavení — rezervace vytvořena bez hlavního lektora.",
            }
        # Program has lecturers configured but none is in main mode / active → reject
        return None

    # Evaluate each candidate: schedule OK + no Outlook/manual block + no same-lecturer overlap
    ranked: list[tuple[int, User, str, str]] = []  # (score, lecturer, reason, source)
    for idx, lect in enumerate(pool):
        lect_id_str = str(lect.id)

        avail = await check_lecturer_available_for_block(
            db, lect_id_str, institution_id, date, time_block, duration
        )
        if not avail:
            continue

        block_err = await check_availability_blocks(
            db, lect_id_str, institution_id, date, time_block, duration
        )
        if block_err:
            continue

        if await _has_same_lecturer_collision(db, lect.id, inst_uuid, date, time_block, duration):
            continue

        load = await _lecturer_load(db, lect.id, inst_uuid)
        # Scoring: default lecturer first; then age-group match; then lower load
        age_match = bool(
            (lect.preferred_age_groups or [])
            and program.age_group
            and program.age_group in (lect.preferred_age_groups or [])
        )
        supports_explicitly = str(program.id) in (lect.supported_program_ids or [])
        score = (
            (0 if idx == 0 else 10)       # keep program default at top
            + (-3 if age_match else 0)    # prefer age-group match
            + (-2 if supports_explicitly else 0)  # prefer explicit supporters
            + load                        # then prefer lower load
        )
        if idx == 0:
            reason = f"{lect.name or lect.email} — výchozí lektor programu (volný rozvrh, bez kolizí)"
            source = SOURCE_DEFAULT
        else:
            parts = []
            if age_match:
                parts.append("preferuje tuto věkovou skupinu")
            if supports_explicitly:
                parts.append("program má v profilu jako podporovaný")
            extra = f" ({'; '.join(parts)})" if parts else ""
            reason = (
                f"{lect.name or lect.email} — auto-výběr z {len(pool)} způsobilých lektorů"
                f", zatížení {load} rez./7 dní{extra}"
            )
            source = SOURCE_AUTO
        ranked.append((score, lect, reason, source))

    if not ranked:
        return None  # Pool exists but nobody is available → caller rejects booking

    ranked.sort(key=lambda x: x[0])
    _, best, reason, source = ranked[0]
    return {
        "lecturer_id": str(best.id),
        "lecturer_name": best.name or best.email,
        "source": source,
        "reason": reason,
    }
