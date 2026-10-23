import io
import unittest
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pypdf import PdfReader

from routes import events
from services.event_schedule import format_event_schedule, UNRECORDED_SCHEDULE, PREREGISTRATION_SCHEDULE
from services.export_service import generate_pdf_confirmation
from templates.emails.templates import event_application_confirmation, event_payment_reminder


def term(start="2026-10-24T08:00:00+00:00", end="2026-10-24T09:30:00+00:00"):
    return {"start_datetime": start, "end_datetime": end}


class EventScheduleOutputTests(unittest.TestCase):
    def test_separate_slots_have_matching_html_text_and_pdf(self):
        for start, end, expected in (
            ("2026-10-24T08:00:00Z", "2026-10-24T09:30:00Z", "24. 10. 2026 10:00–11:30"),
            ("2026-10-24T09:30:00Z", "2026-10-24T11:00:00Z", "24. 10. 2026 11:30–13:00"),
            ("2026-10-26T09:00:00Z", "2026-10-26T10:00:00Z", "26. 10. 2026 10:00–11:00"),
        ):
            with self.subTest(start=start):
                label = format_event_schedule(start, end)
                self.assertEqual(label, expected)
                for render in (event_application_confirmation, event_payment_reminder):
                    email = render({"event_name": "Synthetic event", "date_label": label, "status": "pending"})
                    self.assertIn(label, email["html"])
                    self.assertIn(label, email["text"])
                pdf = generate_pdf_confirmation({"event_date_id": "date", "applicant_name": "Test"},
                    {"name": "Synthetic event", "type": "workshop", "price": 0}, term(start, end), {"name": "Test museum"}, None)
                self.assertIn(label, "".join(page.extract_text() for page in PdfReader(pdf).pages))

    def test_multiple_days_naive_utc_and_clock_changes(self):
        self.assertEqual(format_event_schedule("2026-10-24T08:00:00", "2026-10-26T10:00:00"),
                         "24. 10. 2026 10:00 CEST – 26. 10. 2026 11:00 CET")
        self.assertEqual(format_event_schedule("2026-10-25T00:30:00Z", "2026-10-25T01:30:00Z"),
                         "25. 10. 2026 02:30 CEST – 02:30 CET")
        self.assertEqual(format_event_schedule("2026-03-29T00:30:00Z", "2026-03-29T01:30:00Z"),
                         "29. 03. 2026 01:30 CET – 03:30 CEST")

    def test_invalid_schedule_is_not_silently_omitted(self):
        for start, end in ((None, None), ("bad", "bad"), ("2026-10-24T10:00Z", "2026-10-24T09:00Z")):
            with self.assertRaises((ValueError, TypeError)):
                format_event_schedule(start, end)
        with self.assertRaises(ValueError):
            generate_pdf_confirmation({"event_date_id": "missing"}, {}, None, {}, None)

    def test_unknown_historical_date_is_explicit_and_preregistration_email_is_explicit(self):
        pdf = generate_pdf_confirmation({}, {"name": "Test"}, None, {"name": "Test museum"}, None)
        self.assertIn(UNRECORDED_SCHEDULE, "".join(p.extract_text() for p in PdfReader(pdf).pages))
        email = event_application_confirmation({"date_label": PREREGISTRATION_SCHEDULE})
        self.assertIn(PREREGISTRATION_SCHEDULE, email["text"])


class EventScheduleRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_retry_retains_date_for_both_endpoints(self):
        inst_id, app_id = uuid.uuid4(), uuid.uuid4()
        application = SimpleNamespace(event_id=uuid.uuid4(), applicant_name="Test")
        ed = SimpleNamespace(**term())
        for public in (False, True):
            with self.subTest(public=public):
                db = AsyncMock()
                db.execute.side_effect = [SimpleNamespace(scalar_one_or_none=lambda: application),
                                         SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace()),
                                         SimpleNamespace(scalar_one_or_none=lambda: None)]
                with patch.object(events, "require_events_module", AsyncMock()), \
                     patch.object(events, "is_feature_enabled", AsyncMock(return_value=True)), \
                     patch.object(events, "_application_pdf_token_valid", return_value=True), \
                     patch.object(events, "_application_event_date", AsyncMock(return_value=ed)), \
                     patch.object(events, "_application_pdf_institution_data", AsyncMock(return_value={"name": "Test"})), \
                     patch.object(events, "_to_dict", side_effect=lambda x: vars(x)), \
                     patch("services.export_service.generate_pdf_confirmation", side_effect=[RuntimeError("optional component"), io.BytesIO(b"pdf")]) as render:
                    if public:
                        await events.public_application_pdf(str(inst_id), str(app_id), token="test", db=db)
                    else:
                        await events.export_application_pdf(str(app_id), db=db, current_user={"institution_id": str(inst_id)})
                    self.assertEqual(render.call_count, 2)
                    self.assertEqual(render.call_args_list[0].args[2], render.call_args_list[1].args[2])

    async def test_orphan_date_and_unassigned_date_require_resolution(self):
        for date_id, existing in ((uuid.uuid4(), None), (None, uuid.uuid4())):
            db = AsyncMock()
            db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: existing)
            with self.assertRaises(HTTPException) as error:
                await events._application_event_date(db, SimpleNamespace(event_date_id=date_id, event_id=uuid.uuid4()))
            self.assertEqual(error.exception.status_code, 409)

    async def test_selected_date_is_preserved_and_wrong_event_is_filtered(self):
        application = SimpleNamespace(event_date_id=uuid.uuid4(), event_id=uuid.uuid4())
        selected = SimpleNamespace(start_datetime=datetime.fromisoformat("2026-10-24T09:30:00+00:00"),
                                   end_datetime=datetime.fromisoformat("2026-10-24T11:00:00+00:00"))
        db = AsyncMock()
        db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: selected)
        self.assertIs(await events._application_event_date(db, application), selected)
        from sqlalchemy.dialects import postgresql
        sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn(str(application.event_date_id), sql)
        self.assertIn(str(application.event_id), sql)

    async def test_removal_of_booked_date_is_blocked_and_tenant_scoped(self):
        db = AsyncMock()
        ed = SimpleNamespace(id=uuid.uuid4())
        inst_id = uuid.uuid4()
        db.execute.side_effect = [SimpleNamespace(scalar_one_or_none=lambda: ed),
                                 SimpleNamespace(scalar_one_or_none=lambda: uuid.uuid4())]
        with patch.object(events, "require_events_module", AsyncMock()):
            with self.assertRaises(HTTPException) as error:
                await events.remove_event_date(str(uuid.uuid4()), str(ed.id), db=db,
                    current_user={"institution_id": str(inst_id), "role": "admin"})
        self.assertEqual(error.exception.status_code, 409)
        from sqlalchemy.dialects import postgresql
        sql = str(db.execute.call_args_list[0].args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        self.assertIn("FOR UPDATE OF event_dates", sql)
        self.assertIn(str(inst_id), sql)
        db.delete.assert_not_awaited()
        db.commit.assert_not_awaited()

    async def test_unbooked_date_can_still_be_removed(self):
        db = AsyncMock()
        ed = SimpleNamespace(id=uuid.uuid4())
        db.execute.side_effect = [SimpleNamespace(scalar_one_or_none=lambda: ed),
                                 SimpleNamespace(scalar_one_or_none=lambda: None)]
        with patch.object(events, "require_events_module", AsyncMock()):
            await events.remove_event_date(str(uuid.uuid4()), str(ed.id), db=db,
                current_user={"institution_id": str(uuid.uuid4()), "role": "admin"})
        db.delete.assert_awaited_once_with(ed)
        db.commit.assert_awaited_once()
