"""
E2E (DB-dependent) tests for A10 (capacity → waitlist race),
A11 (soft plan usage endpoint), A12 (GDPR anonymize guard).

Uses cookie-auth via the public ingress (REACT_APP_BACKEND_URL).
"""
import os
import uuid
from datetime import date, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

DEMO_EMAIL = "demo@budezivo.cz"
DEMO_PASSWORD = "Demo2026!"
DEMO_INSTITUTION_ID = "c18a10b9-4dd0-4779-86b9-b68dae21c71f"
TEST_MUZEUM_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    # bearer fallback
    tok = r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


def _institution_with_events_enabled(admin_session):
    """Find an institution where the events feature is on. Try the demo one
    first, otherwise fall back to Test Muzeum."""
    for inst_id in [DEMO_INSTITUTION_ID, TEST_MUZEUM_ID]:
        # public detail probe — if 404 'Not found' the feature flag is off.
        r = requests.get(
            f"{BASE_URL}/api/events/public/{inst_id}", timeout=15
        )
        if r.status_code == 200:
            return inst_id
    pytest.skip("No institution with the events feature enabled")


# --------------------------------------------------------------- A11 / usage


class TestA11PlanUsage:
    def test_usage_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/plan/usage", timeout=15)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text[:200]}"

    def test_usage_snapshot_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/plan/usage", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("enforced") is False, "A11 must remain SOFT"
        for key in ("programs", "bookings_month"):
            assert key in data, f"missing block: {key}"
            block = data[key]
            for f in ("used", "limit", "unlimited", "percent", "remaining",
                      "near_limit", "over_limit"):
                assert f in block, f"{key} missing field {f}: {block}"
        # demo is PRO+ so both should be unlimited
        assert data["programs"]["unlimited"] is True
        assert data["bookings_month"]["unlimited"] is True


# ---------------------------------------------------------- A10 / capacity


class TestA10CapacityWaitlist:
    @pytest.fixture(scope="class")
    def ctx(self, admin_session):
        inst_id = _institution_with_events_enabled(admin_session)

        # Create event with capacity 1
        ev_payload = {
            "name": f"TEST_CAP_{uuid.uuid4().hex[:8]}",
            "description": "Test waitlist",
            "capacity": 1,
            "price": 0,
        }
        r = admin_session.post(f"{BASE_URL}/api/events", json=ev_payload, timeout=30)
        if r.status_code == 404:
            pytest.skip(f"events feature gated off for inst {inst_id}: {r.text}")
        assert r.status_code in (200, 201), f"create event failed: {r.status_code} {r.text}"
        event = r.json()
        event_id = event["id"]

        # Add a future date
        target_date = (date.today() + timedelta(days=21)).isoformat()
        rd = admin_session.post(
            f"{BASE_URL}/api/events/{event_id}/dates",
            json={
                "start_datetime": f"{target_date}T10:00:00",
                "end_datetime": f"{target_date}T12:00:00",
                "capacity_override": 1,
            },
            timeout=30,
        )
        assert rd.status_code in (200, 201), f"add date failed: {rd.status_code} {rd.text}"
        date_obj = rd.json()
        event_date_id = date_obj["id"]

        yield {
            "inst_id": inst_id,
            "event_id": event_id,
            "event_date_id": event_date_id,
        }

        # cleanup
        try:
            admin_session.delete(f"{BASE_URL}/api/events/{event_id}", timeout=20)
        except Exception:
            pass

    def test_first_application_is_pending(self, ctx):
        payload = {
            "event_id": ctx["event_id"],
            "event_date_id": ctx["event_date_id"],
            "applicant_name": "TEST First Applicant",
            "applicant_email": "test_first_applicant@example.com",
            "applicant_data": {"name": "TEST First Applicant"},
            "marketing_consent": False,
        }
        r = requests.post(
            f"{BASE_URL}/api/events/public/{ctx['inst_id']}/apply",
            json=payload, timeout=30,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        body = r.json()
        assert body.get("status") == "pending", body
        assert body.get("waitlisted") is False, body
        ctx["first_app_id"] = body["id"]

    def test_second_application_is_waitlisted(self, ctx):
        payload = {
            "event_id": ctx["event_id"],
            "event_date_id": ctx["event_date_id"],
            "applicant_name": "TEST Second Applicant",
            "applicant_email": "test_second_applicant@example.com",
            "applicant_data": {"name": "TEST Second Applicant"},
            "marketing_consent": False,
        }
        r = requests.post(
            f"{BASE_URL}/api/events/public/{ctx['inst_id']}/apply",
            json=payload, timeout=30,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        body = r.json()
        assert body.get("status") == "waitlist", body
        assert body.get("waitlisted") is True, body
        # waitlisted MUST NOT generate a QR payment
        assert not body.get("qr_payload"), f"waitlisted should not generate QR: {body.get('qr_payload')}"
        ctx["second_app_id"] = body["id"]

    def test_public_detail_counts(self, ctx):
        r = requests.get(
            f"{BASE_URL}/api/events/public/{ctx['inst_id']}/{ctx['event_id']}",
            timeout=20,
        )
        assert r.status_code == 200, r.text
        detail = r.json()
        # find our date in the dates array
        dates = detail.get("dates") or []
        the_date = next((d for d in dates if d.get("id") == ctx["event_date_id"]), None)
        assert the_date is not None, f"date not found in {dates}"
        assert the_date.get("applications_count") == 1, the_date
        assert the_date.get("waitlist_count") == 1, the_date
        assert the_date.get("spots_left") == 0, the_date
        assert the_date.get("is_full") is True, the_date

    def test_promote_waitlist_to_pending(self, admin_session, ctx):
        if "second_app_id" not in ctx:
            pytest.skip("no second app to promote")
        r = admin_session.put(
            f"{BASE_URL}/api/events/applications/{ctx['second_app_id']}/status",
            json={"status": "pending"}, timeout=20,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        body = r.json()
        assert body.get("status") == "pending", body

    def test_idor_other_institution_returns_404(self, admin_session, ctx):
        """Status update for a fake-uuid application must 404, proving tenant scope."""
        fake_id = str(uuid.uuid4())
        r = admin_session.put(
            f"{BASE_URL}/api/events/applications/{fake_id}/status",
            json={"status": "pending"}, timeout=20,
        )
        assert r.status_code == 404, f"expected 404, got {r.status_code} {r.text}"


# ----------------------------------------------------------------- A12 GDPR


class TestA12GDPRGuard:
    def test_anonymize_requires_confirmation(self, admin_session):
        r = admin_session.post(
            f"{BASE_URL}/api/gdpr/anonymize",
            json={"confirmation": "WRONG"}, timeout=20,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"

    def test_anonymize_requires_auth(self):
        r = requests.post(
            f"{BASE_URL}/api/gdpr/anonymize",
            json={"confirmation": "SMAZAT"}, timeout=20,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
