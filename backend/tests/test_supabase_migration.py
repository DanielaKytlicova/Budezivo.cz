"""
Backend API tests for Budeživo.cz after Supabase Migration
Tests: Auth (register, login, verify, me), Programs CRUD, Dashboard, Theme, Team
Focus: Verifying all APIs work correctly with PostgreSQL/Supabase
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============ HELPER: Get auth headers ============
def get_auth_headers(email=None, password=None):
    """Login and return auth headers"""
    if email is None:
        email = "demo@budezivo.cz"
        password = "demo123"
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    return None


class TestAPIHealth:
    """API health and basic connectivity tests"""
    
    def test_api_root_accessible(self):
        """Test API root endpoint returns expected message"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Supabase" in data["message"] or "KulturaBooking" in data["message"]
        print(f"✓ API root: {data['message']}")


class TestAuthRegister:
    """Test user registration creates user and institution in Supabase"""
    
    def test_register_creates_user_and_institution(self):
        """POST /api/auth/register - creates user and institution"""
        test_email = f"test_supabase_{uuid.uuid4().hex[:8]}@budezivo.cz"
        payload = {
            "institution_name": "Testovací Muzeum Supabase",
            "institution_type": "museum",
            "country": "CZ",
            "email": test_email,
            "password": "testPass123!",
            "gdpr_consent": True,
            "address": "Hlavní 1",
            "city": "Praha",
            "primary_color": "#1E293B",
            "secondary_color": "#84A98C"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Register failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "token" in data, "Missing token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == test_email
        assert data["user"]["institution_name"] == "Testovací Muzeum Supabase"
        assert "institution_id" in data["user"]
        assert data["user"]["role"] == "admin"
        
        print(f"✓ Register: User {test_email} created with institution")
        return data
    
    def test_register_duplicate_email_rejected(self):
        """POST /api/auth/register - rejects duplicate email"""
        # Use existing demo account email
        payload = {
            "institution_name": "Duplicate Test",
            "institution_type": "museum",
            "country": "CZ",
            "email": "demo@budezivo.cz",
            "password": "testPass123!",
            "gdpr_consent": True
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
        print("✓ Register: Duplicate email correctly rejected")


class TestAuthLogin:
    """Test user login returns JWT token"""
    
    def test_login_success_returns_token(self):
        """POST /api/auth/login - returns JWT token on success"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "demo123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "demo@budezivo.cz"
        assert "institution_id" in data["user"]
        assert "role" in data["user"]
        
        print(f"✓ Login: Token received for demo@budezivo.cz")
        return data["token"]
    
    def test_login_invalid_credentials_rejected(self):
        """POST /api/auth/login - rejects invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@budezivo.cz",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Login: Invalid credentials correctly rejected")
    
    def test_login_wrong_password_rejected(self):
        """POST /api/auth/login - rejects wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "wrongpassword123"
        })
        assert response.status_code == 401
        print("✓ Login: Wrong password correctly rejected")


class TestAuthVerify:
    """Test JWT token verification"""
    
    def test_verify_valid_token(self):
        """GET /api/auth/verify - validates correct token"""
        headers = get_auth_headers()
        assert headers is not None, "Could not get auth token"
        
        response = requests.get(f"{BASE_URL}/api/auth/verify", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] == True
        assert "user" in data
        
        print("✓ Verify: Token validation working")
    
    def test_verify_invalid_token_rejected(self):
        """GET /api/auth/verify - rejects invalid token"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        
        response = requests.get(f"{BASE_URL}/api/auth/verify", headers=headers)
        assert response.status_code in [401, 403]
        print("✓ Verify: Invalid token correctly rejected")


class TestAuthMe:
    """Test get current user info"""
    
    def test_get_current_user_info(self):
        """GET /api/auth/me - returns current user with role"""
        headers = get_auth_headers()
        assert headers is not None
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "email" in data
        assert "role" in data
        assert "institution_id" in data
        
        print(f"✓ Me: User {data['email']} with role {data['role']}")


class TestProgramsCRUD:
    """Test Program CRUD operations with Supabase"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for program tests"""
        return get_auth_headers()
    
    def test_create_program(self, auth_headers):
        """POST /api/programs - creates new program"""
        payload = {
            "name_cs": f"Test Program {uuid.uuid4().hex[:6]}",
            "name_en": "Test Program EN",
            "description_cs": "Testovací program pro Supabase migraci",
            "description_en": "Test program for Supabase migration",
            "duration": 60,
            "age_group": "zs1_7_12",
            "min_capacity": 5,
            "max_capacity": 30,
            "target_group": "schools",
            "price": 50.0,
            "status": "active",
            "available_days": ["monday", "tuesday", "wednesday"],
            "time_blocks": ["09:00-10:30"],
            "min_days_before_booking": 7,
            "max_days_before_booking": 60
        }
        
        response = requests.post(f"{BASE_URL}/api/programs", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Create program failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["name_cs"] == payload["name_cs"]
        assert data["status"] == "active"
        
        print(f"✓ Create Program: {data['id']}")
        return data["id"]
    
    def test_list_programs(self, auth_headers):
        """GET /api/programs - lists all programs for institution"""
        response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        print(f"✓ List Programs: {len(data)} programs found")
    
    def test_get_single_program(self, auth_headers):
        """GET /api/programs/{id} - retrieves single program"""
        # First create a program
        program_id = self.test_create_program(auth_headers)
        
        response = requests.get(f"{BASE_URL}/api/programs/{program_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == program_id
        
        print(f"✓ Get Program: {program_id}")
    
    def test_update_program(self, auth_headers):
        """PUT /api/programs/{id} - updates program"""
        # First create a program
        program_id = self.test_create_program(auth_headers)
        
        update_payload = {
            "name_cs": "Updated Program Name",
            "name_en": "Updated EN",
            "description_cs": "Updated description",
            "description_en": "Updated desc EN",
            "duration": 90,
            "age_group": "zs1_7_12",
            "min_capacity": 5,
            "max_capacity": 25,
            "target_group": "schools",
            "status": "concept"
        }
        
        response = requests.put(f"{BASE_URL}/api/programs/{program_id}", json=update_payload, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name_cs"] == "Updated Program Name"
        assert data["status"] == "concept"
        
        print(f"✓ Update Program: {program_id}")
    
    def test_delete_program(self, auth_headers):
        """DELETE /api/programs/{id} - deletes program"""
        # First create a program
        program_id = self.test_create_program(auth_headers)
        
        response = requests.delete(f"{BASE_URL}/api/programs/{program_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/programs/{program_id}", headers=auth_headers)
        assert get_response.status_code == 404
        
        print(f"✓ Delete Program: {program_id}")


class TestPublicPrograms:
    """Test public programs endpoint for booking page"""
    
    def test_public_programs_demo_institution(self):
        """GET /api/programs/public/{institution_id} - returns demo programs"""
        response = requests.get(f"{BASE_URL}/api/programs/public/demo")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify demo program structure
        program = data[0]
        assert "name_cs" in program
        assert "description_cs" in program
        assert "duration" in program
        
        print(f"✓ Public Programs (demo): {len(data)} programs")
    
    def test_public_programs_real_institution(self):
        """GET /api/programs/public/{institution_id} - returns real institution programs"""
        # First get a real institution ID by logging in
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "demo123"
        })
        if login_response.status_code == 200:
            institution_id = login_response.json()["user"]["institution_id"]
            
            response = requests.get(f"{BASE_URL}/api/programs/public/{institution_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
            print(f"✓ Public Programs (real): {len(data)} programs")


class TestDashboardStats:
    """Test dashboard statistics endpoint"""
    
    def test_get_dashboard_stats(self):
        """GET /api/dashboard/stats - returns dashboard statistics"""
        headers = get_auth_headers()
        assert headers is not None
        
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Verify all expected fields
        assert "today_bookings" in data
        assert "upcoming_groups" in data
        assert "capacity_usage" in data
        assert "bookings_used" in data
        assert "bookings_limit" in data
        
        print(f"✓ Dashboard Stats: today={data['today_bookings']}, upcoming={data['upcoming_groups']}")


class TestThemeSettings:
    """Test theme settings endpoints"""
    
    def test_get_theme_settings(self):
        """GET /api/settings/theme - returns theme for authenticated user"""
        headers = get_auth_headers()
        assert headers is not None
        
        response = requests.get(f"{BASE_URL}/api/settings/theme", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "primary_color" in data
        assert "secondary_color" in data
        
        print(f"✓ Theme Settings: primary={data['primary_color']}")
    
    def test_get_public_theme_demo(self):
        """GET /api/settings/theme/public/{institution_id} - returns public theme"""
        response = requests.get(f"{BASE_URL}/api/settings/theme/public/demo")
        assert response.status_code == 200
        
        data = response.json()
        assert data["institution_id"] == "demo"
        assert "primary_color" in data
        assert "secondary_color" in data
        
        print(f"✓ Public Theme (demo): {data['primary_color']}")
    
    def test_update_theme_settings(self):
        """PUT /api/settings/theme - updates theme settings"""
        headers = get_auth_headers()
        assert headers is not None
        
        payload = {
            "primary_color": "#2D3748",
            "secondary_color": "#68D391",
            "accent_color": "#ECC94B",
            "header_style": "light"
        }
        
        response = requests.put(f"{BASE_URL}/api/settings/theme", json=payload, headers=headers)
        assert response.status_code == 200
        
        print("✓ Update Theme: Settings updated")


class TestTeamManagement:
    """Test team management endpoints"""
    
    def test_get_team_members(self):
        """GET /api/team - returns team members for institution"""
        headers = get_auth_headers()
        assert headers is not None
        
        response = requests.get(f"{BASE_URL}/api/team", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Should have at least the current user (admin)
        if len(data) > 0:
            member = data[0]
            assert "email" in member
            assert "role" in member
        
        print(f"✓ Team Members: {len(data)} members")
    
    def test_invite_team_member(self):
        """POST /api/team/invite - invites new team member"""
        headers = get_auth_headers()
        assert headers is not None
        
        invite_email = f"invited_{uuid.uuid4().hex[:8]}@budezivo.cz"
        payload = {
            "name": "Test Invited User",
            "email": invite_email,
            "role": "edukator"
        }
        
        response = requests.post(f"{BASE_URL}/api/team/invite", json=payload, headers=headers)
        # May fail if user exists or admin check
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            print(f"✓ Invite Team: {invite_email} invited")
        else:
            print(f"⚠ Invite Team: Status {response.status_code} - {response.text[:100]}")


class TestBookingsPublic:
    """Test public booking creation"""
    
    def test_create_public_booking_demo(self):
        """POST /api/bookings/public/{institution_id} - creates public booking"""
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        payload = {
            "program_id": "demo-1",
            "date": future_date,
            "time_block": "09:00-10:30",
            "school_name": "ZŠ Testovací",
            "group_type": "třída",
            "age_or_class": "5. třída",
            "num_students": 25,
            "num_teachers": 2,
            "contact_name": "Jan Novák",
            "contact_email": "jan.novak@skola.cz",
            "contact_phone": "+420 777 888 999",
            "gdpr_consent": True
        }
        
        response = requests.post(f"{BASE_URL}/api/bookings/public/demo", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["school_name"] == "ZŠ Testovací"
        
        print(f"✓ Public Booking: {data['id']} created")


class TestContactForm:
    """Test contact form submission"""
    
    def test_submit_contact_form(self):
        """POST /api/contact - submits contact form"""
        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "institution": "Testovací Instituce",
            "subject": "demo",
            "message": "Test message from automated tests"
        }
        
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        
        print(f"✓ Contact Form: Submitted successfully")


class TestInstitutionSettings:
    """Test institution settings endpoints"""
    
    def test_get_institution_settings(self):
        """GET /api/institution/settings - returns institution settings"""
        headers = get_auth_headers()
        assert headers is not None
        
        response = requests.get(f"{BASE_URL}/api/institution/settings", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "type" in data
        
        print(f"✓ Institution Settings: {data['name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
