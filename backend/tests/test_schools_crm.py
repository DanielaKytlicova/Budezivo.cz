"""
Test Schools CRM API - Multi-contact system, tags, and filtering
Tests for:
- Schools list with contacts array
- Filtering by source (import, organic, reservation)
- Filtering by tag
- Search by name, email, city
- Add/update/delete contacts
- Tags management
- Import template download
- IČO field NOT present in response
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSchoolsCRM:
    """Schools CRM API tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@budezivo.cz", "password": "Demo2026!"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ============ Schools List Tests ============
    
    def test_schools_list_returns_contacts_array(self):
        """Schools list should return schools with contacts array"""
        response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        schools = response.json()
        assert isinstance(schools, list), "Response should be a list"
        
        if len(schools) > 0:
            school = schools[0]
            # Verify contacts array exists
            assert "contacts" in school, "School should have 'contacts' field"
            assert isinstance(school["contacts"], list), "contacts should be a list"
            
            # Verify contact structure if contacts exist
            if len(school["contacts"]) > 0:
                contact = school["contacts"][0]
                assert "id" in contact or contact["id"] is None, "Contact should have 'id'"
                assert "email" in contact, "Contact should have 'email'"
                assert "status" in contact, "Contact should have 'status'"
                assert "is_primary" in contact, "Contact should have 'is_primary'"
        
        print(f"PASS: Schools list returns {len(schools)} schools with contacts array")
    
    def test_schools_list_no_ico_field(self):
        """IČO field should NOT be present in school response"""
        response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        assert response.status_code == 200
        
        schools = response.json()
        if len(schools) > 0:
            school = schools[0]
            # IČO should NOT be in response
            assert "ico" not in school, "IČO field should NOT be in response"
            assert "ičo" not in school, "IČO field should NOT be in response"
            assert "ic" not in school, "IC field should NOT be in response"
        
        print("PASS: IČO field is NOT present in school response")
    
    def test_schools_list_has_required_fields(self):
        """Schools should have all required fields"""
        response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        assert response.status_code == 200
        
        schools = response.json()
        if len(schools) > 0:
            school = schools[0]
            required_fields = ["id", "name", "tags", "source", "contacts", "booking_count"]
            for field in required_fields:
                assert field in school, f"School should have '{field}' field"
        
        print("PASS: Schools have all required fields")
    
    # ============ Filtering Tests ============
    
    def test_filter_by_source_import(self):
        """Filter schools by source=import"""
        response = requests.get(
            f"{BASE_URL}/api/schools?source=import", 
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        schools = response.json()
        for school in schools:
            assert school.get("source") == "import", f"School source should be 'import', got {school.get('source')}"
        
        print(f"PASS: Filter by source=import returns {len(schools)} schools")
    
    def test_filter_by_source_organic(self):
        """Filter schools by source=organic"""
        response = requests.get(
            f"{BASE_URL}/api/schools?source=organic", 
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        schools = response.json()
        for school in schools:
            assert school.get("source") == "organic", f"School source should be 'organic', got {school.get('source')}"
        
        print(f"PASS: Filter by source=organic returns {len(schools)} schools")
    
    def test_filter_by_source_reservation(self):
        """Filter schools by source=reservation"""
        response = requests.get(
            f"{BASE_URL}/api/schools?source=reservation", 
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        schools = response.json()
        for school in schools:
            assert school.get("source") == "reservation", f"School source should be 'reservation', got {school.get('source')}"
        
        print(f"PASS: Filter by source=reservation returns {len(schools)} schools")
    
    def test_filter_by_source_all(self):
        """Filter by source=all should return all schools"""
        response_all = requests.get(
            f"{BASE_URL}/api/schools?source=all", 
            headers=self.headers
        )
        response_none = requests.get(
            f"{BASE_URL}/api/schools", 
            headers=self.headers
        )
        
        assert response_all.status_code == 200
        assert response_none.status_code == 200
        
        # source=all should return same as no filter
        assert len(response_all.json()) == len(response_none.json())
        
        print("PASS: Filter by source=all returns all schools")
    
    # ============ Tags Tests ============
    
    def test_get_all_tags(self):
        """Get all unique tags endpoint"""
        response = requests.get(f"{BASE_URL}/api/schools/tags", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "tags" in data, "Response should have 'tags' field"
        assert isinstance(data["tags"], list), "tags should be a list"
        
        print(f"PASS: Get all tags returns {len(data['tags'])} tags")
    
    def test_update_school_tags(self):
        """Update tags for a school"""
        # First get a school
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        assert schools_response.status_code == 200
        schools = schools_response.json()
        
        if len(schools) == 0:
            pytest.skip("No schools to test tags update")
        
        school_id = schools[0]["id"]
        new_tags = ["ZŠ", "Gymnázium"]
        
        # Update tags
        response = requests.put(
            f"{BASE_URL}/api/schools/{school_id}/tags",
            json=new_tags,
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify tags were updated
        verify_response = requests.get(f"{BASE_URL}/api/schools/{school_id}", headers=self.headers)
        assert verify_response.status_code == 200
        updated_school = verify_response.json()
        assert set(updated_school["tags"]) == set(new_tags), f"Tags not updated correctly"
        
        print(f"PASS: Updated tags for school {school_id}")
    
    def test_filter_by_tag(self):
        """Filter schools by tag"""
        # First set a tag on a school
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        schools = schools_response.json()
        
        if len(schools) == 0:
            pytest.skip("No schools to test tag filter")
        
        school_id = schools[0]["id"]
        test_tag = "MŠ"
        
        # Set tag
        requests.put(
            f"{BASE_URL}/api/schools/{school_id}/tags",
            json=[test_tag],
            headers=self.headers
        )
        
        # Filter by tag
        response = requests.get(
            f"{BASE_URL}/api/schools?tag={test_tag}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        filtered_schools = response.json()
        for school in filtered_schools:
            assert test_tag in school.get("tags", []), f"School should have tag '{test_tag}'"
        
        print(f"PASS: Filter by tag={test_tag} returns {len(filtered_schools)} schools")
    
    # ============ Contacts API Tests ============
    
    def test_add_contact_to_school(self):
        """Add a new contact to a school"""
        # Get a school
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        schools = schools_response.json()
        
        if len(schools) == 0:
            pytest.skip("No schools to test contact add")
        
        school_id = schools[0]["id"]
        
        # Add contact
        contact_data = {
            "email": f"test_contact_{school_id[:8]}@example.com",
            "name": "Test Contact",
            "phone": "+420123456789",
            "is_primary": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/schools/{school_id}/contacts",
            json=contact_data,
            headers=self.headers
        )
        
        # May fail if email already exists
        if response.status_code == 400 and "již existuje" in response.text:
            print("PASS: Add contact correctly rejects duplicate email")
            return
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data, "Response should have contact id"
        
        print(f"PASS: Added contact to school {school_id}")
    
    def test_update_contact_status_invalid(self):
        """Update contact status to invalid"""
        # Get a school with contacts
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        schools = schools_response.json()
        
        school_with_contact = None
        contact_id = None
        
        for school in schools:
            if school.get("contacts") and len(school["contacts"]) > 0:
                for contact in school["contacts"]:
                    if contact.get("id"):
                        school_with_contact = school
                        contact_id = contact["id"]
                        break
            if contact_id:
                break
        
        if not contact_id:
            pytest.skip("No contacts with ID to test status update")
        
        # Update status to invalid
        response = requests.put(
            f"{BASE_URL}/api/schools/{school_with_contact['id']}/contacts/{contact_id}",
            json={"status": "invalid"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Verify status was updated
        verify_response = requests.get(
            f"{BASE_URL}/api/schools/{school_with_contact['id']}",
            headers=self.headers
        )
        updated_school = verify_response.json()
        updated_contact = next((c for c in updated_school["contacts"] if c["id"] == contact_id), None)
        assert updated_contact is not None
        assert updated_contact["status"] == "invalid"
        
        # Restore to active
        requests.put(
            f"{BASE_URL}/api/schools/{school_with_contact['id']}/contacts/{contact_id}",
            json={"status": "active"},
            headers=self.headers
        )
        
        print(f"PASS: Updated contact status to invalid and back to active")
    
    def test_update_contact_status_active(self):
        """Update contact status to active"""
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        schools = schools_response.json()
        
        school_with_contact = None
        contact_id = None
        
        for school in schools:
            if school.get("contacts") and len(school["contacts"]) > 0:
                for contact in school["contacts"]:
                    if contact.get("id"):
                        school_with_contact = school
                        contact_id = contact["id"]
                        break
            if contact_id:
                break
        
        if not contact_id:
            pytest.skip("No contacts with ID to test status update")
        
        response = requests.put(
            f"{BASE_URL}/api/schools/{school_with_contact['id']}/contacts/{contact_id}",
            json={"status": "active"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        print("PASS: Updated contact status to active")
    
    # ============ Import Template Test ============
    
    def test_import_template_download(self):
        """Download import template"""
        response = requests.get(
            f"{BASE_URL}/api/schools/import-template",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "excel" in content_type or "octet-stream" in content_type, \
            f"Expected Excel content type, got {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, "Should be attachment download"
        assert ".xlsx" in content_disp, "Should be .xlsx file"
        
        # Check file size (should be > 0)
        assert len(response.content) > 0, "Template file should not be empty"
        
        print(f"PASS: Import template download works ({len(response.content)} bytes)")
    
    # ============ Single School Tests ============
    
    def test_get_single_school(self):
        """Get single school with all contacts"""
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        schools = schools_response.json()
        
        if len(schools) == 0:
            pytest.skip("No schools to test single school get")
        
        school_id = schools[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/schools/{school_id}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        school = response.json()
        assert school["id"] == school_id
        assert "contacts" in school
        assert "tags" in school
        assert "source" in school
        
        # IČO should NOT be present
        assert "ico" not in school
        assert "ičo" not in school
        
        print(f"PASS: Get single school {school_id}")
    
    def test_get_nonexistent_school(self):
        """Get nonexistent school returns 404"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{BASE_URL}/api/schools/{fake_id}",
            headers=self.headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print("PASS: Nonexistent school returns 404")
    
    # ============ Invalid Contacts Filter Test ============
    
    def test_filter_has_invalid_contacts(self):
        """Filter schools with invalid contacts"""
        response = requests.get(
            f"{BASE_URL}/api/schools?has_invalid=true",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        schools = response.json()
        for school in schools:
            assert school.get("invalid_contacts_count", 0) > 0, \
                "Schools with has_invalid=true should have invalid contacts"
        
        print(f"PASS: Filter has_invalid=true returns {len(schools)} schools")


class TestContactsValidation:
    """Contact validation tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@budezivo.cz", "password": "Demo2026!"}
        )
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_add_contact_invalid_email(self):
        """Adding contact with invalid email should fail"""
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        schools = schools_response.json()
        
        if len(schools) == 0:
            pytest.skip("No schools to test")
        
        school_id = schools[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/schools/{school_id}/contacts",
            json={"email": "invalid-email", "name": "Test"},
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400 for invalid email, got {response.status_code}"
        
        print("PASS: Invalid email rejected")
    
    def test_add_contact_duplicate_email(self):
        """Adding contact with duplicate email should fail"""
        schools_response = requests.get(f"{BASE_URL}/api/schools", headers=self.headers)
        schools = schools_response.json()
        
        # Find a school with existing contact
        existing_email = None
        school_id = None
        
        for school in schools:
            if school.get("contacts") and len(school["contacts"]) > 0:
                existing_email = school["contacts"][0]["email"]
                school_id = school["id"]
                break
        
        if not existing_email:
            pytest.skip("No existing contacts to test duplicate")
        
        response = requests.post(
            f"{BASE_URL}/api/schools/{school_id}/contacts",
            json={"email": existing_email, "name": "Duplicate Test"},
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400 for duplicate email, got {response.status_code}"
        
        print("PASS: Duplicate email rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
