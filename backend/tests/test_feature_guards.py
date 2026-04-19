"""
Test Feature Guards - require_feature() enforcement on protected endpoints.

Tests that:
1. FREE users get HTTP 403 on protected endpoints
2. PRO+ users have full access
3. Error messages include plan name

Feature enforcement mapping:
- mailing → mailings routes (router-level guard)
- events_basic → events CRUD (per-endpoint guards)
- events_payments → payment settings (per-endpoint guard, PRO+ only)
- waitlist → admin waitlist (per-endpoint guards)
- audit_log → audit routes (router-level guard)
- outlook_sync → microsoft calendar (router-level guard)
- collision_system → rooms (router-level guard)
- advanced_stats → advanced statistics (per-endpoint guards)
- data_export → CSV/XLSX exports (per-endpoint guards)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


class TestSetup:
    """Setup and helper methods"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for PRO+ user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def institution_id(self, auth_headers):
        """Get institution ID"""
        response = requests.get(f"{BASE_URL}/api/plan/status", headers=auth_headers)
        assert response.status_code == 200
        # Get institution ID from user info
        user_response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        if user_response.status_code == 200:
            return user_response.json().get("institution_id")
        return "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"  # fallback


class TestProPlusAccess(TestSetup):
    """Test that PRO+ users have full access to all protected endpoints"""
    
    def test_plan_status_shows_pro_plus(self, auth_headers):
        """Verify demo institution is PRO+"""
        response = requests.get(f"{BASE_URL}/api/plan/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "pro_plus", f"Expected pro_plus, got {data['plan']}"
        assert data["plan_status"] == "active"
        print(f"✓ Plan status: {data['plan']} ({data['plan_status']})")
    
    # ---- Router-level guards (PRO features) ----
    
    def test_mailings_accessible_for_pro_plus(self, auth_headers):
        """GET /api/mailings returns 200 for PRO+ user (mailing feature)"""
        response = requests.get(f"{BASE_URL}/api/mailings", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/mailings: 200 OK")
    
    def test_audit_log_accessible_for_pro_plus(self, auth_headers):
        """GET /api/audit-log returns 200 for PRO+ user (audit_log feature)"""
        response = requests.get(f"{BASE_URL}/api/audit-log", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/audit-log: 200 OK")
    
    def test_rooms_accessible_for_pro_plus(self, auth_headers):
        """GET /api/rooms returns 200 for PRO+ user (collision_system feature)"""
        response = requests.get(f"{BASE_URL}/api/rooms", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/rooms: 200 OK")
    
    def test_microsoft_calendar_status_accessible_for_pro_plus(self, auth_headers):
        """GET /api/microsoft-calendar/status returns 200 for PRO+ user (outlook_sync feature)"""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/status", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/microsoft-calendar/status: 200 OK")
    
    # ---- Per-endpoint guards (PRO features) ----
    
    def test_waitlist_admin_accessible_for_pro_plus(self, auth_headers):
        """GET /api/waitlist returns 200 for PRO+ user (waitlist feature)"""
        response = requests.get(f"{BASE_URL}/api/waitlist", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/waitlist: 200 OK")
    
    def test_advanced_stats_accessible_for_pro_plus(self, auth_headers):
        """GET /api/statistics/bookings-over-time returns 200 for PRO+ user (advanced_stats feature)"""
        response = requests.get(f"{BASE_URL}/api/statistics/bookings-over-time", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/statistics/bookings-over-time: 200 OK")
    
    def test_basic_stats_accessible_for_all(self, auth_headers):
        """GET /api/statistics returns 200 for ALL users (basic stats, no guard)"""
        response = requests.get(f"{BASE_URL}/api/statistics", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/statistics: 200 OK (no guard)")
    
    def test_schools_export_csv_accessible_for_pro_plus(self, auth_headers):
        """GET /api/schools/export-csv returns 200 for PRO+ user (data_export feature)"""
        response = requests.get(f"{BASE_URL}/api/schools/export-csv", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/schools/export-csv: 200 OK")
    
    # ---- PRO+ only features ----
    
    def test_events_payment_settings_accessible_for_pro_plus(self, auth_headers):
        """GET /api/events/settings/payment returns 200 for PRO+ user (events_payments feature)"""
        response = requests.get(f"{BASE_URL}/api/events/settings/payment", headers=auth_headers)
        # May return 404 if events module not enabled, but should NOT return 403
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        if response.status_code == 200:
            print("✓ GET /api/events/settings/payment: 200 OK")
        else:
            print("✓ GET /api/events/settings/payment: 404 (events module not enabled, but no 403)")


class TestFreeUserAccess(TestSetup):
    """Test that FREE users get HTTP 403 on protected endpoints"""
    
    @pytest.fixture(scope="class")
    def downgrade_and_restore(self, auth_headers, institution_id):
        """Downgrade to FREE, run tests, then restore to PRO+"""
        # Downgrade to FREE
        response = requests.put(f"{BASE_URL}/api/plan/downgrade", headers=auth_headers)
        assert response.status_code == 200, f"Downgrade failed: {response.text}"
        print("✓ Downgraded to FREE plan")
        
        yield  # Run tests
        
        # Restore to PRO+ using admin-change
        restore_response = requests.put(
            f"{BASE_URL}/api/plan/admin-change",
            headers=auth_headers,
            json={
                "institution_id": institution_id,
                "target_plan": "pro_plus",
                "target_status": "active",
                "activated_by": "test_restore"
            }
        )
        assert restore_response.status_code == 200, f"Restore failed: {restore_response.text}"
        print("✓ Restored to PRO+ plan")
    
    def test_mailings_returns_403_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/mailings returns 403 for FREE user"""
        response = requests.get(f"{BASE_URL}/api/mailings", headers=auth_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO" in data.get("detail", ""), f"Error should mention PRO plan: {data}"
        print(f"✓ GET /api/mailings: 403 - {data.get('detail')}")
    
    def test_audit_log_returns_403_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/audit-log returns 403 for FREE user"""
        response = requests.get(f"{BASE_URL}/api/audit-log", headers=auth_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO" in data.get("detail", ""), f"Error should mention PRO plan: {data}"
        print(f"✓ GET /api/audit-log: 403 - {data.get('detail')}")
    
    def test_rooms_returns_403_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/rooms returns 403 for FREE user"""
        response = requests.get(f"{BASE_URL}/api/rooms", headers=auth_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO" in data.get("detail", ""), f"Error should mention PRO plan: {data}"
        print(f"✓ GET /api/rooms: 403 - {data.get('detail')}")
    
    def test_microsoft_calendar_returns_403_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/microsoft-calendar/status returns 403 for FREE user"""
        response = requests.get(f"{BASE_URL}/api/microsoft-calendar/status", headers=auth_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO" in data.get("detail", ""), f"Error should mention PRO plan: {data}"
        print(f"✓ GET /api/microsoft-calendar/status: 403 - {data.get('detail')}")
    
    def test_waitlist_returns_403_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/waitlist returns 403 for FREE user"""
        response = requests.get(f"{BASE_URL}/api/waitlist", headers=auth_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO" in data.get("detail", ""), f"Error should mention PRO plan: {data}"
        print(f"✓ GET /api/waitlist: 403 - {data.get('detail')}")
    
    def test_advanced_stats_returns_403_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/statistics/bookings-over-time returns 403 for FREE user"""
        response = requests.get(f"{BASE_URL}/api/statistics/bookings-over-time", headers=auth_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO" in data.get("detail", ""), f"Error should mention PRO plan: {data}"
        print(f"✓ GET /api/statistics/bookings-over-time: 403 - {data.get('detail')}")
    
    def test_schools_export_csv_returns_403_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/schools/export-csv returns 403 for FREE user"""
        response = requests.get(f"{BASE_URL}/api/schools/export-csv", headers=auth_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO" in data.get("detail", ""), f"Error should mention PRO plan: {data}"
        print(f"✓ GET /api/schools/export-csv: 403 - {data.get('detail')}")
    
    def test_basic_stats_still_accessible_for_free(self, auth_headers, downgrade_and_restore):
        """GET /api/statistics returns 200 for FREE user (no guard on basic stats)"""
        response = requests.get(f"{BASE_URL}/api/statistics", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/statistics: 200 OK (no guard on basic stats)")


class TestProUserAccess(TestSetup):
    """Test that PRO users (not PRO+) get 403 on PRO+ only features"""
    
    @pytest.fixture(scope="class")
    def set_pro_plan(self, auth_headers, institution_id):
        """Set to PRO plan, run tests, then restore to PRO+"""
        # Set to PRO
        response = requests.put(
            f"{BASE_URL}/api/plan/admin-change",
            headers=auth_headers,
            json={
                "institution_id": institution_id,
                "target_plan": "pro",
                "target_status": "active",
                "activated_by": "test"
            }
        )
        assert response.status_code == 200, f"Set PRO failed: {response.text}"
        print("✓ Set to PRO plan")
        
        yield  # Run tests
        
        # Restore to PRO+
        restore_response = requests.put(
            f"{BASE_URL}/api/plan/admin-change",
            headers=auth_headers,
            json={
                "institution_id": institution_id,
                "target_plan": "pro_plus",
                "target_status": "active",
                "activated_by": "test_restore"
            }
        )
        assert restore_response.status_code == 200, f"Restore failed: {restore_response.text}"
        print("✓ Restored to PRO+ plan")
    
    def test_events_payment_settings_returns_403_for_pro(self, auth_headers, set_pro_plan):
        """GET /api/events/settings/payment returns 403 for PRO user (only PRO+ has events_payments)"""
        response = requests.get(f"{BASE_URL}/api/events/settings/payment", headers=auth_headers)
        # Should be 403 because events_payments is PRO+ only
        # But may be 404 if events module not enabled
        if response.status_code == 404:
            print("✓ GET /api/events/settings/payment: 404 (events module not enabled)")
            pytest.skip("Events module not enabled for this institution")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "PRO+" in data.get("detail", "") or "pro_plus" in data.get("detail", "").lower(), f"Error should mention PRO+ plan: {data}"
        print(f"✓ GET /api/events/settings/payment: 403 - {data.get('detail')}")
    
    def test_mailings_accessible_for_pro(self, auth_headers, set_pro_plan):
        """GET /api/mailings returns 200 for PRO user (mailing is PRO feature)"""
        response = requests.get(f"{BASE_URL}/api/mailings", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/mailings: 200 OK (PRO has mailing)")
    
    def test_audit_log_accessible_for_pro(self, auth_headers, set_pro_plan):
        """GET /api/audit-log returns 200 for PRO user (audit_log is PRO feature)"""
        response = requests.get(f"{BASE_URL}/api/audit-log", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/audit-log: 200 OK (PRO has audit_log)")


class TestPublicEndpoints(TestSetup):
    """Test that public endpoints work without feature guards"""
    
    def test_waitlist_post_public_no_guard(self, institution_id):
        """POST /api/waitlist (public, no auth) still works without feature guard"""
        # This endpoint is public and should not have a feature guard
        # We just verify it doesn't return 403 (it may return 400/404 for invalid data)
        response = requests.post(
            f"{BASE_URL}/api/waitlist",
            json={
                "institution_id": institution_id,
                "program_id": "00000000-0000-0000-0000-000000000000",  # Invalid but tests guard
                "teacher_name": "Test Teacher",
                "school_name": "Test School",
                "email": "test@example.com",
                "participant_count": 10
            }
        )
        # Should NOT be 403 (feature guard) - may be 404 (program not found) or other
        assert response.status_code != 403, f"Public endpoint should not have feature guard: {response.status_code}"
        print(f"✓ POST /api/waitlist: {response.status_code} (no 403 feature guard)")


class TestErrorMessages(TestSetup):
    """Test that error messages include plan name"""
    
    @pytest.fixture(scope="class")
    def downgrade_for_error_test(self, auth_headers, institution_id):
        """Downgrade to FREE for error message testing"""
        response = requests.put(f"{BASE_URL}/api/plan/downgrade", headers=auth_headers)
        assert response.status_code == 200
        
        yield
        
        # Restore
        requests.put(
            f"{BASE_URL}/api/plan/admin-change",
            headers=auth_headers,
            json={
                "institution_id": institution_id,
                "target_plan": "pro_plus",
                "target_status": "active",
                "activated_by": "test_restore"
            }
        )
    
    def test_error_message_includes_plan_name(self, auth_headers, downgrade_for_error_test):
        """Error message includes plan name: 'Tato funkce vyžaduje plán PRO'"""
        response = requests.get(f"{BASE_URL}/api/mailings", headers=auth_headers)
        assert response.status_code == 403
        data = response.json()
        detail = data.get("detail", "")
        # Check for Czech message format
        assert "Tato funkce vyžaduje plán" in detail or "PRO" in detail, f"Error should mention plan: {detail}"
        print(f"✓ Error message format: {detail}")


class TestPlanStatusFeatures(TestSetup):
    """Test that /api/plan/status shows correct features"""
    
    def test_plan_status_shows_correct_features_for_pro_plus(self, auth_headers):
        """GET /api/plan/status shows correct features for PRO+ user"""
        response = requests.get(f"{BASE_URL}/api/plan/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        features = data.get("features", {})
        
        # PRO+ should have all features
        pro_plus_features = [
            "mailing", "events_basic", "events_payments", "waitlist",
            "audit_log", "outlook_sync", "collision_system", "advanced_stats", "data_export"
        ]
        
        for feature in pro_plus_features:
            assert feature in features, f"Feature {feature} not in response"
            assert features[feature]["has_access"] == True, f"PRO+ should have access to {feature}"
        
        print(f"✓ PRO+ has access to all {len(pro_plus_features)} tested features")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
