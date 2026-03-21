"""
P1 Features Backend Tests for Budeživo.cz
Tests for:
1. Team Invitation UI integration (TeamPage.js backend APIs)
2. Feedback Statistics (StatisticsPage.js backend APIs)
3. Reminder emails scheduler (process_feedback_reminders)
"""
import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"


class TestAuthSetup:
    """Authentication setup for tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        # API returns 'token' not 'access_token'
        token = data.get("access_token") or data.get("token")
        assert token, "No token in response"
        return token
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}


class TestTeamInvitationAPIs(TestAuthSetup):
    """
    Tests for Team Invitation APIs used by TeamPage.js
    - POST /api/invitations/send
    - GET /api/invitations/pending
    - DELETE /api/invitations/{id}
    """
    
    def test_send_invitation_success(self, auth_headers):
        """Test sending a team invitation"""
        test_email = f"test_p1_{int(time.time())}@example.com"
        response = requests.post(
            f"{BASE_URL}/api/invitations/send",
            headers=auth_headers,
            json={
                "email": test_email,
                "name": "Test User P1",
                "role": "edukator"
            }
        )
        assert response.status_code == 200, f"Send invitation failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert data["email"] == test_email
        print(f"✓ Invitation sent to {test_email}")
    
    def test_send_invitation_all_roles(self, auth_headers):
        """Test sending invitations with all valid roles"""
        valid_roles = ["spravce", "edukator", "lektor", "pokladni"]
        
        for role in valid_roles:
            test_email = f"test_role_{role}_{int(time.time())}@example.com"
            response = requests.post(
                f"{BASE_URL}/api/invitations/send",
                headers=auth_headers,
                json={
                    "email": test_email,
                    "name": f"Test {role}",
                    "role": role
                }
            )
            assert response.status_code == 200, f"Send invitation with role {role} failed: {response.text}"
            print(f"✓ Invitation with role '{role}' sent successfully")
    
    def test_send_invitation_invalid_role(self, auth_headers):
        """Test sending invitation with invalid role"""
        response = requests.post(
            f"{BASE_URL}/api/invitations/send",
            headers=auth_headers,
            json={
                "email": "invalid_role@example.com",
                "name": "Invalid Role",
                "role": "invalid_role_xyz"
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid role, got {response.status_code}"
        print("✓ Invalid role correctly rejected")
    
    def test_get_pending_invitations(self, auth_headers):
        """Test getting pending invitations list"""
        response = requests.get(
            f"{BASE_URL}/api/invitations/pending",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get pending invitations failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Verify structure of invitation objects
        if len(data) > 0:
            invitation = data[0]
            assert "id" in invitation
            assert "email" in invitation
            assert "role" in invitation
            assert "expires_at" in invitation
            print(f"✓ Found {len(data)} pending invitations")
        else:
            print("✓ Pending invitations endpoint works (no pending invitations)")
    
    def test_cancel_invitation(self, auth_headers):
        """Test canceling a pending invitation"""
        # First create an invitation
        test_email = f"test_cancel_{int(time.time())}@example.com"
        create_response = requests.post(
            f"{BASE_URL}/api/invitations/send",
            headers=auth_headers,
            json={
                "email": test_email,
                "name": "To Cancel",
                "role": "lektor"
            }
        )
        assert create_response.status_code == 200
        
        # Get pending invitations to find the ID
        pending_response = requests.get(
            f"{BASE_URL}/api/invitations/pending",
            headers=auth_headers
        )
        assert pending_response.status_code == 200
        pending = pending_response.json()
        
        # Find our invitation
        invitation_id = None
        for inv in pending:
            if inv["email"] == test_email:
                invitation_id = inv["id"]
                break
        
        assert invitation_id is not None, f"Could not find invitation for {test_email}"
        
        # Cancel the invitation
        cancel_response = requests.delete(
            f"{BASE_URL}/api/invitations/{invitation_id}",
            headers=auth_headers
        )
        assert cancel_response.status_code == 200, f"Cancel invitation failed: {cancel_response.text}"
        print(f"✓ Invitation {invitation_id} cancelled successfully")
    
    def test_cancel_nonexistent_invitation(self, auth_headers):
        """Test canceling a non-existent invitation"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.delete(
            f"{BASE_URL}/api/invitations/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404 for non-existent invitation, got {response.status_code}"
        print("✓ Non-existent invitation correctly returns 404")
    
    def test_invitations_require_auth(self):
        """Test that invitation endpoints require authentication"""
        # Test send without auth
        response = requests.post(
            f"{BASE_URL}/api/invitations/send",
            json={"email": "test@example.com", "role": "edukator"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
        # Test pending without auth
        response = requests.get(f"{BASE_URL}/api/invitations/pending")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        
        print("✓ Invitation endpoints correctly require authentication")


class TestTeamAPIs(TestAuthSetup):
    """
    Tests for Team member APIs used by TeamPage.js
    - GET /api/team
    """
    
    def test_get_team_members(self, auth_headers):
        """Test getting team members list"""
        response = requests.get(
            f"{BASE_URL}/api/team",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get team members failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Should have at least the admin user
        assert len(data) >= 1, "Should have at least one team member"
        
        # Verify structure
        member = data[0]
        assert "id" in member
        assert "email" in member
        assert "role" in member
        print(f"✓ Found {len(data)} team members")


class TestFeedbackStatisticsAPIs(TestAuthSetup):
    """
    Tests for Feedback Statistics APIs used by StatisticsPage.js
    - GET /api/feedback/statistics
    """
    
    def test_get_feedback_statistics(self, auth_headers):
        """Test getting feedback statistics"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/statistics",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get feedback statistics failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "total_feedbacks" in data
        assert "average_rating" in data
        assert "recommendation_rate" in data
        assert "by_rating" in data
        assert "by_program" in data
        
        # Verify by_rating structure
        assert isinstance(data["by_rating"], dict)
        
        # Verify by_program structure
        assert isinstance(data["by_program"], list)
        
        print(f"✓ Feedback statistics: {data['total_feedbacks']} total feedbacks")
        if data["average_rating"]:
            print(f"  Average rating: {data['average_rating']}")
        if data["recommendation_rate"]:
            print(f"  Recommendation rate: {data['recommendation_rate']}%")
    
    def test_feedback_statistics_with_filters(self, auth_headers):
        """Test feedback statistics with date filters"""
        response = requests.get(
            f"{BASE_URL}/api/feedback/statistics",
            headers=auth_headers,
            params={
                "date_from": "2025-01-01",
                "date_to": "2026-12-31"
            }
        )
        assert response.status_code == 200, f"Get filtered feedback statistics failed: {response.text}"
        print("✓ Feedback statistics with date filters works")
    
    def test_feedback_statistics_require_auth(self):
        """Test that feedback statistics requires authentication"""
        response = requests.get(f"{BASE_URL}/api/feedback/statistics")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Feedback statistics correctly requires authentication")


class TestStatisticsAPIs(TestAuthSetup):
    """
    Tests for general Statistics APIs used by StatisticsPage.js
    - GET /api/statistics
    """
    
    def test_get_statistics_monthly(self, auth_headers):
        """Test getting monthly statistics"""
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers,
            params={
                "period_type": "month",
                "year": 2026,
                "month": 3
            }
        )
        assert response.status_code == 200, f"Get monthly statistics failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "overview" in data
        assert "period" in data
        
        overview = data["overview"]
        assert "total_bookings" in overview
        assert "total_students" in overview
        assert "total_teachers" in overview
        
        print(f"✓ Monthly statistics: {overview['total_bookings']} bookings")
    
    def test_get_statistics_school_year(self, auth_headers):
        """Test getting school year statistics"""
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers,
            params={
                "period_type": "school_year",
                "year": 2025
            }
        )
        assert response.status_code == 200, f"Get school year statistics failed: {response.text}"
        print("✓ School year statistics works")
    
    def test_get_statistics_semester(self, auth_headers):
        """Test getting semester statistics"""
        response = requests.get(
            f"{BASE_URL}/api/statistics",
            headers=auth_headers,
            params={
                "period_type": "semester",
                "year": 2025,
                "semester": 1
            }
        )
        assert response.status_code == 200, f"Get semester statistics failed: {response.text}"
        print("✓ Semester statistics works")


class TestSchedulerConfiguration:
    """
    Tests for scheduler configuration
    Verifies that the feedback reminder job is properly configured
    """
    
    def test_scheduler_module_exists(self):
        """Test that scheduler module exists and has required functions"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from scheduler import (
                process_completed_reservations,
                process_feedback_reminders,
                start_scheduler,
                stop_scheduler
            )
            print("✓ Scheduler module has all required functions")
            
            # Verify functions are callable
            assert callable(process_completed_reservations)
            assert callable(process_feedback_reminders)
            assert callable(start_scheduler)
            assert callable(stop_scheduler)
            print("✓ All scheduler functions are callable")
            
        except ImportError as e:
            pytest.fail(f"Failed to import scheduler functions: {e}")
    
    def test_reminder_email_function_exists(self):
        """Test that send_feedback_reminder_email function exists"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from scheduler import send_feedback_reminder_email
            assert callable(send_feedback_reminder_email)
            print("✓ send_feedback_reminder_email function exists and is callable")
        except ImportError as e:
            pytest.fail(f"Failed to import send_feedback_reminder_email: {e}")


class TestFeedbackModel:
    """
    Tests for Feedback model to verify reminder_sent_at field exists
    """
    
    def test_feedback_model_has_reminder_field(self):
        """Test that Feedback model has reminder_sent_at field"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from database.models import Feedback
            
            # Check that reminder_sent_at column exists
            columns = [c.name for c in Feedback.__table__.columns]
            assert 'reminder_sent_at' in columns, "Feedback model missing reminder_sent_at field"
            print("✓ Feedback model has reminder_sent_at field")
            
            # Check other required fields
            required_fields = ['email_sent_at', 'status', 'token', 'institution_id', 'reservation_id']
            for field in required_fields:
                assert field in columns, f"Feedback model missing {field} field"
            print("✓ Feedback model has all required fields")
            
        except ImportError as e:
            pytest.fail(f"Failed to import Feedback model: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
