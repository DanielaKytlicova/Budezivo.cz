"""
Test suite for Email System API endpoints
Tests: Email config, templates, variables, test emails, logs, and account deletion
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://ares-integration.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


class TestEmailConfigEndpoints:
    """Tests for public email configuration endpoints."""
    
    def test_get_email_config(self):
        """GET /api/emails/config - returns email service configuration."""
        response = requests.get(f"{BASE_URL}/api/emails/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "configured" in data
        assert "development_mode" in data
        assert "available_templates" in data
        assert "sender_addresses" in data
        assert isinstance(data["available_templates"], list)
        assert len(data["available_templates"]) == 13
        print(f"PASS: Email config returned with {len(data['available_templates'])} templates")
    
    def test_get_email_templates(self):
        """GET /api/emails/templates - lists all 13 email templates."""
        response = requests.get(f"{BASE_URL}/api/emails/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert "templates" in data
        assert "count" in data
        assert "categories" in data
        assert data["count"] == 13
        
        # Verify categories
        categories = data["categories"]
        assert "account" in categories
        assert "reservation" in categories
        assert "reminder" in categories
        assert "admin" in categories
        
        # Verify all 13 templates
        expected_templates = [
            "user_registration_confirmation",
            "account_activation",
            "password_reset",
            "password_changed",
            "reservation_created_teacher",
            "reservation_created_institution",
            "reservation_confirmed",
            "reservation_rejected",
            "reservation_updated",
            "reservation_cancelled",
            "reservation_reminder_teacher",
            "reservation_reminder_institution",
            "new_institution_registration"
        ]
        for template in expected_templates:
            assert template in data["templates"], f"Missing template: {template}"
        print(f"PASS: All 13 templates listed correctly")
    
    def test_get_template_variables(self):
        """GET /api/emails/variables - lists available template variables."""
        response = requests.get(f"{BASE_URL}/api/emails/variables")
        assert response.status_code == 200
        
        data = response.json()
        assert "variables" in data
        assert "count" in data
        
        # Verify key variables exist
        required_vars = [
            "institution_name",
            "program_name",
            "teacher_name",
            "school_name",
            "reservation_date",
            "reset_link",
            "dashboard_url"
        ]
        for var in required_vars:
            assert var in data["variables"], f"Missing variable: {var}"
        print(f"PASS: {data['count']} template variables returned")


class TestTemplatePreviewEndpoints:
    """Tests for template preview endpoints."""
    
    def test_get_template_preview_password_reset(self):
        """GET /api/emails/templates/password_reset - preview specific template."""
        response = requests.get(f"{BASE_URL}/api/emails/templates/password_reset")
        assert response.status_code == 200
        
        data = response.json()
        assert data["template_name"] == "password_reset"
        assert "subject" in data
        assert "html" in data
        assert "text" in data
        assert "sample_data" in data
        
        # Verify HTML structure
        assert "Obnovení hesla" in data["html"]
        assert "Budeživo.cz" in data["html"]
        print("PASS: Password reset template preview returned correctly")
    
    def test_get_template_preview_reservation_confirmed(self):
        """GET /api/emails/templates/reservation_confirmed - preview reservation template."""
        response = requests.get(f"{BASE_URL}/api/emails/templates/reservation_confirmed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["template_name"] == "reservation_confirmed"
        assert "Rezervace potvrzena" in data["subject"]
        print("PASS: Reservation confirmed template preview returned correctly")
    
    def test_get_template_preview_404(self):
        """GET /api/emails/templates/{nonexistent} - returns 404."""
        response = requests.get(f"{BASE_URL}/api/emails/templates/nonexistent_template")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        print("PASS: Nonexistent template returns 404")


class TestAuthenticatedEndpoints:
    """Tests for authenticated email endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login and get auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed - skipping authenticated tests")
        
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_email_logs(self):
        """GET /api/emails/logs - get email logs for institution."""
        response = requests.get(f"{BASE_URL}/api/emails/logs", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "logs" in data
        assert "count" in data
        assert isinstance(data["logs"], list)
        print(f"PASS: Email logs returned ({data['count']} logs)")
    
    def test_send_test_email(self):
        """POST /api/emails/test - send test email (requires auth)."""
        response = requests.post(
            f"{BASE_URL}/api/emails/test",
            headers=self.headers,
            json={
                "email_type": "reservation_confirmed",
                "email": "testing@example.com"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "sent"
        assert data["template_name"] == "reservation_confirmed"
        assert "email_id" in data
        print(f"PASS: Test email sent successfully, ID: {data['email_id']}")
    
    def test_send_test_email_invalid_type(self):
        """POST /api/emails/test - returns 400 for invalid template type."""
        response = requests.post(
            f"{BASE_URL}/api/emails/test",
            headers=self.headers,
            json={
                "email_type": "invalid_email_type",
                "email": "test@example.com"
            }
        )
        assert response.status_code == 400
        assert "Unknown email type" in response.json()["detail"]
        print("PASS: Invalid email type returns 400")


class TestAccountEndpoints:
    """Tests for account management endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login and get auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed - skipping authenticated tests")
        
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_account_status(self):
        """GET /api/account/status - get account status with can_delete flag."""
        response = requests.get(f"{BASE_URL}/api/account/status", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "user" in data
        assert "institution" in data
        assert "can_delete" in data
        
        # Verify user data structure
        user = data["user"]
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "status" in user
        
        # Verify institution data structure
        institution = data["institution"]
        assert "id" in institution
        assert "name" in institution
        
        print(f"PASS: Account status returned (can_delete={data['can_delete']})")
    
    def test_delete_account_wrong_confirmation(self):
        """DELETE /api/account/delete - returns 400 without DELETE confirmation."""
        response = requests.delete(
            f"{BASE_URL}/api/account/delete",
            headers=self.headers,
            json={"confirmation": "wrong"}
        )
        assert response.status_code == 400
        assert "DELETE" in response.json()["detail"]
        print("PASS: Delete without proper confirmation returns 400")
    
    def test_delete_account_requires_auth(self):
        """DELETE /api/account/delete - returns 401/403 without auth."""
        response = requests.delete(
            f"{BASE_URL}/api/account/delete",
            json={"confirmation": "DELETE"}
        )
        assert response.status_code in [401, 403, 422]  # Unauthorized, Forbidden or validation error
        print("PASS: Delete account requires authentication")


class TestEmailServiceIntegration:
    """Integration tests for email service."""
    
    def test_email_service_configured(self):
        """Verify email service reports configured status."""
        response = requests.get(f"{BASE_URL}/api/emails/config")
        assert response.status_code == 200
        
        data = response.json()
        # Since RESEND_API_KEY is configured, service should be configured
        assert data["configured"] == True
        print("PASS: Email service is configured")
    
    def test_sender_addresses_configured(self):
        """Verify all three sender addresses are configured."""
        response = requests.get(f"{BASE_URL}/api/emails/config")
        assert response.status_code == 200
        
        data = response.json()
        senders = data["sender_addresses"]
        
        # Check for all three required sender types
        assert "no_reply" in senders
        assert "reservations" in senders
        assert "accounts" in senders
        
        # Verify they contain the proper domain
        assert "budezivo.cz" in senders["no_reply"]
        assert "budezivo.cz" in senders["reservations"]
        assert "budezivo.cz" in senders["accounts"]
        print("PASS: All sender addresses configured correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
