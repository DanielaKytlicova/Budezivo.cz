"""
Test Logo Upload Feature
Tests for:
- POST /api/settings/logo/upload - upload logo (auth required)
- GET /api/settings/logo/{path} - serve logo (public)
- File type validation (PNG, JPG, SVG, WebP only)
- File size validation (max 2MB)
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


class TestLogoUpload:
    """Logo upload and serving tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_01_upload_logo_requires_auth(self):
        """Test that logo upload requires authentication"""
        # Create a small test PNG
        png_data = self._create_test_png()
        files = {"file": ("test.png", png_data, "image/png")}
        
        # Try without auth
        response = requests.post(f"{BASE_URL}/api/settings/logo/upload", files=files)
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Logo upload requires authentication")
        
    def test_02_upload_valid_png(self):
        """Test uploading a valid PNG file"""
        png_data = self._create_test_png()
        files = {"file": ("test_logo.png", png_data, "image/png")}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        data = response.json()
        assert "logo_url" in data, "Response should contain logo_url"
        assert "message" in data, "Response should contain message"
        assert data["logo_url"].startswith("/api/settings/logo/"), f"Invalid logo_url format: {data['logo_url']}"
        
        # Store for later tests
        self.__class__.uploaded_logo_url = data["logo_url"]
        print(f"PASS: PNG upload successful, logo_url: {data['logo_url']}")
        
    def test_03_upload_valid_jpeg(self):
        """Test uploading a valid JPEG file"""
        jpeg_data = self._create_test_jpeg()
        files = {"file": ("test_logo.jpg", jpeg_data, "image/jpeg")}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert response.status_code == 200, f"JPEG upload failed: {response.text}"
        
        data = response.json()
        assert "logo_url" in data
        print("PASS: JPEG upload successful")
        
    def test_04_upload_valid_svg(self):
        """Test uploading a valid SVG file"""
        svg_data = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" fill="blue"/></svg>'
        files = {"file": ("test_logo.svg", svg_data, "image/svg+xml")}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert response.status_code == 200, f"SVG upload failed: {response.text}"
        
        data = response.json()
        assert "logo_url" in data
        print("PASS: SVG upload successful")
        
    def test_05_upload_valid_webp(self):
        """Test uploading a valid WebP file"""
        webp_data = self._create_test_webp()
        files = {"file": ("test_logo.webp", webp_data, "image/webp")}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert response.status_code == 200, f"WebP upload failed: {response.text}"
        
        data = response.json()
        assert "logo_url" in data
        print("PASS: WebP upload successful")
        
    def test_06_reject_invalid_file_type_txt(self):
        """Test that .txt files are rejected"""
        txt_data = b"This is a text file, not an image"
        files = {"file": ("test.txt", txt_data, "text/plain")}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400 for .txt file, got {response.status_code}"
        print("PASS: .txt file correctly rejected")
        
    def test_07_reject_invalid_file_type_pdf(self):
        """Test that .pdf files are rejected"""
        # Minimal PDF header
        pdf_data = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("test.pdf", pdf_data, "application/pdf")}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400 for .pdf file, got {response.status_code}"
        print("PASS: .pdf file correctly rejected")
        
    def test_08_reject_file_too_large(self):
        """Test that files over 2MB are rejected"""
        # Create a file slightly over 2MB
        large_data = b"x" * (2 * 1024 * 1024 + 1000)  # 2MB + 1KB
        files = {"file": ("large.png", large_data, "image/png")}
        
        response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400 for large file, got {response.status_code}"
        print("PASS: Large file correctly rejected")
        
    def test_09_serve_logo_public(self):
        """Test that logo serving is public (no auth needed)"""
        # First upload a logo to get a valid path
        png_data = self._create_test_png()
        files = {"file": ("serve_test.png", png_data, "image/png")}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert upload_response.status_code == 200
        logo_url = upload_response.json()["logo_url"]
        
        # Now try to access without auth
        serve_response = requests.get(f"{BASE_URL}{logo_url}")
        assert serve_response.status_code == 200, f"Logo serve failed: {serve_response.status_code}"
        
        # Check content type
        content_type = serve_response.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image content type, got: {content_type}"
        
        # Note: Cache-Control header may be overwritten by CDN (Cloudflare)
        # The backend sets "public, max-age=86400" but CDN may override
        cache_control = serve_response.headers.get("Cache-Control", "")
        print(f"Cache-Control header: {cache_control} (may be CDN-modified)")
        
        print(f"PASS: Logo served publicly with content-type: {content_type}")
        
    def test_10_serve_nonexistent_logo_returns_404(self):
        """Test that serving a non-existent logo returns 404"""
        response = requests.get(f"{BASE_URL}/api/settings/logo/nonexistent/path/logo.png")
        assert response.status_code == 404, f"Expected 404 for non-existent logo, got {response.status_code}"
        print("PASS: Non-existent logo returns 404")
        
    def test_11_logo_url_saved_to_institution(self):
        """Test that logo URL is saved to institution settings"""
        # Upload a logo
        png_data = self._create_test_png()
        files = {"file": ("institution_test.png", png_data, "image/png")}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert upload_response.status_code == 200
        uploaded_logo_url = upload_response.json()["logo_url"]
        
        # Check institution settings
        settings_response = requests.get(
            f"{BASE_URL}/api/institution/settings",
            headers=self.headers
        )
        assert settings_response.status_code == 200
        
        settings = settings_response.json()
        assert settings.get("logo_url") == uploaded_logo_url, f"Logo URL not saved to institution. Expected: {uploaded_logo_url}, Got: {settings.get('logo_url')}"
        print("PASS: Logo URL saved to institution settings")
        
    def test_12_logo_url_saved_to_theme(self):
        """Test that logo URL is saved to theme settings"""
        # Upload a logo
        png_data = self._create_test_png()
        files = {"file": ("theme_test.png", png_data, "image/png")}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/settings/logo/upload",
            files=files,
            headers=self.headers
        )
        assert upload_response.status_code == 200
        uploaded_logo_url = upload_response.json()["logo_url"]
        
        # Check theme settings
        theme_response = requests.get(
            f"{BASE_URL}/api/settings/theme",
            headers=self.headers
        )
        assert theme_response.status_code == 200
        
        theme = theme_response.json()
        assert theme.get("logo_url") == uploaded_logo_url, f"Logo URL not saved to theme. Expected: {uploaded_logo_url}, Got: {theme.get('logo_url')}"
        print("PASS: Logo URL saved to theme settings")
        
    # Helper methods to create test images
    def _create_test_png(self):
        """Create a minimal valid PNG file"""
        # Minimal 1x1 red PNG
        return bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # 8-bit RGB
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,  # compressed data
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,
            0x8D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
            0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
    def _create_test_jpeg(self):
        """Create a minimal valid JPEG file"""
        # Minimal 1x1 JPEG
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
            0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
            0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
            0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
            0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
            0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
            0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
            0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4,
            0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
            0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
            0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF,
            0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04,
            0x00, 0x00, 0x01, 0x7D, 0x01, 0x02, 0x03, 0x00,
            0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
            0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1,
            0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A,
            0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35,
            0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55,
            0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65,
            0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85,
            0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94,
            0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2,
            0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA,
            0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8,
            0xD9, 0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6,
            0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA,
            0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
            0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x7F, 0xFF,
            0xD9
        ])
        
    def _create_test_webp(self):
        """Create a minimal valid WebP file"""
        # Minimal 1x1 WebP (lossy)
        return bytes([
            0x52, 0x49, 0x46, 0x46,  # RIFF
            0x24, 0x00, 0x00, 0x00,  # File size - 8
            0x57, 0x45, 0x42, 0x50,  # WEBP
            0x56, 0x50, 0x38, 0x20,  # VP8 
            0x18, 0x00, 0x00, 0x00,  # Chunk size
            0x30, 0x01, 0x00, 0x9D,  # VP8 bitstream
            0x01, 0x2A, 0x01, 0x00,  # Width/height
            0x01, 0x00, 0x02, 0x00,
            0x34, 0x25, 0xA4, 0x00,
            0x03, 0x70, 0x00, 0xFE,
            0xFB, 0x94, 0x00, 0x00
        ])


class TestRegressionAuth:
    """Regression tests for auth flow"""
    
    def test_login_with_refresh_token(self):
        """Test that login still returns both tokens"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain 'token'"
        assert "refresh_token" in data, "Response should contain 'refresh_token'"
        print("PASS: Login returns both token and refresh_token")
        
    def test_admin_dashboard_loads(self):
        """Test that admin can access dashboard data"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access dashboard stats
        stats_response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert stats_response.status_code == 200, f"Dashboard stats failed: {stats_response.status_code}"
        print("PASS: Admin dashboard loads correctly")
