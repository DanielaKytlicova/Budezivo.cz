"""Tests for Platform migration + Impersonation feature (iteration 54).

Covers:
  - POST /api/superadmin/setup/move-to-platform (idempotent)
  - POST /api/superadmin/impersonate/start/{user_id}
  - POST /api/superadmin/impersonate/stop
  - Impersonation token blocks superadmin endpoints (403 Czech)
  - GET /api/auth/me reflects impersonation state
  - Audit log contains impersonation_start and impersonation_end
  - DELETE /api/superadmin/institutions/{id} no longer blocked by "Nelze smazat vlastní instituci"
"""
import os
import base64
import json
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL")
assert BASE, "REACT_APP_BACKEND_URL must be set"
BASE = BASE.rstrip("/")

SUPERADMIN_EMAIL = "demo@budezivo.cz"
SUPERADMIN_PASSWORD = "Demo2026!"
TEST_MUZEUM_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"
IMPERSONATE_TARGET_USER_ID = "61751fe4-82ec-49e8-a339-7327360638a2"
IMPERSONATE_TARGET_EMAIL = "invited_6bbf94e7@budezivo.cz"


def _jwt_claims(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload + padding))
    except Exception:
        return {}


@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"superadmin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_headers(super_token):
    return {"Authorization": f"Bearer {super_token}"}


# ---------- Platform migration ----------

class TestPlatformMigration:
    def test_move_to_platform_idempotent(self, super_headers):
        # First call (may or may not create, depending on previous manual run)
        r1 = requests.post(f"{BASE}/api/superadmin/setup/move-to-platform", headers=super_headers, timeout=30)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert "platform_institution_id" in d1
        assert isinstance(d1["moved_users"], list)
        assert isinstance(d1["platform_created_now"], bool)

        # Second call MUST be idempotent
        r2 = requests.post(f"{BASE}/api/superadmin/setup/move-to-platform", headers=super_headers, timeout=30)
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        assert d2["platform_created_now"] is False, "Second call must not re-create platform"
        assert d2["moved_users"] == [], f"Second call must move nothing, got {d2['moved_users']}"
        assert d2["platform_institution_id"] == d1["platform_institution_id"]

    def test_platform_institution_has_correct_plan(self, super_headers):
        r = requests.get(f"{BASE}/api/superadmin/institutions", headers=super_headers, timeout=30)
        assert r.status_code == 200
        items = r.json().get("institutions") or r.json().get("items") or []
        platform = next((i for i in items if i.get("name") == "Budeživo Platform"), None)
        assert platform is not None, "Budeživo Platform institution must exist after migration"
        assert platform.get("plan") == "pro_plus"
        assert platform.get("plan_activated_by") == "system"

    def test_auth_me_after_migration_points_to_platform(self, super_headers):
        r = requests.get(f"{BASE}/api/auth/me", headers=super_headers, timeout=30)
        assert r.status_code == 200, r.text
        me = r.json()
        # Resolve institution_id to name via superadmin endpoint
        inst_id = me.get("institution_id") or (me.get("user") or {}).get("institution_id")
        assert inst_id, f"/auth/me missing institution_id: {me}"
        insts = requests.get(f"{BASE}/api/superadmin/institutions", headers=super_headers, timeout=30).json()
        items = insts.get("institutions") or insts.get("items") or []
        match = next((i for i in items if i.get("id") == inst_id), None)
        assert match is not None, f"institution {inst_id} not found in list"
        assert match.get("name") == "Budeživo Platform", \
            f"Expected Platform, got: {match.get('name')}"


# ---------- Delete institution no longer blocked ----------

class TestDeleteInstitutionUnblocked:
    def test_wrong_confirmation_name_returns_name_mismatch_not_own_institution(self, super_headers):
        # Sending wrong confirmation_name — we expect "Název instituce nesouhlasí"
        # (NOT "Nelze smazat vlastní instituci")
        r = requests.request(
            "DELETE",
            f"{BASE}/api/superadmin/institutions/{TEST_MUZEUM_ID}",
            headers=super_headers,
            json={"confirmation_name": "ZCELA_SPATNE_JMENO"},
            timeout=30,
        )
        assert r.status_code in (400, 403, 409, 422), r.text
        detail = (r.json().get("detail") or "").lower() if r.headers.get("content-type", "").startswith("application/json") else r.text.lower()
        assert "vlastní instituci" not in detail, f"Must no longer say 'Nelze smazat vlastní instituci', got: {detail}"
        assert ("nesouhlas" in detail or "název" in detail or "potvr" in detail), \
            f"Expected name-mismatch error, got: {detail}"


# ---------- Impersonation ----------

class TestImpersonationStartValidation:
    def test_non_existent_user_returns_404(self, super_headers):
        r = requests.post(
            f"{BASE}/api/superadmin/impersonate/start/00000000-0000-0000-0000-000000000000",
            headers=super_headers, json={"reason": "test"}, timeout=30,
        )
        assert r.status_code == 404

    def test_cannot_impersonate_other_superadmin(self, super_headers):
        # Easiest check: get demo's own user_id from /auth/me and try to impersonate self.
        # demo is in SUPERADMIN_EMAILS so the endpoint must 403.
        me = requests.get(f"{BASE}/api/auth/me", headers=super_headers, timeout=30).json()
        self_id = me.get("id") or (me.get("user") or {}).get("id")
        assert self_id, f"/auth/me missing id: {me}"
        r = requests.post(
            f"{BASE}/api/superadmin/impersonate/start/{self_id}",
            headers=super_headers, json={"reason": "test"}, timeout=30,
        )
        assert r.status_code == 403, r.text
        assert "superadmin" in r.json()["detail"].lower()


class TestImpersonationFullCycle:
    def test_full_impersonation_cycle(self, super_headers, super_token):
        # 1) Start impersonation
        r = requests.post(
            f"{BASE}/api/superadmin/impersonate/start/{IMPERSONATE_TARGET_USER_ID}",
            headers=super_headers, json={"reason": "TEST_impersonation_e2e"}, timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["target_email"] == IMPERSONATE_TARGET_EMAIL
        assert d["expires_in_minutes"] == 30
        imp_token = d["token"]
        assert imp_token and imp_token != super_token

        # 2) JWT claims contain impersonated_by_*
        claims = _jwt_claims(imp_token)
        assert claims.get("user_id") == IMPERSONATE_TARGET_USER_ID, claims
        assert claims.get("impersonated_by_email") == SUPERADMIN_EMAIL, claims
        assert claims.get("impersonated_by_user_id"), claims
        # 30-min expiry check: exp - iat ≈ 1800s (allow +-60)
        if "exp" in claims and "iat" in claims:
            assert 1700 < (claims["exp"] - claims["iat"]) < 1900, \
                f"expected ~1800s (30 min), got {claims['exp']-claims['iat']}"

        imp_headers = {"Authorization": f"Bearer {imp_token}"}

        # 3) /auth/me during impersonation
        me = requests.get(f"{BASE}/api/auth/me", headers=imp_headers, timeout=30)
        assert me.status_code == 200, me.text
        mj = me.json()
        imp_state = mj.get("impersonation") or {}
        assert imp_state.get("active") is True, mj
        assert imp_state.get("original_email") == SUPERADMIN_EMAIL
        # user identity should be the target
        assert (mj.get("user") or mj).get("email") == IMPERSONATE_TARGET_EMAIL

        # 4) Superadmin endpoint must be blocked while impersonating
        blocked = requests.get(f"{BASE}/api/superadmin/institutions", headers=imp_headers, timeout=30)
        assert blocked.status_code == 403, f"expected 403, got {blocked.status_code}: {blocked.text}"
        assert "impersonac" in blocked.json()["detail"].lower()

        # 5) Audit log contains impersonation_start
        audit = requests.get(f"{BASE}/api/superadmin/audit-log",
                             headers=super_headers, timeout=30)
        assert audit.status_code == 200, audit.text
        items = audit.json().get("items") or audit.json()
        starts = [it for it in items if it.get("action") == "impersonation_start"]
        assert starts, "No impersonation_start audit entry found"
        latest_start = starts[0]
        det = latest_start.get("details") or {}
        assert det.get("target_email") == IMPERSONATE_TARGET_EMAIL
        assert det.get("expires_in_minutes") == 30

        # 6) Stop impersonation (using impersonation token)
        stop = requests.post(f"{BASE}/api/superadmin/impersonate/stop",
                             headers=imp_headers, timeout=30)
        assert stop.status_code == 200, stop.text
        sj = stop.json()
        assert sj.get("restored_email") == SUPERADMIN_EMAIL
        assert sj.get("token") and sj["token"] != imp_token

        # Restored token must work as superadmin again
        restored_headers = {"Authorization": f"Bearer {sj['token']}"}
        ok = requests.get(f"{BASE}/api/superadmin/institutions", headers=restored_headers, timeout=30)
        assert ok.status_code == 200, ok.text

        # Auth/me with restored token shows impersonation inactive
        me2 = requests.get(f"{BASE}/api/auth/me", headers=restored_headers, timeout=30)
        imp2 = (me2.json().get("impersonation") or {})
        assert imp2.get("active") is False, me2.json()

        # 7) Audit log contains impersonation_end
        audit2 = requests.get(f"{BASE}/api/superadmin/audit-log",
                              headers=restored_headers, timeout=30).json()
        items2 = audit2.get("items") or audit2
        ends = [it for it in items2 if it.get("action") == "impersonation_end"]
        assert ends, "No impersonation_end audit entry found"

    def test_stop_without_impersonation_returns_400(self, super_headers):
        r = requests.post(f"{BASE}/api/superadmin/impersonate/stop",
                          headers=super_headers, timeout=30)
        assert r.status_code == 400, r.text
        assert "impersonac" in r.json()["detail"].lower()
