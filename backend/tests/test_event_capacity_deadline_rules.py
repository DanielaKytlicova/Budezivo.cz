import asyncio
import os
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-secret-for-event-rule-tests")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routes import events


class Column:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return ("eq", self.name, other)

    def is_(self, other):
        return ("is", self.name, other)

    def in_(self, values):
        return ("in", self.name, tuple(values))


class FakeEventDateModel:
    id = Column("event_dates.id")


class FakeEventApplicationModel:
    id = Column("event_applications.id")
    event_id = Column("event_applications.event_id")
    event_date_id = Column("event_applications.event_date_id")
    status = Column("event_applications.status")


class FakeFunc:
    @staticmethod
    def count(value):
        return ("count", value)


@dataclass
class Query:
    kind: object
    condition: object = None

    def where(self, condition):
        self.condition = condition
        return self


def fake_select(kind):
    return Query(kind)


def fake_and_(*conditions):
    return ("and", conditions)


def fake_text(sql):
    return ("text", sql)


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar(self):
        return self.value


class FakeDB:
    def __init__(self, responses):
        self.responses = list(responses)
        self.queries = []

    async def execute(self, query, params=None):
        self.queries.append((query, params))
        if self.responses:
            return Result(self.responses.pop(0))
        return Result(None)


def run(coro):
    return asyncio.run(coro)


class EventCapacityAndDeadlineTests(unittest.TestCase):
    def patch_events(self):
        return patch.multiple(
            events,
            EventDate=FakeEventDateModel,
            EventApplication=FakeEventApplicationModel,
            select=fake_select,
            and_=fake_and_,
            func=FakeFunc,
            text=fake_text,
        )

    def test_unlimited_capacity_stays_pending_without_lock(self):
        event = SimpleNamespace(id="event-1", capacity=None)
        db = FakeDB([])

        with self.patch_events():
            status = run(events._resolve_application_status(db, event, None))

        self.assertEqual(status, "pending")
        self.assertEqual(db.queries, [])

    def test_full_capacity_goes_to_waitlist(self):
        event = SimpleNamespace(id="event-1", capacity=1)
        db = FakeDB([None, 1])

        with self.patch_events():
            status = run(events._resolve_application_status(db, event, None))

        self.assertEqual(status, "waitlist")
        self.assertEqual(db.queries[0][0][0], "text")
        self.assertEqual(db.queries[1][0].kind[0], "count")

    def test_available_date_override_capacity_stays_pending(self):
        event = SimpleNamespace(id="event-1", capacity=1)
        event_date = SimpleNamespace(capacity_override=2)
        db = FakeDB([event_date, None, 1])

        with self.patch_events():
            status = run(events._resolve_application_status(db, event, "date-1"))

        self.assertEqual(status, "pending")
        self.assertEqual(db.queries[0][0].kind, FakeEventDateModel)

    def test_only_real_seat_statuses_occupy_capacity(self):
        self.assertEqual(events.OCCUPYING_STATUSES, ("pending", "approved"))
        self.assertNotIn("waitlist", events.OCCUPYING_STATUSES)
        self.assertNotIn("rejected", events.OCCUPYING_STATUSES)

    def test_event_date_deadline_override_wins(self):
        event_deadline = datetime(2026, 8, 20, 10, tzinfo=timezone.utc)
        date_deadline = datetime(2026, 8, 19, 10, tzinfo=timezone.utc)
        event_start = datetime(2026, 8, 24, 10, tzinfo=timezone.utc)
        event = SimpleNamespace(registration_deadline=event_deadline)
        event_date = SimpleNamespace(
            registration_deadline_override=date_deadline,
            start_datetime=event_start,
        )

        self.assertEqual(events._effective_registration_deadline(event, event_date), date_deadline)

    def test_event_date_start_is_fallback_deadline(self):
        event_start = datetime(2026, 8, 24, 10, tzinfo=timezone.utc)
        event = SimpleNamespace(registration_deadline=None)
        event_date = SimpleNamespace(
            registration_deadline_override=None,
            start_datetime=event_start,
        )

        self.assertEqual(events._effective_registration_deadline(event, event_date), event_start)


if __name__ == "__main__":
    unittest.main()
