"""
Test suite for Mailing Campaign Module
Tests: CRUD operations, recipient preview, default templates, campaign sending
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


class TestMailingsCRUD:
    """Test mailing campaign CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        self.created_campaign_ids = []
        yield
        # Cleanup: delete created campaigns
        for cid in self.created_campaign_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/mailings/{cid}")
            except:
                pass
    
    def test_list_campaigns_empty_or_existing(self):
        """GET /api/mailings returns campaigns list"""
        response = self.session.get(f"{BASE_URL}/api/mailings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "campaigns" in data, "Response should contain 'campaigns' key"
        assert "count" in data, "Response should contain 'count' key"
        assert isinstance(data["campaigns"], list), "campaigns should be a list"
        print(f"PASS: GET /api/mailings returns {data['count']} campaigns")
    
    def test_create_draft_campaign(self):
        """POST /api/mailings creates a new draft campaign"""
        # First get a program ID to use
        programs_response = self.session.get(f"{BASE_URL}/api/programs")
        assert programs_response.status_code == 200
        programs = programs_response.json()
        if not programs or len(programs) == 0:
            pytest.skip("No programs available for testing")
        
        program_id = programs[0]["id"]
        
        payload = {
            "name": f"TEST_Campaign_{uuid.uuid4().hex[:8]}",
            "type": "single_program",
            "recipient_mode": "relevant_only",
            "program_ids": [program_id],
            "subject": "Test Subject",
            "greeting": "Dobrý den,",
            "intro_text": "Test intro text",
            "closing_text": "Test closing text",
            "signature": "Test signature"
        }
        
        response = self.session.post(f"{BASE_URL}/api/mailings", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain campaign ID"
        assert data["status"] == "draft", "New campaign should be in draft status"
        self.created_campaign_ids.append(data["id"])
        print(f"PASS: POST /api/mailings created campaign {data['id']}")
        return data["id"]
    
    def test_get_campaign_detail(self):
        """GET /api/mailings/{id} returns full campaign detail"""
        # Create a campaign first
        programs_response = self.session.get(f"{BASE_URL}/api/programs")
        programs = programs_response.json()
        if not programs:
            pytest.skip("No programs available")
        
        create_payload = {
            "name": f"TEST_Detail_{uuid.uuid4().hex[:8]}",
            "type": "seasonal",
            "recipient_mode": "all",
            "program_ids": [programs[0]["id"]],
            "subject": "Detail Test Subject"
        }
        create_response = self.session.post(f"{BASE_URL}/api/mailings", json=create_payload)
        assert create_response.status_code == 200
        campaign_id = create_response.json()["id"]
        self.created_campaign_ids.append(campaign_id)
        
        # Get detail
        response = self.session.get(f"{BASE_URL}/api/mailings/{campaign_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert data["id"] == campaign_id
        assert data["name"] == create_payload["name"]
        assert data["type"] == "seasonal"
        assert data["recipient_mode"] == "all"
        assert "programs" in data, "Should include programs list"
        assert "recipients" in data, "Should include recipients list"
        print(f"PASS: GET /api/mailings/{campaign_id} returns full detail with programs and recipients")
    
    def test_update_draft_campaign(self):
        """PUT /api/mailings/{id} updates a draft campaign"""
        # Create a campaign first
        programs_response = self.session.get(f"{BASE_URL}/api/programs")
        programs = programs_response.json()
        if not programs:
            pytest.skip("No programs available")
        
        create_payload = {
            "name": f"TEST_Update_{uuid.uuid4().hex[:8]}",
            "type": "single_program",
            "recipient_mode": "relevant_only",
            "program_ids": [programs[0]["id"]],
            "subject": "Original Subject"
        }
        create_response = self.session.post(f"{BASE_URL}/api/mailings", json=create_payload)
        assert create_response.status_code == 200
        campaign_id = create_response.json()["id"]
        self.created_campaign_ids.append(campaign_id)
        
        # Update
        update_payload = {
            "name": "Updated Campaign Name",
            "subject": "Updated Subject",
            "recipient_mode": "all"
        }
        response = self.session.put(f"{BASE_URL}/api/mailings/{campaign_id}", json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update
        detail_response = self.session.get(f"{BASE_URL}/api/mailings/{campaign_id}")
        detail = detail_response.json()
        assert detail["name"] == "Updated Campaign Name"
        assert detail["subject"] == "Updated Subject"
        assert detail["recipient_mode"] == "all"
        print(f"PASS: PUT /api/mailings/{campaign_id} updated campaign successfully")
    
    def test_delete_draft_campaign(self):
        """DELETE /api/mailings/{id} deletes a draft campaign"""
        # Create a campaign first
        programs_response = self.session.get(f"{BASE_URL}/api/programs")
        programs = programs_response.json()
        if not programs:
            pytest.skip("No programs available")
        
        create_payload = {
            "name": f"TEST_Delete_{uuid.uuid4().hex[:8]}",
            "type": "custom",
            "recipient_mode": "manual",
            "program_ids": [programs[0]["id"]]
        }
        create_response = self.session.post(f"{BASE_URL}/api/mailings", json=create_payload)
        assert create_response.status_code == 200
        campaign_id = create_response.json()["id"]
        
        # Delete
        response = self.session.delete(f"{BASE_URL}/api/mailings/{campaign_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        detail_response = self.session.get(f"{BASE_URL}/api/mailings/{campaign_id}")
        assert detail_response.status_code == 404, "Deleted campaign should return 404"
        print(f"PASS: DELETE /api/mailings/{campaign_id} deleted campaign successfully")


class TestMailingsRecipientPreview:
    """Test recipient preview functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_preview_recipients_relevant_only(self):
        """POST /api/mailings/preview-recipients returns relevant schools"""
        # Get a program with target_groups
        programs_response = self.session.get(f"{BASE_URL}/api/programs")
        programs = programs_response.json()
        if not programs:
            pytest.skip("No programs available")
        
        # Find a program with target_groups
        program_with_tg = None
        for p in programs:
            if p.get("target_groups") and len(p["target_groups"]) > 0:
                program_with_tg = p
                break
        
        if not program_with_tg:
            program_with_tg = programs[0]
        
        payload = {
            "program_ids": [program_with_tg["id"]],
            "recipient_mode": "relevant_only"
        }
        
        response = self.session.post(f"{BASE_URL}/api/mailings/preview-recipients", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "recipients" in data, "Should contain recipients list"
        assert "excluded" in data, "Should contain excluded list"
        assert "warnings" in data, "Should contain warnings list"
        assert "stats" in data, "Should contain stats object"
        
        stats = data["stats"]
        assert "total_schools" in stats
        assert "total_contacts" in stats
        assert "schools_no_tags" in stats
        assert "excluded_count" in stats
        
        print(f"PASS: preview-recipients returns {stats['total_contacts']} recipients, {stats['excluded_count']} excluded")
        print(f"  Warnings: {data['warnings']}")
    
    def test_preview_recipients_all_mode(self):
        """POST /api/mailings/preview-recipients with mode=all returns all schools"""
        programs_response = self.session.get(f"{BASE_URL}/api/programs")
        programs = programs_response.json()
        if not programs:
            pytest.skip("No programs available")
        
        payload = {
            "program_ids": [programs[0]["id"]],
            "recipient_mode": "all"
        }
        
        response = self.session.post(f"{BASE_URL}/api/mailings/preview-recipients", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # In 'all' mode, excluded should be empty or minimal
        print(f"PASS: preview-recipients (all mode) returns {data['stats']['total_contacts']} recipients")


class TestMailingsDefaultTemplates:
    """Test default Czech email templates"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_default_texts_ms(self):
        """POST /api/mailings/default-texts?audience=ms returns MŠ template"""
        response = self.session.post(f"{BASE_URL}/api/mailings/default-texts?audience=ms")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "subject" in data
        assert "greeting" in data
        assert "intro_text" in data
        assert "closing_text" in data
        assert "signature" in data
        
        # MŠ template should mention mateřské školy
        assert "mateřské" in data["subject"].lower() or "mš" in data["subject"].lower(), \
            f"MŠ template subject should mention mateřské školy: {data['subject']}"
        print(f"PASS: default-texts?audience=ms returns MŠ template")
        print(f"  Subject: {data['subject']}")
    
    def test_default_texts_zs(self):
        """POST /api/mailings/default-texts?audience=zs returns ZŠ template"""
        response = self.session.post(f"{BASE_URL}/api/mailings/default-texts?audience=zs")
        assert response.status_code == 200
        data = response.json()
        
        assert "základní" in data["subject"].lower() or "zš" in data["subject"].lower(), \
            f"ZŠ template subject should mention základní školy: {data['subject']}"
        print(f"PASS: default-texts?audience=zs returns ZŠ template")
    
    def test_default_texts_ss(self):
        """POST /api/mailings/default-texts?audience=ss returns SŠ template"""
        response = self.session.post(f"{BASE_URL}/api/mailings/default-texts?audience=ss")
        assert response.status_code == 200
        data = response.json()
        
        assert "střední" in data["subject"].lower() or "sš" in data["subject"].lower(), \
            f"SŠ template subject should mention střední školy: {data['subject']}"
        print(f"PASS: default-texts?audience=ss returns SŠ template")
    
    def test_default_texts_general(self):
        """POST /api/mailings/default-texts?audience=general returns general template"""
        response = self.session.post(f"{BASE_URL}/api/mailings/default-texts?audience=general")
        assert response.status_code == 200
        data = response.json()
        
        assert "subject" in data
        assert "signature" in data
        print(f"PASS: default-texts?audience=general returns general template")
    
    def test_all_templates_endpoint(self):
        """GET /api/mailings/templates/defaults returns all templates"""
        response = self.session.get(f"{BASE_URL}/api/mailings/templates/defaults")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "templates" in data
        templates = data["templates"]
        assert "ms" in templates, "Should have MŠ template"
        assert "zs" in templates, "Should have ZŠ template"
        assert "ss" in templates, "Should have SŠ template"
        assert "general" in templates, "Should have general template"
        print(f"PASS: templates/defaults returns all 4 templates")


class TestMailingsSend:
    """Test campaign sending functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and get session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        self.created_campaign_ids = []
        yield
        # Note: We don't delete sent campaigns as they're part of audit trail
    
    def test_send_campaign_creates_recipients(self):
        """POST /api/mailings/{id}/send triggers sending and creates recipient records"""
        # Get programs
        programs_response = self.session.get(f"{BASE_URL}/api/programs")
        programs = programs_response.json()
        if not programs:
            pytest.skip("No programs available")
        
        # Create campaign
        create_payload = {
            "name": f"TEST_Send_{uuid.uuid4().hex[:8]}",
            "type": "single_program",
            "recipient_mode": "all",  # Use 'all' to ensure we have recipients
            "program_ids": [programs[0]["id"]],
            "subject": "Test Send Subject",
            "greeting": "Dobrý den,",
            "intro_text": "Test intro",
            "closing_text": "Test closing",
            "signature": "Test signature"
        }
        create_response = self.session.post(f"{BASE_URL}/api/mailings", json=create_payload)
        assert create_response.status_code == 200
        campaign_id = create_response.json()["id"]
        self.created_campaign_ids.append(campaign_id)
        
        # Preview recipients first to check if we have any
        preview_response = self.session.post(f"{BASE_URL}/api/mailings/preview-recipients", json={
            "program_ids": [programs[0]["id"]],
            "recipient_mode": "all"
        })
        preview_data = preview_response.json()
        
        if preview_data["stats"]["total_contacts"] == 0:
            pytest.skip("No recipients available for sending test")
        
        # Send campaign
        send_response = self.session.post(f"{BASE_URL}/api/mailings/{campaign_id}/send", json={})
        assert send_response.status_code == 200, f"Expected 200, got {send_response.status_code}: {send_response.text}"
        send_data = send_response.json()
        
        assert "total_recipients" in send_data
        assert send_data["total_recipients"] > 0, "Should have at least one recipient"
        
        # Verify campaign status changed
        detail_response = self.session.get(f"{BASE_URL}/api/mailings/{campaign_id}")
        detail = detail_response.json()
        assert detail["status"] in ["sending", "sent", "partial", "failed"], \
            f"Campaign status should change after send, got: {detail['status']}"
        assert detail["total_recipients"] > 0
        assert "recipients" in detail and len(detail["recipients"]) > 0, \
            "Campaign should have recipient records after send"
        
        # Verify snapshots were created
        assert detail.get("content_snapshot"), "Should have content snapshot"
        assert detail.get("programs_snapshot"), "Should have programs snapshot"
        
        print(f"PASS: POST /api/mailings/{campaign_id}/send created {send_data['total_recipients']} recipient records")
        print(f"  Campaign status: {detail['status']}")
    
    def test_send_campaign_without_programs_fails(self):
        """POST /api/mailings/{id}/send fails if no programs"""
        # Create campaign without programs
        create_payload = {
            "name": f"TEST_NoPrograms_{uuid.uuid4().hex[:8]}",
            "type": "custom",
            "recipient_mode": "all",
            "program_ids": [],  # No programs
            "subject": "Test Subject"
        }
        create_response = self.session.post(f"{BASE_URL}/api/mailings", json=create_payload)
        assert create_response.status_code == 200
        campaign_id = create_response.json()["id"]
        self.created_campaign_ids.append(campaign_id)
        
        # Try to send
        send_response = self.session.post(f"{BASE_URL}/api/mailings/{campaign_id}/send", json={})
        assert send_response.status_code == 400, f"Expected 400, got {send_response.status_code}"
        print(f"PASS: Sending campaign without programs returns 400")


class TestMailingsAuth:
    """Test authentication requirements"""
    
    def test_list_campaigns_requires_auth(self):
        """GET /api/mailings requires authentication"""
        response = requests.get(f"{BASE_URL}/api/mailings")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: GET /api/mailings requires authentication")
    
    def test_create_campaign_requires_auth(self):
        """POST /api/mailings requires authentication"""
        response = requests.post(f"{BASE_URL}/api/mailings", json={"name": "Test"})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: POST /api/mailings requires authentication")
    
    def test_preview_recipients_requires_auth(self):
        """POST /api/mailings/preview-recipients requires authentication"""
        response = requests.post(f"{BASE_URL}/api/mailings/preview-recipients", json={
            "program_ids": [],
            "recipient_mode": "all"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: POST /api/mailings/preview-recipients requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
