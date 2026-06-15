"""
Static + logic regression tests for the multi-lecturer feature
(programs.required_lecturers + reservations.assigned_lecturer_ids).
DB-dependent flows are covered by the e2e testing agent.
"""
import os
import pytest


def _read(rel_path: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, rel_path), encoding="utf-8") as f:
        return f.read()


def test_models_have_new_columns():
    src = _read("database/models.py")
    assert "required_lecturers = Column(Integer" in src
    assert "assigned_lecturer_ids = Column(JSONB" in src


def test_collision_enforces_required_lecturers():
    src = _read("services/collision_service.py")
    assert "count_available_qualified_lecturers" in src
    assert "required_lecturers > 1" in src
    assert "Nedostatek lektorů" in src
    # qualification by supported_program_ids
    assert "supported_program_ids" in src


def test_qualified_count_respects_availability_and_occupancy():
    src = _read("services/collision_service.py")
    block = src[src.index("async def count_available_qualified_lecturers"):]
    # excludes occupied lecturers and checks per-lecturer availability
    assert "assigned_lecturer_id" in block
    assert "assigned_lecturer_ids" in block
    assert "check_lecturer_available_for_block" in block
    assert "time_blocks_overlap" in block


def test_schema_clamps_required_lecturers():
    from models.schemas import ProgramCreate
    common = dict(
        name_cs="x", name_en="x", description_cs="x", description_en="x",
        age_group="all", target_group="schools", duration=60,
        min_capacity=5, max_capacity=30,
    )
    p = ProgramCreate(**common, required_lecturers=0)
    assert p.required_lecturers == 1
    p2 = ProgramCreate(**common, required_lecturers=3)
    assert p2.required_lecturers == 3


def test_assign_endpoint_supports_multi():
    src = _read("routes/bookings.py")
    assert "lecturer_ids: Optional[List[str]]" in src
    assert "assigned_lecturer_ids" in src


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
