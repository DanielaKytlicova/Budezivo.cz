"""
Test Plan Hierarchy System - Iteration 48
Tests hierarchical plan features with delta view (no duplication).
Plans: START (base), PRO (START + extras), PRO+ (PRO + payments, API, Outlook, SLA)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPlanHierarchy:
    """Test plan hierarchy and feature counts"""
    
    def test_plans_endpoint_returns_hierarchical_data(self):
        """GET /api/plan/plans returns hierarchical plan data"""
        response = requests.get(f"{BASE_URL}/api/plan/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        plans = data["plans"]
        
        # Should have 4 plans: free, start, pro, pro_plus
        assert len(plans) == 4
        plan_keys = [p["key"] for p in plans]
        assert plan_keys == ["free", "start", "pro", "pro_plus"]
    
    def test_start_plan_has_9_own_features(self):
        """Start plan should have 9 own features (base features)"""
        response = requests.get(f"{BASE_URL}/api/plan/plans")
        assert response.status_code == 200
        plans = response.json()["plans"]
        
        start_plan = next(p for p in plans if p["key"] == "start")
        assert len(start_plan["own_features"]) == 9
        assert len(start_plan["all_feature_keys"]) == 9
        
        # Verify inherits_from_label is None (inherits from free which has no features)
        assert start_plan.get("inherits_from_label") is None
    
    def test_pro_plan_has_10_own_features_19_total(self):
        """PRO plan should have 10 own features, 19 total (cumulative)"""
        response = requests.get(f"{BASE_URL}/api/plan/plans")
        assert response.status_code == 200
        plans = response.json()["plans"]
        
        pro_plan = next(p for p in plans if p["key"] == "pro")
        assert len(pro_plan["own_features"]) == 10
        assert len(pro_plan["all_feature_keys"]) == 19
        
        # Verify inherits_from_label is "Start"
        assert pro_plan.get("inherits_from_label") == "Start"
    
    def test_pro_plus_plan_has_7_own_features_26_total(self):
        """PRO+ plan should have 7 own features, 26 total (cumulative)"""
        response = requests.get(f"{BASE_URL}/api/plan/plans")
        assert response.status_code == 200
        plans = response.json()["plans"]
        
        pro_plus_plan = next(p for p in plans if p["key"] == "pro_plus")
        assert len(pro_plus_plan["own_features"]) == 7
        assert len(pro_plus_plan["all_feature_keys"]) == 26
        
        # Verify inherits_from_label is "PRO"
        assert pro_plus_plan.get("inherits_from_label") == "PRO"
    
    def test_events_basic_in_pro_not_pro_plus(self):
        """events_basic should be in PRO's own_features, not PRO+'s"""
        response = requests.get(f"{BASE_URL}/api/plan/plans")
        assert response.status_code == 200
        plans = response.json()["plans"]
        
        pro_plan = next(p for p in plans if p["key"] == "pro")
        pro_plus_plan = next(p for p in plans if p["key"] == "pro_plus")
        
        pro_own_keys = [f["key"] for f in pro_plan["own_features"]]
        pro_plus_own_keys = [f["key"] for f in pro_plus_plan["own_features"]]
        
        assert "events_basic" in pro_own_keys
        assert "events_basic" not in pro_plus_own_keys
    
    def test_events_payments_only_in_pro_plus(self):
        """events_payments should only be in PRO+'s own_features"""
        response = requests.get(f"{BASE_URL}/api/plan/plans")
        assert response.status_code == 200
        plans = response.json()["plans"]
        
        pro_plan = next(p for p in plans if p["key"] == "pro")
        pro_plus_plan = next(p for p in plans if p["key"] == "pro_plus")
        
        pro_own_keys = [f["key"] for f in pro_plan["own_features"]]
        pro_plus_own_keys = [f["key"] for f in pro_plus_plan["own_features"]]
        
        assert "events_payments" not in pro_own_keys
        assert "events_payments" in pro_plus_own_keys


class TestPlanDiff:
    """Test plan diff endpoint for delta view"""
    
    def test_diff_pro_plus_to_start_shows_lost_features(self):
        """Downgrade from PRO+ to Start should show 17 lost features"""
        response = requests.get(f"{BASE_URL}/api/plan/diff?from_plan=pro_plus&to_plan=start")
        assert response.status_code == 200
        data = response.json()
        
        assert "lost" in data
        assert "gained" in data
        assert "is_upgrade" in data
        
        # Should lose 17 features (10 PRO + 7 PRO+)
        assert len(data["lost"]) == 17
        assert len(data["gained"]) == 0
        assert data["is_upgrade"] == False
    
    def test_diff_start_to_pro_shows_gained_features(self):
        """Upgrade from Start to PRO should show 10 gained features"""
        response = requests.get(f"{BASE_URL}/api/plan/diff?from_plan=start&to_plan=pro")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["gained"]) == 10
        assert len(data["lost"]) == 0
        assert data["is_upgrade"] == True
        
        # Verify specific features gained
        gained_keys = [f["key"] for f in data["gained"]]
        assert "mailing" in gained_keys
        assert "events_basic" in gained_keys
        assert "parallel_programs" in gained_keys
    
    def test_diff_pro_to_pro_plus_shows_7_gained(self):
        """Upgrade from PRO to PRO+ should show 7 gained features"""
        response = requests.get(f"{BASE_URL}/api/plan/diff?from_plan=pro&to_plan=pro_plus")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["gained"]) == 7
        assert len(data["lost"]) == 0
        assert data["is_upgrade"] == True
        
        # Verify PRO+ specific features
        gained_keys = [f["key"] for f in data["gained"]]
        assert "events_payments" in gained_keys
        assert "api_access" in gained_keys
        assert "outlook_sync" in gained_keys
        assert "sla_support" in gained_keys
    
    def test_diff_invalid_plan_returns_400(self):
        """Invalid plan in diff should return 400"""
        response = requests.get(f"{BASE_URL}/api/plan/diff?from_plan=invalid&to_plan=pro")
        assert response.status_code == 400


class TestPlanStatusAuthenticated:
    """Test authenticated plan endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "Demo2026!"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_plan_status_returns_all_fields(self, auth_token):
        """GET /api/plan/status returns plan, plan_status, plan_label, features, limits"""
        response = requests.get(
            f"{BASE_URL}/api/plan/status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "plan" in data
        assert "plan_status" in data
        assert "plan_label" in data
        assert "features" in data
        assert "limits" in data
        
        # Demo institution should be on pro_plus/active
        assert data["plan"] == "pro_plus"
        assert data["plan_status"] == "active"
        assert data["plan_label"] == "PRO+"
    
    def test_check_feature_mailing_has_access(self, auth_token):
        """GET /api/plan/check-feature/mailing returns has_access=true for pro_plus"""
        response = requests.get(
            f"{BASE_URL}/api/plan/check-feature/mailing",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_access"] == True
        assert data["min_plan"] == "pro"
    
    def test_check_feature_events_payments_has_access(self, auth_token):
        """GET /api/plan/check-feature/events_payments returns has_access=true for pro_plus only"""
        response = requests.get(
            f"{BASE_URL}/api/plan/check-feature/events_payments",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_access"] == True
        assert data["min_plan"] == "pro_plus"
        assert data["min_plan_label"] == "PRO+"


class TestUpgradeBlocked:
    """Test that direct upgrade is blocked"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "Demo2026!"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_put_upgrade_returns_400(self, auth_token):
        """PUT /api/plan/upgrade returns 400 (blocked)"""
        response = requests.put(
            f"{BASE_URL}/api/plan/upgrade",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        # Should mention that direct activation is not available
        assert "aktivace" in data["detail"].lower() or "dostupn" in data["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
