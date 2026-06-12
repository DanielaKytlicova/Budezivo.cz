"""
B2B catalog tests — public read-only catalog and admin opt-in toggle.
Endpoints under test:
  GET  /api/public/catalog
  GET  /api/public/catalog/{id}
  PUT  /api/programs/{id}    (admin toggle is_in_catalog)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://audit-backend-fixes.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

GAL_EMAIL = "galerie@budezivo.cz"
GAL_PASS = "Galerie2026!"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def gal_token(session):
    r = session.post(f"{API}/auth/login", json={"email": GAL_EMAIL, "password": GAL_PASS})
    if r.status_code != 200:
        pytest.skip(f"Galerie login failed {r.status_code}: {r.text}")
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def gal_client(session, gal_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {gal_token}"})
    return s


# ---------- Public catalog list ----------

class TestCatalogList:
    def test_list_basic(self, session):
        r = session.get(f"{API}/public/catalog")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "total" in data and "facets" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1, "Expected at least 1 in_catalog program (Galerie has 4 seeded)"
        # response should not contain MongoDB _id
        for it in data["items"]:
            assert "_id" not in it
            assert isinstance(it["id"], str)
            assert "institution" in it and "id" in it["institution"]
            assert isinstance(it["institution"]["id"], str)

    def test_facets(self, session):
        r = session.get(f"{API}/public/catalog")
        assert r.status_code == 200
        f = r.json()["facets"]
        assert "cities" in f and "categories" in f and "age_groups" in f
        # Galerie is in Brno
        assert any("brno" in c.lower() for c in f["cities"]), f["cities"]

    def test_filter_city_case_insensitive(self, session):
        r = session.get(f"{API}/public/catalog", params={"city": "BRNO"})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 1
        for it in d["items"]:
            assert "brno" in (it["institution"]["city"] or "").lower()

    def test_filter_age_ms(self, session):
        r = session.get(f"{API}/public/catalog", params={"age": "ms"})
        assert r.status_code == 200
        # Either some items returned or empty — but no error
        assert isinstance(r.json()["items"], list)

    def test_filter_q_search(self, session):
        # search by likely common Czech word
        r = session.get(f"{API}/public/catalog", params={"q": "a"})
        assert r.status_code == 200

    def test_sort_newest(self, session):
        r = session.get(f"{API}/public/catalog", params={"sort": "newest"})
        assert r.status_code == 200
        items = r.json()["items"]
        # ensure ordering by created_at desc when there is more than 1
        if len(items) >= 2:
            ts = [it["created_at"] for it in items if it["created_at"]]
            assert ts == sorted(ts, reverse=True)

    def test_sort_popular(self, session):
        r = session.get(f"{API}/public/catalog", params={"sort": "popular"})
        assert r.status_code == 200

    def test_filter_unknown_city_zero(self, session):
        r = session.get(f"{API}/public/catalog", params={"city": "neexistujemesto-xyz-zzz"})
        assert r.status_code == 200
        assert r.json()["total"] == 0


# ---------- Public catalog detail ----------

class TestCatalogDetail:
    def test_detail_for_first_item(self, session):
        r = session.get(f"{API}/public/catalog")
        assert r.status_code == 200
        items = r.json()["items"]
        assert items, "no items in catalog to test detail"
        pid = items[0]["id"]
        d = session.get(f"{API}/public/catalog/{pid}")
        assert d.status_code == 200, d.text
        body = d.json()
        assert body["id"] == pid
        assert "description_full" in body
        assert "institution" in body and "address" in body["institution"]
        assert "reservation_count" in body
        assert "_id" not in body

    def test_detail_unknown_id_returns_404(self, session):
        r = session.get(f"{API}/public/catalog/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ---------- Admin opt-in toggle ----------

class TestAdminToggle:
    def test_toggle_off_then_on(self, session, gal_client):
        # Find a program belonging to galerie that's currently in catalog
        r = session.get(f"{API}/public/catalog", params={"city": "brno"})
        assert r.status_code == 200
        items = [it for it in r.json()["items"] if "galer" in (it["institution"]["name"] or "").lower()]
        if not items:
            pytest.skip("No Galerie program in public catalog to toggle")
        pid = items[0]["id"]

        # Fetch the program detail via admin (need full payload to PUT)
        gp = gal_client.get(f"{API}/programs/{pid}")
        assert gp.status_code == 200, gp.text
        prog = gp.json()
        assert prog.get("is_in_catalog") is True

        # PUT with is_in_catalog=False
        payload = {**prog, "is_in_catalog": False}
        # Some APIs reject unknown fields like 'id', 'created_at' — strip them
        for k in ("id", "created_at", "updated_at", "deleted_at", "institution_name"):
            payload.pop(k, None)
        upd = gal_client.put(f"{API}/programs/{pid}", json=payload)
        assert upd.status_code in (200, 204), upd.text

        # Verify hidden from public
        d = session.get(f"{API}/public/catalog/{pid}")
        assert d.status_code == 404

        # Now toggle back to True
        payload["is_in_catalog"] = True
        upd2 = gal_client.put(f"{API}/programs/{pid}", json=payload)
        assert upd2.status_code in (200, 204), upd2.text

        # Verify visible again
        d2 = session.get(f"{API}/public/catalog/{pid}")
        assert d2.status_code == 200
        assert d2.json()["id"] == pid


# ---------- Default false for new program ----------

class TestDefaultFalse:
    def test_new_program_defaults_to_not_in_catalog(self, gal_client):
        # GET first program of Galerie's institution to grab institution_id
        r = gal_client.get(f"{API}/programs")
        assert r.status_code == 200, r.text
        progs = r.json()
        if isinstance(progs, dict) and "items" in progs:
            progs = progs["items"]
        assert progs, "no programs found for galerie admin"
        inst_id = progs[0].get("institution_id")
        payload = {
            "name_cs": "TEST_default_false_v60",
            "description_cs": "Test program for default catalog flag",
            "duration": 45,
            "min_capacity": 10,
            "max_capacity": 25,
            "price": 100.0,
            "age_group": "ms_3_6",
            "target_groups": ["ms_3_6"],
            "subject_tags": ["test"],
            "institution_id": inst_id,
            "is_published": False,
            "status": "active",
        }
        cr = gal_client.post(f"{API}/programs", json=payload)
        assert cr.status_code in (200, 201), cr.text
        body = cr.json()
        new_id = body.get("id")
        try:
            assert body.get("is_in_catalog") is False, f"Expected False got {body.get('is_in_catalog')}"
            # verify in public catalog: not present (also not published, but check 404 either way)
            r2 = requests.get(f"{API}/public/catalog/{new_id}")
            assert r2.status_code == 404
        finally:
            # cleanup
            if new_id:
                gal_client.delete(f"{API}/programs/{new_id}")
