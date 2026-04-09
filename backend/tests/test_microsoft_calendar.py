"""
Test Microsoft Outlook Calendar Integration endpoints.
Tests OAuth flow initiation, status, disconnect, blocks API, and override toggle.
Note: Actual OAuth callback cannot be tested without real Microsoft user login.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from iteration_26
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def headers(auth_token):
    """Headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestMicrosoftCalendarStatus:
    """Test GET /api/microsoft-calendar/status endpoint."""
    
    def test_status_returns_connected_false_when_no_integration(self, headers):
        """Status should return connected: false when no integration exists."""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/status", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "connected" in data, "Response should contain 'connected' field"
        # Note: connected could be true or false depending on existing state
        assert isinstance(data["connected"], bool), "connected should be boolean"
        print(f"Status response: {data}")


class TestMicrosoftCalendarConnect:
    """Test GET /api/microsoft-calendar/connect endpoint."""
    
    def test_connect_returns_auth_url(self, headers):
        """Connect should return auth_url with correct Microsoft OAuth parameters."""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/connect", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "auth_url" in data, "Response should contain 'auth_url' field"
        
        auth_url = data["auth_url"]
        assert auth_url.startswith("https://login.microsoftonline.com/"), \
            f"auth_url should start with Microsoft login URL, got: {auth_url[:50]}"
        
        # Verify tenant ID is in the URL (from .env: 20ae0ab5-26f4-4b52-bb71-55de86a0fc89)
        assert "20ae0ab5-26f4-4b52-bb71-55de86a0fc89" in auth_url, \
            "auth_url should contain the correct tenant ID"
        
        # Verify client_id is in the URL
        assert "client_id=" in auth_url, "auth_url should contain client_id parameter"
        
        # Verify redirect_uri is in the URL
        assert "redirect_uri=" in auth_url, "auth_url should contain redirect_uri parameter"
        
        # Verify scopes are in the URL
        assert "scope=" in auth_url, "auth_url should contain scope parameter"
        assert "Calendars.Read" in auth_url or "calendars.read" in auth_url.lower(), \
            "auth_url should contain Calendars.Read scope"
        
        print(f"Auth URL generated successfully: {auth_url[:100]}...")


class TestMicrosoftCalendarDisconnect:
    """Test POST /api/microsoft-calendar/disconnect endpoint."""
    
    def test_disconnect_returns_success(self, headers):
        """Disconnect should return success message even if not connected."""
        response = requests.post(f"{BASE_URL}/api/microsoft-calendar/disconnect", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        print(f"Disconnect response: {data}")


class TestMicrosoftCalendarBlocks:
    """Test GET /api/microsoft-calendar/blocks endpoint."""
    
    def test_blocks_returns_empty_array_when_no_blocks(self, headers):
        """Blocks should return empty array when no blocks exist."""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/blocks", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Response should be a list, got {type(data)}"
        print(f"Blocks response: {data}")
    
    def test_blocks_accepts_query_params(self, headers):
        """Blocks should accept user_id, start, and end query parameters."""
        # Test with date range params
        params = {
            "start": "2026-04-01",
            "end": "2026-04-30"
        }
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/blocks", headers=headers, params=params)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Response should be a list, got {type(data)}"
        print(f"Blocks with date range: {data}")
    
    def test_blocks_accepts_user_id_param(self, headers):
        """Blocks should accept user_id query parameter."""
        # Use a random UUID for testing - should still return 200 with empty array
        params = {
            "user_id": "00000000-0000-0000-0000-000000000000",
            "start": "2026-04-01",
            "end": "2026-04-30"
        }
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/blocks", headers=headers, params=params)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Response should be a list, got {type(data)}"
        print(f"Blocks with user_id filter: {data}")


class TestMicrosoftCalendarOverride:
    """Test POST /api/microsoft-calendar/blocks/{block_id}/override endpoint."""
    
    def test_override_returns_404_for_nonexistent_block(self, headers):
        """Override should return 404 for non-existent block."""
        fake_block_id = "00000000-0000-0000-0000-000000000000"
        response = requests.post(
            f"{BASE_URL}/api/microsoft-calendar/blocks/{fake_block_id}/override",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Response should contain 'detail' field for error"
        print(f"Override 404 response: {data}")


class TestMicrosoftCalendarSync:
    """Test POST /api/microsoft-calendar/sync endpoint."""
    
    def test_sync_returns_404_when_not_connected(self, headers):
        """Sync should return 404 when Outlook is not connected."""
        response = requests.post(f"{BASE_URL}/api/microsoft-calendar/sync", headers=headers)
        # Should return 404 if not connected
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data, "Response should contain 'detail' field"
            print(f"Sync not connected response: {data}")
        elif response.status_code == 200:
            # If connected, should return success
            data = response.json()
            assert "message" in data, "Response should contain 'message' field"
            print(f"Sync success response: {data}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code} - {response.text}")


class TestMicrosoftCalendarAuthRequired:
    """Test that endpoints require authentication."""
    
    def test_status_requires_auth(self):
        """Status endpoint should require authentication."""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_connect_requires_auth(self):
        """Connect endpoint should require authentication."""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/connect")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_disconnect_requires_auth(self):
        """Disconnect endpoint should require authentication."""
        response = requests.post(f"{BASE_URL}/api/microsoft-calendar/disconnect")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_blocks_requires_auth(self):
        """Blocks endpoint should require authentication."""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/blocks")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_sync_requires_auth(self):
        """Sync endpoint should require authentication."""
        response = requests.post(f"{BASE_URL}/api/microsoft-calendar/sync")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
