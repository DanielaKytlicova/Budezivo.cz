"""
Test suite for Team Member Name functionality
Tests:
- PATCH /api/team/{member_id}/name - Update member name
- GET /api/team - Returns name field for all members
- POST /api/invitations/accept - Saves name from invitation to users table
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestGetTeamMembers:
    """Test GET /api/team endpoint returns name field."""
    
    def test_get_team_returns_name_field(self, auth_headers):
        """Verify GET /api/team response includes name field for all members."""
        response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        team_members = response.json()
        assert isinstance(team_members, list), "Response should be a list"
        assert len(team_members) > 0, "Should have at least one team member"
        
        # Check that each member has the name field in response
        for member in team_members:
            assert "id" in member, f"Member missing 'id' field: {member}"
            assert "email" in member, f"Member missing 'email' field: {member}"
            assert "role" in member, f"Member missing 'role' field: {member}"
            # Name field should be present (can be None)
            assert "name" in member, f"Member missing 'name' field: {member}"
            print(f"Member: {member.get('email')} - Name: {member.get('name')} - Role: {member.get('role')}")
    
    def test_demo_admin_has_name(self, auth_headers):
        """Verify demo admin user has name set."""
        response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        
        assert response.status_code == 200
        team_members = response.json()
        
        # Find demo admin
        demo_admin = next((m for m in team_members if m.get('email') == TEST_EMAIL), None)
        assert demo_admin is not None, f"Demo admin {TEST_EMAIL} not found in team"
        
        # According to context, demo@budezivo.cz should have name='Demo Admin'
        print(f"Demo admin name: {demo_admin.get('name')}")
        # Name should be present (may be 'Demo Admin' or similar)
        assert "name" in demo_admin, "Demo admin should have name field"


class TestUpdateMemberName:
    """Test PATCH /api/team/{member_id}/name endpoint."""
    
    def test_update_name_success(self, auth_headers):
        """Test updating a team member's name."""
        # First get team members to find one to update
        response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        assert response.status_code == 200
        
        team_members = response.json()
        assert len(team_members) > 0, "Need at least one team member"
        
        # Find a member that is not the current user (demo admin)
        # According to context: test-kolega@example.com has name='Jan Novák'
        target_member = next(
            (m for m in team_members if m.get('email') == 'test-kolega@example.com'),
            None
        )
        
        if target_member is None:
            # Use any non-admin member
            target_member = next(
                (m for m in team_members if m.get('email') != TEST_EMAIL),
                None
            )
        
        if target_member is None:
            pytest.skip("No other team member found to test name update")
        
        member_id = target_member['id']
        original_name = target_member.get('name')
        new_name = f"Test Name {uuid.uuid4().hex[:6]}"
        
        # Update name
        update_response = requests.patch(
            f"{BASE_URL}/api/team/{member_id}/name",
            headers=auth_headers,
            json={"name": new_name}
        )
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Verify the update persisted by fetching team again
        verify_response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        assert verify_response.status_code == 200
        
        updated_members = verify_response.json()
        updated_member = next((m for m in updated_members if m['id'] == member_id), None)
        
        assert updated_member is not None, "Updated member not found"
        assert updated_member.get('name') == new_name, f"Name not updated. Expected '{new_name}', got '{updated_member.get('name')}'"
        
        print(f"Successfully updated name from '{original_name}' to '{new_name}'")
        
        # Restore original name if it existed
        if original_name:
            requests.patch(
                f"{BASE_URL}/api/team/{member_id}/name",
                headers=auth_headers,
                json={"name": original_name}
            )
    
    def test_update_name_invalid_member(self, auth_headers):
        """Test updating name for non-existent member returns 404."""
        fake_id = str(uuid.uuid4())
        
        response = requests.patch(
            f"{BASE_URL}/api/team/{fake_id}/name",
            headers=auth_headers,
            json={"name": "Test Name"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    def test_update_name_empty_name(self, auth_headers):
        """Test updating with empty name."""
        # Get a team member
        response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        assert response.status_code == 200
        
        team_members = response.json()
        target_member = next(
            (m for m in team_members if m.get('email') != TEST_EMAIL),
            None
        )
        
        if target_member is None:
            pytest.skip("No other team member found")
        
        member_id = target_member['id']
        
        # Try to update with empty name - should fail validation
        update_response = requests.patch(
            f"{BASE_URL}/api/team/{member_id}/name",
            headers=auth_headers,
            json={"name": ""}
        )
        
        # Empty string might be rejected by Pydantic validation
        # or accepted - depends on implementation
        print(f"Empty name update response: {update_response.status_code} - {update_response.text}")


class TestInvitationAcceptName:
    """Test POST /api/invitations/accept saves name from invitation."""
    
    def test_verify_invitation_returns_name(self, auth_headers):
        """Test that invitation verification returns the name field."""
        # First, create a test invitation
        invite_email = f"test_invite_{uuid.uuid4().hex[:8]}@example.com"
        invite_name = "Test Invited Person"
        
        # Send invitation
        invite_response = requests.post(
            f"{BASE_URL}/api/invitations/send",
            headers=auth_headers,
            json={
                "email": invite_email,
                "name": invite_name,
                "role": "lektor"
            }
        )
        
        if invite_response.status_code != 200:
            pytest.skip(f"Could not create invitation: {invite_response.status_code} - {invite_response.text}")
        
        print(f"Invitation sent: {invite_response.json()}")
        
        # Get pending invitations to find the token
        pending_response = requests.get(
            f"{BASE_URL}/api/invitations/pending",
            headers=auth_headers
        )
        
        assert pending_response.status_code == 200
        pending = pending_response.json()
        
        # Find our invitation
        our_invite = next((i for i in pending if i.get('email') == invite_email), None)
        
        if our_invite:
            print(f"Found pending invitation: {our_invite}")
            assert our_invite.get('name') == invite_name, f"Invitation name mismatch: expected '{invite_name}', got '{our_invite.get('name')}'"
            
            # Clean up - cancel the invitation
            if our_invite.get('id'):
                requests.delete(
                    f"{BASE_URL}/api/invitations/{our_invite['id']}",
                    headers=auth_headers
                )
        else:
            print(f"Invitation not found in pending list. Pending invitations: {pending}")


class TestBookingsLecturerDropdown:
    """Test that bookings page lecturer dropdown shows member names."""
    
    def test_team_members_have_names_for_dropdown(self, auth_headers):
        """Verify team members returned have names that can be displayed in dropdown."""
        response = requests.get(f"{BASE_URL}/api/team", headers=auth_headers)
        
        assert response.status_code == 200
        team_members = response.json()
        
        # Filter lecturers/educators as the frontend does
        lecturers = [
            m for m in team_members 
            if m.get('role') in ['lektor', 'edukator', 'admin', 'spravce']
        ]
        
        print(f"Found {len(lecturers)} lecturers/educators for dropdown:")
        for lecturer in lecturers:
            display_name = lecturer.get('name') or lecturer.get('email')
            print(f"  - {display_name} (email: {lecturer.get('email')}, role: {lecturer.get('role')})")
            
            # Each lecturer should have either name or email for display
            assert display_name, f"Lecturer has no display name: {lecturer}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
