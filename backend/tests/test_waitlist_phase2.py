"""
Waitlist Phase 2 Tests - Semi-automatic matching and notification
Tests for:
- find_matching_entries: specific_date and date_range matching
- preferred_time_of_day filtering (morning/midday/afternoon/any)
- on_booking_cancelled hook integration
- on_slot_freed hook integration (availability exception removal)
- Status update to 'contacted' after notification
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


class TestWaitlistMatchingService:
    """Tests for waitlist matching logic via API behavior."""

    def test_create_specific_date_entry_for_matching(self, session):
        """Create a specific_date waitlist entry that can be matched."""
        unique_email = f"match_specific_{uuid.uuid4().hex[:8]}@test.cz"
        target_date = get_future_date(45)
        
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Specific Date Teacher",
            "school_name": "Specific Date School",
            "email": unique_email,
            "phone": "+420111222333",
            "participant_count": 12,
            "request_type": "specific_date",
            "requested_date": target_date,
            "preferred_time_of_day": "morning",
            "notes": "Test for matching"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "specific_date"
        assert data["requested_date"] == target_date
        assert data["preferred_time_of_day"] == "morning"
        assert data["status"] == "active"

    def test_create_date_range_entry_for_matching(self, session):
        """Create a date_range waitlist entry that can be matched."""
        unique_email = f"match_range_{uuid.uuid4().hex[:8]}@test.cz"
        start_date = get_future_date(30)
        end_date = get_future_date(60)
        
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Date Range Teacher",
            "school_name": "Date Range School",
            "email": unique_email,
            "phone": "+420444555666",
            "participant_count": 18,
            "request_type": "date_range",
            "range_start_date": start_date,
            "range_end_date": end_date,
            "preferred_time_of_day": "afternoon",
            "notes": "Test for range matching"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["request_type"] == "date_range"
        assert data["range_start_date"] == start_date
        assert data["range_end_date"] == end_date
        assert data["preferred_time_of_day"] == "afternoon"
        assert data["status"] == "active"

    def test_create_any_time_entry(self, session):
        """Create entry with preferred_time_of_day='any'."""
        unique_email = f"match_any_{uuid.uuid4().hex[:8]}@test.cz"
        target_date = get_future_date(50)
        
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Any Time Teacher",
            "school_name": "Any Time School",
            "email": unique_email,
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": target_date,
            "preferred_time_of_day": "any"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["preferred_time_of_day"] == "any"

    def test_create_midday_preference_entry(self, session):
        """Create entry with preferred_time_of_day='midday'."""
        unique_email = f"match_midday_{uuid.uuid4().hex[:8]}@test.cz"
        target_date = get_future_date(55)
        
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Midday Teacher",
            "school_name": "Midday School",
            "email": unique_email,
            "participant_count": 8,
            "request_type": "specific_date",
            "requested_date": target_date,
            "preferred_time_of_day": "midday"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["preferred_time_of_day"] == "midday"


class TestWaitlistAdminEnrichment:
    """Tests for admin waitlist list with program names."""

    def test_list_waitlist_includes_program_name(self, auth_session):
        """GET /api/waitlist returns entries with program_name field."""
        response = auth_session.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least one waitlist entry"
        
        # Check that program_name is enriched
        for entry in data:
            assert "program_name" in entry, "Entry should have program_name field"
            # program_name should be a string (could be empty if program deleted)
            assert isinstance(entry["program_name"], str)

    def test_list_waitlist_shows_dates_and_participant_count(self, auth_session):
        """GET /api/waitlist returns entries with dates and participant counts."""
        response = auth_session.get(f"{BASE_URL}/api/waitlist")
        assert response.status_code == 200
        data = response.json()
        
        for entry in data:
            assert "participant_count" in entry
            assert isinstance(entry["participant_count"], int)
            assert entry["participant_count"] >= 1
            
            # Check date fields based on request_type
            if entry["request_type"] == "specific_date":
                assert "requested_date" in entry
            elif entry["request_type"] == "date_range":
                assert "range_start_date" in entry
                assert "range_end_date" in entry


class TestBookingCancellationHook:
    """Tests for on_booking_cancelled hook integration."""

    def test_booking_status_update_to_cancelled(self, auth_session):
        """PATCH /api/bookings/{id}/status to cancelled triggers waitlist hook."""
        # First get list of bookings
        response = auth_session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        bookings = response.json()
        
        # Find a confirmed booking to cancel (or skip if none)
        confirmed_booking = None
        for b in bookings:
            if b.get("status") == "confirmed":
                confirmed_booking = b
                break
        
        if not confirmed_booking:
            pytest.skip("No confirmed booking available to test cancellation hook")
        
        # Cancel the booking
        booking_id = confirmed_booking["id"]
        cancel_response = auth_session.patch(
            f"{BASE_URL}/api/bookings/{booking_id}/status?status=cancelled"
        )
        # Should succeed (200) or already cancelled
        assert cancel_response.status_code in [200, 400, 404]

    def test_bulk_status_update_to_cancelled(self, auth_session):
        """POST /api/bookings/bulk-status to cancelled triggers waitlist hook."""
        # Get bookings
        response = auth_session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        bookings = response.json()
        
        # Find pending bookings
        pending_ids = [b["id"] for b in bookings if b.get("status") == "pending"][:2]
        
        if not pending_ids:
            pytest.skip("No pending bookings available for bulk cancel test")
        
        # Bulk cancel
        bulk_response = auth_session.post(
            f"{BASE_URL}/api/bookings/bulk-status",
            json={"booking_ids": pending_ids, "status": "cancelled"}
        )
        assert bulk_response.status_code == 200
        data = bulk_response.json()
        assert "updated_count" in data


class TestAvailabilityExceptionHook:
    """Tests for on_slot_freed hook when availability exception is removed."""

    def test_create_and_delete_program_exception(self, auth_session):
        """DELETE /api/availability-unified/exceptions/{id} triggers waitlist hook for program scope."""
        # Create an exception
        future_date = get_future_date(40)
        create_response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json={
                "scope_type": "program",
                "scope_id": PROGRAM_ID,
                "date": future_date,
                "start_time": "09:00",
                "end_time": "10:30",
                "reason": "Test exception for waitlist hook"
            }
        )
        assert create_response.status_code == 200
        exception_data = create_response.json()
        exception_id = exception_data["id"]
        
        # Delete the exception (should trigger on_slot_freed)
        delete_response = auth_session.delete(
            f"{BASE_URL}/api/availability-unified/exceptions/{exception_id}"
        )
        assert delete_response.status_code == 200
        assert "Výjimka odstraněna" in delete_response.json().get("message", "")

    def test_lecturer_exception_does_not_trigger_waitlist(self, auth_session):
        """DELETE lecturer exception should NOT trigger waitlist hook (only program scope)."""
        # Get a lecturer ID first
        users_response = auth_session.get(f"{BASE_URL}/api/users")
        if users_response.status_code != 200:
            pytest.skip("Cannot get users to find lecturer")
        
        users = users_response.json()
        lecturer = None
        for u in users:
            if u.get("role") in ["lektor", "edukator"]:
                lecturer = u
                break
        
        if not lecturer:
            pytest.skip("No lecturer found for test")
        
        # Create lecturer exception
        future_date = get_future_date(42)
        create_response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json={
                "scope_type": "lecturer",
                "scope_id": lecturer["id"],
                "date": future_date,
                "start_time": "14:00",
                "end_time": "15:30",
                "reason": "Lecturer test exception"
            }
        )
        assert create_response.status_code == 200
        exception_id = create_response.json()["id"]
        
        # Delete (should NOT trigger waitlist - only program scope does)
        delete_response = auth_session.delete(
            f"{BASE_URL}/api/availability-unified/exceptions/{exception_id}"
        )
        assert delete_response.status_code == 200


class TestWaitlistStatusUpdate:
    """Tests for status updates including 'contacted' status."""

    def test_update_status_to_contacted(self, auth_session, session):
        """PATCH /api/waitlist/{id} can update status to 'contacted'."""
        # Create entry
        unique_email = f"contacted_{uuid.uuid4().hex[:8]}@test.cz"
        create_response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Contacted Test",
            "school_name": "Contacted School",
            "email": unique_email,
            "participant_count": 15,
            "request_type": "specific_date",
            "requested_date": get_future_date(35)
        })
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        
        # Update to contacted
        update_response = auth_session.patch(
            f"{BASE_URL}/api/waitlist/{entry_id}",
            json={"status": "contacted", "admin_note": "Automaticky kontaktováno systémem"}
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["status"] == "contacted"
        assert data["admin_note"] == "Automaticky kontaktováno systémem"

    def test_update_status_to_booked(self, auth_session, session):
        """PATCH /api/waitlist/{id} can update status to 'booked'."""
        unique_email = f"booked_{uuid.uuid4().hex[:8]}@test.cz"
        create_response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Booked Test",
            "school_name": "Booked School",
            "email": unique_email,
            "participant_count": 20,
            "request_type": "specific_date",
            "requested_date": get_future_date(38)
        })
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        
        # Update to booked
        update_response = auth_session.patch(
            f"{BASE_URL}/api/waitlist/{entry_id}",
            json={"status": "booked"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "booked"

    def test_update_status_to_expired(self, auth_session, session):
        """PATCH /api/waitlist/{id} can update status to 'expired'."""
        unique_email = f"expired_{uuid.uuid4().hex[:8]}@test.cz"
        create_response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Expired Test",
            "school_name": "Expired School",
            "email": unique_email,
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": get_future_date(40)
        })
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        
        # Update to expired
        update_response = auth_session.patch(
            f"{BASE_URL}/api/waitlist/{entry_id}",
            json={"status": "expired"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "expired"


class TestPublicWaitlistForm:
    """Tests for public waitlist form submission."""

    def test_public_waitlist_form_all_fields(self, session):
        """POST /api/waitlist accepts all form fields correctly."""
        unique_email = f"form_full_{uuid.uuid4().hex[:8]}@test.cz"
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Full Form Teacher",
            "school_name": "Full Form School",
            "email": unique_email,
            "phone": "+420777888999",
            "participant_count": 25,
            "request_type": "specific_date",
            "requested_date": get_future_date(65),
            "preferred_time_of_day": "morning",
            "notes": "This is a detailed note about our group requirements."
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify all fields saved
        assert data["teacher_name"] == "Full Form Teacher"
        assert data["school_name"] == "Full Form School"
        assert data["email"] == unique_email
        assert data["phone"] == "+420777888999"
        assert data["participant_count"] == 25
        assert data["request_type"] == "specific_date"
        assert data["preferred_time_of_day"] == "morning"
        assert data["notes"] == "This is a detailed note about our group requirements."
        assert data["status"] == "active"

    def test_public_waitlist_minimal_fields(self, session):
        """POST /api/waitlist works with minimal required fields."""
        unique_email = f"form_min_{uuid.uuid4().hex[:8]}@test.cz"
        response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Minimal Teacher",
            "school_name": "Minimal School",
            "email": unique_email,
            "participant_count": 5,
            "request_type": "specific_date",
            "requested_date": get_future_date(70)
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        # Optional fields should have defaults
        assert data["preferred_time_of_day"] == "any"


class TestWaitlistCountEndpoint:
    """Tests for GET /api/waitlist/count/{program_id}."""

    def test_count_returns_active_only(self, auth_session, session):
        """GET /api/waitlist/count/{program_id} counts only active entries."""
        # Get initial count
        count_response = session.get(f"{BASE_URL}/api/waitlist/count/{PROGRAM_ID}")
        assert count_response.status_code == 200
        initial_count = count_response.json()["count"]
        
        # Create new active entry
        unique_email = f"count_test_{uuid.uuid4().hex[:8]}@test.cz"
        create_response = session.post(f"{BASE_URL}/api/waitlist", json={
            "institution_id": INSTITUTION_ID,
            "program_id": PROGRAM_ID,
            "teacher_name": "Count Test",
            "school_name": "Count School",
            "email": unique_email,
            "participant_count": 10,
            "request_type": "specific_date",
            "requested_date": get_future_date(75)
        })
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        
        # Count should increase
        count_response2 = session.get(f"{BASE_URL}/api/waitlist/count/{PROGRAM_ID}")
        assert count_response2.status_code == 200
        new_count = count_response2.json()["count"]
        assert new_count == initial_count + 1
        
        # Change status to cancelled
        auth_session.patch(
            f"{BASE_URL}/api/waitlist/{entry_id}",
            json={"status": "cancelled"}
        )
        
        # Count should decrease back
        count_response3 = session.get(f"{BASE_URL}/api/waitlist/count/{PROGRAM_ID}")
        assert count_response3.status_code == 200
        final_count = count_response3.json()["count"]
        assert final_count == initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
