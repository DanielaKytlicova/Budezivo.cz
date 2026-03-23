"""
Test School Import Functionality
- GET /api/schools/import-template - downloads Excel template
- POST /api/schools/import - imports schools from Excel/CSV
- Validates required columns (Název školy, Email)
- Validates email format
- Detects duplicates by email
- update_existing=true updates existing records
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


class TestSchoolImport:
    """School import endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
            self.authenticated = True
        else:
            self.authenticated = False
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_download_import_template(self):
        """Test GET /api/schools/import-template - downloads Excel template"""
        response = self.session.get(f"{BASE_URL}/api/schools/import-template")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check content type is Excel
        content_type = response.headers.get('Content-Type', '')
        assert 'spreadsheet' in content_type or 'excel' in content_type or 'octet-stream' in content_type, \
            f"Expected Excel content type, got {content_type}"
        
        # Check content disposition header
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disposition, "Expected attachment disposition"
        assert 'vzorovy_import_skol.xlsx' in content_disposition, "Expected correct filename"
        
        # Check file has content
        assert len(response.content) > 0, "Template file should not be empty"
        print(f"Template downloaded successfully: {len(response.content)} bytes")
    
    def test_import_valid_excel_file(self):
        """Test POST /api/schools/import with valid Excel file"""
        # Use the test file created by main agent
        test_file_path = "/tmp/test_import.xlsx"
        
        if not os.path.exists(test_file_path):
            pytest.skip("Test file not found at /tmp/test_import.xlsx")
        
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test_import.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            # Remove Content-Type header for multipart
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/schools/import",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'total_rows' in data, "Response should contain total_rows"
        assert 'imported' in data, "Response should contain imported count"
        assert 'duplicates' in data, "Response should contain duplicates count"
        assert 'errors' in data, "Response should contain errors count"
        assert 'error_details' in data, "Response should contain error_details"
        
        print(f"Import result: imported={data['imported']}, duplicates={data['duplicates']}, errors={data['errors']}")
    
    def test_import_with_update_existing(self):
        """Test POST /api/schools/import?update_existing=true"""
        test_file_path = "/tmp/test_import.xlsx"
        
        if not os.path.exists(test_file_path):
            pytest.skip("Test file not found at /tmp/test_import.xlsx")
        
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test_import.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(
                f"{BASE_URL}/api/schools/import?update_existing=true",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # With update_existing=true, duplicates should be updated (counted as imported)
        assert 'imported' in data, "Response should contain imported count"
        print(f"Import with update: imported={data['imported']}, duplicates={data['duplicates']}")
    
    def test_import_invalid_file_type(self):
        """Test POST /api/schools/import with invalid file type"""
        # Create a fake text file
        fake_file = io.BytesIO(b"This is not an Excel file")
        
        files = {'file': ('test.txt', fake_file, 'text/plain')}
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{BASE_URL}/api/schools/import",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid file type, got {response.status_code}"
        print(f"Invalid file type correctly rejected: {response.json()}")
    
    def test_import_csv_file(self):
        """Test POST /api/schools/import with CSV file"""
        # Create a valid CSV file
        csv_content = "Název školy;Email;Telefon;Město\nTEST_CSV_Škola;test_csv@example.com;123456789;Praha\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {'file': ('test.csv', csv_file, 'text/csv')}
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{BASE_URL}/api/schools/import",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'imported' in data, "Response should contain imported count"
        print(f"CSV import result: imported={data['imported']}, duplicates={data['duplicates']}, errors={data['errors']}")
    
    def test_import_missing_required_columns(self):
        """Test import with missing required columns (Název školy, Email)"""
        # CSV without Email column
        csv_content = "Název školy;Telefon\nTest Škola;123456789\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {'file': ('test.csv', csv_file, 'text/csv')}
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{BASE_URL}/api/schools/import",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Should have errors about missing column
        assert data['errors'] > 0 or data['success'] == False, "Should report error for missing Email column"
        print(f"Missing column error: {data.get('error_details', [])}")
    
    def test_import_invalid_email_format(self):
        """Test import with invalid email format"""
        csv_content = "Název školy;Email\nTest Škola;invalid-email\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {'file': ('test.csv', csv_file, 'text/csv')}
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{BASE_URL}/api/schools/import",
            files=files,
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Should have errors about invalid email
        assert data['errors'] > 0, "Should report error for invalid email format"
        
        # Check error details mention email
        error_messages = [e.get('error', '') for e in data.get('error_details', [])]
        has_email_error = any('email' in msg.lower() for msg in error_messages)
        assert has_email_error, f"Should have email validation error, got: {error_messages}"
        print(f"Invalid email error: {data.get('error_details', [])}")
    
    def test_import_duplicate_detection(self):
        """Test that import detects duplicates by email"""
        # First import a school
        csv_content = "Název školy;Email\nTEST_Duplicate_Škola;test_duplicate@example.com\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {'file': ('test.csv', csv_file, 'text/csv')}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # First import
        response1 = requests.post(
            f"{BASE_URL}/api/schools/import",
            files=files,
            headers=headers
        )
        assert response1.status_code == 200
        
        # Second import with same email
        csv_file2 = io.BytesIO(csv_content.encode('utf-8'))
        files2 = {'file': ('test.csv', csv_file2, 'text/csv')}
        
        response2 = requests.post(
            f"{BASE_URL}/api/schools/import",
            files=files2,
            headers=headers
        )
        
        assert response2.status_code == 200
        data = response2.json()
        
        # Should detect as duplicate
        assert data['duplicates'] > 0 or data['imported'] == 0, \
            f"Should detect duplicate, got: imported={data['imported']}, duplicates={data['duplicates']}"
        print(f"Duplicate detection: imported={data['imported']}, duplicates={data['duplicates']}")
    
    def test_get_schools_list(self):
        """Test GET /api/schools returns imported schools"""
        response = self.session.get(f"{BASE_URL}/api/schools")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Schools list: {len(data)} schools found")
        
        # Check if any TEST_ prefixed schools exist (from our tests)
        test_schools = [s for s in data if s.get('name', '').startswith('TEST_')]
        print(f"Test schools found: {len(test_schools)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
