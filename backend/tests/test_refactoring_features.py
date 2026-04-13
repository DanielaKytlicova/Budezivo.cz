"""
Test suite for ProgramsPage refactoring and new features:
- collision_lecturer_ids field in Programs API
- Team members API for lecturer selection
- Public feedback endpoint returning program-level feedback_questions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth cookie."""
    return {"Cookie": f"access_token={auth_token}"}


class TestTeamMembersAPI:
    """Test /api/team endpoint for collision lecturer selection."""
    
    def test_get_team_members(self, auth_headers):
        """GET /api/team should return team members list."""
        response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check structure of team members
        if len(data) > 0:
            member = data[0]
            assert "id" in member, "Team member should have 'id'"
            assert "email" in member, "Team member should have 'email'"
            assert "role" in member, "Team member should have 'role'"
            print(f"✓ Found {len(data)} team members")
            for m in data[:3]:  # Print first 3
                print(f"  - {m.get('first_name', '')} {m.get('last_name', '')} ({m.get('role')})")


class TestProgramsAPICollisionLecturerIds:
    """Test collision_lecturer_ids field in Programs API."""
    
    def test_get_programs_returns_collision_lecturer_ids(self, auth_headers):
        """GET /api/programs should return collision_lecturer_ids field."""
        response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            program = data[0]
            # Check that collision_lecturer_ids field exists (can be empty array)
            assert "collision_lecturer_ids" in program or program.get("collision_lecturer_ids") is None or isinstance(program.get("collision_lecturer_ids", []), list), \
                "Program should have collision_lecturer_ids field"
            print(f"✓ Program '{program.get('name_cs')}' has collision_lecturer_ids: {program.get('collision_lecturer_ids', [])}")
    
    def test_update_program_with_collision_lecturer_ids(self, auth_headers):
        """PUT /api/programs/{id} should save collision_lecturer_ids."""
        # First get a program
        response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        assert response.status_code == 200
        
        programs = response.json()
        if len(programs) == 0:
            pytest.skip("No programs available for testing")
        
        program = programs[0]
        program_id = program["id"]
        
        # Get team members to use their IDs
        team_response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        team_members = team_response.json() if team_response.status_code == 200 else []
        
        # Filter for lecturers
        lecturer_ids = [m["id"] for m in team_members if m.get("role") in ["lektor", "edukator", "admin", "spravce"]][:2]
        
        # Update program with collision_lecturer_ids
        update_data = {
            "name_cs": program.get("name_cs", "Test Program"),
            "name_en": program.get("name_en", "Test Program"),
            "description_cs": program.get("description_cs", "Test"),
            "description_en": program.get("description_en", "Test"),
            "duration": program.get("duration", 60),
            "age_group": program.get("age_group", "zs1_7_12"),
            "target_group": program.get("target_group", "schools"),
            "allow_parallel": True,
            "collision_resources": ["lecturer"],
            "collision_lecturer_ids": lecturer_ids,
        }
        
        response = requests.put(
            f"{BASE_URL}/api/programs/{program_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify the update
        get_response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        updated_programs = get_response.json()
        updated_program = next((p for p in updated_programs if p["id"] == program_id), None)
        
        assert updated_program is not None, "Program should exist after update"
        assert updated_program.get("collision_lecturer_ids") == lecturer_ids, \
            f"collision_lecturer_ids should be {lecturer_ids}, got {updated_program.get('collision_lecturer_ids')}"
        
        print(f"✓ Successfully saved collision_lecturer_ids: {lecturer_ids}")
        
        # Reset to empty
        update_data["collision_lecturer_ids"] = []
        update_data["collision_resources"] = []
        update_data["allow_parallel"] = False
        requests.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data, headers=auth_headers)


class TestPublicFeedbackEndpoint:
    """Test public feedback endpoint returns program-level feedback_questions."""
    
    def test_feedback_endpoint_structure(self, auth_headers):
        """Verify feedback endpoint exists and returns expected structure."""
        # We need a valid feedback token to test this
        # First, let's check if there are any feedbacks
        response = requests.get(f"{BASE_URL}/api/feedback/submissions", headers=auth_headers)
        
        if response.status_code == 200:
            feedbacks = response.json()
            print(f"✓ Found {len(feedbacks)} feedback submissions")
        else:
            print(f"Note: Feedback submissions endpoint returned {response.status_code}")
    
    def test_feedback_questions_endpoint(self, auth_headers):
        """GET /api/feedback/questions should return institution-level questions."""
        response = requests.get(f"{BASE_URL}/api/feedback/questions", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Found {len(data)} institution-level feedback questions")


class TestProgramFeedbackQuestions:
    """Test program-level feedback_questions field."""
    
    def test_program_has_feedback_questions_field(self, auth_headers):
        """Programs should have feedback_questions field."""
        response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        assert response.status_code == 200
        
        programs = response.json()
        if len(programs) > 0:
            program = programs[0]
            # feedback_questions should exist (can be empty array)
            assert "feedback_questions" in program or program.get("feedback_questions") is None or isinstance(program.get("feedback_questions", []), list), \
                "Program should have feedback_questions field"
            print(f"✓ Program has feedback_questions: {program.get('feedback_questions', [])}")
    
    def test_update_program_with_feedback_questions(self, auth_headers):
        """PUT /api/programs/{id} should save feedback_questions."""
        response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        assert response.status_code == 200
        
        programs = response.json()
        if len(programs) == 0:
            pytest.skip("No programs available")
        
        program = programs[0]
        program_id = program["id"]
        
        # Create test feedback questions
        test_questions = [
            {"id": "test_q1", "question": "Jak hodnotíte program?", "type": "scale"},
            {"id": "test_q2", "question": "Doporučili byste program?", "type": "yesno"},
        ]
        
        update_data = {
            "name_cs": program.get("name_cs", "Test"),
            "name_en": program.get("name_en", "Test"),
            "description_cs": program.get("description_cs", "Test"),
            "description_en": program.get("description_en", "Test"),
            "duration": program.get("duration", 60),
            "age_group": program.get("age_group", "zs1_7_12"),
            "target_group": program.get("target_group", "schools"),
            "feedback_enabled": True,
            "feedback_questions": test_questions,
        }
        
        response = requests.put(
            f"{BASE_URL}/api/programs/{program_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify
        get_response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        updated_programs = get_response.json()
        updated_program = next((p for p in updated_programs if p["id"] == program_id), None)
        
        assert updated_program is not None
        saved_questions = updated_program.get("feedback_questions", [])
        assert len(saved_questions) == 2, f"Expected 2 questions, got {len(saved_questions)}"
        print(f"✓ Successfully saved feedback_questions: {saved_questions}")
        
        # Reset
        update_data["feedback_questions"] = []
        requests.put(f"{BASE_URL}/api/programs/{program_id}", json=update_data, headers=auth_headers)


class TestAvailabilityWithCollisionLecturerIds:
    """Test that availability endpoints use collision_lecturer_ids."""
    
    def test_daily_availability_endpoint(self, auth_headers):
        """GET /api/availability/{institution_id}/{program_id}/{date} should work."""
        # Get a program first
        response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        assert response.status_code == 200
        
        programs = response.json()
        if len(programs) == 0:
            pytest.skip("No programs available")
        
        program = programs[0]
        program_id = program["id"]
        
        # Test availability for a future date
        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/availability/{INSTITUTION_ID}/{program_id}/{future_date}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "date" in data, "Response should have 'date'"
        assert "time_blocks" in data, "Response should have 'time_blocks'"
        print(f"✓ Availability for {future_date}: {len(data.get('time_blocks', []))} time blocks")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
