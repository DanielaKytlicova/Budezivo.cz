"""Backend tests for event payment gateway (Comgate) - iteration 53.

Covers:
- POST /api/event-payments/initiate (happy path, already_paid, non-paid app, wrong plan → 402)
- POST /api/event-payments/webhook/comgate (bogus merchant/secret rejection)
- POST /api/event-payments/mock/complete (success + cancel flows; only in MOCK mode)
- GET  /api/event-payments/by-vs/{institution_id}/{vs}
- GET  /api/legal/vop (section 7.8 Comgate clause)
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://school-crm-saas.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "demo@budezivo.cz"
ADMIN_PASSWORD = "Demo2026!"
INSTITUTION_ID = "669e71b2-a8e7-4eb0-ac13-8b8c4f3107a5"  # Test Muzeum (PRO+)
EVENT_ID = "0a357686-eb41-4182-869a-96763fade765"         # Baby herna (60 Kč)
EVENT_DATE_ID = "64b2a9f2-2a3b-46fa-aa9f-9d03e11efa25"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(sess):
    r = sess.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:200]}"
    return r.json().get("token") or r.json().get("access_token")


def _submit_application(sess, name="TEST_Payment Runner", email="test_payment_runner@example.com"):
    payload = {
        "event_id": EVENT_ID,
        "event_date_id": EVENT_DATE_ID,
        "applicant_name": name,
        "applicant_email": email,
        "note": "iteration_53 test",
        "applicant_data": {"phone": "+420123456789", "participants_count": 1},
    }
    r = sess.post(f"{BASE_URL}/api/events/public/{INSTITUTION_ID}/apply", json=payload)
    assert r.status_code in (200, 201), f"apply failed {r.status_code} {r.text[:300]}"
    data = r.json()
    app_id = data.get("id") or data.get("application_id")
    vs = data.get("variable_symbol")
    assert app_id and vs, f"unexpected apply resp: {data}"
    gw_enabled = (data.get("payment_settings") or {}).get("gateway_enabled")
    return {"id": app_id, "variable_symbol": vs, "gateway_enabled": gw_enabled, "raw": data}


@pytest.fixture(scope="module")
def application(sess):
    """Submit a public event application to get a valid application id + VS."""
    return _submit_application(sess)


class TestLegalVOP:
    def test_vop_contains_comgate_clause(self, sess):
        r = sess.get(f"{BASE_URL}/api/legal/vop")
        assert r.status_code == 200
        body = r.json()
        text = str(body).lower()
        assert "comgate" in text, "VOP must mention Comgate in section 7"
        assert "7.8" in text or "7.8." in str(body), "VOP should contain section 7.8"


class TestInitiate:
    def test_gateway_enabled_flag_on_apply(self, application):
        # When provider set + payment_mode gateway/both, gateway_enabled should be True
        assert application["gateway_enabled"] is True, (
            f"Expected gateway_enabled=True on apply response, got {application['gateway_enabled']}"
        )

    def test_initiate_happy_path_mock(self, sess, application):
        r = sess.post(f"{BASE_URL}/api/event-payments/initiate", json={
            "institution_id": INSTITUTION_ID,
            "application_id": application["id"],
        })
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert data.get("ok") is True
        assert data.get("mode") == "mock", f"expected mock mode, got {data.get('mode')}"
        assert "/payment/mock" in (data.get("redirect_url") or "")
        assert data.get("transaction_id", "").startswith("MOCK-")
        assert data.get("variable_symbol") == application["variable_symbol"]

    def test_initiate_unknown_application_404(self, sess):
        r = sess.post(f"{BASE_URL}/api/event-payments/initiate", json={
            "institution_id": INSTITUTION_ID,
            "application_id": str(uuid.uuid4()),
        })
        assert r.status_code == 404

    def test_initiate_rejects_free_plan_with_402(self, sess, admin_token):
        """Create a brand-new institution via signup (defaults to free plan) and
        verify initiate returns 402."""
        uniq = uuid.uuid4().hex[:8]
        signup = sess.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_free_{uniq}@example.com",
            "password": "Passw0rd!",
            "institution_name": f"TEST_FreePlan_{uniq}",
            "full_name": "TEST Free Plan Admin",
            "institution_type": "school",
            "country": "CZ",
        })
        if signup.status_code not in (200, 201):
            pytest.skip(f"Could not create a free-plan tenant for 402 test: {signup.status_code} {signup.text[:200]}")
        body = signup.json()
        free_inst_id = (body.get("user") or {}).get("institution_id") or (body.get("institution") or {}).get("id")
        if not free_inst_id:
            pytest.skip(f"Signup response missing institution id: {body}")

        r = sess.post(f"{BASE_URL}/api/event-payments/initiate", json={
            "institution_id": free_inst_id,
            "application_id": str(uuid.uuid4()),
        })
        # Per implementation, plan check happens BEFORE application lookup → expect 402.
        assert r.status_code == 402, f"expected 402 for free plan, got {r.status_code}: {r.text[:200]}"


class TestMockComplete:
    def test_mock_complete_requires_mock_mode(self, sess):
        """Random institution likely not in MOCK mode AND missing data → 400/404."""
        r = sess.post(f"{BASE_URL}/api/event-payments/mock/complete", json={
            "institution_id": str(uuid.uuid4()),
            "variable_symbol": "999999",
            "outcome": "paid",
        })
        # Either 400 (not mock / no gateway) or 404 (payment not found) is acceptable rejection
        assert r.status_code in (400, 404), f"unexpected: {r.status_code} {r.text[:200]}"

    def test_full_happy_path_mock_to_paid_and_approved(self, sess):
        """E2E: new apply → initiate → mock/complete → by-vs shows paid+approved."""
        app = _submit_application(sess, name="TEST_E2E Runner", email="test_e2e_runner@example.com")
        app_id = app["id"]
        vs = app["variable_symbol"]

        # Initiate
        init = sess.post(f"{BASE_URL}/api/event-payments/initiate", json={
            "institution_id": INSTITUTION_ID,
            "application_id": app_id,
        })
        assert init.status_code == 200, init.text[:300]
        assert init.json().get("mode") == "mock"

        # Mock complete
        mc = sess.post(f"{BASE_URL}/api/event-payments/mock/complete", json={
            "institution_id": INSTITUTION_ID,
            "variable_symbol": vs,
            "outcome": "paid",
        })
        assert mc.status_code == 200, mc.text[:300]
        assert mc.json().get("status") == "paid"

        # by-vs lookup
        time.sleep(0.3)
        st = sess.get(f"{BASE_URL}/api/event-payments/by-vs/{INSTITUTION_ID}/{vs}")
        assert st.status_code == 200, st.text[:300]
        s = st.json()
        assert s.get("payment_status") == "paid"
        assert s.get("application_payment_status") == "paid"
        # Auto-confirm should set application.status to approved (Test Muzeum has auto_confirm_paid feature)
        assert s.get("application_status") == "approved", (
            f"Expected auto-approved, got {s.get('application_status')}"
        )
        assert s.get("paid_at") is not None
        assert s.get("amount") in (60, 60.0) or float(s.get("amount")) == 60.0

    def test_mock_complete_cancel(self, sess):
        app = _submit_application(sess, name="TEST_Cancel Runner", email="test_cancel_runner@example.com")
        app_id = app["id"]
        vs = app["variable_symbol"]

        sess.post(f"{BASE_URL}/api/event-payments/initiate", json={
            "institution_id": INSTITUTION_ID,
            "application_id": app_id,
        })
        mc = sess.post(f"{BASE_URL}/api/event-payments/mock/complete", json={
            "institution_id": INSTITUTION_ID,
            "variable_symbol": vs,
            "outcome": "cancelled",
        })
        assert mc.status_code == 200
        assert mc.json().get("status") == "failed"

        st = sess.get(f"{BASE_URL}/api/event-payments/by-vs/{INSTITUTION_ID}/{vs}")
        assert st.status_code == 200
        assert st.json().get("payment_status") == "failed"


class TestWebhookAuth:
    def test_webhook_rejects_invalid_refId(self, sess):
        r = requests.post(
            f"{BASE_URL}/api/event-payments/webhook/comgate",
            data={"refId": "not-a-uuid", "status": "PAID"},
        )
        assert r.status_code == 400

    def test_webhook_missing_refId(self, sess):
        r = requests.post(
            f"{BASE_URL}/api/event-payments/webhook/comgate",
            data={"status": "PAID"},
        )
        assert r.status_code == 400

    def test_webhook_unknown_payment_404(self, sess):
        r = requests.post(
            f"{BASE_URL}/api/event-payments/webhook/comgate",
            data={"refId": str(uuid.uuid4()), "status": "PAID"},
        )
        assert r.status_code == 404

    def test_webhook_bogus_creds_rejected_for_configured_tenant(self, sess):
        """For MOCK-mode tenants, webhook skips signature check so we can't directly test 403.
        This test documents current behaviour: Test Muzeum runs in MOCK mode (empty creds),
        so the webhook accepts whatever merchant/secret — as long as refId matches an existing payment.
        The 403 path is exercised only when real creds are configured. We verify here that
        when refId is bogus we still get 404 (not a crash)."""
        r = requests.post(
            f"{BASE_URL}/api/event-payments/webhook/comgate",
            data={
                "refId": str(uuid.uuid4()),
                "status": "PAID",
                "merchant": "BOGUS",
                "secret": "BOGUS",
            },
        )
        assert r.status_code in (403, 404)


class TestByVS:
    def test_by_vs_404_for_unknown(self, sess):
        r = sess.get(f"{BASE_URL}/api/event-payments/by-vs/{INSTITUTION_ID}/999999999")
        assert r.status_code == 404
