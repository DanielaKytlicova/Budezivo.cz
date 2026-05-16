"""
Test new fixes batch (Jan 2026):
- POST /api/settings/logo/upload syncs logo_url to public theme endpoint
- PUT /api/institution/settings with logo_url propagates to public theme
- POST /api/programs/{program_id}/image/upload (PRO_PLUS gated)
- Upload endpoints reject unsupported formats with Czech error
"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
TEST_EMAIL = "demo@budezivo.cz"
TEST_PASSWORD = "Demo2026!"


def _create_test_png():
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,
        0x8D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,
        0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])


@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    data = r.json()
    token = data.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    # Resolve institution_id
    me = requests.get(f"{BASE_URL}/api/institution/settings", headers=headers)
    assert me.status_code == 200, me.text
    institution_id = me.json().get("id") or me.json().get("institution_id")
    return {"headers": headers, "institution_id": institution_id}


# ---- Logo upload + theme sync ----
class TestLogoThemeSync:
    def test_upload_logo_syncs_public_theme(self, auth):
        files = {"file": ("sync.png", _create_test_png(), "image/png")}
        r = requests.post(f"{BASE_URL}/api/settings/logo/upload",
                          files=files, headers=auth["headers"])
        assert r.status_code == 200, r.text
        uploaded = r.json()["logo_url"]
        assert uploaded

        # Institution settings
        s = requests.get(f"{BASE_URL}/api/institution/settings", headers=auth["headers"])
        assert s.status_code == 200
        assert s.json().get("logo_url") == uploaded

        # Public theme endpoint
        inst_id = auth["institution_id"]
        assert inst_id, "institution_id missing"
        pub = requests.get(f"{BASE_URL}/api/settings/theme/public/{inst_id}")
        assert pub.status_code == 200, pub.text
        assert pub.json().get("logo_url") == uploaded, (
            f"public theme not synced; got {pub.json().get('logo_url')}, expected {uploaded}"
        )

    def test_put_institution_settings_logo_url_syncs_public_theme(self, auth):
        new_logo = "https://example.com/x.png"
        r = requests.put(f"{BASE_URL}/api/institution/settings",
                         json={"logo_url": new_logo}, headers=auth["headers"])
        assert r.status_code in (200, 204), r.text

        inst_id = auth["institution_id"]
        pub = requests.get(f"{BASE_URL}/api/settings/theme/public/{inst_id}")
        assert pub.status_code == 200
        assert pub.json().get("logo_url") == new_logo, (
            f"public theme not updated; got {pub.json().get('logo_url')}"
        )

    def test_reject_unsupported_format_txt(self, auth):
        files = {"file": ("bad.txt", b"hello", "text/plain")}
        r = requests.post(f"{BASE_URL}/api/settings/logo/upload",
                          files=files, headers=auth["headers"])
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        # Verify Czech-language error if present
        body = r.text.lower()
        # accept Czech keywords or generic error structure
        assert ("formát" in body or "podporov" in body or "neplatn" in body
                or "detail" in body), f"Error message not informative: {r.text}"


# ---- Program image upload (PRO_PLUS) ----
class TestProgramImageUpload:
    def _get_program_id(self, headers):
        r = requests.get(f"{BASE_URL}/api/programs", headers=headers)
        assert r.status_code == 200, r.text
        items = r.json()
        if isinstance(items, dict):
            items = items.get("programs") or items.get("items") or []
        if not items:
            # create one
            payload = {
                "name": "TEST_program_for_image",
                "description": "test",
                "duration_minutes": 60,
                "capacity": 20,
                "price": 100
            }
            cr = requests.post(f"{BASE_URL}/api/programs", json=payload, headers=headers)
            assert cr.status_code in (200, 201), cr.text
            return cr.json().get("id")
        return items[0].get("id")

    def test_upload_program_image_pro_plus(self, auth):
        program_id = self._get_program_id(auth["headers"])
        assert program_id, "no program available"
        files = {"file": ("p.png", _create_test_png(), "image/png")}
        r = requests.post(
            f"{BASE_URL}/api/programs/{program_id}/image/upload",
            files=files, headers=auth["headers"]
        )
        assert r.status_code == 200, f"Expected 200 on PRO_PLUS, got {r.status_code}: {r.text}"
        data = r.json()
        assert "image_url" in data, data
        image_url = data["image_url"]
        # verify saved on program
        g = requests.get(f"{BASE_URL}/api/programs/{program_id}", headers=auth["headers"])
        assert g.status_code == 200
        assert g.json().get("image_url") == image_url

    def test_program_image_reject_invalid_type(self, auth):
        program_id = self._get_program_id(auth["headers"])
        files = {"file": ("p.txt", b"nope", "text/plain")}
        r = requests.post(
            f"{BASE_URL}/api/programs/{program_id}/image/upload",
            files=files, headers=auth["headers"]
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
