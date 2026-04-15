"""
Export System Tests for Event Applications
Tests: XLSX export, CSV export, PDF confirmation, Public PDF endpoint
Features: Styled XLSX, UTF-8 BOM CSV with semicolons, PDF with QR payment
"""
import pytest
import requests
import os
import io
import zipfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"

# Known event with applications: "Za uměním do Lázní"
TEST_EVENT_ID = "e7ed3b6d-6d9f-4d73-aae1-e818a153e291"
TEST_APPLICATION_ID = "eb8a6d8e-9ab8-480b-9192-843c1336b5fe"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_session(api_client):
    """Authenticated session for admin user."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return api_client


class TestXLSXExport:
    """XLSX export endpoint tests."""
    
    def test_xlsx_export_returns_200(self, auth_session):
        """GET /api/events/{event_id}/export/xlsx returns 200."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/xlsx")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: XLSX export returns 200")
    
    def test_xlsx_export_content_type(self, auth_session):
        """XLSX export has correct content type."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/xlsx")
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'spreadsheetml' in content_type or 'application/vnd.openxmlformats' in content_type, \
            f"Expected XLSX content type, got: {content_type}"
        print(f"PASS: XLSX content type: {content_type}")
    
    def test_xlsx_export_content_disposition(self, auth_session):
        """XLSX export has Content-Disposition header with filename."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/xlsx")
        assert response.status_code == 200
        disposition = response.headers.get('Content-Disposition', '')
        assert 'attachment' in disposition, f"Expected attachment disposition, got: {disposition}"
        assert 'filename' in disposition, f"Expected filename in disposition, got: {disposition}"
        assert '.xlsx' in disposition, f"Expected .xlsx extension in filename, got: {disposition}"
        print(f"PASS: XLSX Content-Disposition: {disposition[:80]}...")
    
    def test_xlsx_is_valid_zip_format(self, auth_session):
        """XLSX file is valid ZIP format (XLSX is ZIP-based)."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/xlsx")
        assert response.status_code == 200
        
        # XLSX files are ZIP archives
        buffer = io.BytesIO(response.content)
        assert zipfile.is_zipfile(buffer), "XLSX should be a valid ZIP file"
        
        # Check for required XLSX components
        with zipfile.ZipFile(buffer, 'r') as zf:
            names = zf.namelist()
            assert 'xl/worksheets/sheet1.xml' in names, "XLSX should contain sheet1.xml"
            assert 'xl/styles.xml' in names, "XLSX should contain styles.xml (for formatting)"
            assert 'xl/workbook.xml' in names, "XLSX should contain workbook.xml"
        print("PASS: XLSX is valid ZIP with required components")
    
    def test_xlsx_contains_styled_content(self, auth_session):
        """XLSX contains styled content (styles.xml has formatting)."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/xlsx")
        assert response.status_code == 200
        
        buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(buffer, 'r') as zf:
            styles_content = zf.read('xl/styles.xml').decode('utf-8')
            # Check for fill colors (conditional formatting)
            assert 'fill' in styles_content.lower(), "Styles should contain fill definitions"
            # Check for fonts
            assert 'font' in styles_content.lower(), "Styles should contain font definitions"
        print("PASS: XLSX contains styled content")
    
    def test_xlsx_export_requires_auth(self):
        """XLSX export requires authentication."""
        response = requests.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/xlsx")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: XLSX export requires authentication")


class TestCSVExport:
    """CSV export endpoint tests."""
    
    def test_csv_export_returns_200(self, auth_session):
        """GET /api/events/{event_id}/export/csv returns 200."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/csv")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: CSV export returns 200")
    
    def test_csv_export_content_type(self, auth_session):
        """CSV export has correct content type."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/csv")
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, f"Expected text/csv, got: {content_type}"
        print(f"PASS: CSV content type: {content_type}")
    
    def test_csv_has_utf8_bom(self, auth_session):
        """CSV file starts with UTF-8 BOM for Excel compatibility."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/csv")
        assert response.status_code == 200
        
        content = response.content
        # UTF-8 BOM is EF BB BF
        assert content[:3] == b'\xef\xbb\xbf', \
            f"CSV should start with UTF-8 BOM (EF BB BF), got: {content[:3].hex()}"
        print("PASS: CSV has UTF-8 BOM")
    
    def test_csv_uses_semicolon_separator(self, auth_session):
        """CSV uses semicolon as separator (European Excel standard)."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/csv")
        assert response.status_code == 200
        
        content = response.content.decode('utf-8-sig')  # Decode with BOM handling
        lines = content.strip().split('\n')
        assert len(lines) >= 1, "CSV should have at least header row"
        
        header = lines[0]
        assert ';' in header, f"CSV should use semicolon separator, header: {header[:100]}"
        # Should not use comma as primary separator
        semicolon_count = header.count(';')
        comma_count = header.count(',')
        assert semicolon_count > comma_count, \
            f"Semicolons ({semicolon_count}) should be more than commas ({comma_count})"
        print(f"PASS: CSV uses semicolon separator ({semicolon_count} semicolons in header)")
    
    def test_csv_contains_czech_column_names(self, auth_session):
        """CSV contains Czech column names (labels, not field IDs)."""
        response = auth_session.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/csv")
        assert response.status_code == 200
        
        content = response.content.decode('utf-8-sig')
        header = content.split('\n')[0]
        
        # Check for Czech column names
        czech_columns = ['Jméno', 'Email', 'Status', 'Platba', 'Částka', 'VS', 'Datum']
        found_czech = sum(1 for col in czech_columns if col in header)
        assert found_czech >= 4, f"Expected Czech column names, found {found_czech}/7. Header: {header[:200]}"
        
        # Should NOT contain raw field IDs like "field_1776161309549"
        assert 'field_' not in header.lower(), \
            f"Header should use labels not field IDs. Header: {header[:200]}"
        print(f"PASS: CSV contains Czech column names ({found_czech} found)")
    
    def test_csv_export_requires_auth(self):
        """CSV export requires authentication."""
        response = requests.get(f"{BASE_URL}/api/events/{TEST_EVENT_ID}/export/csv")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: CSV export requires authentication")


class TestPDFExport:
    """PDF confirmation export tests."""
    
    def test_pdf_export_returns_200(self, auth_session):
        """GET /api/events/applications/{id}/pdf returns 200."""
        response = auth_session.get(f"{BASE_URL}/api/events/applications/{TEST_APPLICATION_ID}/pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: PDF export returns 200")
    
    def test_pdf_export_content_type(self, auth_session):
        """PDF export has correct content type."""
        response = auth_session.get(f"{BASE_URL}/api/events/applications/{TEST_APPLICATION_ID}/pdf")
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got: {content_type}"
        print(f"PASS: PDF content type: {content_type}")
    
    def test_pdf_is_valid_format(self, auth_session):
        """PDF file starts with %PDF header."""
        response = auth_session.get(f"{BASE_URL}/api/events/applications/{TEST_APPLICATION_ID}/pdf")
        assert response.status_code == 200
        
        content = response.content
        assert content[:4] == b'%PDF', f"PDF should start with %PDF, got: {content[:10]}"
        print("PASS: PDF has valid %PDF header")
    
    def test_pdf_has_content_disposition(self, auth_session):
        """PDF export has Content-Disposition header."""
        response = auth_session.get(f"{BASE_URL}/api/events/applications/{TEST_APPLICATION_ID}/pdf")
        assert response.status_code == 200
        disposition = response.headers.get('Content-Disposition', '')
        assert 'filename' in disposition, f"Expected filename in disposition, got: {disposition}"
        assert '.pdf' in disposition, f"Expected .pdf extension, got: {disposition}"
        print(f"PASS: PDF Content-Disposition: {disposition[:80]}...")
    
    def test_pdf_export_requires_auth(self):
        """PDF export (admin endpoint) requires authentication."""
        response = requests.get(f"{BASE_URL}/api/events/applications/{TEST_APPLICATION_ID}/pdf")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("PASS: PDF export requires authentication")


class TestPublicPDFExport:
    """Public PDF endpoint tests (no auth required)."""
    
    def test_public_pdf_returns_200(self):
        """GET /api/events/public/{inst_id}/application/{app_id}/pdf returns 200 without auth."""
        response = requests.get(
            f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/application/{TEST_APPLICATION_ID}/pdf"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: Public PDF returns 200 without auth")
    
    def test_public_pdf_is_valid_format(self):
        """Public PDF is valid PDF format."""
        response = requests.get(
            f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/application/{TEST_APPLICATION_ID}/pdf"
        )
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF', "Public PDF should be valid PDF format"
        print("PASS: Public PDF is valid format")
    
    def test_public_pdf_content_type(self):
        """Public PDF has correct content type."""
        response = requests.get(
            f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/application/{TEST_APPLICATION_ID}/pdf"
        )
        assert response.status_code == 200
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got: {content_type}"
        print(f"PASS: Public PDF content type: {content_type}")
    
    def test_public_pdf_inline_disposition(self):
        """Public PDF has inline disposition (for browser viewing)."""
        response = requests.get(
            f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/application/{TEST_APPLICATION_ID}/pdf"
        )
        assert response.status_code == 200
        disposition = response.headers.get('Content-Disposition', '')
        assert 'inline' in disposition, f"Expected inline disposition for public PDF, got: {disposition}"
        print(f"PASS: Public PDF has inline disposition")
    
    def test_public_pdf_404_for_invalid_application(self):
        """Public PDF returns 404 for non-existent application."""
        fake_app_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/application/{fake_app_id}/pdf"
        )
        assert response.status_code == 404, f"Expected 404 for invalid app, got {response.status_code}"
        print("PASS: Public PDF returns 404 for invalid application")
    
    def test_public_pdf_404_for_invalid_institution(self):
        """Public PDF returns 404 for non-whitelisted institution."""
        fake_inst_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{BASE_URL}/api/events/public/{fake_inst_id}/application/{TEST_APPLICATION_ID}/pdf"
        )
        assert response.status_code == 404, f"Expected 404 for invalid institution, got {response.status_code}"
        print("PASS: Public PDF returns 404 for invalid institution")


class TestApplicationSubmissionPDFUrl:
    """Test that application submission returns pdf_url."""
    
    @pytest.fixture(scope="class")
    def test_event_with_date(self, auth_session):
        """Create test event with date for application testing."""
        # Create event
        event_response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Export_PDFUrl_Event",
            "type": "event",
            "capacity": 10,
            "price": 100.0,
            "form_fields": [
                {"id": "name", "type": "text", "label": "Jméno", "required": True},
                {"id": "email", "type": "email", "label": "Email", "required": True}
            ]
        })
        assert event_response.status_code == 200
        event_id = event_response.json()["id"]
        
        # Add date
        date_response = auth_session.post(f"{BASE_URL}/api/events/{event_id}/dates", json={
            "start_datetime": "2026-12-01T10:00:00",
            "end_datetime": "2026-12-01T18:00:00"
        })
        assert date_response.status_code == 200
        date_id = date_response.json()["id"]
        
        yield {"event_id": event_id, "date_id": date_id}
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/events/{event_id}")
    
    def test_application_submission_returns_pdf_url(self, test_event_with_date):
        """Application submission response includes pdf_url field."""
        event_id = test_event_with_date["event_id"]
        date_id = test_event_with_date["date_id"]
        
        response = requests.post(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/apply", json={
            "event_id": event_id,
            "event_date_id": date_id,
            "applicant_data": {
                "name": "PDF URL Test",
                "email": "pdfurl@test.com"
            },
            "applicant_email": "pdfurl@test.com",
            "applicant_name": "PDF URL Test"
        })
        assert response.status_code == 200, f"Application submission failed: {response.text}"
        data = response.json()
        
        # Verify pdf_url is present
        assert "pdf_url" in data, f"Response should contain pdf_url field. Keys: {data.keys()}"
        assert data["pdf_url"] is not None, "pdf_url should not be None"
        
        # Verify pdf_url format
        pdf_url = data["pdf_url"]
        assert "/api/events/public/" in pdf_url, f"pdf_url should be public endpoint: {pdf_url}"
        assert "/application/" in pdf_url, f"pdf_url should contain /application/: {pdf_url}"
        assert "/pdf" in pdf_url, f"pdf_url should end with /pdf: {pdf_url}"
        assert data["id"] in pdf_url, f"pdf_url should contain application ID: {pdf_url}"
        
        print(f"PASS: Application submission returns pdf_url: {pdf_url}")
    
    def test_pdf_url_is_accessible(self, test_event_with_date):
        """PDF URL from submission is accessible without auth."""
        event_id = test_event_with_date["event_id"]
        date_id = test_event_with_date["date_id"]
        
        # Submit application
        submit_response = requests.post(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/apply", json={
            "event_id": event_id,
            "event_date_id": date_id,
            "applicant_data": {
                "name": "PDF Access Test",
                "email": "pdfaccess@test.com"
            },
            "applicant_email": "pdfaccess@test.com",
            "applicant_name": "PDF Access Test"
        })
        assert submit_response.status_code == 200
        pdf_url = submit_response.json()["pdf_url"]
        
        # Access PDF URL
        pdf_response = requests.get(f"{BASE_URL}{pdf_url}")
        assert pdf_response.status_code == 200, f"PDF URL not accessible: {pdf_response.status_code}"
        assert pdf_response.content[:4] == b'%PDF', "PDF URL should return valid PDF"
        
        print("PASS: PDF URL from submission is accessible")


class TestExportEdgeCases:
    """Edge case tests for export functionality."""
    
    def test_xlsx_export_empty_event(self, auth_session):
        """XLSX export works for event with no applications."""
        # Create event without applications
        event_response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Empty_Event_Export",
            "type": "event"
        })
        assert event_response.status_code == 200
        event_id = event_response.json()["id"]
        
        try:
            # Export should still work
            response = auth_session.get(f"{BASE_URL}/api/events/{event_id}/export/xlsx")
            assert response.status_code == 200, f"XLSX export failed for empty event: {response.status_code}"
            
            # Verify it's valid XLSX
            buffer = io.BytesIO(response.content)
            assert zipfile.is_zipfile(buffer), "Empty event XLSX should be valid"
            print("PASS: XLSX export works for empty event")
        finally:
            auth_session.delete(f"{BASE_URL}/api/events/{event_id}")
    
    def test_csv_export_empty_event(self, auth_session):
        """CSV export works for event with no applications."""
        # Create event without applications
        event_response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Empty_Event_CSV",
            "type": "event"
        })
        assert event_response.status_code == 200
        event_id = event_response.json()["id"]
        
        try:
            response = auth_session.get(f"{BASE_URL}/api/events/{event_id}/export/csv")
            assert response.status_code == 200, f"CSV export failed for empty event: {response.status_code}"
            
            # Should have BOM and header
            content = response.content
            assert content[:3] == b'\xef\xbb\xbf', "Empty CSV should have BOM"
            print("PASS: CSV export works for empty event")
        finally:
            auth_session.delete(f"{BASE_URL}/api/events/{event_id}")
    
    def test_export_nonexistent_event_returns_404(self, auth_session):
        """Export returns 404 for non-existent event."""
        fake_event_id = "00000000-0000-0000-0000-000000000000"
        
        xlsx_response = auth_session.get(f"{BASE_URL}/api/events/{fake_event_id}/export/xlsx")
        assert xlsx_response.status_code == 404, f"Expected 404 for XLSX, got {xlsx_response.status_code}"
        
        csv_response = auth_session.get(f"{BASE_URL}/api/events/{fake_event_id}/export/csv")
        assert csv_response.status_code == 404, f"Expected 404 for CSV, got {csv_response.status_code}"
        
        print("PASS: Export returns 404 for non-existent event")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
