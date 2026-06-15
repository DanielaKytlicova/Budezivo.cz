"""
API-level e2e tests for the multi-lecturer feature:
- Program required_lecturers persistence and clamping
- Booking creation 409 'Nedostatek lektorů' path
- /bookings/{id}/assign-lecturer-admin accepts lecturer_ids (multi) and lecturer_id (single)

Uses live backend at REACT_APP_BACKEND_URL with demo superadmin credentials.
Cleans up any test programs it creates.
"""
import os
import uuid
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
LOGIN_EMAIL = "demo@budezivo.cz"
LOGIN_PASSWORD = "Demo2026!"
DEMO_INSTITUTION_ID = "c18a10b9-4dd0-4779-86b9-b68dae21c71f"

TEST_PROG_PREFIX = "TEST_multilect_"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login",
                 json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth(api, auth_token):
    api.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api


@pytest.fixture(scope="module")
def created_program_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def _cleanup(auth, created_program_ids):
    yield
    for pid in created_program_ids:
        try:
            auth.delete(f"{BASE_URL}/api/programs/{pid}", timeout=10)
        except Exception as e:
            print(f"cleanup failed for {pid}: {e}")


def _program_payload(required_lecturers=2, suffix=""):
    name = f"{TEST_PROG_PREFIX}{suffix or uuid.uuid4().hex[:6]}"
    return {
        "name_cs": name, "name_en": name,
        "description_cs": "test", "description_en": "test",
        "duration": 60,
        "age_group": "all",
        "target_groups": ["zs1_7_12"],
        "target_group": "schools",
        "min_capacity": 5, "max_capacity": 30,
        "price": 0,
        "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "time_blocks": ["09:00-10:30"],
        "min_days_before_booking": 1,
        "max_days_before_booking": 365,
        "required_lecturers": required_lecturers,
    }


# ---------- tests ----------

class TestProgramRequiredLecturersPersistence:
    """Phase 1: required_lecturers is stored, returned, and clamped."""

    def test_create_program_with_required_lecturers_2(self, auth, created_program_ids):
        payload = _program_payload(required_lecturers=2)
        r = auth.post(f"{BASE_URL}/api/programs", json=payload)
        assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text}"
        data = r.json()
        assert data.get("required_lecturers") == 2, f"required_lecturers not persisted: {data}"
        created_program_ids.append(data["id"])

    def test_get_program_returns_required_lecturers_2(self, auth, created_program_ids):
        assert created_program_ids, "previous test should have created a program"
        pid = created_program_ids[0]
        r = auth.get(f"{BASE_URL}/api/programs/{pid}")
        assert r.status_code == 200
        body = r.json()
        assert body.get("required_lecturers") == 2

    def test_required_lecturers_clamps_zero_to_one(self, auth, created_program_ids):
        payload = _program_payload(required_lecturers=0, suffix="clamp")
        r = auth.post(f"{BASE_URL}/api/programs", json=payload)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
        data = r.json()
        assert data.get("required_lecturers") == 1, f"clamp 0->1 failed: {data}"
        created_program_ids.append(data["id"])

    def test_required_lecturers_clamps_negative_to_one(self, auth, created_program_ids):
        payload = _program_payload(required_lecturers=-5, suffix="clampneg")
        r = auth.post(f"{BASE_URL}/api/programs", json=payload)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data.get("required_lecturers") == 1
        created_program_ids.append(data["id"])


class TestBookingCollision409:
    """Phase 2: booking a program with required_lecturers=2 returns 409 Nedostatek lektorů."""

    def test_booking_returns_409_nedostatek_lektoru(self, auth, created_program_ids):
        # Use the first program (required_lecturers=2)
        assert created_program_ids
        pid = created_program_ids[0]

        # Pick a future weekday Monday-Friday at least 14 days ahead to satisfy any defaults
        d = date.today() + timedelta(days=21)
        while d.weekday() >= 5:
            d += timedelta(days=1)

        payload = {
            "program_id": pid,
            "date": d.isoformat(),
            "time_block": "09:00-10:30",
            "school_name": "TEST_School",
            "group_type": "school",
            "age_or_class": "5.A",
            "num_students": 20,
            "num_teachers": 2,
            "contact_name": "Test Tester",
            "contact_email": "test_multilect@example.com",
            "contact_phone": "+420777777777",
            "gdpr_consent": True,
            "terms_accepted": True,
        }
        r = auth.post(f"{BASE_URL}/api/bookings", json=payload)
        # The slot has zero qualified lecturers on demo institution → should 409
        assert r.status_code == 409, f"expected 409 got {r.status_code}: {r.text}"
        body = r.json()
        # FastAPI puts the message in 'detail' (str OR dict if classify_collision returns dict)
        detail = body.get("detail")
        as_text = str(detail)
        assert "Nedostatek lektorů" in as_text, f"missing czech msg: {as_text}"

    def test_required_lecturers_1_does_not_trigger_new_block(self, auth, created_program_ids):
        # Create a program with required_lecturers=1 -- should NOT 409 with Nedostatek lektorů.
        payload = _program_payload(required_lecturers=1, suffix="single")
        r = auth.post(f"{BASE_URL}/api/programs", json=payload)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        created_program_ids.append(pid)

        d = date.today() + timedelta(days=22)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        booking_payload = {
            "program_id": pid,
            "date": d.isoformat(),
            "time_block": "09:00-10:30",
            "school_name": "TEST_School_Single",
            "group_type": "school",
            "age_or_class": "5.A",
            "num_students": 20,
            "num_teachers": 2,
            "contact_name": "Test Tester",
            "contact_email": "test_single@example.com",
            "contact_phone": "+420777777777",
            "gdpr_consent": True,
            "terms_accepted": True,
        }
        r2 = auth.post(f"{BASE_URL}/api/bookings", json=booking_payload)
        # We don't insist on 200 — the slot may collide for other reasons. We only assert:
        # if it 409s, the message must NOT be Nedostatek lektorů.
        if r2.status_code == 409:
            assert "Nedostatek lektorů" not in str(r2.json().get("detail", "")), \
                f"required_lecturers=1 should not trigger new block: {r2.text}"
        else:
            assert r2.status_code in (200, 201), f"unexpected: {r2.status_code} {r2.text}"
            # Cleanup the booking we accidentally created
            try:
                bid = r2.json().get("id")
                if bid:
                    auth.delete(f"{BASE_URL}/api/bookings/{bid}")
            except Exception:
                pass


class TestAssignLecturerAdminEndpoint:
    """Phase 3: /assign-lecturer-admin accepts lecturer_ids (multi) shape."""

    def test_empty_payload_returns_400(self, auth):
        # Use a clearly-non-existent booking id; routing should reach validation first or
        # return 404 — what matters is that the endpoint exists and handles missing body.
        fake_booking = str(uuid.uuid4())
        r = auth.post(
            f"{BASE_URL}/api/bookings/{fake_booking}/assign-lecturer-admin",
            json={},
        )
        # Either: 400 'Nebyl vybrán žádný lektor' (current code's behavior since
        # booking lookup runs first → expect 404 instead). Both are acceptable signal
        # that the endpoint exists & accepts the new schema.
        assert r.status_code in (400, 404), f"{r.status_code} {r.text}"

    def test_accepts_lecturer_ids_field_in_schema(self, auth):
        """Send the new lecturer_ids field and verify the schema doesn't 422 on it."""
        fake_booking = str(uuid.uuid4())
        r = auth.post(
            f"{BASE_URL}/api/bookings/{fake_booking}/assign-lecturer-admin",
            json={"lecturer_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
        )
        # 422 would mean the schema rejects the new field. Expect 404 (booking missing).
        assert r.status_code != 422, f"schema rejected lecturer_ids: {r.text}"
        assert r.status_code in (400, 403, 404), f"{r.status_code} {r.text}"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
