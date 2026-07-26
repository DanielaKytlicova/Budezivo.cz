import unittest
import uuid

from fastapi import HTTPException

from routes.schools import (
    BulkArchiveRequest,
    BulkContactArchiveRequest,
    bulk_archive_school_contacts,
    bulk_archive_schools,
)


class _Result:
    rowcount = 2


class _Database:
    def __init__(self):
        self.statement = None
        self.params = None
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement, params):
        self.statement = str(statement)
        self.params = params
        return _Result()

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class SchoolArchivingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.institution_id = str(uuid.uuid4())
        self.current_user = {
            "institution_id": self.institution_id,
            "role": "spravce",
        }

    async def test_school_archive_preserves_related_data(self):
        db = _Database()
        school_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        result = await bulk_archive_schools(
            BulkArchiveRequest(school_ids=school_ids, action="archive"),
            current_user=self.current_user,
            db=db,
        )

        self.assertIn("deleted_at = NOW()", db.statement)
        self.assertEqual(db.params["inst"], self.institution_id)
        self.assertEqual(db.params["ids"], school_ids)
        self.assertTrue(db.committed)
        self.assertTrue(result["preserved_bookings"])
        self.assertTrue(result["preserved_statistics"])

    async def test_archived_contacts_can_be_restored(self):
        db = _Database()
        contact_id = str(uuid.uuid4())

        result = await bulk_archive_school_contacts(
            BulkContactArchiveRequest(
                contact_ids=[contact_id],
                action="restore",
            ),
            current_user=self.current_user,
            db=db,
        )

        self.assertIn("status LIKE 'archived%'", db.statement)
        self.assertIn("archived_invalid", db.statement)
        self.assertEqual(db.params["ids"], [contact_id])
        self.assertEqual(result["updated_contacts"], 2)

    async def test_unauthorized_role_cannot_archive_schools(self):
        with self.assertRaises(HTTPException) as raised:
            await bulk_archive_schools(
                BulkArchiveRequest(
                    school_ids=[str(uuid.uuid4())],
                    action="archive",
                ),
                current_user={
                    "institution_id": self.institution_id,
                    "role": "pokladni",
                },
                db=_Database(),
            )

        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
