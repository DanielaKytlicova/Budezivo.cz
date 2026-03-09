"""
Email Template API Tests.
Tests for the new email template functionality added to the booking system.
Covers: GET template, PUT template, POST preview, GET config status endpoints.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://template-manager-29.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@budezivo.cz"
TEST_PASSWORD = "test123"
TEST_PROGRAM_ID = "fa7c7513-813c-4c10-827c-30ff11a46caf"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestEmailConfigStatus:
    """Tests for /api/programs/email-config/status endpoint."""
    
    def test_get_email_config_status_returns_200(self, authenticated_client):
        """GET /api/programs/email-config/status should return 200."""
        response = authenticated_client.get(f"{BASE_URL}/api/programs/email-config/status")
        assert response.status_code == 200
        
    def test_email_config_status_returns_configured_flag(self, authenticated_client):
        """Response should include configured flag (false since RESEND_API_KEY is empty)."""
        response = authenticated_client.get(f"{BASE_URL}/api/programs/email-config/status")
        data = response.json()
        assert "configured" in data
        assert isinstance(data["configured"], bool)
        # Since RESEND_API_KEY is empty, should be false
        assert data["configured"] == False
        
    def test_email_config_status_returns_available_variables(self, authenticated_client):
        """Response should include available_variables dictionary."""
        response = authenticated_client.get(f"{BASE_URL}/api/programs/email-config/status")
        data = response.json()
        assert "available_variables" in data
        variables = data["available_variables"]
        # Check for expected variables
        expected_vars = ["school_name", "contact_person", "email", "phone", 
                        "reservation_date", "reservation_time", "number_of_students",
                        "number_of_teachers", "program_name", "program_duration",
                        "institution_name", "special_requirements"]
        for var in expected_vars:
            assert var in variables, f"Missing variable: {var}"


class TestEmailTemplateGet:
    """Tests for GET /api/programs/{id}/email-template endpoint."""
    
    def test_get_email_template_returns_200(self, authenticated_client):
        """GET /api/programs/{id}/email-template should return 200."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template"
        )
        assert response.status_code == 200
        
    def test_get_email_template_returns_template_data(self, authenticated_client):
        """Response should include template data (or null if no template exists)."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template"
        )
        data = response.json()
        # Should have template key (can be null or object)
        assert "template" in data
        
    def test_get_email_template_returns_available_variables(self, authenticated_client):
        """Response should include available_variables."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template"
        )
        data = response.json()
        assert "available_variables" in data
        assert isinstance(data["available_variables"], dict)
        
    def test_get_email_template_returns_email_service_configured(self, authenticated_client):
        """Response should include email_service_configured flag."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template"
        )
        data = response.json()
        assert "email_service_configured" in data
        assert isinstance(data["email_service_configured"], bool)
        
    def test_get_email_template_404_for_invalid_program(self, authenticated_client):
        """Should return 404 for non-existent program."""
        response = authenticated_client.get(
            f"{BASE_URL}/api/programs/00000000-0000-0000-0000-000000000000/email-template"
        )
        assert response.status_code == 404


class TestEmailTemplatePut:
    """Tests for PUT /api/programs/{id}/email-template endpoint."""
    
    def test_put_email_template_saves_successfully(self, authenticated_client):
        """PUT should save template and return 200."""
        payload = {
            "subject": "Potvrzení rezervace - {{program_name}}",
            "body": "<h2>Potvrzení</h2><p>Dobrý den, {{contact_person}}</p>"
        }
        response = authenticated_client.put(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template",
            json=payload
        )
        assert response.status_code == 200
        
    def test_put_email_template_returns_saved_template(self, authenticated_client):
        """PUT should return the saved template data."""
        payload = {
            "subject": "Test Subject {{program_name}}",
            "body": "<p>Test body {{contact_person}}</p>"
        }
        response = authenticated_client.put(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template",
            json=payload
        )
        data = response.json()
        assert "template" in data
        assert data["template"]["subject"] == payload["subject"]
        assert data["template"]["body"] == payload["body"]
        
    def test_put_email_template_includes_message(self, authenticated_client):
        """PUT should return success message."""
        payload = {
            "subject": "Test",
            "body": "<p>Test</p>"
        }
        response = authenticated_client.put(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template",
            json=payload
        )
        data = response.json()
        assert "message" in data
        assert "saved" in data["message"].lower() or "success" in data["message"].lower()
        
    def test_put_email_template_rejects_unknown_variables(self, authenticated_client):
        """PUT should reject templates with unknown variables."""
        payload = {
            "subject": "Test {{unknown_variable}}",
            "body": "<p>Test</p>"
        }
        response = authenticated_client.put(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template",
            json=payload
        )
        # Should return 400 for unknown variables
        assert response.status_code == 400
        
    def test_put_email_template_404_for_invalid_program(self, authenticated_client):
        """PUT should return 404 for non-existent program."""
        payload = {
            "subject": "Test",
            "body": "<p>Test</p>"
        }
        response = authenticated_client.put(
            f"{BASE_URL}/api/programs/00000000-0000-0000-0000-000000000000/email-template",
            json=payload
        )
        assert response.status_code == 404


class TestEmailTemplatePreview:
    """Tests for POST /api/programs/{id}/email-template/preview endpoint."""
    
    def test_preview_returns_200(self, authenticated_client):
        """POST preview should return 200."""
        payload = {
            "subject": "Test {{program_name}}",
            "body": "<p>{{contact_person}}</p>"
        }
        response = authenticated_client.post(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template/preview",
            json=payload
        )
        assert response.status_code == 200
        
    def test_preview_returns_rendered_template(self, authenticated_client):
        """Preview should return template with variables replaced."""
        payload = {
            "subject": "Potvrzení - {{program_name}}",
            "body": "<p>Dobrý den, {{contact_person}}</p>"
        }
        response = authenticated_client.post(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template/preview",
            json=payload
        )
        data = response.json()
        assert "preview" in data
        # Variables should be replaced with sample values
        assert "{{program_name}}" not in data["preview"]["subject"]
        assert "{{contact_person}}" not in data["preview"]["body"]
        
    def test_preview_returns_sample_data(self, authenticated_client):
        """Preview should include sample_data used for rendering."""
        payload = {
            "subject": "Test",
            "body": "<p>Test</p>"
        }
        response = authenticated_client.post(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template/preview",
            json=payload
        )
        data = response.json()
        assert "sample_data" in data
        # Sample data should have all expected keys
        sample_keys = ["school_name", "contact_person", "email", "phone",
                      "reservation_date", "reservation_time", "program_name"]
        for key in sample_keys:
            assert key in data["sample_data"], f"Missing sample key: {key}"
            
    def test_preview_uses_program_data(self, authenticated_client):
        """Preview should use actual program data for program_name."""
        payload = {
            "subject": "{{program_name}}",
            "body": "<p>Test</p>"
        }
        response = authenticated_client.post(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template/preview",
            json=payload
        )
        data = response.json()
        # program_name in sample_data should be the actual program's name
        assert data["sample_data"]["program_name"] != ""
        assert len(data["sample_data"]["program_name"]) > 0
        
    def test_preview_404_for_invalid_program(self, authenticated_client):
        """Preview should return 404 for non-existent program."""
        payload = {
            "subject": "Test",
            "body": "<p>Test</p>"
        }
        response = authenticated_client.post(
            f"{BASE_URL}/api/programs/00000000-0000-0000-0000-000000000000/email-template/preview",
            json=payload
        )
        assert response.status_code == 404


class TestEmailTemplateIntegration:
    """Integration tests for email template workflow."""
    
    def test_save_and_retrieve_template(self, authenticated_client):
        """Save template then retrieve it - data should match."""
        # Save new template
        save_payload = {
            "subject": "Integration Test - {{program_name}}",
            "body": "<h2>Integration Test</h2><p>Hello {{contact_person}}</p>"
        }
        save_response = authenticated_client.put(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template",
            json=save_payload
        )
        assert save_response.status_code == 200
        
        # Retrieve template
        get_response = authenticated_client.get(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template"
        )
        assert get_response.status_code == 200
        data = get_response.json()
        
        # Verify data matches
        assert data["template"]["subject"] == save_payload["subject"]
        assert data["template"]["body"] == save_payload["body"]
        
    def test_preview_matches_saved_template(self, authenticated_client):
        """Preview should work with saved template data."""
        # Save template first
        save_payload = {
            "subject": "Preview Test - {{program_name}}",
            "body": "<p>Contact: {{contact_person}}, Phone: {{phone}}</p>"
        }
        authenticated_client.put(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template",
            json=save_payload
        )
        
        # Get preview
        preview_response = authenticated_client.post(
            f"{BASE_URL}/api/programs/{TEST_PROGRAM_ID}/email-template/preview",
            json=save_payload
        )
        assert preview_response.status_code == 200
        data = preview_response.json()
        
        # Preview should have replaced variables
        assert "{{program_name}}" not in data["preview"]["subject"]
        assert "{{contact_person}}" not in data["preview"]["body"]
        assert "{{phone}}" not in data["preview"]["body"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
