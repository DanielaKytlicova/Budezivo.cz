"""
Test lecturer collision availability feature.
Tests the fix for: when program has collision_resources=['lecturer'] and no assigned_lecturer_id,
the system checks ALL scheduled team lecturers. If none available → blocks marked 'unavailable'.

Key scenarios:
- Daily availability: afternoon blocks outside lecturer hours → 'unavailable'
- Monthly calendar: days with no lecturer availability → has_availability=false
- Only lecturers WITH defined availability schedules are considered
"""
import pytest
import requests
import os
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test constants
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
PROGRAM_ID = "128d6178-e199-4cc5-b247-0e42fe1955d7"  # "Čteme obrazy" - has lecturer collision
DEMO_ADMIN_ID = "2868bc35-7d6e-4046-87fa-013ee5efdb60"  # Has Mon-Fri 8:00-12:00 availability


class TestLecturerCollisionAvailability:
    """Tests for lecturer collision availability feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "Demo2026!"
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_login_works(self):
        """Test that login flow works with httpOnly cookies"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "Demo2026!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "demo@budezivo.cz"
        print("✓ Login works correctly")
    
    def test_program_has_lecturer_collision_enabled(self):
        """Verify program 'Čteme obrazy' has collision_resources=['lecturer'] and no assigned_lecturer"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        response = self.session.get(
            f"{BASE_URL}/api/programs/{PROGRAM_ID}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to get program: {response.text}"
        
        program = response.json()
        assert program["collision_resources"] == ["lecturer"], \
            f"Expected collision_resources=['lecturer'], got {program.get('collision_resources')}"
        assert program["assigned_lecturer_id"] is None, \
            f"Expected assigned_lecturer_id=None, got {program.get('assigned_lecturer_id')}"
        print(f"✓ Program '{program['name_cs']}' has lecturer collision enabled, no assigned lecturer")
    
    def test_daily_availability_morning_block_available(self):
        """
        CRITICAL: Morning block (08:30-12:00) should be 'available' 
        because Demo Admin has 8:00-12:00 availability
        """
        # Find a future Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        future_monday = today + timedelta(days=days_until_monday + 14)  # 2+ weeks out
        date_str = future_monday.strftime("%Y-%m-%d")
        
        response = self.session.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_ID}/{date_str}"
        )
        assert response.status_code == 200, f"Failed to get availability: {response.text}"
        
        data = response.json()
        assert data["date"] == date_str
        
        # Find morning block
        morning_block = next((b for b in data["time_blocks"] if b["time"] == "08:30-12:00"), None)
        assert morning_block is not None, "Morning block 08:30-12:00 not found"
        
        # Morning block should be available (within lecturer's 8:00-12:00 window)
        assert morning_block["status"] in ["available", "booked"], \
            f"Morning block should be available or booked, got {morning_block['status']}"
        print(f"✓ Morning block on {date_str}: {morning_block['status']}")
    
    def test_daily_availability_afternoon_block_unavailable(self):
        """
        CRITICAL: Afternoon block (13:00-15:00) should be 'unavailable'
        because Demo Admin only has 8:00-12:00 availability
        """
        # Find a future Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        future_monday = today + timedelta(days=days_until_monday + 14)  # 2+ weeks out
        date_str = future_monday.strftime("%Y-%m-%d")
        
        response = self.session.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_ID}/{date_str}"
        )
        assert response.status_code == 200, f"Failed to get availability: {response.text}"
        
        data = response.json()
        
        # Find afternoon block
        afternoon_block = next((b for b in data["time_blocks"] if b["time"] == "13:00-15:00"), None)
        assert afternoon_block is not None, "Afternoon block 13:00-15:00 not found"
        
        # Afternoon block should be unavailable (outside lecturer's 8:00-12:00 window)
        assert afternoon_block["status"] == "unavailable", \
            f"Afternoon block should be 'unavailable', got {afternoon_block['status']}"
        print(f"✓ Afternoon block on {date_str}: {afternoon_block['status']} (correctly unavailable)")
    
    def test_daily_availability_weekend_returns_empty(self):
        """Weekend dates should return empty time_blocks (not in available_days)"""
        # Find a future Saturday
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        future_saturday = today + timedelta(days=days_until_saturday + 14)
        date_str = future_saturday.strftime("%Y-%m-%d")
        
        response = self.session.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_ID}/{date_str}"
        )
        assert response.status_code == 200, f"Failed to get availability: {response.text}"
        
        data = response.json()
        assert data["time_blocks"] == [], \
            f"Weekend should have empty time_blocks, got {data['time_blocks']}"
        print(f"✓ Weekend ({date_str}) returns empty time_blocks")
    
    def test_monthly_calendar_weekdays_have_availability(self):
        """
        CRITICAL: Monthly calendar should show weekdays as available
        because morning block IS covered by lecturer
        """
        # Use a future month
        today = date.today()
        future_month = today.month + 2 if today.month <= 10 else 1
        future_year = today.year if today.month <= 10 else today.year + 1
        
        response = self.session.get(
            f"{BASE_URL}/api/calendar/{INSTITUTION_ID}/{future_year}/{future_month}?program_id={PROGRAM_ID}"
        )
        assert response.status_code == 200, f"Failed to get calendar: {response.text}"
        
        data = response.json()
        assert data["year"] == future_year
        assert data["month"] == future_month
        
        # Check that at least some weekdays have availability
        weekday_dates = [d for d in data["dates"] 
                        if date.fromisoformat(d["date"]).weekday() < 5]  # Mon-Fri
        
        available_weekdays = [d for d in weekday_dates if d["has_availability"]]
        assert len(available_weekdays) > 0, \
            "Expected some weekdays to have availability (morning block is covered)"
        print(f"✓ Monthly calendar: {len(available_weekdays)} weekdays have availability")
    
    def test_monthly_calendar_weekends_no_availability(self):
        """Monthly calendar should show weekends as unavailable"""
        # Use a future month
        today = date.today()
        future_month = today.month + 2 if today.month <= 10 else 1
        future_year = today.year if today.month <= 10 else today.year + 1
        
        response = self.session.get(
            f"{BASE_URL}/api/calendar/{INSTITUTION_ID}/{future_year}/{future_month}?program_id={PROGRAM_ID}"
        )
        assert response.status_code == 200, f"Failed to get calendar: {response.text}"
        
        data = response.json()
        
        # Check that weekends have no availability
        weekend_dates = [d for d in data["dates"] 
                        if date.fromisoformat(d["date"]).weekday() >= 5]  # Sat-Sun
        
        unavailable_weekends = [d for d in weekend_dates if not d["has_availability"]]
        assert len(unavailable_weekends) == len(weekend_dates), \
            "All weekends should have no availability"
        print(f"✓ Monthly calendar: all {len(weekend_dates)} weekend days have no availability")
    
    def test_specific_date_april_2026_monday(self):
        """Test specific date 2026-04-06 (Monday) - morning available, afternoon unavailable"""
        response = self.session.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_ID}/2026-04-06"
        )
        assert response.status_code == 200, f"Failed to get availability: {response.text}"
        
        data = response.json()
        assert data["date"] == "2026-04-06"
        
        # Check blocks
        blocks_by_time = {b["time"]: b["status"] for b in data["time_blocks"]}
        
        assert "08:30-12:00" in blocks_by_time, "Morning block not found"
        assert "13:00-15:00" in blocks_by_time, "Afternoon block not found"
        
        # Morning should be available (within 8:00-12:00)
        assert blocks_by_time["08:30-12:00"] in ["available", "booked"], \
            f"Morning block should be available/booked, got {blocks_by_time['08:30-12:00']}"
        
        # Afternoon should be unavailable (outside 8:00-12:00)
        assert blocks_by_time["13:00-15:00"] == "unavailable", \
            f"Afternoon block should be unavailable, got {blocks_by_time['13:00-15:00']}"
        
        print(f"✓ 2026-04-06: morning={blocks_by_time['08:30-12:00']}, afternoon={blocks_by_time['13:00-15:00']}")
    
    def test_bookings_list_loads(self):
        """Test that bookings list page loads correctly"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        response = self.session.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Failed to get bookings: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Bookings should be a list"
        print(f"✓ Bookings list loaded: {len(data)} bookings")


class TestLecturerCollisionEdgeCases:
    """Edge case tests for lecturer collision feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_availability_endpoint_returns_valid_structure(self):
        """Verify availability endpoint returns correct structure"""
        response = self.session.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_ID}/2026-04-06"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "date" in data
        assert "time_blocks" in data
        assert isinstance(data["time_blocks"], list)
        
        for block in data["time_blocks"]:
            assert "time" in block
            assert "status" in block
            assert block["status"] in ["available", "booked", "unavailable"]
        
        print("✓ Availability endpoint returns valid structure")
    
    def test_calendar_endpoint_returns_valid_structure(self):
        """Verify calendar endpoint returns correct structure"""
        response = self.session.get(
            f"{BASE_URL}/api/calendar/{INSTITUTION_ID}/2026/4?program_id={PROGRAM_ID}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "year" in data
        assert "month" in data
        assert "dates" in data
        assert isinstance(data["dates"], list)
        
        for date_entry in data["dates"]:
            assert "date" in date_entry
            assert "has_availability" in date_entry
            assert "available_blocks" in date_entry
            assert isinstance(date_entry["has_availability"], bool)
        
        print("✓ Calendar endpoint returns valid structure")
    
    def test_invalid_program_returns_empty(self):
        """Invalid program ID should return empty time_blocks"""
        response = self.session.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/00000000-0000-0000-0000-000000000000/2026-04-06"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["time_blocks"] == [], "Invalid program should return empty time_blocks"
        print("✓ Invalid program returns empty time_blocks")
    
    def test_invalid_date_format_returns_empty(self):
        """Invalid date format should return empty time_blocks"""
        response = self.session.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{PROGRAM_ID}/invalid-date"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["time_blocks"] == [], "Invalid date should return empty time_blocks"
        print("✓ Invalid date format returns empty time_blocks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
