"""
Backend API tests for Booking Detail with RBAC permissions
Tests: Booking update, actual attendance tracking, lecturer assignment/unassignment
Features from: budezivo.cz booking detail modal implementation
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuthMe:
    """Tests for /api/auth/me endpoint - get current user info including role"""
    
    @pytest.fixture
    def auth_user(self):
        """Create authenticated user"""
        test_email = f"test_me_{uuid.uuid4().hex[:8]}@test.cz"
        payload = {
            "institution_name": "Auth Me Test",
            "institution_type": "museum",
            "country": "Česká republika",
            "email": test_email,
            "password": "testPassword123",
            "gdpr_consent": True
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        data = response.json()
        return {
            "email": test_email,
            "token": data["token"],
            "user_id": data["user"]["id"],
            "institution_id": data["user"]["institution_id"]
        }
    
    def test_get_current_user_info(self, auth_user):
        """Test GET /api/auth/me returns user info with role"""
        headers = {"Authorization": f"Bearer {auth_user['token']}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Auth me failed: {response.text}"
        data = response.json()
        
        # Verify response contains required fields
        assert data["email"] == auth_user["email"]
        assert data["id"] == auth_user["user_id"]
        assert data["institution_id"] == auth_user["institution_id"]
        assert "role" in data  # Role must be present
        assert data["role"] == "admin"  # First user is admin
        print(f"Auth me response: {data['email']}, role: {data['role']}")


class TestBookingUpdate:
    """Tests for PUT /api/bookings/{id} - update booking with RBAC"""
    
    @pytest.fixture
    def setup_booking(self):
        """Create user and booking for update tests"""
        test_email = f"test_update_{uuid.uuid4().hex[:8]}@test.cz"
        register_payload = {
            "institution_name": "Booking Update Test",
            "institution_type": "museum",
            "country": "Česká republika",
            "email": test_email,
            "password": "testPassword123",
            "gdpr_consent": True
        }
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=register_payload)
        reg_data = reg_response.json()
        headers = {"Authorization": f"Bearer {reg_data['token']}"}
        
        # Create a booking
        booking_payload = {
            "program_id": "test-program-1",
            "date": "2026-03-15",
            "time_block": "09:00-10:30",
            "school_name": "ZŠ Testovací",
            "group_type": "zs1_7_12",
            "age_or_class": "4.A",
            "num_students": 25,
            "num_teachers": 2,
            "special_requirements": "Bezbariérový přístup",
            "contact_name": "Jan Novák",
            "contact_email": "jan.novak@skola.cz",
            "contact_phone": "+420 123 456 789",
            "gdpr_consent": True
        }
        booking_response = requests.post(f"{BASE_URL}/api/bookings", json=booking_payload, headers=headers)
        booking_data = booking_response.json()
        
        return {
            "headers": headers,
            "booking_id": booking_data["id"],
            "token": reg_data["token"]
        }
    
    def test_update_booking_status(self, setup_booking):
        """Test updating booking status (admin role)"""
        headers = setup_booking["headers"]
        booking_id = setup_booking["booking_id"]
        
        # Update status to confirmed
        update_payload = {"status": "confirmed"}
        response = requests.put(f"{BASE_URL}/api/bookings/{booking_id}", json=update_payload, headers=headers)
        
        assert response.status_code == 200, f"Update failed: {response.text}"
        data = response.json()
        assert data["message"] == "Booking updated"
        assert "status" in data["updated_fields"]
        print(f"Booking status updated successfully")
    
    def test_update_actual_attendance(self, setup_booking):
        """Test updating actual attendance (skutečná účast)"""
        headers = setup_booking["headers"]
        booking_id = setup_booking["booking_id"]
        
        # First confirm booking
        requests.put(f"{BASE_URL}/api/bookings/{booking_id}", json={"status": "confirmed"}, headers=headers)
        
        # Update actual attendance
        update_payload = {
            "actual_students": 22,
            "actual_teachers": 2
        }
        response = requests.put(f"{BASE_URL}/api/bookings/{booking_id}", json=update_payload, headers=headers)
        
        assert response.status_code == 200, f"Attendance update failed: {response.text}"
        data = response.json()
        assert "actual_students" in data["updated_fields"]
        assert "actual_teachers" in data["updated_fields"]
        print(f"Actual attendance updated: {update_payload}")
        
        # Verify persistence with GET
        get_response = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
        booking = get_response.json()
        assert booking["actual_students"] == 22
        assert booking["actual_teachers"] == 2
    
    def test_update_booking_notes(self, setup_booking):
        """Test updating internal notes"""
        headers = setup_booking["headers"]
        booking_id = setup_booking["booking_id"]
        
        update_payload = {"notes": "Skupina dorazila včas, program proběhl bez problémů."}
        response = requests.put(f"{BASE_URL}/api/bookings/{booking_id}", json=update_payload, headers=headers)
        
        assert response.status_code == 200, f"Notes update failed: {response.text}"
        data = response.json()
        assert "notes" in data["updated_fields"]
        print(f"Notes updated successfully")
    
    def test_update_nonexistent_booking(self, setup_booking):
        """Test updating non-existent booking returns 404"""
        headers = setup_booking["headers"]
        fake_id = str(uuid.uuid4())
        
        response = requests.put(f"{BASE_URL}/api/bookings/{fake_id}", json={"status": "confirmed"}, headers=headers)
        assert response.status_code == 404
        print(f"Non-existent booking correctly returned 404")


class TestLecturerAssignment:
    """Tests for lecturer assignment endpoints"""
    
    @pytest.fixture
    def setup_with_booking(self):
        """Create user with booking for lecturer tests"""
        test_email = f"test_lecturer_{uuid.uuid4().hex[:8]}@test.cz"
        register_payload = {
            "institution_name": "Lecturer Test Institution",
            "institution_type": "gallery",
            "country": "Česká republika",
            "email": test_email,
            "password": "testPassword123",
            "gdpr_consent": True
        }
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=register_payload)
        reg_data = reg_response.json()
        headers = {"Authorization": f"Bearer {reg_data['token']}"}
        
        # Create booking
        booking_payload = {
            "program_id": "test-program-2",
            "date": "2026-03-20",
            "time_block": "10:00-11:30",
            "school_name": "Gymnázium Testovací",
            "group_type": "ss_14_18",
            "age_or_class": "2.A",
            "num_students": 30,
            "num_teachers": 2,
            "contact_name": "Marie Nová",
            "contact_email": "marie@gymn.cz",
            "contact_phone": "+420 987 654 321",
            "gdpr_consent": True
        }
        booking_response = requests.post(f"{BASE_URL}/api/bookings", json=booking_payload, headers=headers)
        booking_data = booking_response.json()
        
        return {
            "headers": headers,
            "booking_id": booking_data["id"],
            "user_email": test_email,
            "user_id": reg_data["user"]["id"]
        }
    
    def test_assign_lecturer_self(self, setup_with_booking):
        """Test POST /api/bookings/{id}/assign-lecturer - self assign"""
        headers = setup_with_booking["headers"]
        booking_id = setup_with_booking["booking_id"]
        
        response = requests.post(f"{BASE_URL}/api/bookings/{booking_id}/assign-lecturer", headers=headers)
        
        assert response.status_code == 200, f"Assign lecturer failed: {response.text}"
        data = response.json()
        assert data["message"] == "Lecturer assigned"
        assert "lecturer_name" in data
        print(f"Lecturer assigned: {data['lecturer_name']}")
        
        # Verify assignment persisted
        get_response = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
        booking = get_response.json()
        assert booking["assigned_lecturer_id"] is not None
        assert booking["assigned_lecturer_name"] is not None
        assert booking["assigned_lecturer_at"] is not None
    
    def test_assign_lecturer_already_assigned(self, setup_with_booking):
        """Test assigning lecturer when already assigned fails"""
        headers = setup_with_booking["headers"]
        booking_id = setup_with_booking["booking_id"]
        
        # First assignment
        requests.post(f"{BASE_URL}/api/bookings/{booking_id}/assign-lecturer", headers=headers)
        
        # Second assignment should fail
        response = requests.post(f"{BASE_URL}/api/bookings/{booking_id}/assign-lecturer", headers=headers)
        assert response.status_code == 400
        assert "already has an assigned lecturer" in response.json()["detail"]
        print(f"Double assignment correctly rejected")
    
    def test_unassign_lecturer(self, setup_with_booking):
        """Test DELETE /api/bookings/{id}/unassign-lecturer"""
        headers = setup_with_booking["headers"]
        booking_id = setup_with_booking["booking_id"]
        
        # First assign
        requests.post(f"{BASE_URL}/api/bookings/{booking_id}/assign-lecturer", headers=headers)
        
        # Then unassign
        response = requests.delete(f"{BASE_URL}/api/bookings/{booking_id}/unassign-lecturer", headers=headers)
        
        assert response.status_code == 200, f"Unassign failed: {response.text}"
        assert response.json()["message"] == "Lecturer unassigned"
        print(f"Lecturer unassigned successfully")
        
        # Verify unassignment persisted
        get_response = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=headers)
        booking = get_response.json()
        assert booking["assigned_lecturer_id"] is None
        assert booking["assigned_lecturer_name"] is None
    
    def test_assign_lecturer_nonexistent_booking(self, setup_with_booking):
        """Test assigning to non-existent booking returns 404"""
        headers = setup_with_booking["headers"]
        fake_id = str(uuid.uuid4())
        
        response = requests.post(f"{BASE_URL}/api/bookings/{fake_id}/assign-lecturer", headers=headers)
        assert response.status_code == 404
        print(f"Non-existent booking correctly returned 404")


class TestBookingsWithNumTeachers:
    """Tests for num_teachers field in BookingBase model"""
    
    @pytest.fixture
    def auth_headers(self):
        """Create authenticated user"""
        test_email = f"test_teachers_{uuid.uuid4().hex[:8]}@test.cz"
        payload = {
            "institution_name": "Teachers Test",
            "institution_type": "museum",
            "country": "Česká republika",
            "email": test_email,
            "password": "testPassword123",
            "gdpr_consent": True
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_create_booking_with_num_teachers(self, auth_headers):
        """Test booking creation includes num_teachers field"""
        booking_payload = {
            "program_id": "test-program-3",
            "date": "2026-04-10",
            "time_block": "13:00-14:30",
            "school_name": "MŠ Sluníčko",
            "group_type": "ms_3_6",
            "age_or_class": "3-4 roky",
            "num_students": 15,
            "num_teachers": 3,  # Multiple teachers for kindergarten
            "contact_name": "Eva Krásná",
            "contact_email": "eva@ms.cz",
            "contact_phone": "+420 111 222 333",
            "gdpr_consent": True
        }
        response = requests.post(f"{BASE_URL}/api/bookings", json=booking_payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Booking creation failed: {response.text}"
        data = response.json()
        
        assert data["num_students"] == 15
        assert data["num_teachers"] == 3
        print(f"Booking created with num_teachers: {data['num_teachers']}")
        
        # Verify via GET
        booking_id = data["id"]
        get_response = requests.get(f"{BASE_URL}/api/bookings/{booking_id}", headers=auth_headers)
        booking = get_response.json()
        assert booking["num_teachers"] == 3


class TestDemoUserLogin:
    """Tests using demo account credentials from requirements"""
    
    def test_login_demo_account(self):
        """Test login with demo@budezivo.cz / demo123"""
        payload = {
            "email": "demo@budezivo.cz",
            "password": "demo123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        # If demo account exists, should return 200
        # If not exists, create it first
        if response.status_code == 401:
            # Create demo account
            register_payload = {
                "institution_name": "Demo Instituce",
                "institution_type": "museum",
                "country": "Česká republika",
                "email": "demo@budezivo.cz",
                "password": "demo123",
                "gdpr_consent": True
            }
            reg_response = requests.post(f"{BASE_URL}/api/auth/register", json=register_payload)
            if reg_response.status_code == 200:
                response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"Demo account login successful, role: {data['user']['role']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
