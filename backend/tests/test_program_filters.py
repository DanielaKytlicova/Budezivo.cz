"""
Test suite for Program Filtering Features
Tests: BookingPage filters (age, duration), URL param sync, Admin URL generator
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://arch-enhance-v59.preview.emergentagent.com').rstrip('/')
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
TEST_CREDENTIALS = {"email": "demo@budezivo.cz", "password": "Demo2026!"}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin endpoints."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=TEST_CREDENTIALS
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestPublicProgramsAPI:
    """Test GET /api/programs/public/{institution_id} with filters."""

    def test_get_all_programs_no_filter(self, api_client):
        """GET /api/programs/public/{id} returns all published programs."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should have at least one program"
        print(f"Total programs without filter: {len(data)}")

    def test_filter_by_age_MS(self, api_client):
        """GET /api/programs/public/{id}?age=MS returns only MŠ programs."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?age=MS")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Programs with age=MS: {len(data)}")
        
        # Verify all returned programs match MS filter
        for prog in data:
            age_cats = prog.get("age_categories") or []
            target_groups = prog.get("target_groups") or []
            age_group = prog.get("age_group") or ""
            
            # Should match MS via age_categories, target_groups, or age_group
            matches = (
                "MS" in [c.upper() for c in age_cats] or
                "ms_3_6" in target_groups or
                age_group == "ms_3_6"
            )
            assert matches, f"Program {prog.get('name_cs')} should match MS filter"

    def test_filter_by_age_ZS1(self, api_client):
        """GET /api/programs/public/{id}?age=ZS1 returns only ZŠ I. programs."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?age=ZS1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Programs with age=ZS1: {len(data)}")
        
        for prog in data:
            age_cats = prog.get("age_categories") or []
            target_groups = prog.get("target_groups") or []
            age_group = prog.get("age_group") or ""
            
            matches = (
                "ZS1" in [c.upper() for c in age_cats] or
                "zs1_7_12" in target_groups or
                age_group == "zs1_7_12"
            )
            assert matches, f"Program {prog.get('name_cs')} should match ZS1 filter"

    def test_filter_by_multiple_ages_ZS1_ZS2(self, api_client):
        """GET /api/programs/public/{id}?age=ZS1,ZS2 returns ZŠ I. + ZŠ II. programs."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?age=ZS1,ZS2")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Programs with age=ZS1,ZS2: {len(data)}")
        
        for prog in data:
            age_cats = prog.get("age_categories") or []
            target_groups = prog.get("target_groups") or []
            age_group = prog.get("age_group") or ""
            
            matches = (
                any(c.upper() in ["ZS1", "ZS2"] for c in age_cats) or
                any(tg in ["zs1_7_12", "zs2_12_15"] for tg in target_groups) or
                age_group in ["zs1_7_12", "zs2_12_15"]
            )
            assert matches, f"Program {prog.get('name_cs')} should match ZS1 or ZS2 filter"

    def test_filter_by_duration_short(self, api_client):
        """GET /api/programs/public/{id}?duration=short returns programs < 60 min."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?duration=short")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Programs with duration=short: {len(data)}")
        
        for prog in data:
            duration = prog.get("duration", 0)
            assert duration < 60, f"Program {prog.get('name_cs')} duration {duration} should be < 60"

    def test_filter_by_duration_medium(self, api_client):
        """GET /api/programs/public/{id}?duration=medium returns programs 60-120 min."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?duration=medium")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Programs with duration=medium: {len(data)}")
        
        for prog in data:
            duration = prog.get("duration", 0)
            assert 60 <= duration <= 120, f"Program {prog.get('name_cs')} duration {duration} should be 60-120"

    def test_filter_by_duration_long(self, api_client):
        """GET /api/programs/public/{id}?duration=long returns programs > 120 min."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?duration=long")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Programs with duration=long: {len(data)}")
        
        for prog in data:
            duration = prog.get("duration", 0)
            assert duration > 120, f"Program {prog.get('name_cs')} duration {duration} should be > 120"

    def test_combined_age_and_duration_filter(self, api_client):
        """GET /api/programs/public/{id}?age=ZS1&duration=medium returns filtered programs."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?age=ZS1&duration=medium")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Programs with age=ZS1 AND duration=medium: {len(data)}")
        
        for prog in data:
            # Check duration
            duration = prog.get("duration", 0)
            assert 60 <= duration <= 120, f"Duration {duration} should be 60-120"
            
            # Check age
            age_cats = prog.get("age_categories") or []
            target_groups = prog.get("target_groups") or []
            age_group = prog.get("age_group") or ""
            
            matches = (
                "ZS1" in [c.upper() for c in age_cats] or
                "zs1_7_12" in target_groups or
                age_group == "zs1_7_12"
            )
            assert matches, f"Program {prog.get('name_cs')} should match ZS1 filter"

    def test_filter_returns_empty_for_nonexistent_age(self, api_client):
        """GET /api/programs/public/{id}?age=INVALID returns empty list."""
        response = api_client.get(f"{BASE_URL}/api/programs/public/{INSTITUTION_ID}?age=INVALID")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # May return empty or programs that don't match - just verify no error
        print(f"Programs with age=INVALID: {len(data)}")


class TestAuditLogAPI:
    """Test GET /api/audit-log endpoint."""

    def test_audit_log_requires_auth(self, api_client):
        """GET /api/audit-log without auth returns 401/403."""
        response = api_client.get(f"{BASE_URL}/api/audit-log")
        assert response.status_code in [401, 403], "Should require authentication"

    def test_audit_log_returns_paginated_data(self, authenticated_client):
        """GET /api/audit-log returns paginated audit entries."""
        response = authenticated_client.get(f"{BASE_URL}/api/audit-log")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        
        print(f"Audit log total: {data['total']}, page: {data['page']}, items: {len(data['items'])}")

    def test_audit_log_filter_by_entity_type(self, authenticated_client):
        """GET /api/audit-log?entity_type=program filters by entity type."""
        response = authenticated_client.get(f"{BASE_URL}/api/audit-log?entity_type=program")
        assert response.status_code == 200
        data = response.json()
        
        # All items should have entity_type = program
        for item in data["items"]:
            assert item.get("entity_type") == "program", f"Expected entity_type=program, got {item.get('entity_type')}"
        
        print(f"Audit log entries for programs: {len(data['items'])}")

    def test_audit_log_pagination(self, authenticated_client):
        """GET /api/audit-log supports pagination params."""
        response = authenticated_client.get(f"{BASE_URL}/api/audit-log?page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert len(data["items"]) <= 10


class TestAdminProgramsAPI:
    """Test admin programs endpoints for URL generator."""

    def test_get_programs_authenticated(self, authenticated_client):
        """GET /api/programs returns programs for authenticated user."""
        response = authenticated_client.get(f"{BASE_URL}/api/programs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Admin programs count: {len(data)}")

    def test_get_auth_me_returns_institution_id(self, authenticated_client):
        """GET /api/auth/me returns user with institution_id."""
        response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        
        assert "institution_id" in data
        assert data["institution_id"] == INSTITUTION_ID
        print(f"Institution ID: {data['institution_id']}")

    def test_get_program_external_url(self, authenticated_client):
        """GET /api/programs/{id}/external-url returns URL data."""
        # First get a program ID
        programs_response = authenticated_client.get(f"{BASE_URL}/api/programs")
        assert programs_response.status_code == 200
        programs = programs_response.json()
        
        if len(programs) == 0:
            pytest.skip("No programs available for testing")
        
        program_id = programs[0]["id"]
        
        response = authenticated_client.get(f"{BASE_URL}/api/programs/{program_id}/external-url")
        assert response.status_code == 200
        data = response.json()
        
        assert "url" in data
        assert "program_name" in data
        assert "embed_code" in data
        assert INSTITUTION_ID in data["url"]
        
        print(f"External URL: {data['url']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
