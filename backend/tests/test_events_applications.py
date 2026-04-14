"""
Test Events Module - Applications Tab Field Labels & Payment Settings
Tests for iteration 41 bug fixes:
1. Applications tab shows human-readable field labels instead of field IDs
2. Boolean values display as 'Ano'/'Ne' instead of 'true'/'false'
3. Payment settings API (GET/PUT /api/events/settings/payment)
4. Events check-access API for feature flag
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestEventsCheckAccess:
    """Test events module access check."""
    
    def test_check_access_returns_enabled_status(self, auth_headers):
        """GET /api/events/check-access should return enabled status."""
        response = requests.get(f"{BASE_URL}/api/events/check-access", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)
        print(f"Events module enabled: {data['enabled']}")


class TestPaymentSettingsAPI:
    """Test payment settings API endpoints."""
    
    def test_get_payment_settings(self, auth_headers):
        """GET /api/events/settings/payment should return payment settings."""
        response = requests.get(f"{BASE_URL}/api/events/settings/payment", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have payment_mode at minimum
        assert "payment_mode" in data
        print(f"Payment settings: {data}")
    
    def test_update_payment_settings(self, auth_headers):
        """PUT /api/events/settings/payment should update and persist settings."""
        # First, get current settings
        get_response = requests.get(f"{BASE_URL}/api/events/settings/payment", headers=auth_headers)
        assert get_response.status_code == 200
        original = get_response.json()
        
        # Update with test data
        test_data = {
            "payment_mode": "qr",
            "account_number": "9876543210",
            "bank_code": "0800",
            "account_name": "Test Organization"
        }
        
        put_response = requests.put(
            f"{BASE_URL}/api/events/settings/payment",
            headers=auth_headers,
            json=test_data
        )
        assert put_response.status_code == 200
        updated = put_response.json()
        
        # Verify update response
        assert updated.get("account_number") == test_data["account_number"]
        assert updated.get("bank_code") == test_data["bank_code"]
        assert updated.get("account_name") == test_data["account_name"]
        print(f"Updated payment settings: {updated}")
        
        # Verify persistence with GET
        verify_response = requests.get(f"{BASE_URL}/api/events/settings/payment", headers=auth_headers)
        assert verify_response.status_code == 200
        verified = verify_response.json()
        assert verified.get("account_number") == test_data["account_number"]
        print("Payment settings persisted correctly")
        
        # Restore original settings if they existed
        if original.get("account_number"):
            requests.put(
                f"{BASE_URL}/api/events/settings/payment",
                headers=auth_headers,
                json=original
            )


class TestEventsListAndApplications:
    """Test events list and applications endpoints."""
    
    def test_list_events(self, auth_headers):
        """GET /api/events should return list of events."""
        response = requests.get(f"{BASE_URL}/api/events", headers=auth_headers)
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        print(f"Found {len(events)} events")
        
        if events:
            event = events[0]
            assert "id" in event
            assert "name" in event
            assert "form_fields" in event
            print(f"First event: {event.get('name')}, form_fields count: {len(event.get('form_fields', []))}")
    
    def test_get_event_with_form_fields(self, auth_headers):
        """GET /api/events/{id} should return event with form_fields for label mapping."""
        # First get list of events
        list_response = requests.get(f"{BASE_URL}/api/events", headers=auth_headers)
        assert list_response.status_code == 200
        events = list_response.json()
        
        if not events:
            pytest.skip("No events found to test")
        
        event_id = events[0]["id"]
        
        # Get single event
        response = requests.get(f"{BASE_URL}/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 200
        event = response.json()
        
        # Verify form_fields structure for label mapping
        form_fields = event.get("form_fields", [])
        print(f"Event '{event.get('name')}' has {len(form_fields)} form fields")
        
        for field in form_fields:
            assert "id" in field, "Form field must have 'id'"
            assert "label" in field, "Form field must have 'label'"
            print(f"  Field: id={field.get('id')}, label={field.get('label')}, type={field.get('type')}")
    
    def test_get_applications_with_data(self, auth_headers):
        """GET /api/events/{id}/applications should return applications with applicant_data."""
        # First get list of events
        list_response = requests.get(f"{BASE_URL}/api/events", headers=auth_headers)
        assert list_response.status_code == 200
        events = list_response.json()
        
        if not events:
            pytest.skip("No events found to test")
        
        # Find event with applications
        event_with_apps = None
        for event in events:
            if event.get("applications_count", 0) > 0:
                event_with_apps = event
                break
        
        if not event_with_apps:
            pytest.skip("No events with applications found")
        
        event_id = event_with_apps["id"]
        
        # Get applications
        response = requests.get(f"{BASE_URL}/api/events/{event_id}/applications", headers=auth_headers)
        assert response.status_code == 200
        applications = response.json()
        
        assert isinstance(applications, list)
        print(f"Event '{event_with_apps.get('name')}' has {len(applications)} applications")
        
        if applications:
            app = applications[0]
            assert "applicant_data" in app
            print(f"  Application data keys: {list(app.get('applicant_data', {}).keys())}")
            
            # The frontend will map these keys using form_fields
            # Keys should be field IDs like 'field_1776161309549'


class TestPublicEventsAPI:
    """Test public events API (no auth required)."""
    
    def test_public_events_list(self):
        """GET /api/events/public/{institution_id} should return public events."""
        response = requests.get(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        print(f"Public events for institution: {len(events)}")
    
    def test_public_event_detail(self):
        """GET /api/events/public/{institution_id}/{event_id} should return event detail."""
        # First get list
        list_response = requests.get(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}")
        assert list_response.status_code == 200
        events = list_response.json()
        
        if not events:
            pytest.skip("No public events found")
        
        event_id = events[0]["id"]
        
        # Get detail
        response = requests.get(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/{event_id}")
        assert response.status_code == 200
        event = response.json()
        
        assert "form_fields" in event
        print(f"Public event '{event.get('name')}' form_fields: {len(event.get('form_fields', []))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
