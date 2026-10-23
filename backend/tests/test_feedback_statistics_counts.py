"""Execute the actual statistics endpoint's queries on an isolated SQLite DB."""
import unittest
import uuid
import warnings
from datetime import datetime, timezone

from sqlalchemy import create_engine, MetaData, Table, Column, Uuid, String, Integer, Boolean, DateTime
from sqlalchemy.exc import SAWarning
from fastapi import HTTPException

from routes.feedback import get_feedback_statistics


class AsyncReadSession:
    def __init__(self, connection):
        self.connection = connection

    async def execute(self, statement):
        return self.connection.execute(statement)


class FeedbackStatisticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        self.reservations = Table("reservations", metadata,
            Column("id", Uuid, primary_key=True), Column("institution_id", Uuid), Column("date", String))
        self.programs = Table("programs", metadata,
            Column("id", Uuid, primary_key=True), Column("institution_id", Uuid), Column("name_cs", String))
        self.feedbacks = Table("feedbacks", metadata,
            Column("id", Uuid, primary_key=True), Column("institution_id", Uuid),
            Column("reservation_id", Uuid), Column("program_id", Uuid), Column("status", String),
            Column("overall_rating", Integer), Column("would_recommend", Boolean),
            Column("email_sent_at", DateTime), Column("reminder_sent_at", DateTime))
        metadata.create_all(self.engine)
        self.connection = self.engine.connect()
        self.db = AsyncReadSession(self.connection)
        self.institution = uuid.uuid4()
        self.other = uuid.uuid4()
        self.program = self.add_program(self.institution)
        self.other_program = self.add_program(self.other)

    def tearDown(self):
        self.connection.close()
        self.engine.dispose()

    def add_program(self, institution):
        identifier = uuid.uuid4()
        self.connection.execute(self.programs.insert().values(id=identifier, institution_id=institution, name_cs=str(identifier)))
        return identifier

    def add_feedback(self, institution=None, program=None, status="submitted", rating=5,
                     recommend=True, sent=True, reminded=False, date="2026-10-23", reservation_institution=None):
        institution = institution or self.institution
        identifier = uuid.uuid4()
        self.connection.execute(self.reservations.insert().values(
            id=identifier, institution_id=reservation_institution or institution, date=date))
        self.connection.execute(self.feedbacks.insert().values(
            id=uuid.uuid4(), reservation_id=identifier, institution_id=institution,
            program_id=program or self.program, status=status, overall_rating=rating,
            would_recommend=recommend, email_sent_at=datetime.now(timezone.utc) if sent else None,
            reminder_sent_at=datetime.now(timezone.utc) if reminded else None))

    async def stats(self, **filters):
        # The former cartesian product emits SAWarning. Treat it as a failure.
        with warnings.catch_warnings():
            warnings.simplefilter("error", SAWarning)
            return await get_feedback_statistics(db=self.db,
                current_user={"institution_id": self.institution, "role": "admin"}, **filters)

    async def test_2831_cartesian_product_regression_and_tenant_isolation(self):
        for _ in range(19):
            self.add_feedback(rating=4)
        for _ in range(130):
            self.add_feedback(institution=self.other, program=self.other_program, rating=1)
        # Former query: 19 scoped responses * 149 global rows = 2831.
        result = await self.stats()
        self.assertEqual(result.total_feedbacks, 19)
        self.assertEqual(result.sent_requests, 19)
        self.assertEqual(result.average_rating, 4)
        self.assertEqual(result.recommendation_rate, 100)
        self.assertEqual(result.by_rating[4], 19)
        self.assertEqual(result.by_program[0]["count"], 19)

    async def test_sent_and_submitted_are_different_and_reminder_is_not_double_counted(self):
        self.add_feedback(status="pending", rating=None, recommend=None, reminded=True)
        self.add_feedback(status="pending", rating=None, recommend=None, sent=False)
        self.add_feedback(status="submitted", sent=False, recommend=False, rating=3)
        self.add_feedback(status="expired", rating=None, recommend=None)
        result = await self.stats()
        self.assertEqual((result.total_feedbacks, result.sent_requests), (1, 2))
        self.assertEqual(result.recommendation_rate, 0)
        self.assertEqual(result.average_rating, 3)

    async def test_program_and_date_filters_apply_to_all_aggregates(self):
        self.add_feedback(rating=2, date="2026-10-20")
        self.add_feedback(rating=5, date="2026-09-20")
        self.add_feedback(program=self.add_program(self.institution), rating=5)
        result = await self.stats(program_id=self.program, date_from="2026-10-01", date_to="2026-10-21")
        self.assertEqual((result.total_feedbacks, result.sent_requests), (1, 1))
        self.assertEqual(result.average_rating, 2)
        self.assertEqual(result.by_rating, {1: 0, 2: 1, 3: 0, 4: 0, 5: 0})
        self.assertEqual(len(result.by_program), 1)

    async def test_empty_and_mismatched_reservation_tenant(self):
        self.add_feedback(reservation_institution=self.other)
        result = await self.stats()
        self.assertEqual((result.total_feedbacks, result.sent_requests, result.programs_with_feedback), (0, 0, 0))
        self.assertIsNone(result.average_rating)
        self.assertIsNone(result.recommendation_rate)
        self.assertEqual(result.by_program, [])

    async def test_program_count_is_not_limited_to_top_ten(self):
        for _ in range(12):
            self.add_feedback(program=self.add_program(self.institution))
        result = await self.stats()
        self.assertEqual(result.programs_with_feedback, 12)
        self.assertEqual(len(result.by_program), 10)

    async def test_unprivileged_role_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            await get_feedback_statistics(db=self.db, current_user={"institution_id": self.institution, "role": "lecturer"})
        self.assertEqual(error.exception.status_code, 403)
