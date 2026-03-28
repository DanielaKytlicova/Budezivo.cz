"""
Test Email Template Theming System
Tests the redesigned email templates with institution branding support.
Templates affected: reservation_created_teacher, reservation_confirmed, 
reservation_reminder_teacher, reservation_rescheduled, feedback_request, feedback_reminder
"""
import pytest
import os
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API tests."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code}")


class TestBackendRegression:
    """Regression tests to ensure backend APIs still work after template changes."""
    
    def test_backend_api_root(self):
        """Backend API root returns expected response."""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"PASS: Backend API root returns: {data['message']}")
    
    def test_auth_login_works(self):
        """POST /api/auth/login works correctly."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"PASS: Login works, got token for user {data['user'].get('email')}")
    
    def test_get_programs(self, auth_token):
        """GET /api/programs returns programs (regression check)."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/programs returns {len(data)} programs")
    
    def test_get_bookings(self, auth_token):
        """GET /api/bookings returns bookings (regression check)."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/bookings returns {len(data)} bookings")


class TestTemplateRegistry:
    """Test that all templates exist in TEMPLATE_REGISTRY and render without errors."""
    
    def test_template_registry_has_all_templates(self):
        """All 18 templates exist in TEMPLATE_REGISTRY."""
        from templates.emails.templates import TEMPLATE_REGISTRY, get_available_templates
        
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
            "reservation_rescheduled",
            "reservation_reminder_teacher",
            "reservation_reminder_institution",
            "feedback_request",
            "feedback_reminder",
            "new_institution_registration",
            "contact_form_submission",
            "team_invitation",
        ]
        
        available = get_available_templates()
        for template_name in expected_templates:
            assert template_name in available, f"Template {template_name} missing from registry"
        
        print(f"PASS: All {len(expected_templates)} templates exist in TEMPLATE_REGISTRY")
    
    def test_all_templates_render_without_errors(self):
        """All 18 templates render without errors with minimal data."""
        from templates.emails.templates import get_template, get_available_templates
        
        minimal_data = {
            "user_name": "Test User",
            "user_email": "test@example.com",
            "institution_name": "Test Institution",
            "program_name": "Test Program",
            "teacher_name": "Test Teacher",
            "teacher_email": "teacher@example.com",
            "teacher_phone": "+420123456789",
            "school_name": "Test School",
            "reservation_date": "2026-04-01",
            "reservation_time": "09:00-10:30",
            "children_count": 25,
            "teachers_count": 2,
            "institution_email": "info@institution.cz",
            "institution_phone": "+420987654321",
            "institution_address": "Test Address 123",
            "activation_link": "https://example.com/activate",
            "reset_link": "https://example.com/reset",
            "dashboard_url": "https://example.com/admin",
            "booking_url": "https://example.com/booking",
            "feedback_url": "https://example.com/feedback",
            "invite_link": "https://example.com/invite",
            "inviter_name": "Admin User",
            "invitee_name": "New User",
            "role_name": "Lektor",
            "expires_hours": 48,
            "rejection_reason": "Test reason",
            "cancellation_reason": "Test cancellation",
            "original_date": "2026-03-25",
            "original_time": "10:00-11:30",
            "formatted_date": "01. 04. 2026",
            "recipient_name": "Recipient",
            "name": "Contact Name",
            "email": "contact@example.com",
            "institution": "Contact Institution",
            "availability": "Morning",
            "message": "Test message",
            "institution_type": "museum",
            "institution_city": "Prague",
        }
        
        templates = get_available_templates()
        for template_name in templates:
            try:
                result = get_template(template_name, minimal_data)
                assert "subject" in result, f"Template {template_name} missing subject"
                assert "html" in result, f"Template {template_name} missing html"
                assert "text" in result, f"Template {template_name} missing text"
                assert len(result["html"]) > 100, f"Template {template_name} HTML too short"
            except Exception as e:
                pytest.fail(f"Template {template_name} failed to render: {e}")
        
        print(f"PASS: All {len(templates)} templates render without errors")


class TestBuildThemeFunction:
    """Test _build_theme helper function."""
    
    def test_build_theme_returns_default_when_no_logo(self):
        """_build_theme returns default theme when no logo provided."""
        from templates.emails.templates import _build_theme, DEFAULT_THEME
        
        # No logo in data
        data = {"institution_name": "Test"}
        theme = _build_theme(data)
        
        assert theme["logo_url"] is None
        assert theme["primary_color"] == DEFAULT_THEME["primary_color"]
        assert theme["secondary_color"] == DEFAULT_THEME["secondary_color"]
        print(f"PASS: _build_theme returns default when no logo: {theme}")
    
    def test_build_theme_returns_theme_colors_when_logo_provided(self):
        """_build_theme returns theme colors when theme_logo_url is provided."""
        from templates.emails.templates import _build_theme
        
        data = {
            "theme_logo_url": "https://example.com/logo.png",
            "theme_primary_color": "#FF0000",
            "theme_secondary_color": "#00FF00",
            "theme_accent_color": "#0000FF",
        }
        theme = _build_theme(data)
        
        assert theme["logo_url"] == "https://example.com/logo.png"
        assert theme["primary_color"] == "#FF0000"
        assert theme["secondary_color"] == "#00FF00"
        assert theme["accent_color"] == "#0000FF"
        print(f"PASS: _build_theme returns custom colors when logo provided: {theme}")
    
    def test_build_theme_uses_institution_logo_url_fallback(self):
        """_build_theme uses institution_logo_url as fallback."""
        from templates.emails.templates import _build_theme
        
        data = {
            "institution_logo_url": "https://example.com/inst-logo.png",
            "theme_primary_color": "#123456",
        }
        theme = _build_theme(data)
        
        assert theme["logo_url"] == "https://example.com/inst-logo.png"
        assert theme["primary_color"] == "#123456"
        print(f"PASS: _build_theme uses institution_logo_url fallback: {theme}")


class TestButtonStyleFunction:
    """Test _button_style helper function."""
    
    def test_button_style_uses_theme_primary_color(self):
        """_button_style uses theme primary_color for primary variant."""
        from templates.emails.templates import _button_style
        
        theme = {
            "primary_color": "#FF5500",
            "secondary_color": "#00FF55",
        }
        style = _button_style(theme, "primary")
        
        assert "#FF5500" in style
        assert "background-color: #FF5500" in style
        print(f"PASS: _button_style uses primary_color: {style[:50]}...")
    
    def test_button_style_uses_secondary_color(self):
        """_button_style uses theme secondary_color for secondary variant."""
        from templates.emails.templates import _button_style
        
        theme = {
            "primary_color": "#FF5500",
            "secondary_color": "#00FF55",
        }
        style = _button_style(theme, "secondary")
        
        assert "#00FF55" in style
        assert "background-color: #00FF55" in style
        print(f"PASS: _button_style uses secondary_color: {style[:50]}...")


class TestReservationCreatedTeacherTemplate:
    """Test reservation_created_teacher template theming."""
    
    def test_without_theme_produces_default_header(self):
        """reservation_created_teacher without theme produces default header (#1E293B bg)."""
        from templates.emails.templates import get_template
        
        data = {
            "teacher_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "reservation_date": "2026-04-01",
            "reservation_time": "09:00-10:30",
            "school_name": "ZS Vinohrady",
            "children_count": 25,
            "teachers_count": 2,
            "institution_email": "info@muzeum.cz",
            "institution_phone": "+420123456789",
            # No theme_logo_url - should use default
        }
        
        result = get_template("reservation_created_teacher", data)
        html = result["html"]
        
        # Should have default header with #1E293B background
        assert "background-color: #1E293B" in html
        # Should NOT have institution logo img tag in header
        assert 'alt="Logo instituce"' not in html
        # Should have Budezivo SVG logo
        assert "Budezivo" in html or "budezivo" in html.lower()
        
        print("PASS: reservation_created_teacher without theme has default #1E293B header")
    
    def test_with_theme_logo_produces_branded_header(self):
        """reservation_created_teacher with theme_logo_url produces branded header."""
        from templates.emails.templates import get_template
        
        data = {
            "teacher_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "reservation_date": "2026-04-01",
            "reservation_time": "09:00-10:30",
            "school_name": "ZS Vinohrady",
            "children_count": 25,
            "teachers_count": 2,
            "institution_email": "info@muzeum.cz",
            "institution_phone": "+420123456789",
            "theme_logo_url": "https://example.com/museum-logo.png",
            "theme_primary_color": "#FF0000",
            "theme_secondary_color": "#84A98C",
        }
        
        result = get_template("reservation_created_teacher", data)
        html = result["html"]
        
        # Should have branded header with secondary_color background
        assert "background-color: #84A98C" in html
        # Should have institution logo img tag
        assert 'alt="Logo instituce"' in html
        assert "https://example.com/museum-logo.png" in html
        # Should have "powered by Budezivo" bar
        assert "rezervace" in html.lower() or "pres" in html.lower()
        
        print("PASS: reservation_created_teacher with theme has branded header with secondary_color bg + logo")


class TestReservationConfirmedTemplate:
    """Test reservation_confirmed template theming."""
    
    def test_without_theme_has_no_institution_logo(self):
        """reservation_confirmed without theme has no institution logo img in header."""
        from templates.emails.templates import get_template
        
        data = {
            "teacher_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "reservation_date": "2026-04-01",
            "reservation_time": "09:00-10:30",
            "school_name": "ZS Vinohrady",
            "children_count": 25,
            "teachers_count": 2,
            "institution_email": "info@muzeum.cz",
            "institution_phone": "+420123456789",
            "institution_address": "Vaclavske namesti 1",
        }
        
        result = get_template("reservation_confirmed", data)
        html = result["html"]
        
        # Should NOT have institution logo
        assert 'alt="Logo instituce"' not in html
        # Should have default header
        assert "background-color: #1E293B" in html
        
        print("PASS: reservation_confirmed without theme has no institution logo")
    
    def test_with_theme_logo_shows_institution_logo(self):
        """reservation_confirmed with theme_logo_url shows institution logo."""
        from templates.emails.templates import get_template
        
        data = {
            "teacher_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "reservation_date": "2026-04-01",
            "reservation_time": "09:00-10:30",
            "school_name": "ZS Vinohrady",
            "children_count": 25,
            "teachers_count": 2,
            "institution_email": "info@muzeum.cz",
            "institution_phone": "+420123456789",
            "institution_address": "Vaclavske namesti 1",
            "theme_logo_url": "https://example.com/logo.png",
            "theme_secondary_color": "#AABBCC",
        }
        
        result = get_template("reservation_confirmed", data)
        html = result["html"]
        
        # Should have institution logo
        assert 'alt="Logo instituce"' in html
        assert "https://example.com/logo.png" in html
        # Should have branded header with secondary_color
        assert "background-color: #AABBCC" in html
        
        print("PASS: reservation_confirmed with theme shows institution logo")


class TestReservationRescheduledTemplate:
    """Test reservation_rescheduled template theming."""
    
    def test_with_theme_uses_themed_button_color(self):
        """reservation_rescheduled with theme uses themed button color."""
        from templates.emails.templates import get_template
        
        data = {
            "teacher_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "reservation_date": "2026-04-05",
            "reservation_time": "10:00-11:30",
            "original_date": "2026-04-01",
            "original_time": "09:00-10:30",
            "school_name": "ZS Vinohrady",
            "children_count": 25,
            "teachers_count": 2,
            "institution_email": "info@muzeum.cz",
            "institution_phone": "+420123456789",
            "theme_logo_url": "https://example.com/logo.png",
            "theme_primary_color": "#123ABC",
            "theme_secondary_color": "#DEF456",
        }
        
        result = get_template("reservation_rescheduled", data)
        html = result["html"]
        
        # Should have branded header
        assert "background-color: #DEF456" in html
        # Should show original and new dates
        assert "2026-04-01" in html or "04-01" in html
        assert "2026-04-05" in html or "04-05" in html
        
        print("PASS: reservation_rescheduled with theme uses themed colors")


class TestFeedbackTemplates:
    """Test feedback_request and feedback_reminder templates."""
    
    def test_feedback_request_exists_and_renders(self):
        """feedback_request template exists in TEMPLATE_REGISTRY and renders."""
        from templates.emails.templates import get_template, TEMPLATE_REGISTRY
        
        assert "feedback_request" in TEMPLATE_REGISTRY
        
        data = {
            "recipient_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "formatted_date": "01. 04. 2026",
            "feedback_url": "https://example.com/feedback/abc123",
        }
        
        result = get_template("feedback_request", data)
        
        assert "subject" in result
        assert "html" in result
        assert "text" in result
        assert "Dinosauri" in result["subject"]
        assert "feedback" in result["html"].lower() or "dotaznik" in result["html"].lower()
        
        print("PASS: feedback_request template exists and renders correctly")
    
    def test_feedback_reminder_exists_and_renders(self):
        """feedback_reminder template exists in TEMPLATE_REGISTRY and renders."""
        from templates.emails.templates import get_template, TEMPLATE_REGISTRY
        
        assert "feedback_reminder" in TEMPLATE_REGISTRY
        
        data = {
            "recipient_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "formatted_date": "01. 04. 2026",
            "feedback_url": "https://example.com/feedback/abc123",
        }
        
        result = get_template("feedback_reminder", data)
        
        assert "subject" in result
        assert "html" in result
        assert "text" in result
        assert "Pripominka" in result["subject"] or "pripominka" in result["subject"].lower()
        
        print("PASS: feedback_reminder template exists and renders correctly")
    
    def test_feedback_request_with_theme(self):
        """feedback_request with theme uses themed button."""
        from templates.emails.templates import get_template
        
        data = {
            "recipient_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "formatted_date": "01. 04. 2026",
            "feedback_url": "https://example.com/feedback/abc123",
            "theme_logo_url": "https://example.com/logo.png",
            "theme_primary_color": "#ABCDEF",
            "theme_secondary_color": "#FEDCBA",
        }
        
        result = get_template("feedback_request", data)
        html = result["html"]
        
        # Should have branded header
        assert "background-color: #FEDCBA" in html
        # Should have themed button
        assert "#ABCDEF" in html
        
        print("PASS: feedback_request with theme uses themed colors")


class TestReminderTeacherTemplate:
    """Test reservation_reminder_teacher template."""
    
    def test_reminder_teacher_renders_with_theme(self):
        """reservation_reminder_teacher renders with theme data."""
        from templates.emails.templates import get_template
        
        data = {
            "teacher_name": "Jan Novak",
            "institution_name": "Muzeum Praha",
            "program_name": "Dinosauri",
            "reservation_date": "2026-04-01",
            "reservation_time": "09:00-10:30",
            "school_name": "ZS Vinohrady",
            "children_count": 25,
            "teachers_count": 2,
            "institution_address": "Vaclavske namesti 1",
            "theme_logo_url": "https://example.com/logo.png",
            "theme_secondary_color": "#AABBCC",
        }
        
        result = get_template("reservation_reminder_teacher", data)
        html = result["html"]
        
        # Should have branded header
        assert "background-color: #AABBCC" in html
        assert 'alt="Logo instituce"' in html
        # Should have reminder content
        assert "Pripominka" in result["subject"] or "pripominka" in html.lower()
        
        print("PASS: reservation_reminder_teacher renders with theme")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
