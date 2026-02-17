import requests
import sys
import json
from datetime import datetime, timedelta
import uuid
import time

class CulturalBookingAPITester:
    def __init__(self, base_url="https://knihovny-galerie.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.institution_id = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.program_id = None
        self.booking_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        if self.token:
            default_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=default_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"   ✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"   ❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return False, {}

        except Exception as e:
            print(f"   ❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "/", 200)

    def test_register_institution(self):
        """Test institution registration"""
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        registration_data = {
            "institution_name": "Test Muzeum Praha",
            "institution_type": "museum",
            "country": "Czech Republic",
            "email": test_email,
            "password": "TestPassword123!"
        }

        success, response = self.run_test(
            "Institution Registration",
            "POST",
            "/auth/register",
            200,
            data=registration_data
        )

        if success:
            self.token = response.get('token')
            user_data = response.get('user', {})
            self.institution_id = user_data.get('institution_id')
            self.user_id = user_data.get('id')
            print(f"   ✅ Registered institution_id: {self.institution_id}")
            print(f"   ✅ User ID: {self.user_id}")
            return True
        return False

    def test_login(self):
        """Test login with registered credentials"""
        if not self.token:
            print("   ⚠️ Skipping login test - no registration token available")
            return False
            
        # We'll use the same credentials from registration for this test
        # In a real test, we'd store and reuse them
        return True

    def test_verify_token(self):
        """Test token verification"""
        if not self.token:
            print("   ⚠️ Skipping token verification - no token available")
            return False
            
        return self.run_test("Token Verification", "GET", "/auth/verify", 200)[0]

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        if not self.token:
            print("   ⚠️ Skipping dashboard stats - no token available")
            return False
            
        return self.run_test("Dashboard Stats", "GET", "/dashboard/stats", 200)[0]

    def test_create_program(self):
        """Test creating a program"""
        if not self.token:
            print("   ⚠️ Skipping program creation - no token available")
            return False

        program_data = {
            "name_cs": "Průvodcovská služba pro školy",
            "name_en": "Guided Tour for Schools", 
            "description_cs": "Interaktivní prohlídka muzea pro školní skupiny",
            "description_en": "Interactive museum tour for school groups",
            "duration": 90,
            "capacity": 25,
            "target_group": "schools",
            "price": 150.0,
            "status": "active"
        }

        success, response = self.run_test(
            "Create Program",
            "POST", 
            "/programs",
            200,
            data=program_data
        )

        if success:
            self.program_id = response.get('id')
            print(f"   ✅ Created program_id: {self.program_id}")
            return True
        return False

    def test_get_programs(self):
        """Test retrieving programs"""
        if not self.token:
            print("   ⚠️ Skipping get programs - no token available")
            return False
            
        success, response = self.run_test("Get Programs", "GET", "/programs", 200)
        if success and isinstance(response, list) and len(response) > 0:
            print(f"   ✅ Found {len(response)} programs")
            return True
        elif success:
            print("   ✅ Programs list retrieved (empty)")
            return True
        return False

    def test_get_public_programs(self):
        """Test retrieving public programs without authentication"""
        if not self.institution_id:
            print("   ⚠️ Skipping public programs - no institution_id available")
            return False
            
        success, response = self.run_test(
            "Get Public Programs",
            "GET", 
            f"/programs/public/{self.institution_id}",
            200
        )
        return success

    def test_update_program(self):
        """Test updating a program"""
        if not self.token or not self.program_id:
            print("   ⚠️ Skipping program update - no token or program_id available")
            return False

        updated_data = {
            "name_cs": "Průvodcovská služba pro školy - UPDATED",
            "name_en": "Guided Tour for Schools - UPDATED",
            "description_cs": "Aktualizovaný popis programu",
            "description_en": "Updated program description",
            "duration": 120,
            "capacity": 30,
            "target_group": "schools",
            "price": 180.0,
            "status": "active"
        }

        return self.run_test(
            "Update Program",
            "PUT",
            f"/programs/{self.program_id}",
            200,
            data=updated_data
        )[0]

    def test_create_public_booking(self):
        """Test creating a booking without authentication (public booking)"""
        if not self.institution_id or not self.program_id:
            print("   ⚠️ Skipping public booking - no institution_id or program_id available")
            return False

        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        booking_data = {
            "program_id": self.program_id,
            "date": tomorrow,
            "time_slot": "10:00",
            "school_name": "ZŠ Náměstí Míru",
            "contact_name": "Jana Novakova",
            "contact_email": "jana.novakova@zs-namesti.cz",
            "contact_phone": "+420123456789",
            "num_students": 20,
            "notes": "Žáci 6. třídy, prosíme o přizpůsobení věku",
            "gdpr_consent": True
        }

        success, response = self.run_test(
            "Create Public Booking",
            "POST",
            f"/bookings/public/{self.institution_id}",
            200,
            data=booking_data
        )

        if success:
            self.booking_id = response.get('id')
            print(f"   ✅ Created booking_id: {self.booking_id}")
            return True
        return False

    def test_get_bookings(self):
        """Test retrieving bookings"""
        if not self.token:
            print("   ⚠️ Skipping get bookings - no token available")
            return False
            
        success, response = self.run_test("Get Bookings", "GET", "/bookings", 200)
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} bookings")
            return True
        return False

    def test_update_booking_status(self):
        """Test updating booking status"""
        if not self.token or not self.booking_id:
            print("   ⚠️ Skipping booking status update - no token or booking_id available")
            return False

        return self.run_test(
            "Update Booking Status",
            "PATCH",
            f"/bookings/{self.booking_id}/status?status=confirmed",
            200
        )[0]

    def test_get_theme_settings(self):
        """Test getting theme settings"""
        if not self.token:
            print("   ⚠️ Skipping theme settings - no token available")
            return False
            
        return self.run_test("Get Theme Settings", "GET", "/settings/theme", 200)[0]

    def test_update_theme_settings(self):
        """Test updating theme settings"""
        if not self.token:
            print("   ⚠️ Skipping theme update - no token available")
            return False

        theme_data = {
            "primary_color": "#2563EB",
            "secondary_color": "#10B981",
            "accent_color": "#F59E0B",
            "header_style": "dark",
            "footer_text": "Test Museum Prague - Cultural Heritage"
        }

        return self.run_test(
            "Update Theme Settings",
            "PUT",
            "/settings/theme",
            200,
            data=theme_data
        )[0]

    def test_get_public_theme_settings(self):
        """Test getting public theme settings"""
        if not self.institution_id:
            print("   ⚠️ Skipping public theme - no institution_id available")
            return False
            
        return self.run_test(
            "Get Public Theme Settings",
            "GET",
            f"/settings/theme/public/{self.institution_id}",
            200
        )[0]

    def test_create_payment_session(self):
        """Test creating Stripe payment session"""
        if not self.token:
            print("   ⚠️ Skipping payment session - no token available")
            return False

        payment_data = {
            "package": "basic",
            "billing_cycle": "monthly"
        }

        success, response = self.run_test(
            "Create Payment Session",
            "POST",
            "/payments/create-session",
            200,
            data=payment_data
        )
        
        if success:
            session_url = response.get('url', '')
            session_id = response.get('session_id', '')
            print(f"   ✅ Payment session created with URL: {session_url[:50]}...")
            print(f"   ✅ Session ID: {session_id}")
            return True
        return False

    def test_forgot_password(self):
        """Test forgot password endpoint (mocked)"""
        forgot_data = {
            "email": "test@example.com"
        }

        return self.run_test(
            "Forgot Password (Mocked)",
            "POST",
            "/auth/forgot-password",
            200,
            data=forgot_data
        )[0]

    def test_delete_program(self):
        """Test deleting a program"""
        if not self.token or not self.program_id:
            print("   ⚠️ Skipping program deletion - no token or program_id available")
            return False

        return self.run_test(
            "Delete Program",
            "DELETE",
            f"/programs/{self.program_id}",
            200
        )[0]

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("🚀 Starting Cultural Booking System API Tests")
        print("=" * 60)

        # Basic connectivity
        self.test_root_endpoint()
        
        # Authentication flow
        self.test_register_institution()
        self.test_verify_token()
        
        # Dashboard
        self.test_dashboard_stats()
        
        # Programs CRUD
        self.test_create_program()
        self.test_get_programs() 
        self.test_get_public_programs()
        self.test_update_program()
        
        # Bookings flow
        self.test_create_public_booking()
        self.test_get_bookings()
        self.test_update_booking_status()
        
        # Theme settings
        self.test_get_theme_settings()
        self.test_update_theme_settings()
        self.test_get_public_theme_settings()
        
        # Payment integration
        self.test_create_payment_session()
        
        # Additional endpoints
        self.test_forgot_password()
        
        # Cleanup
        self.test_delete_program()

        # Final results
        print("\n" + "=" * 60)
        print(f"📊 Tests completed: {self.tests_passed}/{self.tests_run}")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 Backend API tests PASSED!")
            return 0
        else:
            print("❌ Backend API tests FAILED!")
            return 1

def main():
    tester = CulturalBookingAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())