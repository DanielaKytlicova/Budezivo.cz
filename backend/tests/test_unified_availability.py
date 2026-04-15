"""
Test suite for Unified Availability System.
Tests: availability_service.py, unified_availability.py routes, collision_service.py exception integration.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
PROGRAM_ID = "128d6178-e199-4cc5-b247-0e42fe1955d7"  # Čteme obrazy
TEST_DATE = "2026-04-15"  # Wednesday


@pytest.fixture(scope="module")
def auth_session():
    """Create authenticated session with httpOnly cookies."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login to get cookies
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return session


@pytest.fixture(scope="module")
def cleanup_exceptions(auth_session):
    """Cleanup any test exceptions after tests complete."""
    created_exception_ids = []
    yield created_exception_ids
    
    # Teardown: delete all created exceptions
    for exc_id in created_exception_ids:
        try:
            auth_session.delete(f"{BASE_URL}/api/availability-unified/exceptions/{exc_id}")
        except:
            pass


class TestProgramSlotsAPI:
    """Tests for GET /api/availability-unified/program/{id}/slots endpoint."""
    
    def test_get_program_slots_returns_200(self, auth_session):
        """Verify endpoint returns 200 with valid program and date."""
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={TEST_DATE}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "program_id" in data
        assert "date" in data
        assert "slots" in data
        assert data["program_id"] == PROGRAM_ID
        assert data["date"] == TEST_DATE
    
    def test_program_slots_have_required_fields(self, auth_session):
        """Verify each slot has time, status, and reason fields."""
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={TEST_DATE}"
        )
        assert response.status_code == 200
        data = response.json()
        
        for slot in data["slots"]:
            assert "time" in slot, "Slot missing 'time' field"
            assert "status" in slot, "Slot missing 'status' field"
            assert "reason" in slot, "Slot missing 'reason' field"
    
    def test_program_slots_valid_status_values(self, auth_session):
        """Verify slot status is one of the expected values."""
        valid_statuses = [
            "available", "booked", "blocked_exception", "blocked_lecturer",
            "blocked_room", "blocked_parallel", "blocked_program", "outside_base_availability"
        ]
        
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={TEST_DATE}"
        )
        assert response.status_code == 200
        data = response.json()
        
        for slot in data["slots"]:
            assert slot["status"] in valid_statuses, f"Invalid status: {slot['status']}"
    
    def test_program_slots_weekday_returns_slots(self, auth_session):
        """Wednesday (2026-04-15) should return slots for program with weekday availability."""
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date=2026-04-15"
        )
        assert response.status_code == 200
        data = response.json()
        
        # Program 'Čteme obrazy' has time_blocks configured, should return slots
        assert len(data["slots"]) >= 1, "Expected at least 1 slot on Wednesday"
    
    def test_program_slots_invalid_program_returns_empty(self, auth_session):
        """Invalid program ID should return empty slots list."""
        fake_id = str(uuid.uuid4())
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{fake_id}/slots?date={TEST_DATE}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["slots"] == []


class TestLecturerSlotsAPI:
    """Tests for GET /api/availability-unified/lecturer/{id}/slots endpoint."""
    
    def test_get_lecturer_slots_returns_200(self, auth_session):
        """Verify endpoint returns 200 with valid lecturer ID."""
        # Get a lecturer ID from team
        team_response = auth_session.get(f"{BASE_URL}/api/team")
        assert team_response.status_code == 200
        team = team_response.json()
        
        lecturer = next((m for m in team if m["role"] in ["lektor", "edukator", "admin"]), None)
        if not lecturer:
            pytest.skip("No lecturer found in team")
        
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/lecturer/{lecturer['id']}/slots?date={TEST_DATE}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "lecturer_id" in data
        assert "date" in data
        assert "slots" in data


class TestExceptionsAPI:
    """Tests for /api/availability-unified/exceptions CRUD endpoints."""
    
    def test_list_exceptions_returns_200(self, auth_session):
        """Verify GET /exceptions returns 200."""
        response = auth_session.get(f"{BASE_URL}/api/availability-unified/exceptions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_list_exceptions_with_filters(self, auth_session):
        """Verify filtering by scope_type and scope_id works."""
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/exceptions?scope_type=program&scope_id={PROGRAM_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned exceptions should match the filter
        for exc in data:
            assert exc["scope_type"] == "program"
            assert exc["scope_id"] == PROGRAM_ID
    
    def test_create_exception_returns_created(self, auth_session, cleanup_exceptions):
        """Verify POST /exceptions creates exception and returns it."""
        payload = {
            "scope_type": "program",
            "scope_id": PROGRAM_ID,
            "date": "2026-04-16",  # Thursday
            "start_time": "09:00",
            "end_time": "10:00",
            "reason": "TEST_pytest_exception"
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["scope_type"] == "program"
        assert data["scope_id"] == PROGRAM_ID
        assert data["date"] == "2026-04-16"
        assert data["start_time"] == "09:00"
        assert data["end_time"] == "10:00"
        assert data["reason"] == "TEST_pytest_exception"
        
        # Track for cleanup
        cleanup_exceptions.append(data["id"])
    
    def test_create_exception_invalid_scope_type(self, auth_session):
        """Verify invalid scope_type returns 400."""
        payload = {
            "scope_type": "invalid",
            "scope_id": PROGRAM_ID,
            "date": "2026-04-16",
            "start_time": "09:00",
            "end_time": "10:00"
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json=payload
        )
        assert response.status_code == 400
    
    def test_delete_exception_returns_success(self, auth_session, cleanup_exceptions):
        """Verify DELETE /exceptions/{id} removes exception."""
        # First create an exception
        payload = {
            "scope_type": "program",
            "scope_id": PROGRAM_ID,
            "date": "2026-04-17",
            "start_time": "10:00",
            "end_time": "11:00",
            "reason": "TEST_to_delete"
        }
        
        create_response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json=payload
        )
        assert create_response.status_code == 200
        exc_id = create_response.json()["id"]
        
        # Delete it
        delete_response = auth_session.delete(
            f"{BASE_URL}/api/availability-unified/exceptions/{exc_id}"
        )
        assert delete_response.status_code == 200
        assert "message" in delete_response.json()
        
        # Verify it's gone
        list_response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/exceptions?scope_type=program&scope_id={PROGRAM_ID}&date=2026-04-17"
        )
        exceptions = list_response.json()
        assert not any(e["id"] == exc_id for e in exceptions)
    
    def test_delete_nonexistent_exception_returns_404(self, auth_session):
        """Verify deleting non-existent exception returns 404."""
        fake_id = str(uuid.uuid4())
        response = auth_session.delete(
            f"{BASE_URL}/api/availability-unified/exceptions/{fake_id}"
        )
        assert response.status_code == 404


class TestExceptionBlocksSlot:
    """Tests verifying exception blocks slot status correctly."""
    
    def test_exception_changes_slot_to_blocked(self, auth_session, cleanup_exceptions):
        """After creating exception, slot status should change to blocked_exception."""
        test_date = "2026-04-20"  # Monday
        
        # Get initial slots
        initial_response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={test_date}"
        )
        assert initial_response.status_code == 200
        initial_slots = initial_response.json()["slots"]
        
        if not initial_slots:
            pytest.skip("No slots available on test date")
        
        # Find an available slot
        available_slot = next((s for s in initial_slots if s["status"] == "available"), None)
        if not available_slot:
            pytest.skip("No available slots to test")
        
        start_time, end_time = available_slot["time"].split("-")
        
        # Create exception for this slot
        payload = {
            "scope_type": "program",
            "scope_id": PROGRAM_ID,
            "date": test_date,
            "start_time": start_time,
            "end_time": end_time,
            "reason": "TEST_blocking_slot"
        }
        
        create_response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json=payload
        )
        assert create_response.status_code == 200
        exc_id = create_response.json()["id"]
        cleanup_exceptions.append(exc_id)
        
        # Verify slot is now blocked
        after_response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={test_date}"
        )
        assert after_response.status_code == 200
        after_slots = after_response.json()["slots"]
        
        blocked_slot = next((s for s in after_slots if s["time"] == available_slot["time"]), None)
        assert blocked_slot is not None
        assert blocked_slot["status"] == "blocked_exception", f"Expected blocked_exception, got {blocked_slot['status']}"
        assert blocked_slot["reason"] == "TEST_blocking_slot"
    
    def test_removing_exception_restores_slot(self, auth_session):
        """After deleting exception, slot should return to available."""
        test_date = "2026-04-21"  # Tuesday
        
        # Get initial slots
        initial_response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={test_date}"
        )
        initial_slots = initial_response.json()["slots"]
        
        if not initial_slots:
            pytest.skip("No slots available on test date")
        
        available_slot = next((s for s in initial_slots if s["status"] == "available"), None)
        if not available_slot:
            pytest.skip("No available slots to test")
        
        start_time, end_time = available_slot["time"].split("-")
        
        # Create exception
        payload = {
            "scope_type": "program",
            "scope_id": PROGRAM_ID,
            "date": test_date,
            "start_time": start_time,
            "end_time": end_time,
            "reason": "TEST_temp_block"
        }
        
        create_response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json=payload
        )
        exc_id = create_response.json()["id"]
        
        # Delete exception
        auth_session.delete(f"{BASE_URL}/api/availability-unified/exceptions/{exc_id}")
        
        # Verify slot is available again
        final_response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={test_date}"
        )
        final_slots = final_response.json()["slots"]
        
        restored_slot = next((s for s in final_slots if s["time"] == available_slot["time"]), None)
        assert restored_slot is not None
        assert restored_slot["status"] == "available", f"Expected available, got {restored_slot['status']}"


class TestCollisionServiceExceptionIntegration:
    """Tests verifying exception check is integrated into collision_service."""
    
    def test_booking_blocked_when_program_has_exception(self, auth_session, cleanup_exceptions):
        """Creating booking should fail when program has exception on that slot."""
        test_date = "2026-04-22"  # Wednesday
        
        # Get available slot
        slots_response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={test_date}"
        )
        slots = slots_response.json()["slots"]
        
        available_slot = next((s for s in slots if s["status"] == "available"), None)
        if not available_slot:
            pytest.skip("No available slots to test")
        
        start_time, end_time = available_slot["time"].split("-")
        
        # Create exception for this slot
        exc_payload = {
            "scope_type": "program",
            "scope_id": PROGRAM_ID,
            "date": test_date,
            "start_time": start_time,
            "end_time": end_time,
            "reason": "TEST_booking_block"
        }
        
        exc_response = auth_session.post(
            f"{BASE_URL}/api/availability-unified/exceptions",
            json=exc_payload
        )
        exc_id = exc_response.json()["id"]
        cleanup_exceptions.append(exc_id)
        
        # Try to create booking on blocked slot
        booking_payload = {
            "program_id": PROGRAM_ID,
            "date": test_date,
            "time_block": available_slot["time"],
            "school_name": "TEST_School",
            "group_type": "zs1_7_12",
            "age_or_class": "3. třída",
            "num_students": 20,
            "contact_name": "Test Teacher",
            "contact_email": "test@test.cz",
            "contact_phone": "+420123456789",
            "gdpr_consent": True,
            "terms_accepted": True
        }
        
        booking_response = auth_session.post(
            f"{BASE_URL}/api/bookings",
            json=booking_payload
        )
        
        # Should be blocked (400 or 409)
        assert booking_response.status_code in [400, 409], \
            f"Expected booking to be blocked, got {booking_response.status_code}: {booking_response.text}"
        
        # Error message should mention exception/closure
        error_text = booking_response.text.lower()
        assert "uzavřen" in error_text or "exception" in error_text or "nedostupn" in error_text, \
            f"Error should mention closure: {booking_response.text}"


class TestProgramPersonalToggle:
    """Tests for Program/Personal view mode functionality."""
    
    def test_program_view_uses_program_endpoint(self, auth_session):
        """Program view should call /program/{id}/slots endpoint."""
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/program/{PROGRAM_ID}/slots?date={TEST_DATE}"
        )
        assert response.status_code == 200
        assert "program_id" in response.json()
    
    def test_personal_view_uses_lecturer_endpoint(self, auth_session):
        """Personal view should call /lecturer/{id}/slots endpoint."""
        # Get a lecturer
        team_response = auth_session.get(f"{BASE_URL}/api/team")
        team = team_response.json()
        lecturer = next((m for m in team if m["role"] in ["lektor", "edukator"]), None)
        
        if not lecturer:
            pytest.skip("No lecturer found")
        
        response = auth_session.get(
            f"{BASE_URL}/api/availability-unified/lecturer/{lecturer['id']}/slots?date={TEST_DATE}"
        )
        assert response.status_code == 200
        assert "lecturer_id" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
