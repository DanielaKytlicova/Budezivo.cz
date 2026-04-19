"""
Test suite for 4-tier Subscription Plan System.
Plans: free, start, pro, pro_plus
Status: inactive, pending, active, expired

Tests:
1. GET /api/plan/status - Returns plan with plan_status, plan_label, features, limits
2. GET /api/plan/plans - Returns 4 plans with features
3. GET /api/plan/check-feature/{feature_key} - Feature access check
4. PUT /api/plan/upgrade - Returns 400 (direct activation blocked)
5. POST /api/plan/request - Creates pending plan state
6. PUT /api/plan/downgrade - Downgrade to free
7. PUT /api/plan/admin-change - Admin plan change
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"


class TestPlanStatus:
    """Test GET /api/plan/status endpoint"""
    
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
    
    def test_plan_status_returns_required_fields(self):
        """GET /api/plan/status returns plan, plan_status, plan_label, features, limits"""
        response = requests.get(f"{BASE_URL}/api/plan/status", headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Required fields
        assert "plan" in data, "Response should have plan"
        assert "plan_status" in data, "Response should have plan_status"
        assert "plan_label" in data, "Response should have plan_label"
        assert "is_pro" in data, "Response should have is_pro"
        assert "features" in data, "Response should have features"
        assert "limits" in data, "Response should have limits"
        
        # Verify plan is one of 4 valid plans
        valid_plans = ["free", "start", "pro", "pro_plus"]
        assert data["plan"] in valid_plans, f"Plan should be one of {valid_plans}, got {data['plan']}"
        
        # Verify plan_status is valid
        valid_statuses = ["inactive", "pending", "active", "expired"]
        assert data["plan_status"] in valid_statuses, f"Status should be one of {valid_statuses}, got {data['plan_status']}"
        
        # Verify plan_label matches plan
        expected_labels = {"free": "Free", "start": "Start", "pro": "PRO", "pro_plus": "PRO+"}
        assert data["plan_label"] == expected_labels.get(data["plan"]), f"Label mismatch for plan {data['plan']}"
        
        # Verify is_pro logic (pro or pro_plus with active status)
        expected_is_pro = data["plan"] in ("pro", "pro_plus") and data["plan_status"] == "active"
        assert data["is_pro"] == expected_is_pro, f"is_pro mismatch: plan={data['plan']}, status={data['plan_status']}"
        
        print(f"✓ Plan status: plan={data['plan']}, status={data['plan_status']}, label={data['plan_label']}")
    
    def test_plan_status_features_structure(self):
        """GET /api/plan/status features have correct structure"""
        response = requests.get(f"{BASE_URL}/api/plan/status", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        features = data.get("features", {})
        
        # Check some expected feature keys exist
        expected_features = ["csv_export", "mailings", "events_module", "waitlist"]
        for feature in expected_features:
            assert feature in features, f"Features should have {feature}"
            
            # Each feature should have has_access, label, min_plan
            feature_data = features[feature]
            assert "has_access" in feature_data, f"Feature {feature} should have has_access"
            assert "label" in feature_data, f"Feature {feature} should have label"
            assert "min_plan" in feature_data, f"Feature {feature} should have min_plan"
        
        print(f"✓ Features structure verified with {len(features)} features")
    
    def test_plan_status_limits_structure(self):
        """GET /api/plan/status limits have correct structure"""
        response = requests.get(f"{BASE_URL}/api/plan/status", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        limits = data.get("limits", {})
        
        # Check required limit keys
        assert "programs_limit" in limits, "Limits should have programs_limit"
        assert "bookings_monthly_limit" in limits, "Limits should have bookings_monthly_limit"
        
        # Verify limits are integers
        assert isinstance(limits["programs_limit"], int), "programs_limit should be int"
        assert isinstance(limits["bookings_monthly_limit"], int), "bookings_monthly_limit should be int"
        
        print(f"✓ Limits: programs={limits['programs_limit']}, bookings={limits['bookings_monthly_limit']}")
    
    def test_plan_status_requires_auth(self):
        """GET /api/plan/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/plan/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Plan status requires authentication")


class TestAvailablePlans:
    """Test GET /api/plan/plans endpoint"""
    
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
    
    def test_plans_returns_4_plans(self):
        """GET /api/plan/plans returns exactly 4 plans"""
        response = requests.get(f"{BASE_URL}/api/plan/plans", headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "plans" in data, "Response should have plans array"
        
        plans = data["plans"]
        assert len(plans) == 4, f"Expected 4 plans, got {len(plans)}"
        
        # Verify plan keys
        plan_keys = [p["key"] for p in plans]
        expected_keys = ["free", "start", "pro", "pro_plus"]
        assert plan_keys == expected_keys, f"Plan keys should be {expected_keys}, got {plan_keys}"
        
        print(f"✓ Plans endpoint returns 4 plans: {plan_keys}")
    
    def test_plans_have_required_fields(self):
        """GET /api/plan/plans each plan has key, label, limits, features"""
        response = requests.get(f"{BASE_URL}/api/plan/plans", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        for plan in data["plans"]:
            assert "key" in plan, f"Plan should have key"
            assert "label" in plan, f"Plan should have label"
            assert "limits" in plan, f"Plan should have limits"
            assert "features" in plan, f"Plan should have features"
            assert "feature_keys" in plan, f"Plan should have feature_keys"
            
            # Verify limits structure
            limits = plan["limits"]
            assert "programs_limit" in limits, f"Plan {plan['key']} limits should have programs_limit"
            assert "bookings_monthly_limit" in limits, f"Plan {plan['key']} limits should have bookings_monthly_limit"
        
        print("✓ All plans have required fields")
    
    def test_plans_labels_correct(self):
        """GET /api/plan/plans labels are Free, Start, PRO, PRO+"""
        response = requests.get(f"{BASE_URL}/api/plan/plans", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        expected_labels = {"free": "Free", "start": "Start", "pro": "PRO", "pro_plus": "PRO+"}
        
        for plan in data["plans"]:
            expected = expected_labels.get(plan["key"])
            assert plan["label"] == expected, f"Plan {plan['key']} label should be {expected}, got {plan['label']}"
        
        print("✓ Plan labels are correct")
    
    def test_pro_plus_has_events_module(self):
        """GET /api/plan/plans pro_plus has events_module feature"""
        response = requests.get(f"{BASE_URL}/api/plan/plans", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        pro_plus = next((p for p in data["plans"] if p["key"] == "pro_plus"), None)
        assert pro_plus is not None, "pro_plus plan should exist"
        
        feature_keys = pro_plus.get("feature_keys", [])
        assert "events_module" in feature_keys, f"pro_plus should have events_module, got {feature_keys}"
        
        print("✓ PRO+ plan has events_module feature")
    
    def test_pro_has_mailings(self):
        """GET /api/plan/plans pro has mailings feature"""
        response = requests.get(f"{BASE_URL}/api/plan/plans", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        pro = next((p for p in data["plans"] if p["key"] == "pro"), None)
        assert pro is not None, "pro plan should exist"
        
        feature_keys = pro.get("feature_keys", [])
        assert "mailings" in feature_keys, f"pro should have mailings, got {feature_keys}"
        
        print("✓ PRO plan has mailings feature")


class TestFeatureAccess:
    """Test GET /api/plan/check-feature/{feature_key} endpoint"""
    
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
    
    def test_check_mailings_feature(self):
        """GET /api/plan/check-feature/mailings returns has_access"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/mailings", headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "feature" in data, "Response should have feature"
        assert "has_access" in data, "Response should have has_access"
        assert "plan" in data, "Response should have plan"
        assert "plan_status" in data, "Response should have plan_status"
        assert "min_plan" in data, "Response should have min_plan"
        
        assert data["feature"] == "mailings", f"Feature should be mailings, got {data['feature']}"
        
        # For demo institution (pro_plus/active), should have access
        print(f"✓ Mailings feature check: has_access={data['has_access']}, plan={data['plan']}")
    
    def test_check_events_module_feature(self):
        """GET /api/plan/check-feature/events_module returns has_access"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/events_module", headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["feature"] == "events_module", f"Feature should be events_module"
        assert "has_access" in data, "Response should have has_access"
        
        # For demo institution (pro_plus/active), should have access
        print(f"✓ Events module feature check: has_access={data['has_access']}")
    
    def test_check_csv_export_feature(self):
        """GET /api/plan/check-feature/csv_export returns has_access"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/csv_export", headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["feature"] == "csv_export", f"Feature should be csv_export"
        assert "has_access" in data, "Response should have has_access"
        assert "min_plan" in data, "Response should have min_plan"
        
        print(f"✓ CSV export feature check: has_access={data['has_access']}, min_plan={data['min_plan']}")
    
    def test_check_feature_requires_auth(self):
        """GET /api/plan/check-feature/{feature} requires authentication"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/mailings")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Feature check requires authentication")


class TestLegacyUpgradeBlocked:
    """Test PUT /api/plan/upgrade returns 400 (direct activation blocked)"""
    
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
    
    def test_legacy_upgrade_returns_400(self):
        """PUT /api/plan/upgrade returns 400 error (direct activation blocked)"""
        response = requests.put(f"{BASE_URL}/api/plan/upgrade", 
                               json={"confirm": True}, 
                               headers=self.headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Response should have detail"
        
        # Verify error message mentions direct activation is not available
        detail = data["detail"].lower()
        assert "přímá aktivace" in detail or "direct" in detail or "plány" in detail, \
            f"Error should mention direct activation blocked: {data['detail']}"
        
        print(f"✓ Legacy upgrade correctly returns 400: {data['detail']}")
    
    def test_legacy_upgrade_without_confirm_returns_400(self):
        """PUT /api/plan/upgrade without confirm also returns 400"""
        response = requests.put(f"{BASE_URL}/api/plan/upgrade", 
                               json={}, 
                               headers=self.headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Legacy upgrade without confirm also returns 400")


class TestPlanRequest:
    """Test POST /api/plan/request endpoint"""
    
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
    
    def test_request_plan_creates_pending_state(self):
        """POST /api/plan/request creates pending plan state"""
        # Request a plan change
        response = requests.post(f"{BASE_URL}/api/plan/request", 
                                json={"target_plan": "pro"}, 
                                headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        assert "plan" in data, "Response should have plan"
        assert "plan_status" in data, "Response should have plan_status"
        
        # Verify pending status
        assert data["plan_status"] == "pending", f"Status should be pending, got {data['plan_status']}"
        
        print(f"✓ Plan request created pending state: {data['message']}")
    
    def test_request_free_plan_fails(self):
        """POST /api/plan/request with target_plan=free fails"""
        response = requests.post(f"{BASE_URL}/api/plan/request", 
                                json={"target_plan": "free"}, 
                                headers=self.headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Request for free plan correctly rejected")
    
    def test_request_invalid_plan_fails(self):
        """POST /api/plan/request with invalid plan fails"""
        response = requests.post(f"{BASE_URL}/api/plan/request", 
                                json={"target_plan": "invalid_plan"}, 
                                headers=self.headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Request for invalid plan correctly rejected")
    
    def test_request_plan_requires_auth(self):
        """POST /api/plan/request requires authentication"""
        response = requests.post(f"{BASE_URL}/api/plan/request", 
                                json={"target_plan": "pro"})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Plan request requires authentication")


class TestPlanDowngrade:
    """Test PUT /api/plan/downgrade endpoint"""
    
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
    
    def test_downgrade_to_free_works(self):
        """PUT /api/plan/downgrade downgrades to free plan"""
        response = requests.put(f"{BASE_URL}/api/plan/downgrade", 
                               json={"confirm": True}, 
                               headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "plan" in data, "Response should have plan"
        assert "plan_status" in data, "Response should have plan_status"
        assert data["plan"] == "free", f"Plan should be free, got {data['plan']}"
        assert data["plan_status"] == "active", f"Status should be active, got {data['plan_status']}"
        
        print(f"✓ Downgrade to free successful: {data['message']}")
    
    def test_downgrade_requires_auth(self):
        """PUT /api/plan/downgrade requires authentication"""
        response = requests.put(f"{BASE_URL}/api/plan/downgrade", json={"confirm": True})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Downgrade requires authentication")


class TestAdminPlanChange:
    """Test PUT /api/plan/admin-change endpoint"""
    
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
        
        # Get institution ID
        status_response = requests.get(f"{BASE_URL}/api/plan/status", headers=self.headers)
        if status_response.status_code == 200:
            # Get institution ID from user info
            user_response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
            if user_response.status_code == 200:
                self.institution_id = user_response.json().get("institution_id")
    
    def test_admin_change_plan_and_status(self):
        """PUT /api/plan/admin-change can change plan and status"""
        if not hasattr(self, 'institution_id') or not self.institution_id:
            pytest.skip("Could not get institution ID")
        
        response = requests.put(f"{BASE_URL}/api/plan/admin-change", 
                               json={
                                   "institution_id": self.institution_id,
                                   "target_plan": "pro_plus",
                                   "target_status": "active",
                                   "activated_by": "admin"
                               }, 
                               headers=self.headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "plan" in data, "Response should have plan"
        assert "plan_status" in data, "Response should have plan_status"
        assert data["plan"] == "pro_plus", f"Plan should be pro_plus, got {data['plan']}"
        assert data["plan_status"] == "active", f"Status should be active, got {data['plan_status']}"
        
        print(f"✓ Admin plan change successful: {data['message']}")
    
    def test_admin_change_invalid_plan_fails(self):
        """PUT /api/plan/admin-change with invalid plan fails"""
        if not hasattr(self, 'institution_id') or not self.institution_id:
            pytest.skip("Could not get institution ID")
        
        response = requests.put(f"{BASE_URL}/api/plan/admin-change", 
                               json={
                                   "institution_id": self.institution_id,
                                   "target_plan": "invalid_plan",
                                   "target_status": "active"
                               }, 
                               headers=self.headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Admin change with invalid plan correctly rejected")
    
    def test_admin_change_requires_auth(self):
        """PUT /api/plan/admin-change requires authentication"""
        response = requests.put(f"{BASE_URL}/api/plan/admin-change", 
                               json={
                                   "institution_id": "test-id",
                                   "target_plan": "pro",
                                   "target_status": "active"
                               })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Admin change requires authentication")


class TestProPlusFeatureAccess:
    """Test that PRO+ institution has access to all features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token, ensure PRO+ plan"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        self.token = login_response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get institution ID and ensure PRO+ plan
        user_response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        if user_response.status_code == 200:
            self.institution_id = user_response.json().get("institution_id")
            
            # Set to PRO+ for testing
            requests.put(f"{BASE_URL}/api/plan/admin-change", 
                        json={
                            "institution_id": self.institution_id,
                            "target_plan": "pro_plus",
                            "target_status": "active",
                            "activated_by": "admin"
                        }, 
                        headers=self.headers)
    
    def test_pro_plus_has_mailings_access(self):
        """PRO+ institution has access to mailings feature"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/mailings", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_access"] == True, f"PRO+ should have mailings access, got {data}"
        print("✓ PRO+ has mailings access")
    
    def test_pro_plus_has_events_module_access(self):
        """PRO+ institution has access to events_module feature"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/events_module", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_access"] == True, f"PRO+ should have events_module access, got {data}"
        print("✓ PRO+ has events_module access")
    
    def test_pro_plus_has_waitlist_access(self):
        """PRO+ institution has access to waitlist feature"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/waitlist", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_access"] == True, f"PRO+ should have waitlist access, got {data}"
        print("✓ PRO+ has waitlist access")
    
    def test_pro_plus_has_csv_export_access(self):
        """PRO+ institution has access to csv_export feature"""
        response = requests.get(f"{BASE_URL}/api/plan/check-feature/csv_export", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_access"] == True, f"PRO+ should have csv_export access, got {data}"
        print("✓ PRO+ has csv_export access")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
