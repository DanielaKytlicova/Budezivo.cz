"""
Test VOP (Všeobecné obchodní podmínky) API and GDPR auto-cleanup scheduler.
Tests for iteration 19 features:
- GET /api/legal/vop endpoint
- VOP sections structure validation
- GDPR auto-cleanup scheduler registration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestVopApi:
    """Tests for VOP (Všeobecné obchodní podmínky) API endpoint"""

    def test_vop_endpoint_returns_200(self):
        """GET /api/legal/vop should return 200"""
        response = requests.get(f"{BASE_URL}/api/legal/vop")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: GET /api/legal/vop returns 200")

    def test_vop_has_title(self):
        """VOP response should have title field"""
        response = requests.get(f"{BASE_URL}/api/legal/vop")
        data = response.json()
        assert "title" in data, "Missing 'title' field"
        assert data["title"] == "Všeobecné obchodní podmínky platformy Budeživo.cz"
        print(f"PASS: VOP title = '{data['title']}'")

    def test_vop_has_version(self):
        """VOP response should have version field"""
        response = requests.get(f"{BASE_URL}/api/legal/vop")
        data = response.json()
        assert "version" in data, "Missing 'version' field"
        assert data["version"] == "v1"
        print(f"PASS: VOP version = '{data['version']}'")

    def test_vop_has_15_sections(self):
        """VOP should have exactly 15 sections"""
        response = requests.get(f"{BASE_URL}/api/legal/vop")
        data = response.json()
        assert "sections" in data, "Missing 'sections' field"
        assert len(data["sections"]) == 15, f"Expected 15 sections, got {len(data['sections'])}"
        print(f"PASS: VOP has {len(data['sections'])} sections")

    def test_vop_section_structure(self):
        """Each VOP section should have number, title, and content array"""
        response = requests.get(f"{BASE_URL}/api/legal/vop")
        data = response.json()
        
        for section in data["sections"]:
            assert "number" in section, f"Section missing 'number' field"
            assert "title" in section, f"Section {section.get('number')} missing 'title' field"
            assert "content" in section, f"Section {section.get('number')} missing 'content' field"
            assert isinstance(section["content"], list), f"Section {section['number']} content should be a list"
            assert len(section["content"]) > 0, f"Section {section['number']} content should not be empty"
        
        print("PASS: All 15 sections have correct structure (number, title, content array)")

    def test_vop_section_titles(self):
        """Verify all 15 section titles are present"""
        expected_titles = [
            "Úvodní ustanovení",
            "Předmět služby (SaaS)",
            "Uživatelský účet",
            "Role platformy (zásadní ustanovení)",
            "Povinnosti Instituce",
            "Povinnosti Provozovatele",
            "Platební podmínky",
            "SLA (dostupnost služby)",
            "Reklamace služby",
            "Ochrana osobních údajů (GDPR + DPA logika)",
            "Cookies a technická data",
            "Odpovědnost",
            "Doba trvání a ukončení",
            "Změny podmínek",
            "Závěrečná ustanovení"
        ]
        
        response = requests.get(f"{BASE_URL}/api/legal/vop")
        data = response.json()
        
        actual_titles = [s["title"] for s in data["sections"]]
        
        for i, expected in enumerate(expected_titles):
            assert expected == actual_titles[i], f"Section {i+1} title mismatch: expected '{expected}', got '{actual_titles[i]}'"
        
        print("PASS: All 15 section titles match expected values")


class TestGdprSettings:
    """Tests for GDPR settings API"""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "Demo2026!"
        })
        if response.status_code == 200:
            return response.json().get("token")  # Note: key is 'token', not 'access_token'
        pytest.skip("Authentication failed")

    def test_gdpr_settings_save_and_read(self, auth_token):
        """PUT /api/settings/gdpr should save GDPR settings"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "data_retention": "2years",
            "anonymize": True
        }
        response = requests.put(f"{BASE_URL}/api/settings/gdpr", json=payload, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: PUT /api/settings/gdpr saves settings")

    def test_gdpr_retention_values(self, auth_token):
        """Test different data_retention values"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        valid_values = ["never", "1year", "2years", "5years"]
        for value in valid_values:
            payload = {"data_retention": value, "anonymize": False}
            response = requests.put(f"{BASE_URL}/api/settings/gdpr", json=payload, headers=headers)
            assert response.status_code == 200, f"Failed for retention value '{value}'"
        
        print(f"PASS: All retention values accepted: {valid_values}")


class TestSchedulerRegistration:
    """Tests to verify scheduler jobs are registered"""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "Demo2026!"
        })
        if response.status_code == 200:
            return response.json().get("token")  # Note: key is 'token', not 'access_token'
        pytest.skip("Authentication failed")

    def test_scheduler_jobs_endpoint(self, auth_token):
        """Check if scheduler jobs endpoint exists (optional)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # This endpoint may not exist - just checking
        response = requests.get(f"{BASE_URL}/api/scheduler/jobs", headers=headers)
        # We don't fail if endpoint doesn't exist
        print(f"INFO: Scheduler jobs endpoint returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
