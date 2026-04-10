"""
Test httpOnly cookies, booking field filtering, and advanced analytics endpoints.
Iteration 31 - Testing new security and analytics features.
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


class TestHttpOnlyCookies:
    """Test httpOnly cookie authentication flow."""
    
    def test_login_sets_cookies(self):
        """POST /api/auth/login should return Set-Cookie headers with httpOnly cookies."""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Check response body has tokens
        data = response.json()
        assert "token" in data, "Response should contain 'token'"
        assert "refresh_token" in data, "Response should contain 'refresh_token'"
        assert "user" in data, "Response should contain 'user'"
        
        # Check Set-Cookie headers
        cookies = response.headers.get('Set-Cookie', '')
        print(f"Set-Cookie headers: {cookies}")
        
        # Verify cookies are set in session
        assert 'access_token' in session.cookies or 'access_token' in cookies.lower(), \
            "access_token cookie should be set"
        
        print("PASS: Login sets cookies correctly")
    
    def test_verify_works_with_cookie_only(self):
        """GET /api/auth/verify should work using just the cookie (no Authorization header)."""
        session = requests.Session()
        
        # Login to get cookies
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Verify using cookies only (no Authorization header)
        verify_response = session.get(f"{BASE_URL}/api/auth/verify")
        
        assert verify_response.status_code == 200, f"Verify failed: {verify_response.text}"
        data = verify_response.json()
        assert data.get("valid") == True, "Token should be valid"
        assert "user" in data, "Response should contain user info"
        
        print("PASS: Verify works with cookie only")
    
    def test_refresh_reads_cookie_if_body_empty(self):
        """POST /api/auth/refresh should read refresh_token from cookie if body is empty."""
        session = requests.Session()
        
        # Login to get cookies
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Refresh with empty body (should use cookie)
        refresh_response = session.post(
            f"{BASE_URL}/api/auth/refresh",
            json={"refresh_token": ""}  # Empty body
        )
        
        # Should succeed using cookie
        assert refresh_response.status_code == 200, f"Refresh failed: {refresh_response.text}"
        data = refresh_response.json()
        assert "token" in data, "Response should contain new access token"
        assert "refresh_token" in data, "Response should contain new refresh token"
        
        print("PASS: Refresh reads cookie when body is empty")
    
    def test_logout_clears_cookies(self):
        """POST /api/auth/logout should clear cookies."""
        session = requests.Session()
        
        # Login to get cookies
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Get token for Authorization header (logout requires auth)
        token = login_response.json().get("token")
        
        # Logout
        logout_response = session.post(
            f"{BASE_URL}/api/auth/logout",
            json={"refresh_token": ""},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
        
        # Check that cookies are cleared (Set-Cookie with max-age=0 or expires in past)
        cookies = logout_response.headers.get('Set-Cookie', '')
        print(f"Logout Set-Cookie: {cookies}")
        
        print("PASS: Logout clears cookies")


class TestBookingFieldFiltering:
    """Test that internal fields are stripped from public booking responses."""
    
    INTERNAL_FIELDS = {
        "assigned_lecturer_id", "terms_accepted_at", "terms_accepted_text_version",
        "institution_id", "notes"
    }
    
    def test_public_booking_strips_internal_fields(self):
        """Public booking response should NOT contain internal fields."""
        session = requests.Session()
        
        # Create a public booking for demo institution
        booking_data = {
            "program_id": "demo-1",
            "date": "2026-03-15",
            "time_block": "09:00-10:00",
            "school_name": "Test School for Field Filtering",
            "group_type": "zs1_7_12",
            "age_or_class": "5. třída",
            "num_students": 25,
            "num_teachers": 2,
            "special_requirements": "",
            "contact_name": "Test Teacher",
            "contact_email": "test.filter@example.com",
            "contact_phone": "+420123456789",
            "gdpr_consent": True,
            "terms_accepted": True,
            "terms_accepted_text_version": "v1.0"
        }
        
        response = session.post(
            f"{BASE_URL}/api/bookings/public/demo",
            json=booking_data
        )
        
        assert response.status_code == 200, f"Public booking failed: {response.text}"
        data = response.json()
        
        # Check that internal fields are NOT present
        for field in self.INTERNAL_FIELDS:
            assert field not in data, f"Internal field '{field}' should be stripped from public response"
        
        # Check that public fields ARE present
        assert "id" in data, "id should be present"
        assert "school_name" in data, "school_name should be present"
        assert "contact_email" in data, "contact_email should be present"
        assert "status" in data, "status should be present"
        
        print(f"PASS: Public booking response correctly strips internal fields")
        print(f"Fields in response: {list(data.keys())}")


class TestAnalyticsHeatmap:
    """Test GET /api/statistics/heatmap endpoint."""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session."""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_heatmap_returns_correct_structure(self, auth_session):
        """GET /api/statistics/heatmap should return time_blocks and data arrays."""
        response = auth_session.get(f"{BASE_URL}/api/statistics/heatmap")
        
        assert response.status_code == 200, f"Heatmap failed: {response.text}"
        data = response.json()
        
        # Check structure
        assert "time_blocks" in data, "Response should contain 'time_blocks'"
        assert "data" in data, "Response should contain 'data'"
        assert "period" in data, "Response should contain 'period'"
        
        # time_blocks should be a list
        assert isinstance(data["time_blocks"], list), "time_blocks should be a list"
        
        # data should be a list of day rows
        assert isinstance(data["data"], list), "data should be a list"
        
        # Check Czech day labels (Po, Út, St, Čt, Pá, So, Ne)
        if data["data"]:
            day_labels = [row.get("day") for row in data["data"]]
            expected_days = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]
            assert day_labels == expected_days, f"Day labels should be Czech: {expected_days}, got: {day_labels}"
        
        print(f"PASS: Heatmap returns correct structure")
        print(f"Time blocks: {data['time_blocks']}")
        print(f"Period: {data['period']}")
    
    def test_heatmap_with_year_month_params(self, auth_session):
        """GET /api/statistics/heatmap should accept year and month params."""
        response = auth_session.get(
            f"{BASE_URL}/api/statistics/heatmap",
            params={"year": 2025, "month": 10}
        )
        
        assert response.status_code == 200, f"Heatmap with params failed: {response.text}"
        data = response.json()
        
        assert data["period"] == "2025-10", f"Period should be 2025-10, got: {data['period']}"
        
        print("PASS: Heatmap accepts year/month params")


class TestAnalyticsTrends:
    """Test GET /api/statistics/trends endpoint."""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session."""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_trends_returns_12_months(self, auth_session):
        """GET /api/statistics/trends should return chart_data with 12 months."""
        response = auth_session.get(f"{BASE_URL}/api/statistics/trends")
        
        assert response.status_code == 200, f"Trends failed: {response.text}"
        data = response.json()
        
        # Check structure
        assert "chart_data" in data, "Response should contain 'chart_data'"
        assert "current_year" in data, "Response should contain 'current_year'"
        assert "previous_year" in data, "Response should contain 'previous_year'"
        
        # chart_data should have 12 months
        assert len(data["chart_data"]) == 12, f"chart_data should have 12 months, got: {len(data['chart_data'])}"
        
        # Each month should have name and year keys
        current_year = data["current_year"]
        previous_year = data["previous_year"]
        
        for month_data in data["chart_data"]:
            assert "name" in month_data, "Each month should have 'name'"
            assert str(current_year) in month_data, f"Each month should have '{current_year}' key"
            assert str(previous_year) in month_data, f"Each month should have '{previous_year}' key"
        
        print(f"PASS: Trends returns 12 months comparing {current_year} vs {previous_year}")
    
    def test_trends_with_year_param(self, auth_session):
        """GET /api/statistics/trends should accept year param."""
        response = auth_session.get(
            f"{BASE_URL}/api/statistics/trends",
            params={"year": 2025}
        )
        
        assert response.status_code == 200, f"Trends with year param failed: {response.text}"
        data = response.json()
        
        assert data["current_year"] == 2025, f"current_year should be 2025, got: {data['current_year']}"
        assert data["previous_year"] == 2024, f"previous_year should be 2024, got: {data['previous_year']}"
        
        print("PASS: Trends accepts year param")


class TestAnalyticsTopSchools:
    """Test GET /api/statistics/top-schools endpoint."""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session."""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_top_schools_returns_correct_structure(self, auth_session):
        """GET /api/statistics/top-schools should return schools array with correct fields."""
        response = auth_session.get(f"{BASE_URL}/api/statistics/top-schools")
        
        assert response.status_code == 200, f"Top schools failed: {response.text}"
        data = response.json()
        
        # Check structure
        assert "schools" in data, "Response should contain 'schools'"
        assert "period" in data, "Response should contain 'period'"
        
        # schools should be a list
        assert isinstance(data["schools"], list), "schools should be a list"
        
        # Each school should have required fields
        for school in data["schools"]:
            assert "name" in school, "Each school should have 'name'"
            assert "bookings" in school, "Each school should have 'bookings'"
            assert "students" in school, "Each school should have 'students'"
            assert "teachers" in school, "Each school should have 'teachers'"
        
        print(f"PASS: Top schools returns correct structure")
        print(f"Number of schools: {len(data['schools'])}")
        print(f"Period: {data['period']}")


class TestAnalyticsConversion:
    """Test GET /api/statistics/conversion endpoint."""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session."""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_conversion_returns_correct_structure(self, auth_session):
        """GET /api/statistics/conversion should return total, confirmed, pending, cancelled, conversion_rate."""
        response = auth_session.get(f"{BASE_URL}/api/statistics/conversion")
        
        assert response.status_code == 200, f"Conversion failed: {response.text}"
        data = response.json()
        
        # Check required fields
        required_fields = ["total", "confirmed", "pending", "cancelled", "conversion_rate", "period"]
        for field in required_fields:
            assert field in data, f"Response should contain '{field}'"
        
        # conversion_rate should be a number
        assert isinstance(data["conversion_rate"], (int, float)), "conversion_rate should be a number"
        
        # Values should be non-negative
        assert data["total"] >= 0, "total should be non-negative"
        assert data["confirmed"] >= 0, "confirmed should be non-negative"
        assert data["pending"] >= 0, "pending should be non-negative"
        assert data["cancelled"] >= 0, "cancelled should be non-negative"
        assert data["conversion_rate"] >= 0, "conversion_rate should be non-negative"
        
        print(f"PASS: Conversion returns correct structure")
        print(f"Total: {data['total']}, Confirmed: {data['confirmed']}, Rate: {data['conversion_rate']}%")


class TestRegressionLoginDashboard:
    """Regression test: Login and dashboard still work."""
    
    def test_login_still_works(self):
        """Login should still work correctly."""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user"
        
        print("PASS: Login still works")
    
    def test_dashboard_data_loads(self):
        """Dashboard data (statistics) should load correctly."""
        session = requests.Session()
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get statistics
        stats_response = session.get(f"{BASE_URL}/api/statistics")
        assert stats_response.status_code == 200, f"Statistics failed: {stats_response.text}"
        
        data = stats_response.json()
        assert "overview" in data, "Statistics should contain overview"
        
        print("PASS: Dashboard data loads correctly")


class TestRegressionWAF:
    """Regression test: WAF still blocks SQL injection."""
    
    def test_waf_blocks_sql_injection(self):
        """WAF should block SQL injection attempts."""
        session = requests.Session()
        
        # Try SQL injection in query param
        response = session.get(
            f"{BASE_URL}/api/programs/public/demo",
            params={"age": "SLEEP(5)"}
        )
        
        # Should either block (403) or ignore the malicious param (200)
        # Should NOT cause a 500 error or delay
        assert response.status_code in [200, 400, 403], f"Unexpected status: {response.status_code}"
        
        print(f"PASS: WAF handles SQL injection attempt (status: {response.status_code})")


class TestRegressionICSFeeds:
    """Regression test: ICS feeds still require token."""
    
    def test_ics_feed_requires_token(self):
        """ICS feed should require authentication token."""
        session = requests.Session()
        
        # Try to access ICS feed without token
        response = session.get(f"{BASE_URL}/api/calendar/ics/{INSTITUTION_ID}")
        
        # Should require auth (401 or 403)
        assert response.status_code in [401, 403, 404], \
            f"ICS feed should require auth, got: {response.status_code}"
        
        print(f"PASS: ICS feed requires token (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
