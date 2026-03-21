"""
Test suite for Legal/Terms and PRO Plan features.
Tests:
1. Legal API endpoints (terms, reservation-terms)
2. PRO Plan management (status, upgrade, downgrade)
3. Booking terms validation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"


class TestLegalEndpoints:
    """Test Legal/Terms API endpoints"""
    
    def test_get_terms_of_use(self):
        """GET /api/legal/terms - Returns Terms of Use document with Article 10"""
        response = requests.get(f"{BASE_URL}/api/legal/terms")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "title" in data, "Response should have title"
        assert "version" in data, "Response should have version"
        assert "last_updated" in data, "Response should have last_updated"
        assert "articles" in data, "Response should have articles"
        
        # Verify version is v1
        assert data["version"] == "v1", f"Expected version v1, got {data['version']}"
        
        # Verify we have 11 articles
        assert len(data["articles"]) == 11, f"Expected 11 articles, got {len(data['articles'])}"
        
        # Verify Article 10 exists and has correct title
        article_10 = next((a for a in data["articles"] if a["number"] == 10), None)
        assert article_10 is not None, "Article 10 should exist"
        assert article_10["title"] == "Odpovědnost za realizaci rezervací", f"Article 10 title mismatch: {article_10['title']}"
        
        # Verify Article 10 content mentions key points
        assert "Provozovatel platformy" in article_10["content"], "Article 10 should mention platform operator"
        assert "nenese odpovědnost" in article_10["content"], "Article 10 should mention liability disclaimer"
        
        print(f"✓ Terms of Use returned with {len(data['articles'])} articles including Article 10")
    
    def test_get_reservation_terms(self):
        """GET /api/legal/reservation-terms - Returns checkbox text and email disclaimer"""
        response = requests.get(f"{BASE_URL}/api/legal/reservation-terms")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "version" in data, "Response should have version"
        assert "checkbox_text" in data, "Response should have checkbox_text"
        assert "email_disclaimer" in data, "Response should have email_disclaimer"
        
        # Verify checkbox text content
        assert "Budezivo.cz" in data["checkbox_text"], "Checkbox text should mention Budezivo.cz"
        assert "zprostředkovatelem" in data["checkbox_text"], "Checkbox text should mention intermediary role"
        
        # Verify email disclaimer content
        assert "Důležité informace" in data["email_disclaimer"], "Email disclaimer should have 'Důležité informace' header"
        assert "nenese odpovědnost" in data["email_disclaimer"], "Email disclaimer should mention liability"
        
        print(f"✓ Reservation terms returned with checkbox text and email disclaimer")
    
    def test_get_terms_version(self):
        """GET /api/legal/terms/version - Returns current version identifier"""
        response = requests.get(f"{BASE_URL}/api/legal/terms/version")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "version" in data, "Response should have version"
        assert data["version"] == "v1", f"Expected version v1, got {data['version']}"
        
        print(f"✓ Terms version returned: {data['version']}")


class TestPlanEndpoints:
    """Test PRO Plan management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_plan_status(self):
        """GET /api/plan/status - Returns plan info (free/pro, features)"""
        response = requests.get(f"{BASE_URL}/api/plan/status", headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "plan" in data, "Response should have plan"
        assert "is_pro" in data, "Response should have is_pro"
        assert "features" in data, "Response should have features"
        
        # Verify plan is either 'free' or 'pro'
        assert data["plan"] in ["free", "pro"], f"Plan should be 'free' or 'pro', got {data['plan']}"
        
        # Verify is_pro matches plan
        expected_is_pro = data["plan"] == "pro"
        assert data["is_pro"] == expected_is_pro, f"is_pro mismatch: plan={data['plan']}, is_pro={data['is_pro']}"
        
        # Verify features structure
        features = data["features"]
        expected_feature_keys = ["csv_export", "bulk_email", "advanced_statistics", "programs_limit", "monthly_bookings_limit"]
        for key in expected_feature_keys:
            assert key in features, f"Features should have {key}"
        
        print(f"✓ Plan status returned: plan={data['plan']}, is_pro={data['is_pro']}")
        return data
    
    def test_upgrade_to_pro(self):
        """PUT /api/plan/upgrade - Upgrades to PRO plan"""
        response = requests.put(f"{BASE_URL}/api/plan/upgrade", 
                               json={"confirm": True}, 
                               headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        assert "plan" in data, "Response should have plan"
        assert data["plan"] == "pro", f"Plan should be 'pro' after upgrade, got {data['plan']}"
        
        # Verify plan status after upgrade
        status_response = requests.get(f"{BASE_URL}/api/plan/status", headers=self.headers)
        status_data = status_response.json()
        assert status_data["is_pro"] == True, "is_pro should be True after upgrade"
        
        print(f"✓ Plan upgraded to PRO: {data['message']}")
    
    def test_upgrade_without_confirm_fails(self):
        """PUT /api/plan/upgrade - Fails without confirmation"""
        response = requests.put(f"{BASE_URL}/api/plan/upgrade", 
                               json={"confirm": False}, 
                               headers=self.headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Upgrade without confirmation correctly rejected")
    
    def test_downgrade_to_free(self):
        """PUT /api/plan/downgrade - Downgrades to FREE plan"""
        # First ensure we're on PRO
        requests.put(f"{BASE_URL}/api/plan/upgrade", 
                    json={"confirm": True}, 
                    headers=self.headers)
        
        # Now downgrade
        response = requests.put(f"{BASE_URL}/api/plan/downgrade", 
                               json={"confirm": True}, 
                               headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "plan" in data, "Response should have plan"
        assert data["plan"] == "free", f"Plan should be 'free' after downgrade, got {data['plan']}"
        
        print(f"✓ Plan downgraded to FREE: {data['message']}")
    
    def test_check_feature_access(self):
        """GET /api/plan/check-feature/{feature_name} - Check feature access"""
        # Test with csv_export feature
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/csv_export", 
                               headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "feature" in data, "Response should have feature"
        assert "has_access" in data, "Response should have has_access"
        assert "plan" in data, "Response should have plan"
        
        print(f"✓ Feature check returned: feature={data['feature']}, has_access={data['has_access']}")
    
    def test_check_unknown_feature_fails(self):
        """GET /api/plan/check-feature/{feature_name} - Unknown feature returns 400"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/unknown_feature", 
                               headers=self.headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Unknown feature correctly rejected")
    
    def test_plan_requires_auth(self):
        """Plan endpoints require authentication"""
        # Test without auth header
        response = requests.get(f"{BASE_URL}/api/plan/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        response = requests.put(f"{BASE_URL}/api/plan/upgrade", json={"confirm": True})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print("✓ Plan endpoints correctly require authentication")


class TestBookingTermsValidation:
    """Test booking terms acceptance validation"""
    
    def test_booking_without_terms_fails(self):
        """POST /api/bookings/public/{id} - Fails when terms_accepted=false"""
        # Get a valid institution ID first
        response = requests.get(f"{BASE_URL}/api/legal/terms")
        assert response.status_code == 200
        
        # Try to create booking without terms acceptance
        booking_data = {
            "program_id": "test-program-id",
            "date": "2026-02-15",
            "time_block": "09:00-10:30",
            "school_name": "Test School",
            "group_type": "ms_3_6",
            "age_or_class": "3-4 roky",
            "num_students": 15,
            "num_teachers": 1,
            "special_requirements": "",
            "contact_name": "Test Teacher",
            "contact_email": "test@school.cz",
            "contact_phone": "+420123456789",
            "gdpr_consent": True,
            "terms_accepted": False,  # This should cause failure
            "terms_accepted_text_version": "v1"
        }
        
        # Use demo institution for testing
        response = requests.post(f"{BASE_URL}/api/bookings/public/demo", json=booking_data)
        
        # Should fail with 400 because terms_accepted is False
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Response should have detail"
        assert "podmínkami" in data["detail"].lower() or "terms" in data["detail"].lower(), \
            f"Error should mention terms: {data['detail']}"
        
        print(f"✓ Booking without terms acceptance correctly rejected: {data['detail']}")
    
    def test_booking_with_terms_succeeds(self):
        """POST /api/bookings/public/{id} - Succeeds when terms_accepted=true"""
        booking_data = {
            "program_id": "test-program-id",
            "date": "2026-02-15",
            "time_block": "09:00-10:30",
            "school_name": "Test School Terms",
            "group_type": "ms_3_6",
            "age_or_class": "3-4 roky",
            "num_students": 15,
            "num_teachers": 1,
            "special_requirements": "",
            "contact_name": "Test Teacher",
            "contact_email": "test_terms@school.cz",
            "contact_phone": "+420123456789",
            "gdpr_consent": True,
            "terms_accepted": True,  # This should pass
            "terms_accepted_text_version": "v1"
        }
        
        # Use demo institution for testing
        response = requests.post(f"{BASE_URL}/api/bookings/public/demo", json=booking_data)
        
        # Should succeed with 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have id"
        assert data.get("terms_accepted") == True, "terms_accepted should be True"
        assert data.get("terms_accepted_text_version") == "v1", "terms_accepted_text_version should be v1"
        
        print(f"✓ Booking with terms acceptance succeeded: id={data['id']}")


class TestTermsPageAccess:
    """Test /terms page accessibility"""
    
    def test_terms_api_public_access(self):
        """Legal endpoints should be publicly accessible (no auth required)"""
        # Test /api/legal/terms
        response = requests.get(f"{BASE_URL}/api/legal/terms")
        assert response.status_code == 200, f"Terms endpoint should be public, got {response.status_code}"
        
        # Test /api/legal/reservation-terms
        response = requests.get(f"{BASE_URL}/api/legal/reservation-terms")
        assert response.status_code == 200, f"Reservation terms endpoint should be public, got {response.status_code}"
        
        # Test /api/legal/terms/version
        response = requests.get(f"{BASE_URL}/api/legal/terms/version")
        assert response.status_code == 200, f"Terms version endpoint should be public, got {response.status_code}"
        
        print("✓ All legal endpoints are publicly accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
