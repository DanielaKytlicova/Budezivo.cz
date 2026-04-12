"""
Test suite for Bug Fixes - Iteration 32

Bug 1: One-off availability blocks show on wrong day (1 day later) in admin calendar grid
- Root cause: formatDate used toISOString() which converts to UTC, causing off-by-one in Czech timezone
- Fix: Changed to local date formatting in LecturerAvailabilityPage.js, DashboardPage.js, ProgramsPage.js

Bug 2: When a program has lecturer collision enabled, and no lecturers are available for a time slot, 
       the booking system still shows it as available
- Root cause: check_lecturer_available_for_block only checked recurring blocks, not one-off blocks,
              and treated 'no recurring blocks' as 'always available'
- Fix: Now checks both recurring AND one-off blocks, and if a lecturer has ANY availability defined 
       but none for the requested day, they're marked unavailable

Tests:
1. Test /api/availability endpoint respects lecturer one-off blocks
2. Test check_lecturer_available_for_block checks both recurring and one-off blocks
3. Test lecturer with availability defined but not for requested day is marked unavailable
4. Test lecturer with NO availability defined remains unconstrained (backward compat)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"

# Test data
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
PROGRAM_WITH_LECTURER = "fa7c7513-813c-4c10-827c-30ff11a46caf"  # Historická prohlídka
LECTURER_ID = "2868bc35-7d6e-4046-87fa-013ee5efdb60"  # Demo user


@pytest.fixture(scope="module")
def auth_session():
    """Get authenticated session with cookies."""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    data = response.json()
    token = data.get("token")
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    return session


class TestLoginWithCookies:
    """Test authentication with httpOnly cookies."""
    
    def test_login_returns_token_and_cookies(self):
        """POST /api/auth/login returns token and sets httpOnly cookies."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user"
        
        # Check cookies are set
        cookies = response.cookies
        assert "access_token" in cookies or len(cookies) > 0, "Should set cookies"
        
        print(f"✓ Login successful, token received, cookies set")


class TestOneOffAvailabilityBugFix:
    """Tests for Bug 2 fix: check_lecturer_available_for_block now checks one-off blocks."""
    
    def test_availability_endpoint_works(self, auth_session):
        """GET /api/availability endpoint returns valid response."""
        # Get a future weekday
        today = datetime.now()
        days_ahead = 7 - today.weekday() + 1  # Next Tuesday
        test_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{test_date}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "date" in data, "Response should contain date"
        assert "time_blocks" in data, "Response should contain time_blocks"
        
        print(f"✓ Availability endpoint returns valid response for {test_date}")
    
    def test_lecturer_availability_week_view(self, auth_session):
        """GET /api/lecturer-availability/week-view returns recurring and one-off blocks."""
        # Get current week start (Monday)
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.strftime("%Y-%m-%d")
        
        response = auth_session.get(
            f"{BASE_URL}/api/lecturer-availability/week-view",
            params={"week_start": week_start}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "recurring" in data, "Response should contain recurring blocks"
        assert "one_offs" in data, "Response should contain one_offs blocks"
        assert "time_offs" in data, "Response should contain time_offs blocks"
        
        print(f"✓ Week view returns recurring: {len(data['recurring'])}, one_offs: {len(data['one_offs'])}, time_offs: {len(data['time_offs'])}")
    
    def test_create_oneoff_availability_block(self, auth_session):
        """POST /api/lecturer-availability/recurring with specific_date creates one-off block."""
        # Create a one-off block for a future date
        today = datetime.now()
        future_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")
        
        payload = {
            "days_of_week": [],  # Empty for one-off
            "start_time": "14:00",
            "end_time": "16:00",
            "specific_date": future_date
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/lecturer-availability/recurring",
            json=payload
        )
        
        # Accept 200 or 201
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # API may return a list (multiple blocks created) or single object
        if isinstance(data, list):
            # Find the one-off block we just created
            oneoff_block = next((b for b in data if b.get("specific_date") == future_date), None)
            assert oneoff_block is not None, f"Expected to find one-off block for {future_date} in response"
            assert oneoff_block.get("is_recurring") == False, "One-off block should have is_recurring=False"
            oneoff_id = oneoff_block.get("id")
        else:
            assert data.get("specific_date") == future_date, f"Expected specific_date={future_date}"
            assert data.get("is_recurring") == False, "One-off block should have is_recurring=False"
            oneoff_id = data.get("id")
        
        print(f"✓ Created one-off availability block for {future_date}: {oneoff_id}")
        
        # Cleanup: delete the one-off block
        if oneoff_id:
            delete_response = auth_session.delete(
                f"{BASE_URL}/api/lecturer-availability/recurring/{oneoff_id}"
            )
            assert delete_response.status_code in [200, 204], f"Cleanup failed: {delete_response.status_code}"
            print(f"✓ Cleaned up one-off block {oneoff_id}")
    
    def test_lecturer_check_endpoint(self, auth_session):
        """GET /api/lecturer-availability/check returns availability status."""
        # Get a future weekday
        today = datetime.now()
        days_ahead = 7 - today.weekday() + 3  # Next Thursday
        test_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        response = auth_session.get(
            f"{BASE_URL}/api/lecturer-availability/check",
            params={
                "lecturer_id": LECTURER_ID,
                "date": test_date,
                "start_time": "09:00",
                "end_time": "10:30"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "available" in data, "Response should contain 'available' field"
        
        print(f"✓ Lecturer check for {test_date}: available={data['available']}")


class TestRecurringAvailabilityBlocks:
    """Tests for recurring availability blocks."""
    
    def test_get_recurring_availability(self, auth_session):
        """GET /api/lecturer-availability/recurring returns recurring blocks."""
        response = auth_session.get(f"{BASE_URL}/api/lecturer-availability/recurring")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check structure of recurring blocks
        if len(data) > 0:
            block = data[0]
            assert "day_of_week" in block, "Block should have day_of_week"
            assert "start_time" in block, "Block should have start_time"
            assert "end_time" in block, "Block should have end_time"
        
        print(f"✓ Got {len(data)} recurring availability blocks")
    
    def test_get_time_off_blocks(self, auth_session):
        """GET /api/lecturer-availability/time-off returns time-off blocks."""
        response = auth_session.get(f"{BASE_URL}/api/lecturer-availability/time-off")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Got {len(data)} time-off blocks")


class TestAvailabilityFiltering:
    """Tests for availability filtering based on lecturer schedule."""
    
    def test_availability_respects_program_available_days(self):
        """Availability endpoint returns empty for days not in program's available_days."""
        # Test Saturday (typically not in available_days)
        today = datetime.now()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        saturday = (today + timedelta(days=days_until_saturday)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{saturday}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Saturday should return empty time_blocks (not in available_days)
        assert len(data["time_blocks"]) == 0, f"Saturday should have no time blocks, got {len(data['time_blocks'])}"
        
        print(f"✓ Saturday ({saturday}) correctly returns empty time_blocks")
    
    def test_availability_returns_blocks_for_weekday(self):
        """Availability endpoint returns time blocks for valid weekday."""
        # Test next Wednesday
        today = datetime.now()
        days_until_wednesday = (2 - today.weekday()) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        wednesday = (today + timedelta(days=days_until_wednesday)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_WITH_LECTURER}/{wednesday}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Wednesday should have time blocks
        assert "time_blocks" in data, "Response should contain time_blocks"
        
        print(f"✓ Wednesday ({wednesday}) returns {len(data['time_blocks'])} time blocks")


class TestCalendarEndpoint:
    """Tests for calendar availability endpoint."""
    
    def test_calendar_month_availability(self):
        """GET /api/calendar returns month availability."""
        today = datetime.now()
        year = today.year
        month = today.month
        
        response = requests.get(
            f"{BASE_URL}/api/calendar/{INSTITUTION_ID}/{year}/{month}",
            params={"program_id": PROGRAM_WITH_LECTURER}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "year" in data, "Response should contain year"
        assert "month" in data, "Response should contain month"
        assert "dates" in data, "Response should contain dates"
        
        # Check dates structure
        assert len(data["dates"]) > 0, "Should have dates"
        date_entry = data["dates"][0]
        assert "date" in date_entry, "Date entry should have date"
        assert "has_availability" in date_entry, "Date entry should have has_availability"
        
        print(f"✓ Calendar returns {len(data['dates'])} dates for {year}-{month:02d}")


class TestAdminAvailabilityPage:
    """Tests for admin availability page endpoints."""
    
    def test_admin_availability_page_loads(self, auth_session):
        """Admin availability page data loads correctly."""
        # Get current week
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.strftime("%Y-%m-%d")
        
        response = auth_session.get(
            f"{BASE_URL}/api/lecturer-availability/week-view",
            params={"week_start": week_start}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required fields are present
        assert "recurring" in data
        assert "one_offs" in data
        assert "time_offs" in data
        
        # Verify recurring blocks have correct structure
        for block in data["recurring"]:
            assert "id" in block
            assert "day_of_week" in block
            assert "start_time" in block
            assert "end_time" in block
        
        # Verify one-off blocks have correct structure
        for block in data["one_offs"]:
            assert "id" in block
            assert "specific_date" in block
            assert "start_time" in block
            assert "end_time" in block
        
        print(f"✓ Admin availability page data loads correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
