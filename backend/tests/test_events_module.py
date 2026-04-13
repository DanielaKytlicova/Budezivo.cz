"""
Events Module API Tests (Pilot Feature)
Tests: Feature flags, Events CRUD, Event dates, Applications, Payments, Public endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with cookies."""
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


class TestFeatureFlag:
    """Feature flag check tests."""
    
    def test_check_access_requires_auth(self, api_client):
        """Feature flag check requires authentication."""
        # Create new session without auth
        new_session = requests.Session()
        response = new_session.get(f"{BASE_URL}/api/events/check-access")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: check-access requires auth")
    
    def test_check_access_returns_enabled_for_demo(self, auth_session):
        """Demo account should have events module enabled."""
        response = auth_session.get(f"{BASE_URL}/api/events/check-access")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "enabled" in data, "Response should contain 'enabled' field"
        assert data["enabled"] == True, f"Expected enabled=True for demo account, got {data['enabled']}"
        print(f"PASS: check-access returns enabled={data['enabled']} for demo account")


class TestEventsCRUD:
    """Events CRUD operations tests."""
    
    @pytest.fixture(scope="class")
    def test_event_id(self, auth_session):
        """Create a test event and return its ID."""
        response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Event_Pytest",
            "type": "event",
            "description": "Test event created by pytest",
            "capacity": 25,
            "price": 500.0,
            "currency": "CZK",
            "is_active": True,
            "form_fields": [
                {"id": "field_name", "type": "text", "label": "Jméno", "required": True},
                {"id": "field_email", "type": "email", "label": "Email", "required": True}
            ]
        })
        assert response.status_code == 200, f"Create event failed: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain 'id'"
        print(f"PASS: Created test event with ID: {data['id']}")
        yield data["id"]
        
        # Cleanup: Delete the test event
        auth_session.delete(f"{BASE_URL}/api/events/{data['id']}")
    
    def test_list_events(self, auth_session):
        """List events for institution."""
        response = auth_session.get(f"{BASE_URL}/api/events")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: Listed {len(data)} events")
    
    def test_create_event(self, auth_session, test_event_id):
        """Create event returns valid data."""
        # Event already created in fixture, verify it exists
        response = auth_session.get(f"{BASE_URL}/api/events/{test_event_id}")
        assert response.status_code == 200, f"Get event failed: {response.text}"
        data = response.json()
        assert data["name"] == "TEST_Event_Pytest"
        assert data["capacity"] == 25
        assert data["price"] == 500.0
        print("PASS: Created event has correct data")
    
    def test_get_event(self, auth_session, test_event_id):
        """Get single event with dates."""
        response = auth_session.get(f"{BASE_URL}/api/events/{test_event_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "dates" in data, "Response should include dates array"
        assert "applications_count" in data, "Response should include applications_count"
        print(f"PASS: Got event detail with {len(data.get('dates', []))} dates")
    
    def test_update_event(self, auth_session, test_event_id):
        """Update event and verify persistence."""
        # Update
        response = auth_session.put(f"{BASE_URL}/api/events/{test_event_id}", json={
            "name": "TEST_Event_Updated",
            "capacity": 30
        })
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        # Verify persistence
        get_response = auth_session.get(f"{BASE_URL}/api/events/{test_event_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["name"] == "TEST_Event_Updated", f"Name not updated: {data['name']}"
        assert data["capacity"] == 30, f"Capacity not updated: {data['capacity']}"
        print("PASS: Event updated and persisted correctly")
    
    def test_delete_event(self, auth_session):
        """Delete event and verify removal."""
        # Create event to delete
        create_response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Event_ToDelete",
            "type": "event"
        })
        assert create_response.status_code == 200
        event_id = create_response.json()["id"]
        
        # Delete
        delete_response = auth_session.delete(f"{BASE_URL}/api/events/{event_id}")
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify removal
        get_response = auth_session.get(f"{BASE_URL}/api/events/{event_id}")
        assert get_response.status_code == 404, "Event should not exist after deletion"
        print("PASS: Event deleted and verified removed")


class TestEventDates:
    """Event dates management tests."""
    
    @pytest.fixture(scope="class")
    def event_with_date(self, auth_session):
        """Create event with a date for testing."""
        # Create event
        event_response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Event_WithDates",
            "type": "camp",
            "capacity": 20,
            "price": 1000.0
        })
        assert event_response.status_code == 200
        event_id = event_response.json()["id"]
        
        # Add date
        date_response = auth_session.post(f"{BASE_URL}/api/events/{event_id}/dates", json={
            "start_datetime": "2026-07-01T09:00:00",
            "end_datetime": "2026-07-05T16:00:00",
            "capacity_override": 15
        })
        assert date_response.status_code == 200
        date_id = date_response.json()["id"]
        
        yield {"event_id": event_id, "date_id": date_id}
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/events/{event_id}")
    
    def test_add_event_date(self, auth_session, event_with_date):
        """Add date to event."""
        event_id = event_with_date["event_id"]
        response = auth_session.post(f"{BASE_URL}/api/events/{event_id}/dates", json={
            "start_datetime": "2026-08-01T09:00:00",
            "end_datetime": "2026-08-05T16:00:00"
        })
        assert response.status_code == 200, f"Add date failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "start_datetime" in data
        print(f"PASS: Added date with ID: {data['id']}")
    
    def test_remove_event_date(self, auth_session, event_with_date):
        """Remove date from event."""
        event_id = event_with_date["event_id"]
        
        # Add a date to remove
        add_response = auth_session.post(f"{BASE_URL}/api/events/{event_id}/dates", json={
            "start_datetime": "2026-09-01T09:00:00",
            "end_datetime": "2026-09-05T16:00:00"
        })
        assert add_response.status_code == 200
        date_id = add_response.json()["id"]
        
        # Remove it
        delete_response = auth_session.delete(f"{BASE_URL}/api/events/{event_id}/dates/{date_id}")
        assert delete_response.status_code == 200, f"Remove date failed: {delete_response.text}"
        print("PASS: Date removed successfully")


class TestPublicEndpoints:
    """Public endpoints tests (no auth required)."""
    
    def test_public_events_list(self):
        """Get public events for institution (no auth)."""
        response = requests.get(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: Public events list returned {len(data)} events")
        
        # Verify event structure
        if len(data) > 0:
            event = data[0]
            assert "id" in event
            assert "name" in event
            assert "dates" in event
            print(f"PASS: Public event has correct structure: {event['name']}")
    
    def test_public_event_detail(self, auth_session):
        """Get public event detail with spots_left."""
        # First get list to find an event
        list_response = requests.get(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}")
        assert list_response.status_code == 200
        events = list_response.json()
        
        if len(events) == 0:
            pytest.skip("No public events available for testing")
        
        event_id = events[0]["id"]
        response = requests.get(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/{event_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "id" in data
        assert "name" in data
        assert "dates" in data
        assert "form_fields" in data
        
        # Check dates have spots_left
        if len(data["dates"]) > 0:
            date = data["dates"][0]
            assert "spots_left" in date, "Date should have spots_left field"
            assert "capacity" in date, "Date should have capacity field"
            print(f"PASS: Public event detail has spots_left: {date['spots_left']}")
        else:
            print("PASS: Public event detail returned (no dates)")
    
    def test_public_events_404_for_invalid_institution(self):
        """Public events returns 404 for non-whitelisted institution."""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/events/public/{fake_id}")
        assert response.status_code == 404, f"Expected 404 for non-whitelisted institution, got {response.status_code}"
        print("PASS: Non-whitelisted institution returns 404")


class TestApplicationSubmission:
    """Application submission tests."""
    
    @pytest.fixture(scope="class")
    def event_for_application(self, auth_session):
        """Create event with date for application testing."""
        # Create event
        event_response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Event_ForApplication",
            "type": "event",
            "capacity": 10,
            "price": 250.0,
            "form_fields": [
                {"id": "field_jmeno", "type": "text", "label": "Jméno", "required": True},
                {"id": "field_email", "type": "email", "label": "Email", "required": True}
            ]
        })
        assert event_response.status_code == 200
        event_id = event_response.json()["id"]
        
        # Add date
        date_response = auth_session.post(f"{BASE_URL}/api/events/{event_id}/dates", json={
            "start_datetime": "2026-10-01T10:00:00",
            "end_datetime": "2026-10-01T18:00:00"
        })
        assert date_response.status_code == 200
        date_id = date_response.json()["id"]
        
        yield {"event_id": event_id, "date_id": date_id}
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/events/{event_id}")
    
    def test_submit_application(self, event_for_application):
        """Submit application creates record with variable_symbol and QR payload."""
        event_id = event_for_application["event_id"]
        date_id = event_for_application["date_id"]
        
        response = requests.post(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/apply", json={
            "event_id": event_id,
            "event_date_id": date_id,
            "applicant_data": {
                "field_jmeno": "Test Applicant",
                "field_email": "test@example.com"
            },
            "applicant_email": "test@example.com",
            "applicant_name": "Test Applicant"
        })
        assert response.status_code == 200, f"Submit application failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should have application ID"
        assert "variable_symbol" in data, "Response should have variable_symbol"
        assert len(data["variable_symbol"]) == 10, f"Variable symbol should be 10 digits: {data['variable_symbol']}"
        
        # QR payload should be present if payment settings exist
        if data.get("qr_payload"):
            assert "SPD*1.0" in data["qr_payload"], "QR payload should be SPD format"
            assert f"X-VS:{data['variable_symbol']}" in data["qr_payload"], "QR should contain variable symbol"
            print(f"PASS: Application submitted with QR payload: {data['qr_payload'][:50]}...")
        else:
            print("PASS: Application submitted (no payment settings configured)")
        
        print(f"PASS: Application created with VS: {data['variable_symbol']}")


class TestPaymentSettings:
    """Payment settings management tests."""
    
    def test_get_payment_settings(self, auth_session):
        """Get payment settings for institution."""
        response = auth_session.get(f"{BASE_URL}/api/events/settings/payment")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "payment_mode" in data, "Response should have payment_mode"
        print(f"PASS: Got payment settings: mode={data.get('payment_mode')}, account={data.get('account_number')}")
    
    def test_update_payment_settings(self, auth_session):
        """Update payment settings."""
        # Get current settings
        get_response = auth_session.get(f"{BASE_URL}/api/events/settings/payment")
        original = get_response.json()
        
        # Update
        response = auth_session.put(f"{BASE_URL}/api/events/settings/payment", json={
            "payment_mode": "qr",
            "account_number": "9999999999",
            "bank_code": "0800",
            "account_name": "Test Account"
        })
        assert response.status_code == 200, f"Update failed: {response.text}"
        data = response.json()
        assert data["account_number"] == "9999999999"
        assert data["bank_code"] == "0800"
        
        # Restore original if it existed
        if original.get("account_number"):
            auth_session.put(f"{BASE_URL}/api/events/settings/payment", json={
                "payment_mode": original.get("payment_mode", "qr"),
                "account_number": original.get("account_number"),
                "bank_code": original.get("bank_code"),
                "account_name": original.get("account_name")
            })
        
        print("PASS: Payment settings updated and verified")


class TestApplicationManagement:
    """Application management (admin) tests."""
    
    def test_list_applications(self, auth_session):
        """List applications for an event."""
        # Get events first
        events_response = auth_session.get(f"{BASE_URL}/api/events")
        events = events_response.json()
        
        if len(events) == 0:
            pytest.skip("No events available")
        
        event_id = events[0]["id"]
        response = auth_session.get(f"{BASE_URL}/api/events/{event_id}/applications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"PASS: Listed {len(data)} applications for event")
    
    def test_update_application_status(self, auth_session):
        """Update application status (approve/reject/mark-paid)."""
        # Create event with application
        event_response = auth_session.post(f"{BASE_URL}/api/events", json={
            "name": "TEST_Event_StatusTest",
            "type": "event",
            "price": 100.0
        })
        event_id = event_response.json()["id"]
        
        # Submit application
        app_response = requests.post(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/apply", json={
            "event_id": event_id,
            "applicant_name": "Status Test",
            "applicant_email": "status@test.com"
        })
        assert app_response.status_code == 200
        app_id = app_response.json()["id"]
        
        # Approve
        approve_response = auth_session.put(f"{BASE_URL}/api/events/applications/{app_id}/status", json={
            "status": "approved"
        })
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"
        print("PASS: Application approved")
        
        # Mark paid
        paid_response = auth_session.put(f"{BASE_URL}/api/events/applications/{app_id}/status", json={
            "payment_status": "paid"
        })
        assert paid_response.status_code == 200
        assert paid_response.json()["payment_status"] == "paid"
        print("PASS: Application marked as paid")
        
        # Cleanup
        auth_session.delete(f"{BASE_URL}/api/events/{event_id}")


class TestFeatureFlagIsolation:
    """Feature flag isolation tests."""
    
    def test_non_whitelisted_institution_blocked(self):
        """Non-whitelisted institution cannot access events API."""
        fake_institution_id = str(uuid.uuid4())
        
        # Public endpoint should return 404
        response = requests.get(f"{BASE_URL}/api/events/public/{fake_institution_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Non-whitelisted institution blocked from public events")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
