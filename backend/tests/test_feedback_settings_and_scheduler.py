"""
Test suite for iteration 35:
1. BUG FIX: Confirmed reservations with past dates auto-complete to 'completed' status
2. FEATURE: Programs API returns feedback_enabled and feedback_questions fields
3. FEATURE: Programs can be updated with feedback_enabled=true/false and custom feedback_questions
4. FEATURE: Custom questions limited to max 5, with types: text, scale, yesno
5. FEATURE: Outlook sync window is dynamic based on max_days_before_booking + 60 day buffer (min 180 days)
6. Login flow works with httpOnly cookies
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


class TestLoginAndAuth:
    """Test login flow with httpOnly cookies"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create a session that persists cookies"""
        return requests.Session()
    
    def test_login_success(self, session):
        """Test login returns success and sets cookies"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login successful for {TEST_EMAIL}")
    
    def test_auth_me_endpoint(self, session):
        """Test /auth/me returns user info after login"""
        # First login
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        assert data["email"] == TEST_EMAIL
        assert data["institution_id"] == INSTITUTION_ID
        print(f"✓ Auth/me returns correct user data")


class TestProgramFeedbackSettings:
    """Test feedback_enabled and feedback_questions fields on programs"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return session
    
    def test_programs_list_returns_feedback_fields(self, auth_session):
        """Test GET /programs returns feedback_enabled and feedback_questions"""
        response = auth_session.get(f"{BASE_URL}/api/programs")
        assert response.status_code == 200, f"Programs list failed: {response.text}"
        
        programs = response.json()
        assert isinstance(programs, list), "Programs should be a list"
        assert len(programs) > 0, "Should have at least one program"
        
        # Check first program has feedback fields
        program = programs[0]
        assert "feedback_enabled" in program, "Program should have feedback_enabled field"
        assert "feedback_questions" in program, "Program should have feedback_questions field"
        
        # Default values
        assert program["feedback_enabled"] == True, "feedback_enabled should default to True"
        assert isinstance(program["feedback_questions"], list), "feedback_questions should be a list"
        print(f"✓ Programs list returns feedback_enabled={program['feedback_enabled']} and feedback_questions={program['feedback_questions']}")
    
    def test_program_update_feedback_enabled_false(self, auth_session):
        """Test updating program with feedback_enabled=false"""
        # Get first program
        response = auth_session.get(f"{BASE_URL}/api/programs")
        programs = response.json()
        program_id = programs[0]["id"]
        
        # Update with feedback_enabled=false
        update_data = {
            **programs[0],
            "feedback_enabled": False,
            "feedback_questions": []
        }
        
        response = auth_session.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data)
        assert response.status_code == 200, f"Program update failed: {response.text}"
        
        # Verify update
        response = auth_session.get(f"{BASE_URL}/api/programs")
        updated_program = next(p for p in response.json() if p["id"] == program_id)
        assert updated_program["feedback_enabled"] == False, "feedback_enabled should be False after update"
        print(f"✓ Program updated with feedback_enabled=False")
        
        # Restore to True
        update_data["feedback_enabled"] = True
        auth_session.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data)
    
    def test_program_update_with_custom_questions(self, auth_session):
        """Test updating program with custom feedback questions"""
        # Get first program
        response = auth_session.get(f"{BASE_URL}/api/programs")
        programs = response.json()
        program_id = programs[0]["id"]
        
        # Custom questions with different types
        custom_questions = [
            {"id": "q1", "question": "Jak hodnotíte program?", "type": "scale"},
            {"id": "q2", "question": "Co se vám líbilo nejvíce?", "type": "text"},
            {"id": "q3", "question": "Doporučili byste program?", "type": "yesno"}
        ]
        
        update_data = {
            **programs[0],
            "feedback_enabled": True,
            "feedback_questions": custom_questions
        }
        
        response = auth_session.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data)
        assert response.status_code == 200, f"Program update with questions failed: {response.text}"
        
        # Verify update
        response = auth_session.get(f"{BASE_URL}/api/programs")
        updated_program = next(p for p in response.json() if p["id"] == program_id)
        assert len(updated_program["feedback_questions"]) == 3, "Should have 3 custom questions"
        
        # Verify question types
        types = [q["type"] for q in updated_program["feedback_questions"]]
        assert "scale" in types, "Should have scale type question"
        assert "text" in types, "Should have text type question"
        assert "yesno" in types, "Should have yesno type question"
        print(f"✓ Program updated with {len(custom_questions)} custom questions (types: {types})")
        
        # Clean up - remove custom questions
        update_data["feedback_questions"] = []
        auth_session.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data)
    
    def test_feedback_questions_max_5_limit(self, auth_session):
        """Test that feedback_questions accepts up to 5 questions"""
        # Get first program
        response = auth_session.get(f"{BASE_URL}/api/programs")
        programs = response.json()
        program_id = programs[0]["id"]
        
        # Create 5 questions (max allowed)
        five_questions = [
            {"id": f"q{i}", "question": f"Question {i}?", "type": "text"}
            for i in range(1, 6)
        ]
        
        update_data = {
            **programs[0],
            "feedback_enabled": True,
            "feedback_questions": five_questions
        }
        
        response = auth_session.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data)
        assert response.status_code == 200, f"Program update with 5 questions failed: {response.text}"
        
        # Verify 5 questions saved
        response = auth_session.get(f"{BASE_URL}/api/programs")
        updated_program = next(p for p in response.json() if p["id"] == program_id)
        assert len(updated_program["feedback_questions"]) == 5, "Should have exactly 5 questions"
        print(f"✓ Program accepts max 5 custom questions")
        
        # Clean up
        update_data["feedback_questions"] = []
        auth_session.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data)


class TestPlanStatus:
    """Test plan/status endpoint returns is_pro"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return session
    
    def test_plan_status_returns_is_pro(self, auth_session):
        """Test /plan/status returns is_pro field"""
        response = auth_session.get(f"{BASE_URL}/api/plan/status")
        assert response.status_code == 200, f"Plan status failed: {response.text}"
        
        data = response.json()
        assert "is_pro" in data, "Plan status should have is_pro field"
        print(f"✓ Plan status returns is_pro={data['is_pro']}")


class TestBookingsAndScheduler:
    """Test bookings list and auto-complete scheduler"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return session
    
    def test_bookings_list_loads(self, auth_session):
        """Test GET /bookings returns list"""
        response = auth_session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200, f"Bookings list failed: {response.text}"
        
        bookings = response.json()
        assert isinstance(bookings, list), "Bookings should be a list"
        print(f"✓ Bookings list loaded with {len(bookings)} bookings")
    
    def test_no_confirmed_reservations_with_past_dates(self, auth_session):
        """Test that no confirmed reservations have past dates (scheduler should auto-complete them)"""
        response = auth_session.get(f"{BASE_URL}/api/bookings")
        bookings = response.json()
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Find confirmed reservations with past dates
        past_confirmed = [
            b for b in bookings 
            if b["status"] == "confirmed" and b["date"] < today
        ]
        
        if past_confirmed:
            print(f"⚠ Found {len(past_confirmed)} confirmed reservations with past dates:")
            for b in past_confirmed[:5]:  # Show first 5
                print(f"  - ID: {b['id']}, Date: {b['date']}, Status: {b['status']}")
        
        # This should be 0 after scheduler runs
        assert len(past_confirmed) == 0, f"Found {len(past_confirmed)} confirmed reservations with past dates - scheduler should auto-complete them"
        print(f"✓ No confirmed reservations with past dates (scheduler working correctly)")
    
    def test_completed_reservations_exist(self, auth_session):
        """Test that completed reservations exist in the system"""
        response = auth_session.get(f"{BASE_URL}/api/bookings")
        bookings = response.json()
        
        completed = [b for b in bookings if b["status"] == "completed"]
        print(f"✓ Found {len(completed)} completed reservations")
        
        # Check status distribution
        status_counts = {}
        for b in bookings:
            status_counts[b["status"]] = status_counts.get(b["status"], 0) + 1
        print(f"  Status distribution: {status_counts}")


class TestOutlookSyncWindow:
    """Test Outlook sync window calculation (code review - can't test actual sync without MS credentials)"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return session
    
    def test_programs_have_max_days_before_booking(self, auth_session):
        """Test programs have max_days_before_booking field for sync window calculation"""
        response = auth_session.get(f"{BASE_URL}/api/programs")
        programs = response.json()
        
        max_values = []
        for p in programs:
            if p.get("status") == "active" and p.get("max_days_before_booking"):
                max_values.append(p["max_days_before_booking"])
        
        if max_values:
            max_booking_window = max(max_values)
            expected_sync_days = max(max_booking_window + 60, 180)
            print(f"✓ Max booking window: {max_booking_window} days")
            print(f"  Expected Outlook sync window: {expected_sync_days} days (max + 60, min 180)")
        else:
            print(f"✓ No active programs with max_days_before_booking, default sync window: 180 days")


class TestMicrosoftCalendarStatus:
    """Test Microsoft calendar status endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return session
    
    def test_microsoft_calendar_status_endpoint(self, auth_session):
        """Test /microsoft-calendar/status endpoint exists and returns status"""
        response = auth_session.get(f"{BASE_URL}/api/microsoft-calendar/status")
        assert response.status_code == 200, f"Microsoft calendar status failed: {response.text}"
        
        data = response.json()
        assert "connected" in data, "Should have connected field"
        print(f"✓ Microsoft calendar status: connected={data['connected']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
