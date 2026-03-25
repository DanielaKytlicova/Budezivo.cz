"""
Test suite for Lecturer Availability integration with Public Booking Flow.
Tests that availability endpoint correctly filters time blocks based on assigned lecturer's availability.

Key scenarios:
- Program with assigned_lecturer_id: blocks filtered by lecturer availability
- Program without assigned_lecturer_id: all blocks shown as available
- Lecturer blockage (time-off): status = 'unavailable'
- Lecturer available: status = 'available'
- No recurring availability for day: status = 'unavailable'
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"

# Test data from context
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
PROGRAM_WITH_LECTURER = "fa7c7513-813c-4c10-827c-30ff11a46caf"  # Historická prohlídka
PROGRAM_WITHOUT_LECTURER = "5638d57c-b0e9-46a5-af47-ed6b61daf90c"  # Testovací multi program
LECTURER_ID = "2868bc35-7d6e-4046-87fa-013ee5efdb60"  # Demo user

# Dates for testing
DATE_WITH_BLOCKAGE = "2026-03-27"  # Friday with blockage 09:00-11:00
DATE_AVAILABLE = "2026-03-26"  # Thursday - lecturer available
DATE_SATURDAY = "2026-03-28"  # Saturday - not in available_days
DATE_SUNDAY = "2026-03-29"  # Sunday - not in recurring availability


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for testing."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    data = response.json()
    return data.get("token")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Get headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestAvailabilityEndpointPublic:
    """Tests for public availability endpoint - no auth required."""
    
    def test_availability_returns_unavailable_when_lecturer_has_blockage(self):
        """GET /api/availability returns 'unavailable' when assigned lecturer has blockage."""
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{DATE_WITH_BLOCKAGE}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["date"] == DATE_WITH_BLOCKAGE
        assert len(data["time_blocks"]) == 1, "Should return exactly 1 time block (09:00-10:30)"
        
        block = data["time_blocks"][0]
        assert block["time"] == "09:00-10:30"
        assert block["status"] == "unavailable", f"Expected 'unavailable', got '{block['status']}'"
        print(f"✓ Block {block['time']} correctly shows status='unavailable' due to lecturer blockage")
    
    def test_availability_returns_available_when_lecturer_is_free(self):
        """GET /api/availability returns 'available' when assigned lecturer is available."""
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{DATE_AVAILABLE}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["date"] == DATE_AVAILABLE
        assert len(data["time_blocks"]) == 1, "Should return exactly 1 time block (09:00-10:30)"
        
        block = data["time_blocks"][0]
        assert block["time"] == "09:00-10:30"
        assert block["status"] == "available", f"Expected 'available', got '{block['status']}'"
        print(f"✓ Block {block['time']} correctly shows status='available' when lecturer is free")
    
    def test_availability_returns_empty_for_unavailable_day(self):
        """GET /api/availability returns empty time_blocks for days not in available_days."""
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{DATE_SATURDAY}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["date"] == DATE_SATURDAY
        assert len(data["time_blocks"]) == 0, "Should return empty time_blocks for Saturday"
        print(f"✓ Saturday correctly returns empty time_blocks (not in available_days)")
    
    def test_availability_returns_only_program_time_blocks(self):
        """GET /api/availability returns only program's time_blocks (no extra blocks generated)."""
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{DATE_AVAILABLE}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Program has time_blocks: ["09:00-10:30"]
        assert len(data["time_blocks"]) == 1, f"Expected 1 block, got {len(data['time_blocks'])}"
        assert data["time_blocks"][0]["time"] == "09:00-10:30"
        print(f"✓ Only program's defined time_blocks are returned (no extra blocks)")
    
    def test_program_without_lecturer_shows_all_available(self):
        """Program without assigned_lecturer_id shows all blocks as available."""
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITHOUT_LECTURER}/{DATE_WITH_BLOCKAGE}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["date"] == DATE_WITH_BLOCKAGE
        assert len(data["time_blocks"]) >= 1, "Should return at least 1 time block"
        
        # All blocks should be available (no lecturer filter)
        for block in data["time_blocks"]:
            assert block["status"] == "available", f"Block {block['time']} should be 'available', got '{block['status']}'"
        print(f"✓ Program without assigned_lecturer_id shows all blocks as available")


class TestLecturerAvailabilityCheck:
    """Tests for collision_service.check_lecturer_available_for_block function."""
    
    def test_check_lecturer_available_in_recurring_block(self, headers):
        """Lecturer is available when time is within recurring availability."""
        # Use the availability check endpoint
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/check",
            params={
                "lecturer_id": LECTURER_ID,
                "date": DATE_AVAILABLE,  # Thursday
                "start_time": "09:00",
                "end_time": "10:30"
            },
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["available"] == True, f"Expected available=True, got {data}"
        print(f"✓ Lecturer available check returns True for time within recurring block")
    
    def test_check_lecturer_unavailable_with_blockage(self, headers):
        """Lecturer is unavailable when blockage overlaps."""
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/check",
            params={
                "lecturer_id": LECTURER_ID,
                "date": DATE_WITH_BLOCKAGE,  # Friday with blockage 09:00-11:00
                "start_time": "09:00",
                "end_time": "10:30"
            },
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["available"] == False, f"Expected available=False, got {data}"
        print(f"✓ Lecturer available check returns False when blockage overlaps")
    
    def test_check_lecturer_unavailable_no_recurring(self, headers):
        """Lecturer is unavailable when no recurring availability for that day."""
        # Find a Sunday (day 6) - no recurring availability set
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/check",
            params={
                "lecturer_id": LECTURER_ID,
                "date": DATE_SUNDAY,  # Sunday
                "start_time": "09:00",
                "end_time": "10:30"
            },
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["available"] == False, f"Expected available=False, got {data}"
        print(f"✓ Lecturer available check returns False when no recurring availability")


class TestTimeBlockFormatHandling:
    """Tests for collision_service handling of HH:MM and HH:MM-HH:MM formats."""
    
    def test_availability_handles_range_format(self):
        """Availability endpoint handles HH:MM-HH:MM format correctly."""
        # Program with time_blocks: ["09:00-10:30"]
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{DATE_AVAILABLE}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["time_blocks"]) == 1
        assert "-" in data["time_blocks"][0]["time"], "Time block should be in HH:MM-HH:MM format"
        print(f"✓ HH:MM-HH:MM format handled correctly")
    
    def test_availability_handles_simple_time_format(self):
        """Availability endpoint handles HH:MM format correctly."""
        # Program without lecturer has time_blocks: ["09:00"]
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITHOUT_LECTURER}/{DATE_AVAILABLE}"
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["time_blocks"]) >= 1
        # Check that simple HH:MM format is handled
        block = data["time_blocks"][0]
        assert block["time"] == "09:00", f"Expected '09:00', got '{block['time']}'"
        print(f"✓ HH:MM format handled correctly")


class TestProgramAssignedLecturer:
    """Tests for program assigned_lecturer_id field."""
    
    def test_program_has_assigned_lecturer(self, headers):
        """Program with assigned lecturer returns assigned_lecturer_id."""
        response = requests.get(
            f"{BASE_URL}/api/programs/{PROGRAM_WITH_LECTURER}",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("assigned_lecturer_id") == LECTURER_ID, \
            f"Expected assigned_lecturer_id={LECTURER_ID}, got {data.get('assigned_lecturer_id')}"
        print(f"✓ Program correctly returns assigned_lecturer_id")
    
    def test_program_without_assigned_lecturer(self, headers):
        """Program without assigned lecturer returns null assigned_lecturer_id."""
        response = requests.get(
            f"{BASE_URL}/api/programs/{PROGRAM_WITHOUT_LECTURER}",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("assigned_lecturer_id") is None, \
            f"Expected assigned_lecturer_id=None, got {data.get('assigned_lecturer_id')}"
        print(f"✓ Program without lecturer correctly returns null assigned_lecturer_id")


class TestLecturerRecurringAvailability:
    """Tests for lecturer recurring availability data."""
    
    def test_lecturer_has_recurring_availability(self, headers):
        """Lecturer has recurring availability Mon-Fri 08:00-12:00."""
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/recurring",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should have 5 blocks (Mon-Fri)
        assert len(data) >= 5, f"Expected at least 5 recurring blocks, got {len(data)}"
        
        # Check that Mon-Fri (0-4) are covered
        days_covered = {block["day_of_week"] for block in data}
        for day in range(5):  # 0=Monday to 4=Friday
            assert day in days_covered, f"Day {day} should have recurring availability"
        
        print(f"✓ Lecturer has recurring availability for Mon-Fri")
    
    def test_lecturer_has_time_off_blockage(self, headers):
        """Lecturer has time-off blockage on 2026-03-27 09:00-11:00."""
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/time-off",
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Find the blockage for 2026-03-27
        blockage = next((b for b in data if b["start_date"] == DATE_WITH_BLOCKAGE), None)
        assert blockage is not None, f"Expected blockage on {DATE_WITH_BLOCKAGE}"
        assert blockage["start_time"] == "09:00"
        assert blockage["end_time"] == "11:00"
        
        print(f"✓ Lecturer has time-off blockage on {DATE_WITH_BLOCKAGE} 09:00-11:00")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
