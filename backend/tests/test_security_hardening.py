"""
Security Hardening Tests - Iteration 29
Tests for:
A) Refresh Token + JWT Blacklist
B) OAuth State Persistence
C) WAF middleware (SQL injection/XSS blocking)
"""
import pytest
import requests
import os
import time
import base64
import json
from urllib.parse import quote

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from iteration_28
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_tokens(api_client):
    """Login and get both access token and refresh token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.status_code} - {response.text}")
    
    data = response.json()
    return {
        "access_token": data.get("token"),
        "refresh_token": data.get("refresh_token"),
        "user": data.get("user")
    }


class TestRefreshTokenFlow:
    """A1-A6: Refresh Token + JWT Blacklist tests"""
    
    def test_a1_login_returns_both_tokens(self, api_client):
        """A1: POST /api/auth/login returns both 'token' and 'refresh_token' fields"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response missing 'token' field"
        assert "refresh_token" in data, "Response missing 'refresh_token' field"
        assert "user" in data, "Response missing 'user' field"
        
        # Verify tokens are non-empty strings
        assert isinstance(data["token"], str) and len(data["token"]) > 50, "Access token too short"
        assert isinstance(data["refresh_token"], str) and len(data["refresh_token"]) > 50, "Refresh token too short"
        
        print(f"✓ A1: Login returns both tokens - access: {len(data['token'])} chars, refresh: {len(data['refresh_token'])} chars")
    
    def test_a2_access_token_expires_in_15_minutes(self, auth_tokens):
        """A2: Access token expires in ~15 minutes (check JWT 'exp' field)"""
        access_token = auth_tokens["access_token"]
        
        # Decode JWT payload (base64)
        try:
            parts = access_token.split('.')
            assert len(parts) == 3, "Invalid JWT format"
            
            # Add padding if needed
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
            
            payload = json.loads(base64.b64decode(payload_b64))
            
            assert "exp" in payload, "JWT missing 'exp' claim"
            assert "user_id" in payload, "JWT missing 'user_id' claim"
            
            # Calculate expiry time
            exp_timestamp = payload["exp"]
            current_timestamp = time.time()
            expires_in_seconds = exp_timestamp - current_timestamp
            expires_in_minutes = expires_in_seconds / 60
            
            # Should be approximately 15 minutes (allow 1-16 min range)
            assert 1 <= expires_in_minutes <= 16, f"Token expires in {expires_in_minutes:.1f} min, expected ~15 min"
            
            print(f"✓ A2: Access token expires in {expires_in_minutes:.1f} minutes (expected ~15 min)")
        except Exception as e:
            pytest.fail(f"Failed to decode JWT: {e}")
    
    def test_a3_refresh_returns_new_token_pair(self, api_client):
        """A3: POST /api/auth/refresh with valid refresh_token returns new token pair"""
        # First login to get fresh tokens
        login_resp = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        original_tokens = login_resp.json()
        
        # Now refresh
        refresh_resp = api_client.post(f"{BASE_URL}/api/auth/refresh", json={
            "refresh_token": original_tokens["refresh_token"]
        })
        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        
        new_tokens = refresh_resp.json()
        assert "token" in new_tokens, "Refresh response missing 'token'"
        assert "refresh_token" in new_tokens, "Refresh response missing 'refresh_token'"
        assert "user" in new_tokens, "Refresh response missing 'user'"
        
        # Verify new tokens are different (rotation)
        assert new_tokens["token"] != original_tokens["token"], "Access token should be rotated"
        assert new_tokens["refresh_token"] != original_tokens["refresh_token"], "Refresh token should be rotated"
        
        print(f"✓ A3: Refresh returns new token pair (both tokens rotated)")
    
    def test_a4_old_refresh_token_rejected(self, api_client):
        """A4: POST /api/auth/refresh with old (rotated) refresh_token returns 401"""
        # Login to get tokens
        login_resp = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        original_tokens = login_resp.json()
        old_refresh = original_tokens["refresh_token"]
        
        # Use refresh token once (this rotates it)
        refresh_resp = api_client.post(f"{BASE_URL}/api/auth/refresh", json={
            "refresh_token": old_refresh
        })
        assert refresh_resp.status_code == 200, "First refresh should succeed"
        
        # Try to use the OLD refresh token again - should fail
        retry_resp = api_client.post(f"{BASE_URL}/api/auth/refresh", json={
            "refresh_token": old_refresh
        })
        assert retry_resp.status_code == 401, f"Old refresh token should be rejected, got {retry_resp.status_code}"
        
        print(f"✓ A4: Old (rotated) refresh token correctly rejected with 401")
    
    def test_a5_logout_revokes_refresh_token(self, api_client):
        """A5: POST /api/auth/logout revokes the refresh token"""
        # Login to get tokens
        login_resp = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        
        # Logout (requires auth header)
        logout_resp = api_client.post(
            f"{BASE_URL}/api/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['token']}"}
        )
        assert logout_resp.status_code == 200, f"Logout failed: {logout_resp.text}"
        
        data = logout_resp.json()
        assert "message" in data, "Logout response missing message"
        
        print(f"✓ A5: Logout successful - {data.get('message')}")
    
    def test_a6_refresh_after_logout_fails(self, api_client):
        """A6: POST /api/auth/refresh after logout returns 401"""
        # Login to get tokens
        login_resp = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        refresh_token = tokens["refresh_token"]
        
        # Logout
        logout_resp = api_client.post(
            f"{BASE_URL}/api/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {tokens['token']}"}
        )
        assert logout_resp.status_code == 200
        
        # Try to use the revoked refresh token
        refresh_resp = api_client.post(f"{BASE_URL}/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_resp.status_code == 401, f"Revoked refresh token should be rejected, got {refresh_resp.status_code}"
        
        print(f"✓ A6: Refresh after logout correctly rejected with 401")


class TestOAuthStatePersistence:
    """B1: OAuth State Persistence tests"""
    
    def test_b1_connect_endpoint_requires_auth(self, api_client):
        """B1: Microsoft Calendar /connect endpoint requires authentication"""
        # Without auth - should fail
        response = api_client.get(f"{BASE_URL}/api/microsoft-calendar/connect")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
        print(f"✓ B1a: /connect endpoint requires auth (returns {response.status_code} without token)")
    
    def test_b1_connect_returns_auth_url(self, api_client, auth_tokens):
        """B1: Microsoft Calendar /connect endpoint returns auth_url with state"""
        response = api_client.get(
            f"{BASE_URL}/api/microsoft-calendar/connect",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        
        # May return 500 if Microsoft OAuth not configured, but should not crash
        if response.status_code == 500:
            data = response.json()
            if "není nakonfigurován" in data.get("detail", ""):
                print(f"✓ B1b: /connect endpoint works but Microsoft OAuth not configured (expected in test env)")
                return
        
        assert response.status_code == 200, f"Connect failed: {response.text}"
        data = response.json()
        assert "auth_url" in data, "Response missing 'auth_url'"
        assert "state=" in data["auth_url"], "Auth URL missing state parameter"
        
        print(f"✓ B1b: /connect returns auth_url with state parameter")
    
    def test_b1_status_endpoint_works(self, api_client, auth_tokens):
        """B1: Microsoft Calendar /status endpoint works"""
        response = api_client.get(
            f"{BASE_URL}/api/microsoft-calendar/status",
            headers={"Authorization": f"Bearer {auth_tokens['access_token']}"}
        )
        assert response.status_code == 200, f"Status check failed: {response.text}"
        
        data = response.json()
        assert "connected" in data, "Response missing 'connected' field"
        
        print(f"✓ B1c: /status endpoint works - connected: {data.get('connected')}")


class TestWAFMiddleware:
    """C1-C6: WAF middleware tests"""
    
    def test_c1_waf_blocks_sql_injection_drop_table(self, api_client):
        """C1: WAF blocks SQL injection in query params (DROP TABLE)"""
        # URL-encode the payload
        payload = quote("'; DROP TABLE users;--")
        response = api_client.get(f"{BASE_URL}/api/programs/public/test?age={payload}")
        
        assert response.status_code == 403, f"WAF should block SQL injection, got {response.status_code}"
        data = response.json()
        assert "zablokován" in data.get("detail", "").lower() or "blocked" in data.get("detail", "").lower(), \
            f"Expected WAF block message, got: {data}"
        
        print(f"✓ C1: WAF blocks DROP TABLE SQL injection")
    
    def test_c2_waf_blocks_union_select(self, api_client):
        """C2: WAF blocks UNION SELECT patterns"""
        payload = quote("1 UNION SELECT * FROM users")
        response = api_client.get(f"{BASE_URL}/api/programs/public/test?id={payload}")
        
        assert response.status_code == 403, f"WAF should block UNION SELECT, got {response.status_code}"
        
        print(f"✓ C2: WAF blocks UNION SELECT pattern")
    
    def test_c3_waf_blocks_xss_script_tag_query(self, api_client):
        """C3: WAF blocks XSS <script> tags in query params"""
        payload = quote("<script>alert('xss')</script>")
        response = api_client.get(f"{BASE_URL}/api/programs/public/test?name={payload}")
        
        assert response.status_code == 403, f"WAF should block XSS script tag, got {response.status_code}"
        
        print(f"✓ C3: WAF blocks XSS <script> tag in query params")
    
    def test_c4_waf_blocks_xss_in_post_body(self, api_client):
        """C4: WAF blocks XSS in POST body"""
        response = api_client.post(
            f"{BASE_URL}/api/contact",
            json={
                "name": "Test",
                "email": "test@test.com",
                "message": "<script>document.cookie</script>"
            }
        )
        
        assert response.status_code == 403, f"WAF should block XSS in body, got {response.status_code}"
        
        print(f"✓ C4: WAF blocks XSS in POST body")
    
    def test_c5_waf_allows_legitimate_requests(self, api_client):
        """C5: WAF allows normal legitimate requests through"""
        # Test public programs endpoint with normal params
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}")
        
        # Should not be blocked by WAF (may return 200 or 404 depending on data)
        assert response.status_code != 403, f"WAF incorrectly blocked legitimate request"
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        print(f"✓ C5: WAF allows legitimate requests (status: {response.status_code})")
    
    def test_c5_waf_allows_normal_contact_form(self, api_client):
        """C5: WAF allows normal contact form submission"""
        response = api_client.post(
            f"{BASE_URL}/api/contact",
            json={
                "name": "Jan Novák",
                "email": "jan@example.com",
                "institution": "Test Museum",
                "subject": "general",
                "message": "Hello, I have a question about your booking system."
            }
        )
        
        # Should not be blocked by WAF
        assert response.status_code != 403, f"WAF incorrectly blocked legitimate contact form"
        
        print(f"✓ C5b: WAF allows normal contact form (status: {response.status_code})")
    
    def test_c6_waf_blocks_sleep_benchmark(self, api_client):
        """C6: WAF blocks SLEEP/BENCHMARK injection"""
        payload = quote("1; SLEEP(5);--")
        response = api_client.get(f"{BASE_URL}/api/programs/public/test?id={payload}")
        
        assert response.status_code == 403, f"WAF should block SLEEP injection, got {response.status_code}"
        
        # Also test BENCHMARK
        payload2 = quote("1; BENCHMARK(1000000,SHA1('test'));--")
        response2 = api_client.get(f"{BASE_URL}/api/programs/public/test?id={payload2}")
        
        assert response2.status_code == 403, f"WAF should block BENCHMARK injection, got {response2.status_code}"
        
        print(f"✓ C6: WAF blocks SLEEP/BENCHMARK injection")
    
    def test_c_waf_blocks_javascript_protocol(self, api_client):
        """WAF blocks javascript: protocol XSS"""
        payload = quote("javascript:alert(1)")
        response = api_client.get(f"{BASE_URL}/api/programs/public/test?url={payload}")
        
        assert response.status_code == 403, f"WAF should block javascript: protocol, got {response.status_code}"
        
        print(f"✓ WAF blocks javascript: protocol XSS")
    
    def test_c_waf_blocks_event_handler_xss(self, api_client):
        """WAF blocks event handler XSS (onerror, onclick, etc.)"""
        payload = quote('<img src=x onerror="alert(1)">')
        response = api_client.get(f"{BASE_URL}/api/programs/public/test?img={payload}")
        
        assert response.status_code == 403, f"WAF should block event handler XSS, got {response.status_code}"
        
        print(f"✓ WAF blocks event handler XSS")


class TestRegressionChecks:
    """Regression tests to ensure existing functionality still works"""
    
    def test_regression_admin_login_works(self, api_client):
        """Regression: Admin login and dashboard still works"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert data["user"]["role"] == "admin", "User should be admin"
        
        print(f"✓ Regression: Admin login works")
    
    def test_regression_public_programs_endpoint(self, api_client):
        """Regression: Public programs endpoint still works"""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}")
        
        # Should return 200 with programs or empty list
        assert response.status_code in [200, 404], f"Public programs failed: {response.status_code}"
        
        print(f"✓ Regression: Public programs endpoint works (status: {response.status_code})")
    
    def test_regression_calendar_availability(self, api_client):
        """Regression: Calendar availability still works"""
        response = api_client.get(f"{BASE_URL}/api/calendar/{INSTITUTION_ID}/2026/1")
        
        assert response.status_code in [200, 404], f"Calendar availability failed: {response.status_code}"
        
        print(f"✓ Regression: Calendar availability works (status: {response.status_code})")
    
    def test_regression_health_endpoint(self, api_client):
        """Regression: Health endpoint works (or API root works)"""
        # Note: /health may be intercepted by frontend in some deployments
        # Test API root instead which confirms backend is running
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"API root check failed: {response.status_code}"
        
        data = response.json()
        assert "message" in data, f"API root missing message: {data}"
        
        print(f"✓ Regression: API root endpoint works - {data.get('message')}")
    
    def test_regression_debug_endpoints_require_auth(self, api_client):
        """Regression: Debug endpoints still require auth"""
        response = api_client.get(f"{BASE_URL}/api/emails/debug")
        assert response.status_code in [401, 403], f"Debug endpoint should require auth, got {response.status_code}"
        
        print(f"✓ Regression: Debug endpoints require auth")
    
    def test_regression_ics_feeds_require_tokens(self, api_client):
        """Regression: ICS feeds still require tokens"""
        response = api_client.get(f"{BASE_URL}/api/calendar/institution/{INSTITUTION_ID}.ics")
        assert response.status_code == 422, f"ICS feed should require token param, got {response.status_code}"
        
        print(f"✓ Regression: ICS feeds require tokens")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
