"""
Iteration 52 tests: Superadmin institution deletion, usage analytics,
plan-expiration manual trigger, PDF Czech font registration, and IBAN QR generation.
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SUPERADMIN_EMAIL = "demo@budezivo.cz"
SUPERADMIN_PASSWORD = "Demo2026!"


def _extract_institutions(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("institutions") or data.get("items") or []
    return []


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_session(session):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD},
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        # cookie-based auth path
        return session
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


# -------- Usage analytics --------

class TestUsageAnalytics:
    def test_usage_analytics_structure(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/superadmin/usage-analytics")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "total_institutions" in data
        assert "by_feature" in data
        assert "by_plan" in data
        assert "top_institutions" in data
        assert isinstance(data["by_feature"], list)
        assert isinstance(data["by_plan"], list)
        assert isinstance(data["top_institutions"], list)
        assert isinstance(data["total_institutions"], int)
        assert data["total_institutions"] >= 1

    def test_usage_analytics_unauth(self, session):
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/superadmin/usage-analytics")
        assert r.status_code in (401, 403)


# -------- Run expiration job --------

class TestExpirationJob:
    def test_run_expiration_job(self, auth_session):
        r = auth_session.post(f"{BASE_URL}/api/superadmin/run-expiration-job")
        assert r.status_code == 200, r.text
        assert "message" in r.json()

    def test_run_expiration_job_unauth(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/superadmin/run-expiration-job")
        assert r.status_code in (401, 403)


# -------- Institution soft delete --------

class TestInstitutionDelete:
    @pytest.fixture(scope="class")
    def target_inst(self, auth_session):
        """Create a throwaway institution via signup for deletion test."""
        uniq = uuid.uuid4().hex[:8]
        email = f"TEST_del_{uniq}@example.com"
        inst_name = f"TEST_DeleteInst_{uniq}"
        # Create by signup (public endpoint)
        s = requests.Session()
        r = s.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": email,
                "password": "TestPass123!",
                "institution_name": inst_name,
                "institution_type": "museum",
                "country": "CZ",
                "name": "Test User",
            },
        )
        if r.status_code not in (200, 201):
            pytest.skip(f"Cannot create test institution via register: {r.status_code} {r.text}")
        # Find institution id via superadmin list
        list_r = auth_session.get(f"{BASE_URL}/api/superadmin/institutions")
        assert list_r.status_code == 200
        insts = _extract_institutions(list_r.json())
        matches = [i for i in insts if i.get("name") == inst_name]
        assert matches, f"Could not find created institution {inst_name}"
        return {"id": matches[0]["id"], "name": inst_name}

    def test_delete_404_for_missing(self, auth_session):
        r = auth_session.request(
            "DELETE",
            f"{BASE_URL}/api/superadmin/institutions/00000000-0000-0000-0000-000000000000",
            json={"confirmation_name": "whatever", "reason": "test"},
        )
        assert r.status_code == 404

    def test_delete_own_institution_blocked(self, auth_session):
        # superadmin's own institution is "Test Muzeum"
        list_r = auth_session.get(f"{BASE_URL}/api/superadmin/institutions")
        assert list_r.status_code == 200
        insts = _extract_institutions(list_r.json())
        own = [i for i in insts if i.get("name") == "Test Muzeum"]
        assert own, "Own institution 'Test Muzeum' not found"
        r = auth_session.request(
            "DELETE",
            f"{BASE_URL}/api/superadmin/institutions/{own[0]['id']}",
            json={"confirmation_name": "Test Muzeum", "reason": "should be blocked"},
        )
        assert r.status_code == 400
        assert "vlastní" in r.text.lower() or "own" in r.text.lower()

    def test_delete_wrong_confirmation_name(self, auth_session, target_inst):
        r = auth_session.request(
            "DELETE",
            f"{BASE_URL}/api/superadmin/institutions/{target_inst['id']}",
            json={"confirmation_name": "WRONG_NAME", "reason": "test"},
        )
        assert r.status_code == 400

    def test_delete_success_and_filtered(self, auth_session, target_inst):
        r = auth_session.request(
            "DELETE",
            f"{BASE_URL}/api/superadmin/institutions/{target_inst['id']}",
            json={"confirmation_name": target_inst["name"], "reason": "automated test"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("institution_id") == target_inst["id"]
        assert "deleted_at" in data

        # Verify institution is filtered from list
        list_r = auth_session.get(f"{BASE_URL}/api/superadmin/institutions")
        assert list_r.status_code == 200
        insts = _extract_institutions(list_r.json())
        assert not any(i["id"] == target_inst["id"] for i in insts)

    def test_delete_already_deleted(self, auth_session, target_inst):
        r = auth_session.request(
            "DELETE",
            f"{BASE_URL}/api/superadmin/institutions/{target_inst['id']}",
            json={"confirmation_name": target_inst["name"], "reason": "again"},
        )
        # After delete, institution is filtered out -> 404
        assert r.status_code in (400, 404)


# -------- PDF font + IBAN generation (direct import) --------

class TestExportService:
    def test_font_registered(self):
        from services import export_service
        assert export_service._FONT_BASE == "DejaVuSans", (
            f"Expected DejaVuSans registered font, got {export_service._FONT_BASE}. "
            "Czech diacritics will break."
        )

    def test_cz_iban_generation(self):
        from services.export_service import cz_account_to_iban
        iban = cz_account_to_iban("295033917", "0300")
        assert iban == "CZ6003000000000295033917", f"Expected CZ6003000000000295033917, got {iban}"

    def test_cz_iban_with_prefix(self):
        from services.export_service import cz_account_to_iban
        iban = cz_account_to_iban("19-123457", "0100")
        assert iban.startswith("CZ")
        assert len(iban) == 24

    def test_cz_iban_empty(self):
        from services.export_service import cz_account_to_iban
        assert cz_account_to_iban("", "0300") == ""
        assert cz_account_to_iban("123", "") == ""
