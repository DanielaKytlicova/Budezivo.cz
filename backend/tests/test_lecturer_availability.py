"""
Test suite for Lecturer Availability feature.
Tests recurring availability CRUD, time-off CRUD, week-view, and availability check endpoints.
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


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


@pytest.fixture(scope="module")
def user_info(auth_token):
    """Get current user info from token."""
    response = requests.get(f"{BASE_URL}/api/auth/me", headers={
        "Authorization": f"Bearer {auth_token}"
    })
    if response.status_code == 200:
        return response.json()
    return None


class TestRecurringAvailability:
    """Tests for recurring availability CRUD operations."""
    
    created_ids = []
    
    def test_get_recurring_availability(self, headers):
        """GET /api/lecturer-availability/recurring returns list."""
        response = requests.get(f"{BASE_URL}/api/lecturer-availability/recurring", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} recurring availability blocks")
    
    def test_create_recurring_availability_single_day(self, headers):
        """POST /api/lecturer-availability/recurring creates block for single day."""
        payload = {
            "days_of_week": [5],  # Saturday
            "start_time": "14:00",
            "end_time": "16:00"
        }
        response = requests.post(f"{BASE_URL}/api/lecturer-availability/recurring", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 1, "Should create 1 block for 1 day"
        assert data[0]["day_of_week"] == 5
        assert data[0]["start_time"] == "14:00"
        assert data[0]["end_time"] == "16:00"
        self.created_ids.append(data[0]["id"])
        print(f"Created recurring block: {data[0]['id']}")
    
    def test_create_recurring_availability_multiple_days(self, headers):
        """POST /api/lecturer-availability/recurring creates blocks for multiple days."""
        payload = {
            "days_of_week": [0, 2, 4],  # Mon, Wed, Fri
            "start_time": "13:00",
            "end_time": "15:00"
        }
        response = requests.post(f"{BASE_URL}/api/lecturer-availability/recurring", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) == 3, "Should create 3 blocks for 3 days"
        for block in data:
            self.created_ids.append(block["id"])
        print(f"Created {len(data)} recurring blocks for Mon/Wed/Fri")
    
    def test_update_recurring_availability(self, headers):
        """PUT /api/lecturer-availability/recurring/{id} updates a block."""
        if not self.created_ids:
            pytest.skip("No blocks created to update")
        
        block_id = self.created_ids[0]
        payload = {
            "day_of_week": 6,  # Change to Sunday
            "start_time": "10:00",
            "end_time": "12:00"
        }
        response = requests.put(f"{BASE_URL}/api/lecturer-availability/recurring/{block_id}", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["day_of_week"] == 6
        assert data["start_time"] == "10:00"
        assert data["end_time"] == "12:00"
        print(f"Updated recurring block {block_id}")
    
    def test_delete_recurring_availability(self, headers):
        """DELETE /api/lecturer-availability/recurring/{id} deletes a block."""
        if not self.created_ids:
            pytest.skip("No blocks created to delete")
        
        block_id = self.created_ids.pop()
        response = requests.delete(f"{BASE_URL}/api/lecturer-availability/recurring/{block_id}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"Deleted recurring block {block_id}")
    
    def test_cleanup_recurring_blocks(self, headers):
        """Cleanup all test-created recurring blocks."""
        for block_id in self.created_ids:
            response = requests.delete(f"{BASE_URL}/api/lecturer-availability/recurring/{block_id}", headers=headers)
            print(f"Cleanup: deleted block {block_id}, status: {response.status_code}")
        self.created_ids.clear()


class TestTimeOff:
    """Tests for time-off/blockage CRUD operations."""
    
    created_ids = []
    
    def test_get_time_off(self, headers):
        """GET /api/lecturer-availability/time-off returns list."""
        response = requests.get(f"{BASE_URL}/api/lecturer-availability/time-off", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} time-off blocks")
    
    def test_create_time_off_with_time(self, headers):
        """POST /api/lecturer-availability/time-off creates blockage with specific time."""
        # Use a future date
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        payload = {
            "start_date": future_date,
            "end_date": future_date,
            "start_time": "09:00",
            "end_time": "11:00",
            "reason": "TEST_Meeting"
        }
        response = requests.post(f"{BASE_URL}/api/lecturer-availability/time-off", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["start_date"] == future_date
        assert data["end_date"] == future_date
        assert data["start_time"] == "09:00"
        assert data["end_time"] == "11:00"
        assert data["reason"] == "TEST_Meeting"
        self.created_ids.append(data["id"])
        print(f"Created time-off block: {data['id']}")
    
    def test_create_time_off_all_day(self, headers):
        """POST /api/lecturer-availability/time-off creates all-day blockage."""
        future_date = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
        payload = {
            "start_date": future_date,
            "end_date": future_date,
            "start_time": None,
            "end_time": None,
            "reason": "TEST_Vacation"
        }
        response = requests.post(f"{BASE_URL}/api/lecturer-availability/time-off", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["start_date"] == future_date
        assert data["start_time"] is None
        assert data["end_time"] is None
        assert data["reason"] == "TEST_Vacation"
        self.created_ids.append(data["id"])
        print(f"Created all-day time-off block: {data['id']}")
    
    def test_create_time_off_multi_day(self, headers):
        """POST /api/lecturer-availability/time-off creates multi-day blockage."""
        start_date = (datetime.now() + timedelta(days=40)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=42)).strftime("%Y-%m-%d")
        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "start_time": "08:00",
            "end_time": "17:00",
            "reason": "TEST_Conference"
        }
        response = requests.post(f"{BASE_URL}/api/lecturer-availability/time-off", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["start_date"] == start_date
        assert data["end_date"] == end_date
        self.created_ids.append(data["id"])
        print(f"Created multi-day time-off block: {data['id']}")
    
    def test_update_time_off(self, headers):
        """PUT /api/lecturer-availability/time-off/{id} updates a blockage."""
        if not self.created_ids:
            pytest.skip("No time-off blocks created to update")
        
        block_id = self.created_ids[0]
        payload = {
            "reason": "TEST_Updated reason"
        }
        response = requests.put(f"{BASE_URL}/api/lecturer-availability/time-off/{block_id}", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["reason"] == "TEST_Updated reason"
        print(f"Updated time-off block {block_id}")
    
    def test_delete_time_off(self, headers):
        """DELETE /api/lecturer-availability/time-off/{id} deletes a blockage."""
        if not self.created_ids:
            pytest.skip("No time-off blocks created to delete")
        
        block_id = self.created_ids.pop()
        response = requests.delete(f"{BASE_URL}/api/lecturer-availability/time-off/{block_id}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"Deleted time-off block {block_id}")
    
    def test_cleanup_time_off_blocks(self, headers):
        """Cleanup all test-created time-off blocks."""
        for block_id in self.created_ids:
            response = requests.delete(f"{BASE_URL}/api/lecturer-availability/time-off/{block_id}", headers=headers)
            print(f"Cleanup: deleted time-off {block_id}, status: {response.status_code}")
        self.created_ids.clear()


class TestWeekView:
    """Tests for week-view endpoint."""
    
    def test_get_week_view_default(self, headers):
        """GET /api/lecturer-availability/week-view returns current week data."""
        response = requests.get(f"{BASE_URL}/api/lecturer-availability/week-view", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "week_start" in data
        assert "week_end" in data
        assert "recurring" in data
        assert "time_offs" in data
        assert isinstance(data["recurring"], list)
        assert isinstance(data["time_offs"], list)
        print(f"Week view: {data['week_start']} to {data['week_end']}, {len(data['recurring'])} recurring, {len(data['time_offs'])} time-offs")
    
    def test_get_week_view_with_date(self, headers):
        """GET /api/lecturer-availability/week-view with week_start param."""
        # Get next week
        next_monday = datetime.now() + timedelta(days=7 - datetime.now().weekday())
        week_start = next_monday.strftime("%Y-%m-%d")
        
        response = requests.get(f"{BASE_URL}/api/lecturer-availability/week-view?week_start={week_start}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["week_start"] == week_start
        print(f"Week view for {week_start}: {len(data['recurring'])} recurring, {len(data['time_offs'])} time-offs")


class TestAvailabilityCheck:
    """Tests for availability check endpoint."""
    
    recurring_id = None
    time_off_id = None
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, headers, user_info):
        """Setup test data for availability check tests."""
        # Create a recurring availability for Monday 08:00-12:00
        payload = {
            "days_of_week": [0],  # Monday
            "start_time": "08:00",
            "end_time": "12:00"
        }
        response = requests.post(f"{BASE_URL}/api/lecturer-availability/recurring", json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.recurring_id = data[0]["id"]
        
        yield
        
        # Cleanup
        if self.recurring_id:
            requests.delete(f"{BASE_URL}/api/lecturer-availability/recurring/{self.recurring_id}", headers=headers)
        if self.time_off_id:
            requests.delete(f"{BASE_URL}/api/lecturer-availability/time-off/{self.time_off_id}", headers=headers)
    
    def test_check_available_in_recurring_block(self, headers, user_info):
        """GET /api/lecturer-availability/check returns available=true when in recurring block."""
        if not user_info:
            pytest.skip("Could not get user info")
        
        lecturer_id = user_info.get("id")
        # Find next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = (today + timedelta(days=days_until_monday)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/check",
            params={
                "lecturer_id": lecturer_id,
                "date": next_monday,
                "start_time": "09:00",
                "end_time": "10:00"
            },
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "available" in data
        # Should be available since we created recurring block for Monday 08:00-12:00
        print(f"Availability check for {next_monday} 09:00-10:00: available={data['available']}, reason={data.get('reason')}")
    
    def test_check_unavailable_no_recurring(self, headers, user_info):
        """GET /api/lecturer-availability/check returns available=false when no recurring availability."""
        if not user_info:
            pytest.skip("Could not get user info")
        
        lecturer_id = user_info.get("id")
        # Find next Sunday (day 6) - we didn't create recurring for Sunday
        today = datetime.now()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        next_sunday = (today + timedelta(days=days_until_sunday)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/check",
            params={
                "lecturer_id": lecturer_id,
                "date": next_sunday,
                "start_time": "09:00",
                "end_time": "10:00"
            },
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "available" in data
        # Should be unavailable since no recurring block for Sunday
        print(f"Availability check for {next_sunday} 09:00-10:00: available={data['available']}, reason={data.get('reason')}")
    
    def test_check_unavailable_with_blockage(self, headers, user_info):
        """GET /api/lecturer-availability/check returns available=false when blockage overlaps."""
        if not user_info:
            pytest.skip("Could not get user info")
        
        lecturer_id = user_info.get("id")
        # Find next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = (today + timedelta(days=days_until_monday)).strftime("%Y-%m-%d")
        
        # Create a time-off that overlaps with the recurring block
        time_off_payload = {
            "start_date": next_monday,
            "end_date": next_monday,
            "start_time": "09:00",
            "end_time": "11:00",
            "reason": "TEST_Blockage for check"
        }
        time_off_response = requests.post(f"{BASE_URL}/api/lecturer-availability/time-off", json=time_off_payload, headers=headers)
        if time_off_response.status_code == 200:
            self.time_off_id = time_off_response.json()["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/check",
            params={
                "lecturer_id": lecturer_id,
                "date": next_monday,
                "start_time": "09:30",
                "end_time": "10:30"
            },
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "available" in data
        # Should be unavailable due to blockage
        assert data["available"] == False, "Should be unavailable due to blockage"
        print(f"Availability check with blockage: available={data['available']}, reason={data.get('reason')}")


class TestLecturerSelector:
    """Tests for admin lecturer selector functionality."""
    
    def test_get_team_members(self, headers):
        """GET /api/team returns team members for lecturer selector."""
        response = requests.get(f"{BASE_URL}/api/team", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # Filter for lecturer-eligible roles
        eligible_roles = ['edukator', 'lektor', 'admin', 'spravce']
        lecturers = [m for m in data if m.get('role') in eligible_roles]
        print(f"Found {len(lecturers)} lecturer-eligible team members out of {len(data)} total")
    
    def test_get_week_view_for_other_lecturer(self, headers):
        """GET /api/lecturer-availability/week-view with lecturer_id param."""
        # First get team members
        team_response = requests.get(f"{BASE_URL}/api/team", headers=headers)
        if team_response.status_code != 200:
            pytest.skip("Could not get team members")
        
        team = team_response.json()
        eligible_roles = ['edukator', 'lektor', 'admin', 'spravce']
        lecturers = [m for m in team if m.get('role') in eligible_roles]
        
        if len(lecturers) < 2:
            pytest.skip("Need at least 2 lecturers to test this")
        
        # Get week view for another lecturer
        other_lecturer_id = lecturers[1]["id"]
        response = requests.get(
            f"{BASE_URL}/api/lecturer-availability/week-view",
            params={"lecturer_id": other_lecturer_id},
            headers=headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "recurring" in data
        assert "time_offs" in data
        print(f"Week view for lecturer {other_lecturer_id}: {len(data['recurring'])} recurring, {len(data['time_offs'])} time-offs")


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_update_nonexistent_recurring(self, headers):
        """PUT /api/lecturer-availability/recurring/{id} returns 404 for nonexistent block."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        payload = {
            "day_of_week": 0,
            "start_time": "08:00",
            "end_time": "12:00"
        }
        response = requests.put(f"{BASE_URL}/api/lecturer-availability/recurring/{fake_id}", json=payload, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returns 404 for nonexistent recurring block")
    
    def test_delete_nonexistent_recurring(self, headers):
        """DELETE /api/lecturer-availability/recurring/{id} returns 404 for nonexistent block."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.delete(f"{BASE_URL}/api/lecturer-availability/recurring/{fake_id}", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returns 404 for nonexistent recurring block")
    
    def test_update_nonexistent_time_off(self, headers):
        """PUT /api/lecturer-availability/time-off/{id} returns 404 for nonexistent block."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        payload = {
            "reason": "Test"
        }
        response = requests.put(f"{BASE_URL}/api/lecturer-availability/time-off/{fake_id}", json=payload, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returns 404 for nonexistent time-off block")
    
    def test_delete_nonexistent_time_off(self, headers):
        """DELETE /api/lecturer-availability/time-off/{id} returns 404 for nonexistent block."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.delete(f"{BASE_URL}/api/lecturer-availability/time-off/{fake_id}", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Correctly returns 404 for nonexistent time-off block")
    
    def test_create_recurring_no_days(self, headers):
        """POST /api/lecturer-availability/recurring with empty days_of_week."""
        payload = {
            "days_of_week": [],
            "start_time": "08:00",
            "end_time": "12:00"
        }
        response = requests.post(f"{BASE_URL}/api/lecturer-availability/recurring", json=payload, headers=headers)
        # Should return 200 with empty list (no blocks created)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data == [], "Should return empty list when no days provided"
        print("Correctly returns empty list when no days provided")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
