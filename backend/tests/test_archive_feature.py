"""
Test suite for Program Archive feature.
Tests: GET /archived, POST /{id}/archive, POST /{id}/unarchive, GET /{id}/archive-report
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestArchiveEndpoints:
    """Test archive-related API endpoints."""
    
    def test_get_archived_programs(self, auth_headers):
        """GET /api/programs/archived - should return list of archived programs."""
        response = requests.get(
            f"{BASE_URL}/api/programs/archived",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get archived programs: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} archived programs")
        
        # If there are archived programs, verify structure
        if len(data) > 0:
            program = data[0]
            assert "id" in program, "Archived program should have id"
            assert "name_cs" in program or "name_en" in program, "Archived program should have name"
            assert program.get("status") == "archived", "Program status should be 'archived'"
            print(f"First archived program: {program.get('name_cs', program.get('name_en'))}")
    
    def test_get_active_programs(self, auth_headers):
        """GET /api/programs - should return active programs (not archived)."""
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get programs: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify no archived programs in the list
        for program in data:
            assert program.get("status") != "archived", f"Active programs list should not contain archived programs: {program.get('name_cs')}"
        
        print(f"Found {len(data)} active programs")
        return data
    
    def test_archive_and_unarchive_flow(self, auth_headers):
        """Test full archive/unarchive flow."""
        # Step 1: Get active programs
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers=auth_headers
        )
        assert response.status_code == 200
        active_programs = response.json()
        
        if len(active_programs) == 0:
            pytest.skip("No active programs to test archive flow")
        
        # Pick first active program
        test_program = active_programs[0]
        program_id = test_program["id"]
        program_name = test_program.get("name_cs", test_program.get("name_en", "Unknown"))
        print(f"Testing archive flow with program: {program_name} (ID: {program_id})")
        
        # Step 2: Archive the program
        archive_response = requests.post(
            f"{BASE_URL}/api/programs/{program_id}/archive",
            headers=auth_headers,
            json={"reason": "Test archivace"}
        )
        assert archive_response.status_code == 200, f"Failed to archive program: {archive_response.text}"
        archive_data = archive_response.json()
        assert "message" in archive_data, "Archive response should have message"
        print(f"Archive response: {archive_data}")
        
        # Step 3: Verify program is in archived list
        archived_response = requests.get(
            f"{BASE_URL}/api/programs/archived",
            headers=auth_headers
        )
        assert archived_response.status_code == 200
        archived_programs = archived_response.json()
        archived_ids = [p["id"] for p in archived_programs]
        assert program_id in archived_ids, f"Program {program_id} should be in archived list"
        print(f"Verified: Program is now in archived list")
        
        # Step 4: Verify program is NOT in active list
        active_response = requests.get(
            f"{BASE_URL}/api/programs",
            headers=auth_headers
        )
        assert active_response.status_code == 200
        active_programs_after = active_response.json()
        active_ids = [p["id"] for p in active_programs_after]
        assert program_id not in active_ids, f"Program {program_id} should NOT be in active list"
        print(f"Verified: Program is NOT in active list")
        
        # Step 5: Unarchive the program
        unarchive_response = requests.post(
            f"{BASE_URL}/api/programs/{program_id}/unarchive",
            headers=auth_headers
        )
        assert unarchive_response.status_code == 200, f"Failed to unarchive program: {unarchive_response.text}"
        unarchive_data = unarchive_response.json()
        assert "message" in unarchive_data, "Unarchive response should have message"
        print(f"Unarchive response: {unarchive_data}")
        
        # Step 6: Verify program is back in active list
        final_active_response = requests.get(
            f"{BASE_URL}/api/programs",
            headers=auth_headers
        )
        assert final_active_response.status_code == 200
        final_active_programs = final_active_response.json()
        final_active_ids = [p["id"] for p in final_active_programs]
        assert program_id in final_active_ids, f"Program {program_id} should be back in active list"
        print(f"Verified: Program is back in active list after unarchive")
    
    def test_archive_report(self, auth_headers):
        """GET /api/programs/{id}/archive-report - should return structured report."""
        # First get any program (active or archived)
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers=auth_headers
        )
        assert response.status_code == 200
        programs = response.json()
        
        # Also check archived
        archived_response = requests.get(
            f"{BASE_URL}/api/programs/archived",
            headers=auth_headers
        )
        assert archived_response.status_code == 200
        archived_programs = archived_response.json()
        
        all_programs = programs + archived_programs
        
        if len(all_programs) == 0:
            pytest.skip("No programs to test archive report")
        
        # Test report for first program
        test_program = all_programs[0]
        program_id = test_program["id"]
        
        report_response = requests.get(
            f"{BASE_URL}/api/programs/{program_id}/archive-report",
            headers=auth_headers
        )
        assert report_response.status_code == 200, f"Failed to get archive report: {report_response.text}"
        report = report_response.json()
        
        # Verify report structure
        assert "report_generated_at" in report, "Report should have generation timestamp"
        assert "program" in report, "Report should have program info"
        assert "statistics" in report, "Report should have statistics"
        assert "schools" in report, "Report should have schools summary"
        
        # Verify program info
        program_info = report["program"]
        assert "name" in program_info, "Program info should have name"
        assert "capacity" in program_info, "Program info should have capacity"
        
        # Verify statistics
        stats = report["statistics"]
        assert "total_reservations" in stats, "Stats should have total_reservations"
        assert "confirmed" in stats, "Stats should have confirmed count"
        assert "completed" in stats, "Stats should have completed count"
        assert "cancelled" in stats, "Stats should have cancelled count"
        assert "total_students" in stats, "Stats should have total_students"
        assert "unique_schools" in stats, "Stats should have unique_schools"
        
        print(f"Archive report for program '{program_info.get('name')}':")
        print(f"  - Total reservations: {stats.get('total_reservations')}")
        print(f"  - Confirmed: {stats.get('confirmed')}")
        print(f"  - Completed: {stats.get('completed')}")
        print(f"  - Total students: {stats.get('total_students')}")
        print(f"  - Unique schools: {stats.get('unique_schools')}")
    
    def test_archive_already_archived_program(self, auth_headers):
        """POST /api/programs/{id}/archive - should fail for already archived program."""
        # Get archived programs
        response = requests.get(
            f"{BASE_URL}/api/programs/archived",
            headers=auth_headers
        )
        assert response.status_code == 200
        archived_programs = response.json()
        
        if len(archived_programs) == 0:
            pytest.skip("No archived programs to test double-archive")
        
        # Try to archive an already archived program
        program_id = archived_programs[0]["id"]
        archive_response = requests.post(
            f"{BASE_URL}/api/programs/{program_id}/archive",
            headers=auth_headers,
            json={"reason": "Double archive test"}
        )
        
        # Should return 400 error
        assert archive_response.status_code == 400, f"Should fail to archive already archived program: {archive_response.text}"
        error_data = archive_response.json()
        assert "detail" in error_data, "Error response should have detail"
        print(f"Correctly rejected double-archive: {error_data.get('detail')}")
    
    def test_unarchive_active_program(self, auth_headers):
        """POST /api/programs/{id}/unarchive - should fail for active program."""
        # Get active programs
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers=auth_headers
        )
        assert response.status_code == 200
        active_programs = response.json()
        
        if len(active_programs) == 0:
            pytest.skip("No active programs to test unarchive-active")
        
        # Try to unarchive an active program
        program_id = active_programs[0]["id"]
        unarchive_response = requests.post(
            f"{BASE_URL}/api/programs/{program_id}/unarchive",
            headers=auth_headers
        )
        
        # Should return 400 error
        assert unarchive_response.status_code == 400, f"Should fail to unarchive active program: {unarchive_response.text}"
        error_data = unarchive_response.json()
        assert "detail" in error_data, "Error response should have detail"
        print(f"Correctly rejected unarchive-active: {error_data.get('detail')}")
    
    def test_archive_nonexistent_program(self, auth_headers):
        """POST /api/programs/{id}/archive - should return 404 for nonexistent program."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.post(
            f"{BASE_URL}/api/programs/{fake_id}/archive",
            headers=auth_headers,
            json={"reason": "Test"}
        )
        assert response.status_code == 404, f"Should return 404 for nonexistent program: {response.text}"
        print("Correctly returned 404 for nonexistent program")
    
    def test_archive_report_nonexistent_program(self, auth_headers):
        """GET /api/programs/{id}/archive-report - should return 404 for nonexistent program."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(
            f"{BASE_URL}/api/programs/{fake_id}/archive-report",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Should return 404 for nonexistent program: {response.text}"
        print("Correctly returned 404 for nonexistent program report")


class TestArchiveWithoutAuth:
    """Test archive endpoints require authentication."""
    
    def test_archived_requires_auth(self):
        """GET /api/programs/archived - should require auth."""
        response = requests.get(f"{BASE_URL}/api/programs/archived")
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
        print("Correctly requires auth for archived list")
    
    def test_archive_requires_auth(self):
        """POST /api/programs/{id}/archive - should require auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.post(
            f"{BASE_URL}/api/programs/{fake_id}/archive",
            json={"reason": "Test"}
        )
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
        print("Correctly requires auth for archive action")
    
    def test_unarchive_requires_auth(self):
        """POST /api/programs/{id}/unarchive - should require auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.post(f"{BASE_URL}/api/programs/{fake_id}/unarchive")
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
        print("Correctly requires auth for unarchive action")
    
    def test_archive_report_requires_auth(self):
        """GET /api/programs/{id}/archive-report - should require auth."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{BASE_URL}/api/programs/{fake_id}/archive-report")
        assert response.status_code in [401, 403], f"Should require auth: {response.status_code}"
        print("Correctly requires auth for archive report")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
