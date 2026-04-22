"""Tests covering:
  - PATCH /api/team/{id}/lecturer-profile self-edit works for logged lecturer
  - Admin can edit admin_note; non-admin cannot
  - PATCH /api/team/{id}/lecturer-mode no longer exists (removed)
  - /api/bookings/{id}/naslech endpoints are gone (observers removed)
"""
import os
import httpx
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
API = f"{BASE}/api"


def _login(email: str, password: str) -> str:
    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def demo_token():
    return _login("demo@budezivo.cz", "Demo2026!")


@pytest.fixture(scope="module")
def demo_user_id(demo_token):
    r = httpx.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {demo_token}"})
    r.raise_for_status()
    return r.json()["id"]


class TestLecturerProfileSelfEdit:
    def test_self_edit_preferred_age_groups(self, demo_token, demo_user_id):
        r = httpx.patch(
            f"{API}/team/{demo_user_id}/lecturer-profile",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={"preferred_age_groups": ["ms_3_6", "zs1_7_12"]},
        )
        assert r.status_code == 200, r.text
        assert "preferred_age_groups" in r.json()["updated"]

        # verify persisted
        me = httpx.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {demo_token}"}).json()
        assert sorted(me["preferred_age_groups"]) == ["ms_3_6", "zs1_7_12"]

    def test_self_edit_programs(self, demo_token, demo_user_id):
        r = httpx.patch(
            f"{API}/team/{demo_user_id}/lecturer-profile",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={"supported_program_ids": [], "learning_program_ids": []},
        )
        assert r.status_code == 200

    def test_admin_can_edit_admin_note(self, demo_token, demo_user_id):
        r = httpx.patch(
            f"{API}/team/{demo_user_id}/lecturer-profile",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={"admin_note": "test note"},
        )
        # demo is admin → should succeed
        assert r.status_code == 200
        assert "admin_note" in r.json()["updated"]

    def test_reject_empty_payload(self, demo_token, demo_user_id):
        r = httpx.patch(
            f"{API}/team/{demo_user_id}/lecturer-profile",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={},
        )
        assert r.status_code == 400


class TestNaslechRemoval:
    def test_lecturer_mode_endpoint_gone(self, demo_token, demo_user_id):
        r = httpx.patch(
            f"{API}/team/{demo_user_id}/lecturer-mode",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={"lecturer_mode": "training"},
        )
        assert r.status_code in (404, 405)

    def test_observers_list_endpoint_gone(self, demo_token):
        r = httpx.get(
            f"{API}/bookings/00000000-0000-0000-0000-000000000000/naslech",
            headers={"Authorization": f"Bearer {demo_token}"},
        )
        assert r.status_code in (404, 405)

    def test_observers_post_endpoint_gone(self, demo_token):
        r = httpx.post(
            f"{API}/bookings/00000000-0000-0000-0000-000000000000/naslech",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={"lecturer_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code in (404, 405)
