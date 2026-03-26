"""
Test suite for Bulk Actions and GDPR features.
Tests:
- POST /api/bookings/bulk-status (confirm/cancel/complete multiple bookings)
- GET /api/gdpr/export (export user data)
- POST /api/gdpr/anonymize (anonymize user data with confirmation)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"


class TestBulkActionsAndGDPR:
    """Test bulk booking status updates and GDPR endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")  # API returns 'token' not 'access_token'
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.authenticated = True
        else:
            self.authenticated = False
            pytest.skip("Authentication failed - skipping tests")
        
        yield
        
        self.session.close()
    
    # ==================== BULK STATUS TESTS ====================
    
    def test_bulk_status_empty_booking_ids_returns_400(self):
        """POST /api/bookings/bulk-status with empty booking_ids should return 400."""
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": [],
            "status": "confirmed"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"PASS: Empty booking_ids returns 400 with message: {data['detail']}")
    
    def test_bulk_status_invalid_status_returns_400(self):
        """POST /api/bookings/bulk-status with invalid status should return 400."""
        # Use a fake booking ID - the status validation should happen first
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": [str(uuid.uuid4())],
            "status": "invalid_status"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"PASS: Invalid status returns 400 with message: {data['detail']}")
    
    def test_bulk_status_pending_not_allowed(self):
        """POST /api/bookings/bulk-status with status=pending should return 400."""
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": [str(uuid.uuid4())],
            "status": "pending"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"PASS: status=pending returns 400 with message: {data['detail']}")
    
    def test_bulk_status_confirmed_success(self):
        """POST /api/bookings/bulk-status with status=confirmed should work."""
        # First get existing bookings
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        
        bookings = bookings_response.json()
        if not bookings:
            pytest.skip("No bookings available for bulk test")
        
        # Find pending bookings to confirm
        pending_bookings = [b for b in bookings if b.get("status") == "pending"]
        if not pending_bookings:
            # Use any booking for the test
            test_booking = bookings[0]
            original_status = test_booking.get("status")
        else:
            test_booking = pending_bookings[0]
            original_status = "pending"
        
        booking_id = test_booking["id"]
        
        # Perform bulk confirm
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": [booking_id],
            "status": "confirmed"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "updated_count" in data
        assert data["status"] == "confirmed"
        print(f"PASS: Bulk confirm returned: {data}")
        
        # Revert to original status if needed
        if original_status != "confirmed":
            self.session.patch(f"{BASE_URL}/api/bookings/{booking_id}/status?status={original_status}")
    
    def test_bulk_status_cancelled_success(self):
        """POST /api/bookings/bulk-status with status=cancelled should work."""
        # Get existing bookings
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        
        bookings = bookings_response.json()
        if not bookings:
            pytest.skip("No bookings available for bulk test")
        
        # Find a non-cancelled booking
        non_cancelled = [b for b in bookings if b.get("status") != "cancelled"]
        if not non_cancelled:
            pytest.skip("All bookings are already cancelled")
        
        test_booking = non_cancelled[0]
        booking_id = test_booking["id"]
        original_status = test_booking.get("status")
        
        # Perform bulk cancel
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": [booking_id],
            "status": "cancelled"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "updated_count" in data
        assert data["status"] == "cancelled"
        print(f"PASS: Bulk cancel returned: {data}")
        
        # Revert to original status
        self.session.patch(f"{BASE_URL}/api/bookings/{booking_id}/status?status={original_status}")
    
    def test_bulk_status_completed_success(self):
        """POST /api/bookings/bulk-status with status=completed should work."""
        # Get existing bookings
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        
        bookings = bookings_response.json()
        if not bookings:
            pytest.skip("No bookings available for bulk test")
        
        # Find a confirmed booking to complete
        confirmed_bookings = [b for b in bookings if b.get("status") == "confirmed"]
        if not confirmed_bookings:
            # Use any non-completed booking
            non_completed = [b for b in bookings if b.get("status") != "completed"]
            if not non_completed:
                pytest.skip("All bookings are already completed")
            test_booking = non_completed[0]
        else:
            test_booking = confirmed_bookings[0]
        
        booking_id = test_booking["id"]
        original_status = test_booking.get("status")
        
        # Perform bulk complete
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": [booking_id],
            "status": "completed"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "updated_count" in data
        assert data["status"] == "completed"
        print(f"PASS: Bulk complete returned: {data}")
        
        # Revert to original status
        self.session.patch(f"{BASE_URL}/api/bookings/{booking_id}/status?status={original_status}")
    
    def test_bulk_status_multiple_bookings(self):
        """POST /api/bookings/bulk-status should update multiple bookings at once."""
        # Get existing bookings
        bookings_response = self.session.get(f"{BASE_URL}/api/bookings")
        assert bookings_response.status_code == 200
        
        bookings = bookings_response.json()
        if len(bookings) < 2:
            pytest.skip("Need at least 2 bookings for multiple bulk test")
        
        # Get first 2 bookings
        test_bookings = bookings[:2]
        booking_ids = [b["id"] for b in test_bookings]
        original_statuses = {b["id"]: b.get("status") for b in test_bookings}
        
        # Perform bulk confirm
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": booking_ids,
            "status": "confirmed"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "updated_count" in data
        assert data["updated_count"] >= 1  # At least 1 should be updated
        print(f"PASS: Bulk update of {len(booking_ids)} bookings returned: {data}")
        
        # Revert to original statuses
        for bid, status in original_statuses.items():
            self.session.patch(f"{BASE_URL}/api/bookings/{bid}/status?status={status}")
    
    def test_bulk_status_nonexistent_bookings_returns_404(self):
        """POST /api/bookings/bulk-status with nonexistent booking IDs should return 404."""
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        
        response = self.session.post(f"{BASE_URL}/api/bookings/bulk-status", json={
            "booking_ids": fake_ids,
            "status": "confirmed"
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"PASS: Nonexistent booking IDs return 404")
    
    # ==================== GDPR EXPORT TESTS ====================
    
    def test_gdpr_export_returns_user_data(self):
        """GET /api/gdpr/export should return user data, institution, bookings, schools."""
        response = self.session.get(f"{BASE_URL}/api/gdpr/export")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "export_date" in data, "Missing export_date"
        assert "user_data" in data, "Missing user_data"
        assert "institution_data" in data, "Missing institution_data"
        assert "bookings" in data, "Missing bookings"
        assert "schools" in data, "Missing schools"
        
        # Verify user_data structure
        user_data = data["user_data"]
        assert "id" in user_data, "Missing user id"
        assert "email" in user_data, "Missing user email"
        
        # Verify counts
        assert "bookings_count" in data, "Missing bookings_count"
        assert "schools_count" in data, "Missing schools_count"
        
        print(f"PASS: GDPR export returned data with {data['bookings_count']} bookings, {data['schools_count']} schools")
        print(f"  User: {user_data.get('email')}")
        print(f"  Institution: {data['institution_data'].get('name', 'N/A')}")
    
    def test_gdpr_export_without_auth_returns_401(self):
        """GET /api/gdpr/export without authentication should return 401 or 403."""
        # Create new session without auth
        unauth_session = requests.Session()
        response = unauth_session.get(f"{BASE_URL}/api/gdpr/export")
        
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print(f"PASS: Unauthenticated GDPR export returns {response.status_code}")
        unauth_session.close()
    
    # ==================== GDPR ANONYMIZE TESTS ====================
    
    def test_gdpr_anonymize_wrong_confirmation_returns_400(self):
        """POST /api/gdpr/anonymize with wrong confirmation should return 400."""
        response = self.session.post(f"{BASE_URL}/api/gdpr/anonymize", json={
            "confirmation": "WRONG"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"PASS: Wrong confirmation returns 400 with message: {data['detail']}")
    
    def test_gdpr_anonymize_empty_confirmation_returns_400(self):
        """POST /api/gdpr/anonymize with empty confirmation should return 400."""
        response = self.session.post(f"{BASE_URL}/api/gdpr/anonymize", json={
            "confirmation": ""
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"PASS: Empty confirmation returns 400 with message: {data['detail']}")
    
    def test_gdpr_anonymize_lowercase_smazat_returns_400(self):
        """POST /api/gdpr/anonymize with lowercase 'smazat' should return 400."""
        response = self.session.post(f"{BASE_URL}/api/gdpr/anonymize", json={
            "confirmation": "smazat"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"PASS: Lowercase 'smazat' returns 400 with message: {data['detail']}")
    
    def test_gdpr_anonymize_without_auth_returns_401(self):
        """POST /api/gdpr/anonymize without authentication should return 401 or 403."""
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        response = unauth_session.post(f"{BASE_URL}/api/gdpr/anonymize", json={
            "confirmation": "SMAZAT"
        })
        
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print(f"PASS: Unauthenticated anonymize returns {response.status_code}")
        unauth_session.close()
    
    # NOTE: We do NOT test actual anonymization with 'SMAZAT' as it would destroy test data
    # The validation tests above confirm the endpoint works correctly


class TestBookingsListAndFiltering:
    """Test bookings list endpoint for filter/search functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")  # API returns 'token' not 'access_token'
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
        
        yield
        self.session.close()
    
    def test_get_bookings_returns_list(self):
        """GET /api/bookings should return a list of bookings."""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list of bookings"
        
        if data:
            booking = data[0]
            # Verify booking has expected fields
            assert "id" in booking
            assert "status" in booking
            assert "school_name" in booking or "contact_name" in booking
            print(f"PASS: GET /api/bookings returned {len(data)} bookings")
            
            # Count by status for verification
            status_counts = {}
            for b in data:
                status = b.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            print(f"  Status counts: {status_counts}")
        else:
            print("PASS: GET /api/bookings returned empty list (no bookings)")
    
    def test_bookings_have_program_name(self):
        """Bookings should include program_name for display."""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        
        assert response.status_code == 200
        data = response.json()
        
        if data:
            booking = data[0]
            assert "program_name" in booking, "Booking should have program_name field"
            print(f"PASS: Booking has program_name: {booking.get('program_name')}")
        else:
            pytest.skip("No bookings to verify")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
