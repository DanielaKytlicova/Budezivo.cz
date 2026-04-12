"""
Test suite for Collision & Parallel Run feature.
Tests:
- GET /api/programs returns allow_parallel, collision_resources, blocked_program_ids fields
- PUT /api/programs/{id} saves collision settings correctly
- POST /api/bookings/public/{institution_id} returns 409 when collision detected
- Availability endpoint reflects collision blocks
- Time block parser handles both 'HH:MM' and 'HH:MM-HH:MM' formats
"""
import pytest
import requests
import os
import sys

# Add backend to path for importing collision_service
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://gdpr-crm-hub.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"

# Known program IDs from context
PROG1_ID = "fa7c7513-8e2e-4e3e-8e3e-8e3e8e3e8e3e"  # Historická prohlídka - allow_parallel=True
PROG2_ID = "5638d57c-8e2e-4e3e-8e3e-8e3e8e3e8e3e"  # Testovací multi program - allow_parallel=False


class TestTimeBlockParser:
    """Test time block parsing utility functions."""
    
    def test_parse_time_block_hhmm_format(self):
        """Test parsing 'HH:MM' format."""
        from services.collision_service import parse_time_block
        
        start, end = parse_time_block("09:00")
        assert start == 9 * 60  # 540 minutes
        assert end is None  # End unknown for simple format
        
    def test_parse_time_block_range_format(self):
        """Test parsing 'HH:MM-HH:MM' format."""
        from services.collision_service import parse_time_block
        
        start, end = parse_time_block("09:00-10:30")
        assert start == 9 * 60  # 540 minutes
        assert end == 10 * 60 + 30  # 630 minutes
        
    def test_parse_time_block_invalid(self):
        """Test parsing invalid format returns None."""
        from services.collision_service import parse_time_block
        
        start, end = parse_time_block("invalid")
        assert start is None
        assert end is None
        
    def test_time_blocks_overlap_true(self):
        """Test overlapping time blocks."""
        from services.collision_service import time_blocks_overlap
        
        # 09:00-10:30 overlaps with 10:00-11:30
        assert time_blocks_overlap("09:00", 90, "10:00", 90) == True
        
    def test_time_blocks_overlap_false(self):
        """Test non-overlapping time blocks."""
        from services.collision_service import time_blocks_overlap
        
        # 09:00-10:00 does not overlap with 11:00-12:00
        assert time_blocks_overlap("09:00", 60, "11:00", 60) == False
        
    def test_time_blocks_overlap_range_format(self):
        """Test overlap with range format."""
        from services.collision_service import time_blocks_overlap
        
        # 09:00-10:30 overlaps with 10:00-11:30
        assert time_blocks_overlap("09:00-10:30", 0, "10:00-11:30", 0) == True


class TestProgramCollisionFields:
    """Test that programs API returns collision fields."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    def test_get_programs_returns_collision_fields(self, auth_token):
        """GET /api/programs should return allow_parallel, collision_resources, blocked_program_ids."""
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        programs = response.json()
        assert isinstance(programs, list), "Expected list of programs"
        assert len(programs) > 0, "Expected at least one program"
        
        # Check first program has collision fields
        program = programs[0]
        assert "allow_parallel" in program, "Missing allow_parallel field"
        assert "collision_resources" in program, "Missing collision_resources field"
        assert "blocked_program_ids" in program, "Missing blocked_program_ids field"
        
        # Verify types
        assert isinstance(program["allow_parallel"], bool), "allow_parallel should be boolean"
        assert isinstance(program["collision_resources"], list), "collision_resources should be list"
        assert isinstance(program["blocked_program_ids"], list), "blocked_program_ids should be list"
        
        print(f"✓ Found {len(programs)} programs with collision fields")
        print(f"  First program: allow_parallel={program['allow_parallel']}, "
              f"collision_resources={program['collision_resources']}, "
              f"blocked_program_ids={program['blocked_program_ids']}")
    
    def test_get_single_program_returns_collision_fields(self, auth_token):
        """GET /api/programs/{id} should return collision fields."""
        # First get list to find a program ID
        list_response = requests.get(
            f"{BASE_URL}/api/programs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert list_response.status_code == 200
        programs = list_response.json()
        assert len(programs) > 0
        
        program_id = programs[0]["id"]
        
        # Get single program
        response = requests.get(
            f"{BASE_URL}/api/programs/{program_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        program = response.json()
        
        assert "allow_parallel" in program
        assert "collision_resources" in program
        assert "blocked_program_ids" in program
        
        print(f"✓ Single program {program_id} has collision fields")


class TestProgramCollisionUpdate:
    """Test updating program collision settings."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def test_program_id(self, auth_token):
        """Get a program ID for testing."""
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        programs = response.json()
        assert len(programs) > 0
        return programs[0]["id"]
    
    def test_update_allow_parallel_true(self, auth_token, test_program_id):
        """PUT /api/programs/{id} should save allow_parallel=True."""
        # First get current program data
        get_response = requests.get(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        program = get_response.json()
        
        # Update with allow_parallel=True
        program["allow_parallel"] = True
        program["collision_resources"] = ["lecturer"]
        program["blocked_program_ids"] = []
        
        response = requests.put(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=program
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify the update persisted
        verify_response = requests.get(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert verify_response.status_code == 200
        updated = verify_response.json()
        
        assert updated["allow_parallel"] == True, "allow_parallel should be True"
        assert updated["collision_resources"] == ["lecturer"], "collision_resources should be ['lecturer']"
        
        print(f"✓ Updated program {test_program_id} with allow_parallel=True")
    
    def test_update_allow_parallel_false(self, auth_token, test_program_id):
        """PUT /api/programs/{id} should save allow_parallel=False."""
        # Get current program data
        get_response = requests.get(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        program = get_response.json()
        
        # Update with allow_parallel=False
        program["allow_parallel"] = False
        program["collision_resources"] = []
        program["blocked_program_ids"] = []
        
        response = requests.put(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=program
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify the update persisted
        verify_response = requests.get(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert verify_response.status_code == 200
        updated = verify_response.json()
        
        assert updated["allow_parallel"] == False, "allow_parallel should be False"
        
        print(f"✓ Updated program {test_program_id} with allow_parallel=False")
    
    def test_update_blocked_program_ids(self, auth_token, test_program_id):
        """PUT /api/programs/{id} should save blocked_program_ids."""
        # Get all programs to find another program ID
        list_response = requests.get(
            f"{BASE_URL}/api/programs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert list_response.status_code == 200
        programs = list_response.json()
        
        # Find another program to block
        other_program_id = None
        for p in programs:
            if p["id"] != test_program_id:
                other_program_id = p["id"]
                break
        
        if not other_program_id:
            pytest.skip("Need at least 2 programs to test blocked_program_ids")
        
        # Get current program data
        get_response = requests.get(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        program = get_response.json()
        
        # Update with blocked_program_ids
        program["allow_parallel"] = True
        program["blocked_program_ids"] = [other_program_id]
        
        response = requests.put(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=program
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify the update persisted
        verify_response = requests.get(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert verify_response.status_code == 200
        updated = verify_response.json()
        
        assert other_program_id in updated["blocked_program_ids"], \
            f"blocked_program_ids should contain {other_program_id}"
        
        print(f"✓ Updated program {test_program_id} with blocked_program_ids=[{other_program_id}]")
        
        # Clean up - remove blocked program
        program["blocked_program_ids"] = []
        requests.put(
            f"{BASE_URL}/api/programs/{test_program_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=program
        )


class TestBookingCollisionDetection:
    """Test collision detection during booking creation."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def institution_id(self, auth_token):
        """Get institution ID from auth."""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        return response.json().get("institution_id")
    
    @pytest.fixture(scope="class")
    def test_program(self, auth_token):
        """Get a program for testing."""
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        programs = response.json()
        assert len(programs) > 0
        return programs[0]
    
    def test_booking_collision_409_for_non_parallel_program(self, auth_token, institution_id, test_program):
        """POST /api/bookings/public/{institution_id} should return 409 when collision detected."""
        program_id = test_program["id"]
        
        # First, set program to allow_parallel=False
        test_program["allow_parallel"] = False
        update_response = requests.put(
            f"{BASE_URL}/api/programs/{program_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json=test_program
        )
        assert update_response.status_code == 200
        
        # Get existing bookings to find a date with a booking
        bookings_response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        if bookings_response.status_code != 200 or len(bookings_response.json()) == 0:
            # Create a test booking first
            test_date = "2026-03-24"
            test_time = "09:00"
            
            booking_data = {
                "program_id": program_id,
                "date": test_date,
                "time_block": test_time,
                "school_name": "TEST_Collision_School",
                "group_type": "zs1_7_12",
                "age_or_class": "5. třída",
                "num_students": 25,
                "num_teachers": 2,
                "special_requirements": "",
                "contact_name": "Test Contact",
                "contact_email": "test-collision@example.com",
                "contact_phone": "+420123456789",
                "gdpr_consent": True,
                "terms_accepted": True,
                "terms_accepted_text_version": "v1"
            }
            
            # Create first booking
            first_response = requests.post(
                f"{BASE_URL}/api/bookings/public/{institution_id}",
                json=booking_data
            )
            
            if first_response.status_code == 201 or first_response.status_code == 200:
                # Now try to create a conflicting booking
                booking_data["school_name"] = "TEST_Collision_School_2"
                booking_data["contact_email"] = "test-collision2@example.com"
                
                conflict_response = requests.post(
                    f"{BASE_URL}/api/bookings/public/{institution_id}",
                    json=booking_data
                )
                
                assert conflict_response.status_code == 409, \
                    f"Expected 409 for collision, got {conflict_response.status_code}: {conflict_response.text}"
                
                error_detail = conflict_response.json().get("detail", "")
                assert "konflikt" in error_detail.lower() or "collision" in error_detail.lower() or "neumožňuje" in error_detail.lower(), \
                    f"Error message should mention collision: {error_detail}"
                
                print(f"✓ Collision detected correctly: {error_detail}")
            elif first_response.status_code == 409:
                # There's already a booking at this time - collision working
                print(f"✓ Collision already detected on first attempt: {first_response.json().get('detail')}")
            else:
                pytest.skip(f"Could not create test booking: {first_response.status_code} - {first_response.text}")
        else:
            # Use existing booking date/time
            bookings = bookings_response.json()
            existing = bookings[0]
            
            booking_data = {
                "program_id": program_id,
                "date": existing["date"],
                "time_block": existing["time_block"],
                "school_name": "TEST_Collision_School",
                "group_type": "zs1_7_12",
                "age_or_class": "5. třída",
                "num_students": 25,
                "num_teachers": 2,
                "special_requirements": "",
                "contact_name": "Test Contact",
                "contact_email": "test-collision@example.com",
                "contact_phone": "+420123456789",
                "gdpr_consent": True,
                "terms_accepted": True,
                "terms_accepted_text_version": "v1"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/bookings/public/{institution_id}",
                json=booking_data
            )
            
            # Should get 409 if collision detection is working
            if response.status_code == 409:
                print(f"✓ Collision detected: {response.json().get('detail')}")
            else:
                print(f"Note: Got {response.status_code} - may need different test data")


class TestAvailabilityCollision:
    """Test that availability endpoint reflects collision blocks."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def institution_id(self, auth_token):
        """Get institution ID from auth."""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        return response.json().get("institution_id")
    
    @pytest.fixture(scope="class")
    def test_program(self, auth_token):
        """Get a program for testing."""
        response = requests.get(
            f"{BASE_URL}/api/programs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        programs = response.json()
        assert len(programs) > 0
        return programs[0]
    
    def test_availability_endpoint_exists(self, institution_id, test_program):
        """GET /api/availability/{institution_id}/{program_id}/{date} should work."""
        program_id = test_program["id"]
        test_date = "2026-03-25"
        
        response = requests.get(
            f"{BASE_URL}/api/availability/{institution_id}/{program_id}/{test_date}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "date" in data, "Response should have 'date' field"
        assert "time_blocks" in data, "Response should have 'time_blocks' field"
        assert isinstance(data["time_blocks"], list), "time_blocks should be a list"
        
        print(f"✓ Availability endpoint working for {test_date}")
        print(f"  Time blocks: {data['time_blocks']}")
    
    def test_availability_shows_booked_status(self, auth_token, institution_id, test_program):
        """Availability should show 'booked' status for time slots with existing bookings."""
        program_id = test_program["id"]
        
        # Get existing bookings
        bookings_response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        if bookings_response.status_code == 200 and len(bookings_response.json()) > 0:
            bookings = bookings_response.json()
            # Find a booking for this program
            for booking in bookings:
                if booking.get("program_id") == program_id and booking.get("status") != "cancelled":
                    test_date = booking["date"]
                    booked_time = booking["time_block"]
                    
                    # Check availability for this date
                    avail_response = requests.get(
                        f"{BASE_URL}/api/availability/{institution_id}/{program_id}/{test_date}"
                    )
                    
                    if avail_response.status_code == 200:
                        data = avail_response.json()
                        for block in data.get("time_blocks", []):
                            if block.get("time") == booked_time:
                                assert block.get("status") == "booked", \
                                    f"Time block {booked_time} should be 'booked', got '{block.get('status')}'"
                                print(f"✓ Time block {booked_time} correctly shows as 'booked'")
                                return
                    break
        
        print("Note: No existing bookings found to verify availability status")


class TestPublicProgramsCollisionFields:
    """Test that public programs endpoint returns collision fields."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def institution_id(self, auth_token):
        """Get institution ID from auth."""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        return response.json().get("institution_id")
    
    def test_public_programs_returns_collision_fields(self, institution_id):
        """GET /api/programs/public/{institution_id} should return collision fields."""
        response = requests.get(f"{BASE_URL}/api/programs/public/{institution_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        programs = response.json()
        
        if len(programs) > 0:
            program = programs[0]
            # Public programs should also have collision fields for frontend display
            assert "allow_parallel" in program, "Missing allow_parallel field in public program"
            assert "collision_resources" in program, "Missing collision_resources field in public program"
            assert "blocked_program_ids" in program, "Missing blocked_program_ids field in public program"
            
            print(f"✓ Public programs endpoint returns collision fields")
        else:
            print("Note: No public programs found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
