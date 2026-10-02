import asyncio
from pathlib import Path
import pytest

from routes.schools import migrate_existing_contacts


class FakeResult:
    def __init__(self, *, rows=None, rowcount=0):
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows


class FakeDb:
    def __init__(self):
        self.statements = []
        self.committed = False

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))
        if "SELECT s.id, s.institution_id" in sql:
            return FakeResult(rows=[])
        if "RETURNING id" in sql:
            return FakeResult(rows=[])
        return FakeResult(rowcount=0)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        raise AssertionError("successful backfill must not roll back")


def test_historical_contact_backfill_is_tenant_scoped_and_idempotent():
    db = FakeDb()
    institution_id = "11111111-1111-1111-1111-111111111111"

    result = asyncio.run(
        migrate_existing_contacts(
            current_user={"role": "spravce", "institution_id": institution_id},
            db=db,
        )
    )

    combined_sql = "\n".join(sql for sql, _ in db.statements)
    assert "FROM reservations" in combined_sql
    assert "INSERT INTO schools" in combined_sql
    assert "INSERT INTO school_contacts" in combined_sql
    assert "NOT EXISTS" in combined_sql
    assert all(
        params is None or params.get("inst_id", institution_id) == institution_id
        for _, params in db.statements
    )
    assert db.committed is True
    assert result["created_schools"] == 0
    assert result["created_contacts"] == 0


def test_contact_backfill_rejects_non_management_role():
    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            migrate_existing_contacts(
                current_user={"role": "edukator", "institution_id": "ignored"},
                db=FakeDb(),
            )
        )

    assert getattr(exc_info.value, "status_code", None) == 403


def test_schools_page_runs_backfill_before_loading_directory():
    source = (
        Path(__file__).parents[2] / "frontend/src/pages/admin/SchoolsPage.js"
    ).read_text(encoding="utf-8")

    initializer = source.split("const initializeSchools", 1)[1].split("const setupContactsTable", 1)[0]
    assert "await setupContactsTable()" in initializer
    assert "await axios.post(`${API}/schools/migrate-contacts`)" in initializer
    assert initializer.index("migrate-contacts") < initializer.index("fetchData()")


def test_authenticated_booking_keeps_school_directory_in_sync():
    source = (
        Path(__file__).parents[1] / "routes/bookings.py"
    ).read_text(encoding="utf-8")

    authenticated_flow = source.split("async def create_booking(", 1)[1].split(
        '@router.post("/public/{institution_id}"', 1
    )[0]
    assert "created_school = await _school_repo.create" in authenticated_flow
    assert ".values(school_id=uuid.UUID(created_school[\"id\"]))" in authenticated_flow
    assert ".values(booking_count=School.booking_count + 1)" in authenticated_flow
