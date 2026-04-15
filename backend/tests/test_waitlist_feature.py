"""
Waitlist Feature Tests - Phase 1 MVP
Tests for waitlist/term watching functionality:
- POST /api/waitlist (public) - create waitlist entry
- GET /api/waitlist (admin) - list entries with filters
- GET /api/waitlist/count/{program_id} (public) - active count
- PATCH /api/waitlist/{id} (admin) - update status/note
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
PROGRAM_ID = "128d6178-e199-4cc5-b247-0e42fe1955d7"
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def session():
    """Shared requests session."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_session(session):
    """Authenticated session with httpOnly cookies."""
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return session


def get_future_date(days=30):
    """Get a future date string."""
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def get_past_date(days=30):
    """Get a past date string."""
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


class TestWaitlistPublicCreate:
    """Tests for POST /api/waitlist (public endpoint)."""

    def test_create_waitlist_entry_success(self, session):
        """POST /api/waitlist creates entry with valid data."""
        unique_email = f"test_wl_{uuid.uuid4().hex[:8]}@test.cz"
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Test Teacher",
            "school_name": "Test School",
            "email": unique_email,
            "phone": "+420123456789",
            "participant_count": 15,
            "request_type": "specific_date",
            "requested_date": get_future_date(60),
            "preferred_time_of_day": "morning",
            "notes": "Test note"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["teacher_name"] == "Test Teacher"
        assert data["school_name"] == "Test School"
        assert data["email"] == unique_email
        assert data["participant_count"] == 15
        assert data["status"] == "active"
        assert "id" in data

    def test_create_waitlist_date_range_success(self, session):
        """POST /api/waitlist with date_range request type."""
        unique_email = f"test_range_{uuid.uuid4().hex[:8]}@test.cz"
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Range Teacher",
            "school_name": "Range School",
            "email": unique_email,
            "participant_count": 20,
            "request_type": "date_range",
            "range_start_date": get_future_date(30),
            "range_end_date": get_future_date(60),
            "preferred_time_of_day": "afternoon"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "date_range"
        assert data["range_start_date"] is not None
        assert data["range_end_date"] is not None

    def test_validate_program_exists(self, session):
        """POST /api/waitlist validates program exists."""
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": "00000000-0000-0000-0000-000000000000",
            "teacher_name": "Test",
            "school_name": "Test",
            "email": "test@test.cz",
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": get_future_date(30)
        })
        assert response.status_code == 404
        assert "Program nenalezen" in response.json()["detail"]

    def test_validate_participant_count_positive(self, session):
        """POST /api/waitlist validates participant_count > 0."""
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Test",
            "school_name": "Test",
            "email": "test@test.cz",
            "participant_count": 0,
            "request_type": "specific_date",
            "requested_date": get_future_date(30)
        })
        assert response.status_code == 400
        assert "Počet účastníků musí být alespoň 1" in response.json()["detail"]

    def test_validate_date_not_in_past(self, session):
        """POST /api/waitlist validates dates not in past."""
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Test",
            "school_name": "Test",
            "email": "test@test.cz",
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": get_past_date(30)
        })
        assert response.status_code == 400
        assert "minulosti" in response.json()["detail"]

    def test_validate_range_start_before_end(self, session):
        """POST /api/waitlist validates range_start < range_end."""
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Test",
            "school_name": "Test",
            "email": "test@test.cz",
            "participant_count": 10,
            "request_type": "date_range",
            "range_start_date": get_future_date(60),
            "range_end_date": get_future_date(30)
        })
        assert response.status_code == 400
        assert "Začátek rozsahu musí být před koncem" in response.json()["detail"]

    def test_block_duplicate_entry(self, session):
        """POST /api/waitlist blocks duplicate (same email + program + date + active)."""
        unique_email = f"dup_{uuid.uuid4().hex[:8]}@test.cz"
        future_date = get_future_date(90)
        
        # First entry
        response1 = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "First",
            "school_name": "First School",
            "email": unique_email,
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": future_date
        })
        assert response1.status_code == 200
        
        # Duplicate entry
        response2 = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Second",
            "school_name": "Second School",
            "email": unique_email,
            "participant_count": 20,
            "request_type": "specific_date",
            "requested_date": future_date
        })
        assert response2.status_code == 409
        assert "již máte aktivní zájem" in response2.json()["detail"]


class TestWaitlistPublicCount:
    """Tests for GET /api/waitlist/count/{program_id} (public endpoint)."""

    def test_get_waitlist_count_no_auth(self, session):
        """GET /api/waitlist/count/{program_id} returns count without auth."""
        response = session.get(f"{BASE_URL}/api/waitlist/count/{PROGRAM_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] >= 0


class TestWaitlistAdminList:
    """Tests for GET /api/waitlist (admin endpoint)."""

    def test_list_waitlist_requires_auth(self, session):
        """GET /api/waitlist requires authentication."""
        # Use fresh session without auth
        fresh_session = requests.Session()
        response = fresh_session.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 401

    def test_list_waitlist_returns_entries(self, auth_session):
        """GET /api/waitlist returns entries for admin."""
        response = auth_session.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            entry = data[0]
            assert "id" in entry
            assert "teacher_name" in entry
            assert "school_name" in entry
            assert "email" in entry
            assert "status" in entry
            assert "program_name" in entry  # Enriched field

    def test_filter_by_program_id(self, auth_session):
        """GET /api/waitlist?program_id=X filters correctly."""
        response = auth_session.get(f"{BASE_URL}/api/waitlist?program_id={PROGRAM_ID}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for entry in data:
            assert entry["program_id"] == PROGRAM_ID

    def test_filter_by_status(self, auth_session):
        """GET /api/waitlist?status=active filters correctly."""
        response = auth_session.get(f"{BASE_URL}/api/waitlist?status=active")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for entry in data:
            assert entry["status"] == "active"


class TestWaitlistAdminUpdate:
    """Tests for PATCH /api/waitlist/{id} (admin endpoint)."""

    def test_update_requires_auth(self, session):
        """PATCH /api/waitlist/{id} requires authentication."""
        fresh_session = requests.Session()
        response = fresh_session.patch(
            f"{BASE_URL}/api/waitlist/00000000-0000-0000-0000-000000000000",
            json={"status": "contacted"}
        )
        assert response.status_code == 401

    def test_update_status_and_note(self, auth_session, session):
        """PATCH /api/waitlist/{id} updates status and admin_note."""
        # First create an entry
        unique_email = f"update_{uuid.uuid4().hex[:8]}@test.cz"
        create_response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Update Test",
            "school_name": "Update School",
            "email": unique_email,
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": get_future_date(45)
        })
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        
        # Update status and note
        update_response = auth_session.patch(
            f"{BASE_URL}/api/waitlist/{entry_id}",
            json={"status": "contacted", "admin_note": "Kontaktováno telefonicky"}
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["status"] == "contacted"
        assert data["admin_note"] == "Kontaktováno telefonicky"

    def test_update_invalid_status(self, auth_session, session):
        """PATCH /api/waitlist/{id} rejects invalid status."""
        # First create an entry
        unique_email = f"invalid_{uuid.uuid4().hex[:8]}@test.cz"
        create_response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Invalid Test",
            "school_name": "Invalid School",
            "email": unique_email,
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": get_future_date(50)
        })
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        
        # Try invalid status
        update_response = auth_session.patch(
            f"{BASE_URL}/api/waitlist/{entry_id}",
            json={"status": "invalid_status"}
        )
        assert update_response.status_code == 400
        assert "Neplatný status" in update_response.json()["detail"]

    def test_update_nonexistent_entry(self, auth_session):
        """PATCH /api/waitlist/{id} returns 404 for nonexistent entry."""
        response = auth_session.patch(
            f"{BASE_URL}/api/waitlist/00000000-0000-0000-0000-000000000000",
            json={"status": "contacted"}
        )
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
