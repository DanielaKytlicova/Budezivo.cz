"""
Test ICS Calendar Export Endpoints for Outlook Integration
Tests: /api/calendar/institution/{id}.ics, /api/calendar/program/{id}.ics, /api/calendar/reservation/{id}.ics
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Demo institution ID from test context
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for authenticated endpoints."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def program_id(auth_token):
    """Get a valid program ID from the institution."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
    if response.status_code == 200:
        programs = response.json()
        if programs and len(programs) > 0:
            return programs[0]["id"]
    pytest.skip("No programs found - skipping program ICS tests")


@pytest.fixture(scope="module")
def reservation_id(auth_token):
    """Get a valid reservation ID from the institution."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
    if response.status_code == 200:
        bookings = response.json()
        if bookings and len(bookings) > 0:
            return bookings[0]["id"]
    pytest.skip("No reservations found - skipping reservation ICS tests")


class TestInstitutionICSFeed:
    """Tests for GET /api/calendar/institution/{id}.ics"""
    
    def test_institution_ics_returns_valid_ics(self):
        """ICS feed returns valid iCalendar format with VCALENDAR wrapper."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check Content-Type header
        content_type = response.headers.get("Content-Type", "")
        assert "text/calendar" in content_type, f"Expected text/calendar, got {content_type}"
        
        # Check Content-Disposition header (attachment)
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Expected attachment header, got {content_disp}"
        assert ".ics" in content_disp, f"Expected .ics filename in header"
        
        # Validate ICS content structure
        ics_content = response.text
        assert "BEGIN:VCALENDAR" in ics_content, "Missing VCALENDAR begin"
        assert "END:VCALENDAR" in ics_content, "Missing VCALENDAR end"
        assert "VERSION:2.0" in ics_content, "Missing VERSION:2.0"
        assert "PRODID:" in ics_content, "Missing PRODID"
    
    def test_institution_ics_contains_vevent(self):
        """ICS feed contains VEVENT components for reservations."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        # Should have at least one VEVENT (demo institution has ~30 reservations)
        assert "BEGIN:VEVENT" in ics_content, "No VEVENT found - expected reservations"
        assert "END:VEVENT" in ics_content, "Missing VEVENT end"
    
    def test_institution_ics_has_correct_timezone(self):
        """ICS feed uses Europe/Prague timezone."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        # Check timezone is set
        assert "Europe/Prague" in ics_content or "X-WR-TIMEZONE:Europe/Prague" in ics_content, \
            "Expected Europe/Prague timezone"
    
    def test_institution_ics_vevent_has_required_fields(self):
        """VEVENT components have required fields: UID, DTSTART, DTEND, SUMMARY."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        # Check for required VEVENT fields
        assert "UID:" in ics_content, "Missing UID in VEVENT"
        assert "DTSTART" in ics_content, "Missing DTSTART in VEVENT"
        assert "DTEND" in ics_content, "Missing DTEND in VEVENT"
        assert "SUMMARY:" in ics_content, "Missing SUMMARY in VEVENT"
    
    def test_institution_ics_with_status_filter(self):
        """ICS feed supports status filter: ?status=confirmed."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics?status=confirmed")
        
        assert response.status_code == 200
        
        # Check valid ICS structure
        ics_content = response.text
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
    
    def test_institution_ics_nonexistent_returns_404(self):
        """Non-existent institution ID returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{fake_id}.ics")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestProgramICSFeed:
    """Tests for GET /api/calendar/program/{id}.ics"""
    
    def test_program_ics_returns_valid_ics(self, program_id):
        """Program ICS feed returns valid iCalendar format."""
        response = requests.get(f"{BASE_URL}/api/calendar/program/{program_id}.ics")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check headers
        content_type = response.headers.get("Content-Type", "")
        assert "text/calendar" in content_type
        
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        
        # Validate ICS structure
        ics_content = response.text
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
    
    def test_program_ics_nonexistent_returns_404(self):
        """Non-existent program ID returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{BASE_URL}/api/calendar/program/{fake_id}.ics")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestReservationICSDownload:
    """Tests for GET /api/calendar/reservation/{id}.ics"""
    
    def test_reservation_ics_returns_valid_ics(self, reservation_id):
        """Single reservation ICS download returns valid iCalendar."""
        response = requests.get(f"{BASE_URL}/api/calendar/reservation/{reservation_id}.ics")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check headers
        content_type = response.headers.get("Content-Type", "")
        assert "text/calendar" in content_type
        
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert ".ics" in content_disp
        
        # Validate ICS structure
        ics_content = response.text
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
    
    def test_reservation_ics_has_correct_uid(self, reservation_id):
        """Reservation ICS has UID containing reservation ID."""
        response = requests.get(f"{BASE_URL}/api/calendar/reservation/{reservation_id}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        # UID should contain reservation ID
        assert f"UID:{reservation_id}@budezivo.cz" in ics_content, \
            f"Expected UID with reservation ID, got: {ics_content[:500]}"
    
    def test_reservation_ics_has_description_and_location(self, reservation_id):
        """Reservation ICS has DESCRIPTION and LOCATION fields."""
        response = requests.get(f"{BASE_URL}/api/calendar/reservation/{reservation_id}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        # Should have description with booking details
        assert "DESCRIPTION:" in ics_content, "Missing DESCRIPTION in VEVENT"
    
    def test_reservation_ics_nonexistent_returns_404(self):
        """Non-existent reservation ID returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{BASE_URL}/api/calendar/reservation/{fake_id}.ics")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestICSContentValidation:
    """Additional validation tests for ICS content quality."""
    
    def test_ics_dtstart_dtend_format(self):
        """DTSTART and DTEND use proper datetime format with timezone."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        # DTSTART should have timezone info (TZID or Z suffix)
        # Format: DTSTART;TZID=Europe/Prague:20260115T090000 or DTSTART:20260115T090000Z
        import re
        dtstart_pattern = r'DTSTART[;:]'
        assert re.search(dtstart_pattern, ics_content), "DTSTART format not found"
    
    def test_ics_status_mapping(self):
        """ICS STATUS field maps correctly from reservation status."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        # Should have STATUS field (CONFIRMED, TENTATIVE, or CANCELLED)
        assert "STATUS:" in ics_content, "Missing STATUS in VEVENT"
    
    def test_ics_calname_set(self):
        """ICS has X-WR-CALNAME for calendar display name."""
        response = requests.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        
        assert response.status_code == 200
        ics_content = response.text
        
        assert "X-WR-CALNAME:" in ics_content, "Missing X-WR-CALNAME"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
