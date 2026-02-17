"""
Backend API tests for KulturaBooking - Czech Cultural Reservation System
Tests: Registration wizard flow, Programs CRUD with new fields, Authentication
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAPIHealth:
    """Basic API health and connectivity tests"""
    
    def test_api_root(self):
        """Test API root endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"API root response: {data}")


class TestRegistrationWizard:
    """Tests for 4-step registration wizard with all new fields"""
    
    def test_register_step1_basic_fields(self):
        """Test registration with step 1 fields only (institution name, type, email, password)"""
        test_email = f"test_step1_{uuid.uuid4().hex[:8]}@muzeum.cz"
        payload = {
            "institution_name": "Testovací Muzeum",
            "institution_type": "museum",
            "country": "Česká republika",
            "email": test_email,
            "password": "securePassword123",
            "gdpr_consent": True
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == test_email
        assert data["user"]["institution_name"] == "Testovací Muzeum"
        print(f"Step 1 registration successful for: {test_email}")
    
    def test_register_step2_address_logo_colors(self):
        """Test registration with step 2 fields (address, city, IČ/DIČ, logo, colors)"""
        test_email = f"test_step2_{uuid.uuid4().hex[:8]}@galerie.cz"
        payload = {
            # Step 1 - Required
            "institution_name": "Oblastní Galerie",
            "institution_type": "gallery",
            "country": "Česká republika",
            "email": test_email,
            "password": "securePassword123",
            "gdpr_consent": True,
            # Step 2 - Address and branding
            "address": "Zahradní 101",
            "city": "Praha",
            "ico_dic": "CZ12345678",
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#2D3748",
            "secondary_color": "#68D391"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        assert "token" in data
        assert data["user"]["email"] == test_email
        print(f"Step 2 registration successful with address/colors for: {test_email}")
    
    def test_register_step3_schedule_time_blocks(self):
        """Test registration with step 3 fields (available days, time blocks, dates)"""
        test_email = f"test_step3_{uuid.uuid4().hex[:8]}@knihovna.cz"
        payload = {
            # Step 1-2
            "institution_name": "Městská Knihovna",
            "institution_type": "library",
            "country": "Česká republika",
            "email": test_email,
            "password": "securePassword123",
            "gdpr_consent": True,
            "address": "Hlavní 15",
            "city": "Brno",
            # Step 3 - Schedule
            "default_available_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "default_time_blocks": [
                {"start": "09:00", "end": "10:30"},
                {"start": "13:00", "end": "14:30"}
            ],
            "operating_start_date": "2026-01-01",
            "operating_end_date": "2026-12-31"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        assert "token" in data
        print(f"Step 3 registration successful with schedule for: {test_email}")
    
    def test_register_step4_program_defaults(self):
        """Test registration with step 4 fields (default program settings)"""
        test_email = f"test_step4_{uuid.uuid4().hex[:8]}@divadlo.cz"
        payload = {
            # All steps
            "institution_name": "Národní Divadlo",
            "institution_type": "theater",
            "country": "Česká republika",
            "email": test_email,
            "password": "securePassword123",
            "gdpr_consent": True,
            "address": "Karlova 1",
            "city": "Praha",
            "ico_dic": "CZ87654321",
            "default_available_days": ["tuesday", "wednesday", "thursday", "friday", "saturday"],
            "default_time_blocks": [{"start": "10:00", "end": "11:30"}],
            # Step 4 - Program defaults
            "default_program_description": "Interaktivní prohlídka pro školy",
            "default_program_duration": 90,
            "default_program_capacity": 25,
            "default_target_group": "zs1_7_12"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        assert "token" in data
        print(f"Step 4 registration successful with program defaults for: {test_email}")
    
    def test_register_duplicate_email_rejected(self):
        """Test that duplicate email registration is rejected"""
        test_email = f"test_duplicate_{uuid.uuid4().hex[:8]}@test.cz"
        payload = {
            "institution_name": "Test Institution",
            "institution_type": "museum",
            "country": "Česká republika",
            "email": test_email,
            "password": "securePassword123",
            "gdpr_consent": True
        }
        # First registration
        response1 = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response1.status_code == 200
        
        # Duplicate registration should fail
        response2 = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert response2.status_code == 400
        print(f"Duplicate email correctly rejected")


class TestAuthentication:
    """Tests for login and token verification"""
    
    @pytest.fixture
    def registered_user(self):
        """Create a registered user for auth tests"""
        test_email = f"test_auth_{uuid.uuid4().hex[:8]}@test.cz"
        payload = {
            "institution_name": "Auth Test Institution",
            "institution_type": "museum",
            "country": "Česká republika",
            "email": test_email,
            "password": "testPassword123",
            "gdpr_consent": True
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        data = response.json()
        return {"email": test_email, "password": "testPassword123", "token": data["token"]}
    
    def test_login_success(self, registered_user):
        """Test successful login with valid credentials"""
        payload = {
            "email": registered_user["email"],
            "password": registered_user["password"]
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == registered_user["email"]
        print(f"Login successful for: {registered_user['email']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials fails"""
        payload = {
            "email": "nonexistent@test.cz",
            "password": "wrongPassword"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert response.status_code == 401
        print("Invalid login correctly rejected")
    
    def test_token_verification(self, registered_user):
        """Test JWT token verification"""
        headers = {"Authorization": f"Bearer {registered_user['token']}"}
        response = requests.get(f"{BASE_URL}/api/auth/verify", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] == True
        print("Token verification successful")
    
    def test_forgot_password(self, registered_user):
        """Test forgot password endpoint"""
        payload = {"email": registered_user["email"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("Forgot password endpoint working")


class TestProgramsCRUD:
    """Tests for Programs API with new Figma fields (tabs, status, booking params)"""
    
    @pytest.fixture
    def auth_headers(self):
        """Create authenticated user and return headers"""
        test_email = f"test_programs_{uuid.uuid4().hex[:8]}@test.cz"
        payload = {
            "institution_name": "Programs Test Institution",
            "institution_type": "gallery",
            "country": "Česká republika",
            "email": test_email,
            "password": "testPassword123",
            "gdpr_consent": True
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_create_program_basic(self, auth_headers):
        """Test creating a program with basic fields"""
        payload = {
            "name_cs": "Seznam se s galerií",
            "name_en": "Gallery Introduction",
            "description_cs": "Interaktivní program pro školy",
            "description_en": "Interactive program for schools",
            "duration": 90,
            "age_group": "zs1_7_12",
            "min_capacity": 5,
            "max_capacity": 25,
            "target_group": "schools",
            "price": 50.0,
            "status": "active"
        }
        response = requests.post(f"{BASE_URL}/api/programs", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Create program failed: {response.text}"
        data = response.json()
        
        assert data["name_cs"] == "Seznam se s galerií"
        assert data["status"] == "active"
        assert "id" in data
        print(f"Program created: {data['id']}")
        return data["id"]
    
    def test_create_program_with_figma_fields(self, auth_headers):
        """Test creating a program with all new Figma wireframe fields"""
        payload = {
            "name_cs": "Po stopách historie",
            "name_en": "Following History",
            "description_cs": "Tematická prohlídka zaměřená na historii",
            "description_en": "Themed tour focused on history",
            "duration": 60,
            "age_group": "zs2_12_15",
            "min_capacity": 10,
            "max_capacity": 30,
            "target_group": "schools",
            "price": 80.0,
            "status": "concept",
            # New Figma fields
            "requires_approval": True,
            "is_published": False,
            "send_email_notification": True,
            # Schedule settings (Nastavení tab)
            "available_days": ["monday", "tuesday", "wednesday"],
            "time_blocks": ["09:00-10:30", "13:00-14:30"],
            "start_date": "2026-02-01",
            "end_date": "2026-06-30",
            # Booking parameters
            "min_days_before_booking": 14,
            "max_days_before_booking": 90,
            "preparation_time": 15,
            "cleanup_time": 30
        }
        response = requests.post(f"{BASE_URL}/api/programs", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Create program with Figma fields failed: {response.text}"
        data = response.json()
        
        # Verify all new fields
        assert data["status"] == "concept"
        assert data["requires_approval"] == True
        assert data["is_published"] == False
        assert data["send_email_notification"] == True
        assert data["min_days_before_booking"] == 14
        assert data["max_days_before_booking"] == 90
        assert data["preparation_time"] == 15
        assert data["cleanup_time"] == 30
        print(f"Program with Figma fields created: {data['id']}")
    
    def test_get_programs_list(self, auth_headers):
        """Test retrieving list of programs"""
        response = requests.get(f"{BASE_URL}/api/programs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Retrieved {len(data)} programs")
    
    def test_update_program_status(self, auth_headers):
        """Test updating program status (Aktivní, Koncept, Archivovat)"""
        # Create program first
        create_payload = {
            "name_cs": "Program ke změně statusu",
            "name_en": "Status change program",
            "description_cs": "Test",
            "description_en": "Test",
            "duration": 60,
            "age_group": "zs1_7_12",
            "min_capacity": 5,
            "max_capacity": 20,
            "target_group": "schools",
            "status": "active"
        }
        create_response = requests.post(f"{BASE_URL}/api/programs", json=create_payload, headers=auth_headers)
        program_id = create_response.json()["id"]
        
        # Update to concept status
        update_payload = {**create_payload, "status": "concept"}
        update_response = requests.put(f"{BASE_URL}/api/programs/{program_id}", json=update_payload, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "concept"
        
        # Update to archived status
        update_payload["status"] = "archived"
        update_response = requests.put(f"{BASE_URL}/api/programs/{program_id}", json=update_payload, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "archived"
        print(f"Program status updates working: active -> concept -> archived")
    
    def test_duplicate_program_flow(self, auth_headers):
        """Test the duplicate program flow (Duplikovat button)"""
        # Create original program
        original_payload = {
            "name_cs": "Originální program",
            "name_en": "Original program",
            "description_cs": "Originální popis",
            "description_en": "Original description",
            "duration": 90,
            "age_group": "ss_14_18",
            "min_capacity": 5,
            "max_capacity": 30,
            "target_group": "schools",
            "price": 100.0,
            "status": "active"
        }
        create_response = requests.post(f"{BASE_URL}/api/programs", json=original_payload, headers=auth_headers)
        original = create_response.json()
        
        # Create duplicate (simulating frontend Duplikovat button)
        duplicate_payload = {**original_payload}
        duplicate_payload["name_cs"] = f"{original_payload['name_cs']} (kopie)"
        duplicate_payload["name_en"] = f"{original_payload['name_en']} (copy)"
        
        duplicate_response = requests.post(f"{BASE_URL}/api/programs", json=duplicate_payload, headers=auth_headers)
        assert duplicate_response.status_code == 200
        duplicate = duplicate_response.json()
        
        assert duplicate["id"] != original["id"]
        assert "(kopie)" in duplicate["name_cs"]
        print(f"Program duplication successful")
    
    def test_delete_program(self, auth_headers):
        """Test deleting a program"""
        # Create program first
        create_payload = {
            "name_cs": "Program k smazání",
            "name_en": "Program to delete",
            "description_cs": "Test",
            "description_en": "Test",
            "duration": 60,
            "age_group": "zs1_7_12",
            "min_capacity": 5,
            "max_capacity": 20,
            "target_group": "schools"
        }
        create_response = requests.post(f"{BASE_URL}/api/programs", json=create_payload, headers=auth_headers)
        program_id = create_response.json()["id"]
        
        # Delete program
        delete_response = requests.delete(f"{BASE_URL}/api/programs/{program_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/programs/{program_id}", headers=auth_headers)
        assert get_response.status_code == 404
        print(f"Program deletion successful")


class TestPublicEndpoints:
    """Tests for public-facing endpoints (no auth required)"""
    
    def test_public_programs_demo(self):
        """Test public programs endpoint for demo institution"""
        response = requests.get(f"{BASE_URL}/api/programs/public/demo")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify demo programs have expected structure
        program = data[0]
        assert "name_cs" in program
        assert "description_cs" in program
        print(f"Public demo programs: {len(data)} programs found")
    
    def test_public_theme_demo(self):
        """Test public theme settings for demo institution"""
        response = requests.get(f"{BASE_URL}/api/settings/theme/public/demo")
        assert response.status_code == 200
        data = response.json()
        
        assert data["institution_id"] == "demo"
        assert "primary_color" in data
        assert "secondary_color" in data
        print(f"Public theme for demo: {data['primary_color']}")
    
    def test_program_availability(self):
        """Test program availability endpoint"""
        response = requests.get(f"{BASE_URL}/api/availability/demo/demo-1/2026-02-15")
        assert response.status_code == 200
        data = response.json()
        
        assert "date" in data
        assert "time_blocks" in data
        print(f"Availability check: {len(data['time_blocks'])} time blocks")
    
    def test_calendar_availability(self):
        """Test calendar month availability"""
        response = requests.get(f"{BASE_URL}/api/calendar/demo/2026/2")
        assert response.status_code == 200
        data = response.json()
        
        assert data["year"] == 2026
        assert data["month"] == 2
        assert "dates" in data
        print(f"Calendar availability: {len(data['dates'])} dates returned")


class TestDashboard:
    """Tests for dashboard statistics"""
    
    @pytest.fixture
    def auth_headers(self):
        """Create authenticated user for dashboard tests"""
        test_email = f"test_dashboard_{uuid.uuid4().hex[:8]}@test.cz"
        payload = {
            "institution_name": "Dashboard Test",
            "institution_type": "museum",
            "country": "Česká republika",
            "email": test_email,
            "password": "testPassword123",
            "gdpr_consent": True
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_stats(self, auth_headers):
        """Test dashboard statistics endpoint"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected stats fields
        assert "today_bookings" in data
        assert "upcoming_groups" in data
        assert "capacity_usage" in data
        assert "bookings_used" in data
        assert "bookings_limit" in data
        print(f"Dashboard stats: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
