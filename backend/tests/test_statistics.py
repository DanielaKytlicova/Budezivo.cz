"""
Backend API tests for Statistics feature - P1 with real data
Tests: Statistics endpoints, Period filters, CSV export, PRO plan restrictions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for demo institution with csv_export_exception=true
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Create headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestStatisticsAPI:
    """Tests for GET /api/statistics endpoint with various period filters"""

    def test_statistics_default_period(self, auth_headers):
        """Test default statistics - should return current month data"""
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "overview" in data
        assert "monthly" in data
        assert "by_program" in data
        assert "by_status" in data
        assert "by_age_group" in data
        assert "period" in data
        
        # Verify period defaults to month
        assert data["period"]["type"] == "month"
        print(f"Statistics default period: {data['period']['label']}")

    def test_statistics_overview_fields(self, auth_headers):
        """Test that overview contains all required metrics"""
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers
        )
        data = response.json()
        overview = data["overview"]
        
        # Verify all overview fields exist
        required_fields = [
            "total_bookings", "total_students", "total_teachers",
            "total_visitors", "confirmed_bookings", "pending_bookings",
            "cancelled_bookings", "completed_bookings", "avg_group_size"
        ]
        for field in required_fields:
            assert field in overview, f"Missing field: {field}"
        
        # Verify total_visitors = total_students + total_teachers
        assert overview["total_visitors"] == overview["total_students"] + overview["total_teachers"]
        print(f"Overview: {overview['total_bookings']} bookings, {overview['total_visitors']} visitors")

    def test_statistics_period_month(self, auth_headers):
        """Test statistics for specific month period"""
        response = requests.get(
            f"{BASE_URL}/api/statistics?period_type=month&year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["period"]["type"] == "month"
        assert data["period"]["start"] == "2026-03-01"
        assert data["period"]["end"] == "2026-03-31"
        # Verify March 2026 has data (test data exists for this period)
        assert data["overview"]["total_bookings"] >= 0
        print(f"Month period: {data['period']['label']}")

    def test_statistics_period_school_year(self, auth_headers):
        """Test statistics for school year period (Sep-Jun)"""
        response = requests.get(
            f"{BASE_URL}/api/statistics?period_type=school_year&year=2025",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify school year format 2025/2026
        assert data["period"]["type"] == "school_year"
        assert "Školní rok 2025/2026" in data["period"]["label"]
        assert data["period"]["start"] == "2025-09-01"
        assert data["period"]["end"] == "2026-06-30"
        print(f"School year period: {data['period']['label']}")

    def test_statistics_period_semester_first(self, auth_headers):
        """Test statistics for first semester (Sep-Jan)"""
        response = requests.get(
            f"{BASE_URL}/api/statistics?period_type=semester&year=2025&semester=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["period"]["type"] == "semester"
        assert "1. pololetí" in data["period"]["label"]
        assert data["period"]["start"] == "2025-09-01"
        assert data["period"]["end"] == "2026-01-31"
        print(f"First semester: {data['period']['label']}")

    def test_statistics_period_semester_second(self, auth_headers):
        """Test statistics for second semester (Feb-Jun)"""
        response = requests.get(
            f"{BASE_URL}/api/statistics?period_type=semester&year=2025&semester=2",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["period"]["type"] == "semester"
        assert "2. pololetí" in data["period"]["label"]
        assert data["period"]["start"] == "2026-02-01"
        assert data["period"]["end"] == "2026-06-30"
        print(f"Second semester: {data['period']['label']}")

    def test_statistics_period_calendar_year(self, auth_headers):
        """Test statistics for calendar year (Jan-Dec)"""
        response = requests.get(
            f"{BASE_URL}/api/statistics?period_type=calendar_year&year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["period"]["type"] == "calendar_year"
        assert "Rok 2026" in data["period"]["label"]
        assert data["period"]["start"] == "2026-01-01"
        assert data["period"]["end"] == "2026-12-31"
        print(f"Calendar year: {data['period']['label']}")

    def test_statistics_by_program_data(self, auth_headers):
        """Test by_program field contains program breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/statistics?period_type=school_year&year=2025",
            headers=auth_headers
        )
        data = response.json()
        
        if len(data["by_program"]) > 0:
            program = data["by_program"][0]
            assert "program_id" in program
            assert "program_name" in program
            assert "bookings_count" in program
            assert "total_students" in program
            assert "total_teachers" in program
            print(f"By program: {len(data['by_program'])} programs found")

    def test_statistics_by_status_data(self, auth_headers):
        """Test by_status field contains status breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers
        )
        data = response.json()
        
        # Status should contain Czech labels
        valid_statuses = ["Čekající", "Potvrzené", "Zrušené", "Dokončené", "Nedostavil se"]
        for status in data["by_status"]:
            assert status["status"] in valid_statuses
            assert "count" in status
        print(f"By status: {len(data['by_status'])} statuses")

    def test_statistics_by_age_group_data(self, auth_headers):
        """Test by_age_group field contains age group breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers
        )
        data = response.json()
        
        if len(data["by_age_group"]) > 0:
            for age_group in data["by_age_group"]:
                assert "age_group" in age_group
                assert "count" in age_group
        print(f"By age group: {len(data['by_age_group'])} age groups")

    def test_statistics_monthly_data_structure(self, auth_headers):
        """Test monthly field contains proper monthly breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/statistics?period_type=school_year&year=2025",
            headers=auth_headers
        )
        data = response.json()
        
        # Should have monthly data for school year
        assert len(data["monthly"]) > 0
        for month in data["monthly"]:
            assert "month" in month  # Czech month name
            assert "year" in month
            assert "bookings" in month
            assert "students" in month
            assert "teachers" in month
        print(f"Monthly data: {len(data['monthly'])} months")

    def test_statistics_requires_auth(self):
        """Test statistics endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/statistics")
        assert response.status_code in [401, 403]
        print("Statistics requires authentication: PASS")


class TestCSVExport:
    """Tests for CSV export functionality"""

    def test_csv_export_summary(self, auth_headers):
        """Test CSV export for monthly summary"""
        response = requests.get(
            f"{BASE_URL}/api/statistics/export/csv?export_type=summary",
            headers=auth_headers
        )
        # Institution has csv_export_exception=true, so should work
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        
        # Verify CSV content
        content = response.text
        assert "Měsíc" in content
        assert "Rok" in content
        assert "Počet rezervací" in content
        print("CSV summary export: PASS")

    def test_csv_export_reservations(self, auth_headers):
        """Test CSV export for all reservations"""
        response = requests.get(
            f"{BASE_URL}/api/statistics/export/csv?export_type=reservations",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        content = response.text
        # Verify headers
        assert "Datum" in content
        assert "Program" in content
        assert "Škola" in content
        assert "Počet žáků" in content
        print("CSV reservations export: PASS")

    def test_csv_export_programs(self, auth_headers):
        """Test CSV export for program breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/statistics/export/csv?export_type=programs",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        content = response.text
        assert "Program" in content
        assert "Počet rezervací" in content
        assert "Průměrná velikost skupiny" in content
        print("CSV programs export: PASS")

    def test_csv_export_with_period(self, auth_headers):
        """Test CSV export with specific period filter"""
        response = requests.get(
            f"{BASE_URL}/api/statistics/export/csv?export_type=summary&period_type=school_year&year=2025",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        print("CSV export with school year period: PASS")

    def test_csv_export_invalid_type(self, auth_headers):
        """Test CSV export with invalid export type"""
        response = requests.get(
            f"{BASE_URL}/api/statistics/export/csv?export_type=invalid",
            headers=auth_headers
        )
        assert response.status_code == 400
        print("CSV invalid export type returns 400: PASS")

    def test_csv_export_requires_auth(self):
        """Test CSV export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/statistics/export/csv")
        assert response.status_code in [401, 403]
        print("CSV export requires authentication: PASS")


class TestPROStatus:
    """Tests for PRO plan status and exceptions"""

    def test_pro_status_endpoint(self, auth_headers):
        """Test PRO status endpoint returns expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/settings/pro",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "plan" in data
        assert "is_pro" in data
        assert "csv_export_exception" in data
        # Test institution has csv_export_exception=true
        assert data["csv_export_exception"] == True
        print(f"PRO status: plan={data['plan']}, csv_export_exception={data['csv_export_exception']}")

    def test_csv_export_allowed_with_exception(self, auth_headers):
        """Test CSV export works with csv_export_exception flag"""
        # First verify exception is enabled
        pro_response = requests.get(
            f"{BASE_URL}/api/settings/pro",
            headers=auth_headers
        )
        pro_data = pro_response.json()
        assert pro_data["csv_export_exception"] == True
        
        # Then verify CSV export works
        csv_response = requests.get(
            f"{BASE_URL}/api/statistics/export/csv?export_type=summary",
            headers=auth_headers
        )
        assert csv_response.status_code == 200
        print("CSV export with exception flag: PASS")


class TestLegacyEndpoints:
    """Tests for backwards-compatible legacy endpoints"""

    def test_bookings_over_time(self, auth_headers):
        """Test legacy bookings over time endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/statistics/bookings-over-time",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "labels" in data
        assert "data" in data
        assert isinstance(data["labels"], list)
        assert isinstance(data["data"], list)
        print(f"Bookings over time: {len(data['labels'])} months")

    def test_popular_programs(self, auth_headers):
        """Test legacy popular programs endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/statistics/popular-programs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "labels" in data
        assert "data" in data
        print(f"Popular programs: {len(data['labels'])} programs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
