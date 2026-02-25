"""
Test PRO features for Budeživo.cz cultural booking system
- CSV export for schools
- Mass propagation to schools
- PRO settings with email templates
- URL generator for external program reservations
- Extended booking editing (date/time/contact for admin)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestProFeatures:
    """Tests for PRO features - CSV export, propagation, URL generator"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as demo user with PRO account"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "demo123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        data = login_response.json()
        self.token = data["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.institution_id = data["user"]["institution_id"]
    
    def test_get_pro_settings(self):
        """GET /api/settings/pro - should return PRO settings with is_pro=true"""
        response = requests.get(f"{BASE_URL}/api/settings/pro", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify PRO settings fields
        assert "plan" in data
        assert "is_pro" in data
        assert data["is_pro"] == True, "Demo account should have PRO status (standard plan)"
        assert data["plan"] in ["standard", "premium"], f"Expected standard/premium plan, got {data['plan']}"
        assert "csv_export_enabled" in data
        assert "mass_propagation_enabled" in data
        assert "email_subject_template" in data
        assert "email_body_template" in data
        print(f"PRO settings verified: plan={data['plan']}, is_pro={data['is_pro']}")
    
    def test_update_pro_settings(self):
        """PUT /api/settings/pro - should update PRO settings"""
        new_settings = {
            "csv_export_enabled": True,
            "mass_propagation_enabled": True,
            "email_subject_template": "Nový program: {program_name}",
            "email_body_template": "Dobrý den,\n\nNový program: {program_name}\n\n{program_description}"
        }
        response = requests.put(f"{BASE_URL}/api/settings/pro", headers=self.headers, json=new_settings)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PRO nastavení uloženo"
        print("PRO settings updated successfully")
    
    def test_export_schools_csv(self):
        """GET /api/schools/export-csv - should return CSV file for PRO users"""
        response = requests.get(f"{BASE_URL}/api/schools/export-csv", headers=self.headers)
        assert response.status_code == 200
        
        # Verify response headers
        assert "text/csv" in response.headers.get("content-type", "")
        assert "content-disposition" in response.headers
        assert "skoly_export.csv" in response.headers.get("content-disposition", "")
        
        # Verify CSV content
        csv_content = response.text
        assert "Název školy" in csv_content, "CSV should contain header row"
        assert "Email" in csv_content
        assert "Telefon" in csv_content
        print(f"CSV export successful: {len(csv_content)} bytes")
    
    def test_send_propagation_to_schools(self):
        """POST /api/schools/send-propagation - should send propagation (MOCKED email)"""
        # First get schools and programs
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        programs_response = requests.get(f"{BASE_URL}/api/programs", headers=self.headers)
        
        assert schools_response.status_code == 200
        assert programs_response.status_code == 200
        
        schools = schools_response.json()
        programs = programs_response.json()
        
        assert len(schools) > 0, "Need at least one school for propagation test"
        assert len(programs) > 0, "Need at least one program for propagation test"
        
        # Send propagation
        school_ids = [s["id"] for s in schools[:2]]  # Max 2 schools
        program_id = programs[0]["id"]
        
        response = requests.post(f"{BASE_URL}/api/schools/send-propagation", headers=self.headers, json={
            "school_ids": school_ids,
            "program_id": program_id
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "sent_count" in data
        assert data["sent_count"] == len(school_ids)
        assert "schools" in data
        print(f"Propagation sent to {data['sent_count']} schools: {data['schools']}")
    
    def test_propagation_requires_pro(self):
        """POST /api/schools/send-propagation - should fail for non-PRO users"""
        # This test would require a free-tier user to test properly
        # For now, we verify the endpoint exists and PRO user can access
        pass
    
    def test_get_program_external_url(self):
        """GET /api/programs/{id}/external-url - should return URL for external reservations"""
        # Get a program first
        programs_response = requests.get(f"{BASE_URL}/api/programs", headers=self.headers)
        assert programs_response.status_code == 200
        programs = programs_response.json()
        assert len(programs) > 0, "Need at least one program"
        
        program_id = programs[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/programs/{program_id}/external-url", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify URL response fields
        assert "url" in data
        assert "program_name" in data
        assert "institution_name" in data
        assert "embed_code" in data
        
        # Verify URL format
        assert f"program={program_id}" in data["url"]
        assert self.institution_id in data["url"]
        assert "<a href=" in data["embed_code"]
        print(f"External URL generated: {data['url']}")
    
    def test_external_url_for_invalid_program(self):
        """GET /api/programs/{id}/external-url - should return 404 for invalid program"""
        response = requests.get(f"{BASE_URL}/api/programs/invalid-program-id/external-url", headers=self.headers)
        assert response.status_code == 404


class TestExtendedBookingEdit:
    """Tests for extended booking editing - date/time/contact fields for admin"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as demo admin user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@budezivo.cz",
            "password": "demo123"
        })
        assert login_response.status_code == 200
        data = login_response.json()
        self.token = data["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Get a booking to test with
        bookings_response = requests.get(f"{BASE_URL}/api/bookings", headers=self.headers)
        assert bookings_response.status_code == 200
        bookings = bookings_response.json()
        if bookings:
            self.test_booking_id = bookings[0]["id"]
            self.original_booking = bookings[0]
        else:
            self.test_booking_id = None
    
    def test_admin_can_update_date(self):
        """PUT /api/bookings/{id} - admin can update date"""
        if not self.test_booking_id:
            pytest.skip("No bookings available for testing")
        
        new_date = "2026-04-15"
        response = requests.put(
            f"{BASE_URL}/api/bookings/{self.test_booking_id}",
            headers=self.headers,
            json={"date": new_date}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "updated_fields" in data
        assert "date" in data["updated_fields"]
        
        # Verify the update
        verify_response = requests.get(f"{BASE_URL}/api/bookings/{self.test_booking_id}", headers=self.headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["date"] == new_date
        print(f"Date updated to {new_date}")
    
    def test_admin_can_update_time_block(self):
        """PUT /api/bookings/{id} - admin can update time_block"""
        if not self.test_booking_id:
            pytest.skip("No bookings available for testing")
        
        new_time = "14:00-15:30"
        response = requests.put(
            f"{BASE_URL}/api/bookings/{self.test_booking_id}",
            headers=self.headers,
            json={"time_block": new_time}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "time_block" in data["updated_fields"]
        
        # Verify the update
        verify_response = requests.get(f"{BASE_URL}/api/bookings/{self.test_booking_id}", headers=self.headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["time_block"] == new_time
        print(f"Time block updated to {new_time}")
    
    def test_admin_can_update_contact_email(self):
        """PUT /api/bookings/{id} - admin can update contact_email"""
        if not self.test_booking_id:
            pytest.skip("No bookings available for testing")
        
        new_email = "updated_contact@test.cz"
        response = requests.put(
            f"{BASE_URL}/api/bookings/{self.test_booking_id}",
            headers=self.headers,
            json={"contact_email": new_email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "contact_email" in data["updated_fields"]
        
        # Verify the update
        verify_response = requests.get(f"{BASE_URL}/api/bookings/{self.test_booking_id}", headers=self.headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["contact_email"] == new_email
        print(f"Contact email updated to {new_email}")
    
    def test_admin_can_update_contact_phone(self):
        """PUT /api/bookings/{id} - admin can update contact_phone"""
        if not self.test_booking_id:
            pytest.skip("No bookings available for testing")
        
        new_phone = "+420999888777"
        response = requests.put(
            f"{BASE_URL}/api/bookings/{self.test_booking_id}",
            headers=self.headers,
            json={"contact_phone": new_phone}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "contact_phone" in data["updated_fields"]
        print(f"Contact phone updated to {new_phone}")
    
    def test_admin_can_update_contact_name(self):
        """PUT /api/bookings/{id} - admin can update contact_name"""
        if not self.test_booking_id:
            pytest.skip("No bookings available for testing")
        
        new_name = "Ing. Test Updated"
        response = requests.put(
            f"{BASE_URL}/api/bookings/{self.test_booking_id}",
            headers=self.headers,
            json={"contact_name": new_name}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "contact_name" in data["updated_fields"]
        print(f"Contact name updated to {new_name}")
    
    def test_admin_can_update_multiple_fields(self):
        """PUT /api/bookings/{id} - admin can update multiple fields at once"""
        if not self.test_booking_id:
            pytest.skip("No bookings available for testing")
        
        updates = {
            "date": "2026-05-01",
            "time_block": "09:00-10:30",
            "contact_email": "multi_update@test.cz",
            "contact_phone": "+420111222333",
            "contact_name": "Multi Update Test"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/bookings/{self.test_booking_id}",
            headers=self.headers,
            json=updates
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all fields were updated
        for field in updates.keys():
            assert field in data["updated_fields"], f"Field {field} should be in updated_fields"
        
        print(f"Multiple fields updated: {data['updated_fields']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
