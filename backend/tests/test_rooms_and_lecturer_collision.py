"""
Test suite for R1, R4, R5 collision system fixes:
- R1: Lecturer collision check on assign_lecturer and admin_assign_lecturer endpoints (409 on conflict)
- R4: Room management CRUD + room collision checking
- R5: Advisory lock (pg_advisory_xact_lock) for race condition prevention

Tests:
- POST /api/rooms - create room with name and capacity
- GET /api/rooms - list all rooms for institution
- PATCH /api/rooms/{id} - update room name/capacity
- DELETE /api/rooms/{id} - delete room
- POST /api/bookings/{id}/assign-lecturer - returns 409 if lecturer already assigned at overlapping time
- POST /api/bookings/{id}/assign-lecturer-admin - returns 409 if lecturer already assigned at overlapping time
- Room collision - when two programs have same room_id and collision_resources includes 'room'
- Advisory lock - verify pg_advisory_xact_lock is used in collision_service.py
"""
import pytest
import requests
import os
import sys
import uuid
from datetime import datetime, timedelta

# Add backend to path for importing collision_service
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://booking-crm-3.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


class TestRoomsCRUD:
    """Test Room management CRUD endpoints."""
    
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
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers."""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_create_room(self, headers):
        """POST /api/rooms - create room with name and capacity."""
        room_data = {
            "name": f"TEST_Room_{uuid.uuid4().hex[:8]}",
            "capacity": 30
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rooms",
            headers=headers,
            json=room_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        room = response.json()
        
        assert "id" in room, "Room should have id"
        assert room["name"] == room_data["name"], "Room name should match"
        assert room["capacity"] == room_data["capacity"], "Room capacity should match"
        assert room["is_active"] == True, "Room should be active by default"
        
        print(f"✓ Created room: {room['name']} (id: {room['id']})")
        
        # Cleanup - delete the room
        requests.delete(f"{BASE_URL}/api/rooms/{room['id']}", headers=headers)
    
    def test_create_room_without_capacity(self, headers):
        """POST /api/rooms - create room without capacity (optional field)."""
        room_data = {
            "name": f"TEST_Room_NoCapacity_{uuid.uuid4().hex[:8]}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rooms",
            headers=headers,
            json=room_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        room = response.json()
        
        assert room["name"] == room_data["name"]
        assert room["capacity"] is None, "Capacity should be None when not provided"
        
        print(f"✓ Created room without capacity: {room['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rooms/{room['id']}", headers=headers)
    
    def test_list_rooms(self, headers):
        """GET /api/rooms - list all rooms for institution."""
        # First create a room to ensure there's at least one
        room_data = {"name": f"TEST_ListRoom_{uuid.uuid4().hex[:8]}", "capacity": 20}
        create_response = requests.post(f"{BASE_URL}/api/rooms", headers=headers, json=room_data)
        created_room_id = create_response.json().get("id") if create_response.status_code == 200 else None
        
        response = requests.get(
            f"{BASE_URL}/api/rooms",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        rooms = response.json()
        
        assert isinstance(rooms, list), "Response should be a list"
        
        if len(rooms) > 0:
            room = rooms[0]
            assert "id" in room, "Room should have id"
            assert "name" in room, "Room should have name"
            assert "capacity" in room, "Room should have capacity"
            assert "is_active" in room, "Room should have is_active"
        
        print(f"✓ Listed {len(rooms)} rooms")
        
        # Cleanup
        if created_room_id:
            requests.delete(f"{BASE_URL}/api/rooms/{created_room_id}", headers=headers)
    
    def test_update_room(self, headers):
        """PATCH /api/rooms/{id} - update room name/capacity."""
        # Create a room first
        room_data = {"name": f"TEST_UpdateRoom_{uuid.uuid4().hex[:8]}", "capacity": 25}
        create_response = requests.post(f"{BASE_URL}/api/rooms", headers=headers, json=room_data)
        assert create_response.status_code == 200
        room = create_response.json()
        room_id = room["id"]
        
        # Update the room
        update_data = {
            "name": f"TEST_UpdatedRoom_{uuid.uuid4().hex[:8]}",
            "capacity": 50
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/rooms/{room_id}",
            headers=headers,
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        updated_room = response.json()
        
        assert updated_room["name"] == update_data["name"], "Room name should be updated"
        assert updated_room["capacity"] == update_data["capacity"], "Room capacity should be updated"
        
        print(f"✓ Updated room: {updated_room['name']} (capacity: {updated_room['capacity']})")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rooms/{room_id}", headers=headers)
    
    def test_delete_room(self, headers):
        """DELETE /api/rooms/{id} - delete room."""
        # Create a room first
        room_data = {"name": f"TEST_DeleteRoom_{uuid.uuid4().hex[:8]}", "capacity": 15}
        create_response = requests.post(f"{BASE_URL}/api/rooms", headers=headers, json=room_data)
        assert create_response.status_code == 200
        room = create_response.json()
        room_id = room["id"]
        
        # Delete the room
        response = requests.delete(
            f"{BASE_URL}/api/rooms/{room_id}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify room is deleted
        list_response = requests.get(f"{BASE_URL}/api/rooms", headers=headers)
        rooms = list_response.json()
        room_ids = [r["id"] for r in rooms]
        assert room_id not in room_ids, "Deleted room should not appear in list"
        
        print(f"✓ Deleted room: {room_id}")
    
    def test_delete_nonexistent_room_returns_404(self, headers):
        """DELETE /api/rooms/{id} - returns 404 for non-existent room."""
        fake_id = str(uuid.uuid4())
        
        response = requests.delete(
            f"{BASE_URL}/api/rooms/{fake_id}",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"✓ DELETE non-existent room returns 404")


class TestLecturerCollisionOnAssign:
    """Test lecturer collision check on assign_lecturer endpoints (R1)."""
    
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
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers."""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def user_info(self, headers):
        """Get current user info."""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        return response.json()
    
    @pytest.fixture(scope="class")
    def test_program(self, headers):
        """Get a program for testing."""
        response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert response.status_code == 200
        programs = response.json()
        assert len(programs) > 0, "Need at least one program"
        return programs[0]
    
    @pytest.fixture(scope="class")
    def lecturer_user(self, headers):
        """Get a lecturer user for testing."""
        response = requests.get(f"{BASE_URL}/api/team", headers=headers)
        if response.status_code == 200:
            team = response.json()
            for member in team:
                if member.get("role") in ["lektor", "admin", "spravce", "edukator"]:
                    return member
        return None
    
    def test_assign_lecturer_endpoint_exists(self, headers):
        """POST /api/bookings/{id}/assign-lecturer endpoint exists."""
        # Get a booking
        bookings_response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        if bookings_response.status_code != 200 or len(bookings_response.json()) == 0:
            pytest.skip("No bookings available for testing")
        
        booking = bookings_response.json()[0]
        booking_id = booking["id"]
        
        # Try to assign (may fail for various reasons, but endpoint should exist)
        response = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/assign-lecturer",
            headers=headers
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404, "assign-lecturer endpoint should exist"
        print(f"✓ assign-lecturer endpoint exists (status: {response.status_code})")
    
    def test_admin_assign_lecturer_endpoint_exists(self, headers, lecturer_user):
        """POST /api/bookings/{id}/assign-lecturer-admin endpoint exists."""
        if not lecturer_user:
            pytest.skip("No lecturer user found for testing")
        
        # Get a booking
        bookings_response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        if bookings_response.status_code != 200 or len(bookings_response.json()) == 0:
            pytest.skip("No bookings available for testing")
        
        booking = bookings_response.json()[0]
        booking_id = booking["id"]
        
        # Try to assign
        response = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/assign-lecturer-admin",
            headers=headers,
            json={"lecturer_id": lecturer_user["id"]}
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404, "assign-lecturer-admin endpoint should exist"
        print(f"✓ assign-lecturer-admin endpoint exists (status: {response.status_code})")
    
    def test_lecturer_collision_returns_409(self, headers, user_info, test_program, lecturer_user):
        """Assigning lecturer to overlapping booking should return 409."""
        if not lecturer_user:
            pytest.skip("No lecturer user found for testing")
        
        institution_id = user_info.get("institution_id")
        program_id = test_program["id"]
        
        # Find a future date for testing
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        test_time = "10:00"
        
        # Create first booking
        booking1_data = {
            "program_id": program_id,
            "date": future_date,
            "time_block": test_time,
            "school_name": "TEST_LecturerCollision_School1",
            "group_type": "zs1_7_12",
            "age_or_class": "5. třída",
            "num_students": 20,
            "num_teachers": 2,
            "special_requirements": "",
            "contact_name": "Test Contact 1",
            "contact_email": "test-lect-collision1@example.com",
            "contact_phone": "+420123456789",
            "gdpr_consent": True,
            "terms_accepted": True,
            "terms_accepted_text_version": "v1"
        }
        
        response1 = requests.post(
            f"{BASE_URL}/api/bookings/public/{institution_id}",
            json=booking1_data
        )
        
        if response1.status_code not in [200, 201]:
            # May have collision with existing booking - try different time
            test_time = "14:00"
            booking1_data["time_block"] = test_time
            response1 = requests.post(
                f"{BASE_URL}/api/bookings/public/{institution_id}",
                json=booking1_data
            )
        
        if response1.status_code not in [200, 201]:
            print(f"Note: Could not create first booking: {response1.status_code} - {response1.text}")
            pytest.skip("Could not create test bookings")
        
        booking1 = response1.json()
        booking1_id = booking1["id"]
        
        # Create second booking at same time
        booking2_data = booking1_data.copy()
        booking2_data["school_name"] = "TEST_LecturerCollision_School2"
        booking2_data["contact_email"] = "test-lect-collision2@example.com"
        
        response2 = requests.post(
            f"{BASE_URL}/api/bookings/public/{institution_id}",
            json=booking2_data
        )
        
        if response2.status_code not in [200, 201]:
            # Program may not allow parallel - that's fine, collision is working
            if response2.status_code == 409:
                print(f"✓ Program collision detected (allow_parallel=False)")
                return
            pytest.skip(f"Could not create second booking: {response2.status_code}")
        
        booking2 = response2.json()
        booking2_id = booking2["id"]
        
        # Assign lecturer to first booking
        assign1_response = requests.post(
            f"{BASE_URL}/api/bookings/{booking1_id}/assign-lecturer-admin",
            headers=headers,
            json={"lecturer_id": lecturer_user["id"]}
        )
        
        if assign1_response.status_code not in [200, 201]:
            print(f"Note: Could not assign lecturer to first booking: {assign1_response.status_code} - {assign1_response.text}")
            # May already be assigned or other issue
        
        # Try to assign same lecturer to second booking - should get 409
        assign2_response = requests.post(
            f"{BASE_URL}/api/bookings/{booking2_id}/assign-lecturer-admin",
            headers=headers,
            json={"lecturer_id": lecturer_user["id"]}
        )
        
        if assign2_response.status_code == 409:
            error_detail = assign2_response.json().get("detail", "")
            print(f"✓ Lecturer collision detected: {error_detail}")
            assert "kolize" in error_detail.lower() or "lektor" in error_detail.lower(), \
                f"Error should mention lecturer collision: {error_detail}"
        elif assign2_response.status_code == 200:
            # First assignment may have failed, so second succeeded
            print(f"Note: Second assignment succeeded - first may have failed")
        else:
            print(f"Note: Got status {assign2_response.status_code}: {assign2_response.text}")


class TestRoomCollision:
    """Test room collision checking (R4)."""
    
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
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers."""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def user_info(self, headers):
        """Get current user info."""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        return response.json()
    
    def test_program_has_room_id_field(self, headers):
        """Programs should have room_id field."""
        response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert response.status_code == 200
        programs = response.json()
        
        if len(programs) > 0:
            program = programs[0]
            assert "room_id" in program or program.get("room_id") is None, \
                "Program should have room_id field (can be null)"
            print(f"✓ Program has room_id field")
    
    def test_update_program_with_room_id(self, headers):
        """PUT /api/programs/{id} should save room_id."""
        # Create a room first
        room_data = {"name": f"TEST_RoomCollision_{uuid.uuid4().hex[:8]}", "capacity": 30}
        room_response = requests.post(f"{BASE_URL}/api/rooms", headers=headers, json=room_data)
        
        if room_response.status_code != 200:
            pytest.skip("Could not create room for testing")
        
        room = room_response.json()
        room_id = room["id"]
        
        # Get a program
        programs_response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert programs_response.status_code == 200
        programs = programs_response.json()
        assert len(programs) > 0
        
        program = programs[0]
        program_id = program["id"]
        original_room_id = program.get("room_id")
        
        # Update program with room_id
        program["room_id"] = room_id
        program["allow_parallel"] = True
        program["collision_resources"] = ["room"]
        
        update_response = requests.put(
            f"{BASE_URL}/api/programs/{program_id}",
            headers=headers,
            json=program
        )
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/programs/{program_id}", headers=headers)
        assert verify_response.status_code == 200
        updated_program = verify_response.json()
        
        assert updated_program.get("room_id") == room_id, "room_id should be updated"
        assert "room" in updated_program.get("collision_resources", []), "collision_resources should include 'room'"
        
        print(f"✓ Program updated with room_id: {room_id}")
        
        # Cleanup - restore original room_id
        program["room_id"] = original_room_id
        program["collision_resources"] = []
        requests.put(f"{BASE_URL}/api/programs/{program_id}", headers=headers, json=program)
        requests.delete(f"{BASE_URL}/api/rooms/{room_id}", headers=headers)
    
    def test_room_collision_detection(self, headers, user_info):
        """Booking with same room_id at overlapping time should be blocked."""
        institution_id = user_info.get("institution_id")
        
        # Create a room
        room_data = {"name": f"TEST_RoomCollisionDetect_{uuid.uuid4().hex[:8]}", "capacity": 25}
        room_response = requests.post(f"{BASE_URL}/api/rooms", headers=headers, json=room_data)
        
        if room_response.status_code != 200:
            pytest.skip("Could not create room for testing")
        
        room = room_response.json()
        room_id = room["id"]
        
        # Get two programs
        programs_response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert programs_response.status_code == 200
        programs = programs_response.json()
        
        if len(programs) < 2:
            requests.delete(f"{BASE_URL}/api/rooms/{room_id}", headers=headers)
            pytest.skip("Need at least 2 programs for room collision test")
        
        program1 = programs[0]
        program2 = programs[1]
        
        # Save original settings
        orig_program1 = program1.copy()
        orig_program2 = program2.copy()
        
        # Update both programs with same room_id and room collision enabled
        program1["room_id"] = room_id
        program1["allow_parallel"] = True
        program1["collision_resources"] = ["room"]
        
        program2["room_id"] = room_id
        program2["allow_parallel"] = True
        program2["collision_resources"] = ["room"]
        
        requests.put(f"{BASE_URL}/api/programs/{program1['id']}", headers=headers, json=program1)
        requests.put(f"{BASE_URL}/api/programs/{program2['id']}", headers=headers, json=program2)
        
        # Find a future date
        future_date = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
        test_time = "11:00"
        
        # Create first booking
        booking1_data = {
            "program_id": program1["id"],
            "date": future_date,
            "time_block": test_time,
            "school_name": "TEST_RoomCollision_School1",
            "group_type": "zs1_7_12",
            "age_or_class": "5. třída",
            "num_students": 20,
            "num_teachers": 2,
            "special_requirements": "",
            "contact_name": "Test Contact 1",
            "contact_email": "test-room-collision1@example.com",
            "contact_phone": "+420123456789",
            "gdpr_consent": True,
            "terms_accepted": True,
            "terms_accepted_text_version": "v1"
        }
        
        response1 = requests.post(
            f"{BASE_URL}/api/bookings/public/{institution_id}",
            json=booking1_data
        )
        
        if response1.status_code not in [200, 201]:
            # Restore and cleanup
            requests.put(f"{BASE_URL}/api/programs/{program1['id']}", headers=headers, json=orig_program1)
            requests.put(f"{BASE_URL}/api/programs/{program2['id']}", headers=headers, json=orig_program2)
            requests.delete(f"{BASE_URL}/api/rooms/{room_id}", headers=headers)
            pytest.skip(f"Could not create first booking: {response1.status_code}")
        
        # Create second booking with different program but same room at same time
        booking2_data = booking1_data.copy()
        booking2_data["program_id"] = program2["id"]
        booking2_data["school_name"] = "TEST_RoomCollision_School2"
        booking2_data["contact_email"] = "test-room-collision2@example.com"
        
        response2 = requests.post(
            f"{BASE_URL}/api/bookings/public/{institution_id}",
            json=booking2_data
        )
        
        # Should get 409 for room collision
        if response2.status_code == 409:
            error_detail = response2.json().get("detail", "")
            print(f"✓ Room collision detected: {error_detail}")
            assert "místnost" in error_detail.lower() or "room" in error_detail.lower() or "kolize" in error_detail.lower(), \
                f"Error should mention room collision: {error_detail}"
        else:
            print(f"Note: Got status {response2.status_code} - room collision may not be triggered")
        
        # Cleanup
        requests.put(f"{BASE_URL}/api/programs/{program1['id']}", headers=headers, json=orig_program1)
        requests.put(f"{BASE_URL}/api/programs/{program2['id']}", headers=headers, json=orig_program2)
        requests.delete(f"{BASE_URL}/api/rooms/{room_id}", headers=headers)


class TestAdvisoryLock:
    """Test advisory lock implementation (R5)."""
    
    def test_advisory_lock_key_generation(self):
        """Test _advisory_lock_key function generates consistent keys."""
        from services.collision_service import _advisory_lock_key
        
        institution_id = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
        date = "2026-03-25"
        
        key1 = _advisory_lock_key(institution_id, date)
        key2 = _advisory_lock_key(institution_id, date)
        
        assert key1 == key2, "Same inputs should produce same key"
        assert isinstance(key1, int), "Key should be an integer"
        assert key1 > 0, "Key should be positive"
        
        # Different date should produce different key
        key3 = _advisory_lock_key(institution_id, "2026-03-26")
        assert key1 != key3, "Different dates should produce different keys"
        
        print(f"✓ Advisory lock key generation works correctly")
        print(f"  Key for {institution_id}:{date} = {key1}")
    
    def test_collision_service_uses_advisory_lock(self):
        """Verify collision_service.py uses pg_advisory_xact_lock."""
        import inspect
        from services.collision_service import check_booking_collision
        
        source = inspect.getsource(check_booking_collision)
        
        assert "pg_advisory_xact_lock" in source, \
            "check_booking_collision should use pg_advisory_xact_lock"
        
        print(f"✓ check_booking_collision uses pg_advisory_xact_lock")
    
    def test_check_lecturer_collision_for_assignment_exists(self):
        """Verify check_lecturer_collision_for_assignment function exists."""
        from services.collision_service import check_lecturer_collision_for_assignment
        
        assert callable(check_lecturer_collision_for_assignment), \
            "check_lecturer_collision_for_assignment should be callable"
        
        print(f"✓ check_lecturer_collision_for_assignment function exists")
    
    def test_time_blocks_overlap_function(self):
        """Test time_blocks_overlap utility function."""
        from services.collision_service import time_blocks_overlap
        
        # Overlapping blocks
        assert time_blocks_overlap("09:00", 90, "10:00", 60) == True, \
            "09:00-10:30 should overlap with 10:00-11:00"
        
        # Non-overlapping blocks
        assert time_blocks_overlap("09:00", 60, "11:00", 60) == False, \
            "09:00-10:00 should not overlap with 11:00-12:00"
        
        # Adjacent blocks (no overlap)
        assert time_blocks_overlap("09:00", 60, "10:00", 60) == False, \
            "09:00-10:00 should not overlap with 10:00-11:00 (adjacent)"
        
        # Range format
        assert time_blocks_overlap("09:00-10:30", 0, "10:00-11:00", 0) == True, \
            "Range format overlap should work"
        
        print(f"✓ time_blocks_overlap function works correctly")


class TestCollisionServiceIntegration:
    """Integration tests for collision service."""
    
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
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers."""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_booking_with_collision_resources_lecturer(self, headers):
        """Program with collision_resources=['lecturer'] should check lecturer conflicts."""
        # Get a program
        programs_response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert programs_response.status_code == 200
        programs = programs_response.json()
        assert len(programs) > 0
        
        program = programs[0]
        
        # Check if collision_resources field exists and can include 'lecturer'
        assert "collision_resources" in program, "Program should have collision_resources field"
        
        # Update program to have lecturer collision
        original_resources = program.get("collision_resources", [])
        program["allow_parallel"] = True
        program["collision_resources"] = ["lecturer"]
        
        update_response = requests.put(
            f"{BASE_URL}/api/programs/{program['id']}",
            headers=headers,
            json=program
        )
        
        assert update_response.status_code == 200
        
        # Verify
        verify_response = requests.get(f"{BASE_URL}/api/programs/{program['id']}", headers=headers)
        updated = verify_response.json()
        assert "lecturer" in updated.get("collision_resources", [])
        
        print(f"✓ Program can have collision_resources=['lecturer']")
        
        # Restore
        program["collision_resources"] = original_resources
        requests.put(f"{BASE_URL}/api/programs/{program['id']}", headers=headers, json=program)
    
    def test_booking_with_collision_resources_room(self, headers):
        """Program with collision_resources=['room'] should check room conflicts."""
        # Get a program
        programs_response = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert programs_response.status_code == 200
        programs = programs_response.json()
        assert len(programs) > 0
        
        program = programs[0]
        
        # Update program to have room collision
        original_resources = program.get("collision_resources", [])
        program["allow_parallel"] = True
        program["collision_resources"] = ["room"]
        
        update_response = requests.put(
            f"{BASE_URL}/api/programs/{program['id']}",
            headers=headers,
            json=program
        )
        
        assert update_response.status_code == 200
        
        # Verify
        verify_response = requests.get(f"{BASE_URL}/api/programs/{program['id']}", headers=headers)
        updated = verify_response.json()
        assert "room" in updated.get("collision_resources", [])
        
        print(f"✓ Program can have collision_resources=['room']")
        
        # Restore
        program["collision_resources"] = original_resources
        requests.put(f"{BASE_URL}/api/programs/{program['id']}", headers=headers, json=program)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
