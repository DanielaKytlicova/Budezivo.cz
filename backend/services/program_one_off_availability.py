"""Shared loading/merging for additional exact program slots."""
import uuid
from sqlalchemy import select
from database.models import ProgramOneOffAvailability


async def get_program_one_offs(db, institution_id, program_id=None, date_from=None, date_to=None, *, lock=False):
    if institution_id == "demo":
        return []
    query = select(ProgramOneOffAvailability).where(
        ProgramOneOffAvailability.institution_id == uuid.UUID(institution_id)
    )
    if program_id:
        query = query.where(ProgramOneOffAvailability.program_id == uuid.UUID(program_id))
    if date_from:
        query = query.where(ProgramOneOffAvailability.date >= date_from)
    if date_to:
        query = query.where(ProgramOneOffAvailability.date <= date_to)
    if lock:
        # Prevent deletion between public submit validation and reservation commit.
        query = query.with_for_update(read=True)
    result = await db.execute(query.order_by(
        ProgramOneOffAvailability.date, ProgramOneOffAvailability.start_time,
        ProgramOneOffAvailability.end_time,
    ))
    return list(result.scalars().all())


def merge_program_one_off_slots(regular_slots, one_offs):
    """Keep recurring expansion unchanged; extra intervals are exact single slots."""
    if not one_offs:
        return list(regular_slots)
    return sorted(set(regular_slots) | {
        f"{slot.start_time}-{slot.end_time}" for slot in one_offs
    })


def one_off_dict(slot):
    return {
        "id": str(slot.id), "program_id": str(slot.program_id),
        "date": slot.date, "start_time": slot.start_time, "end_time": slot.end_time,
    }
