"""
Test Onboarding Feature - GET /api/onboarding/status and POST /api/onboarding/complete
Tests for the onboarding wizard endpoints for new institutions.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from previous test reports
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for testing."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with authentication token."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestOnboardingStatus:
    """Tests for GET /api/onboarding/status endpoint."""
    
    def test_get_onboarding_status_requires_auth(self):
        """GET /api/onboarding/status requires authentication."""
        response = requests.get(f"{BASE_URL}/api/onboarding/status")
        # 401 or 403 both indicate auth is required
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: GET /api/onboarding/status requires authentication")
    
    def test_get_onboarding_status_success(self, auth_headers):
        """GET /api/onboarding/status returns onboarding status with completed flag and steps."""
        response = requests.get(f"{BASE_URL}/api/onboarding/status", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "completed" in data, "Response should contain 'completed' field"
        assert isinstance(data["completed"], bool), "'completed' should be a boolean"
        
        # If not completed, should have steps info
        if not data["completed"]:
            assert "steps" in data, "Response should contain 'steps' field when not completed"
            steps = data["steps"]
            assert "has_programs" in steps, "Steps should contain 'has_programs'"
            assert "program_count" in steps, "Steps should contain 'program_count'"
            assert isinstance(steps["has_programs"], bool), "'has_programs' should be boolean"
            assert isinstance(steps["program_count"], int), "'program_count' should be integer"
        
        print(f"PASS: GET /api/onboarding/status returns valid response: {data}")


class TestOnboardingComplete:
    """Tests for POST /api/onboarding/complete endpoint."""
    
    def test_complete_onboarding_requires_auth(self):
        """POST /api/onboarding/complete requires authentication."""
        response = requests.post(f"{BASE_URL}/api/onboarding/complete")
        # 401 or 403 both indicate auth is required
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: POST /api/onboarding/complete requires authentication")
    
    def test_complete_onboarding_success(self, auth_headers):
        """POST /api/onboarding/complete marks onboarding as done."""
        response = requests.post(f"{BASE_URL}/api/onboarding/complete", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        print(f"PASS: POST /api/onboarding/complete returns: {data}")
    
    def test_verify_onboarding_completed(self, auth_headers):
        """After completing, GET /api/onboarding/status should return completed=True."""
        response = requests.get(f"{BASE_URL}/api/onboarding/status", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["completed"] == True, f"Expected completed=True, got {data}"
        print(f"PASS: Onboarding status shows completed=True after completion")


class TestOnboardingReset:
    """Test to reset onboarding for frontend testing."""
    
    def test_reset_onboarding_for_frontend_tests(self, auth_headers):
        """
        Reset onboarding_completed to false for frontend testing.
        This is done via direct SQL update through a special endpoint or manual DB update.
        For now, we'll just verify the current state.
        """
        # First check current status
        response = requests.get(f"{BASE_URL}/api/onboarding/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Current onboarding status: {data}")
        
        # Note: To reset for frontend tests, run:
        # UPDATE institutions SET onboarding_completed = false WHERE id = '669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5'
        print("INFO: To reset onboarding for frontend tests, run SQL: UPDATE institutions SET onboarding_completed = false WHERE id = '669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5'")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
