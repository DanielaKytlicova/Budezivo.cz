"""
Iteration 57 — JSON-to-PDF migration for archive reports + GDPR exports.
Tests:
  * GET /api/programs/{id}/archive-report (default PDF, ?format=json fallback)
  * GET /api/gdpr/export (default ZIP with json+pdf+README, ?format=json, ?format=pdf)
  * GET /api/exports/download-bundle (ZIP must contain 07_gdpr_export.{json,pdf} and 10_archive_report_*.pdf)
"""
import io
import os
import zipfile

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://arch-enhance-v59.preview.emergentagent.com").rstrip("/")
GALLERY_INSTITUTION_ID = "eefb9cbf-52bf-4e20-9418-5b2f659f8d23"


# ---- Auth helpers --------------------------------------------------------

def _login(email: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    j = r.json()
    return j.get("access_token") or j.get("token")


@pytest.fixture(scope="module")
def gallery_headers():
    token = _login("galerie@budezivo.cz", "Galerie2026!")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def superadmin_headers():
    token = _login("demo@budezivo.cz", "Demo2026!")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def lecturer_headers():
    token = _login("anna.dvorakova@budezivo.cz", "Lektor2026!")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def first_program_id(gallery_headers):
    r = requests.get(f"{BASE_URL}/api/programs", headers=gallery_headers, timeout=30)
    assert r.status_code == 200, r.text
    progs = r.json()
    assert len(progs) > 0, "Gallery should have seeded programs"
    return progs[0]["id"]


# ---- Archive report -------------------------------------------------------

class TestArchiveReport:
    def test_default_returns_pdf(self, gallery_headers, first_program_id):
        r = requests.get(f"{BASE_URL}/api/programs/{first_program_id}/archive-report",
                         headers=gallery_headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF", "Body must start with %PDF magic"
        assert len(r.content) > 1000, "PDF should be >1 KB"
        cd = r.headers.get("content-disposition", "")
        assert ".pdf" in cd.lower(), f"Content-Disposition missing .pdf: {cd}"
        # RFC 5987 UTF-8 encoded filename for diacritics
        assert "filename*=UTF-8''" in cd, f"Missing RFC 5987 filename*: {cd}"

    def test_format_json_returns_legacy_payload(self, gallery_headers, first_program_id):
        r = requests.get(f"{BASE_URL}/api/programs/{first_program_id}/archive-report?format=json",
                         headers=gallery_headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/json")
        data = r.json()
        # Original JSON contract preserved
        for key in ("report_generated_at", "institution", "program",
                    "statistics", "schools", "feedback_count", "feedbacks", "bookings"):
            assert key in data, f"Missing legacy field: {key}"


# ---- GDPR export ----------------------------------------------------------

class TestGdprExport:
    def test_default_returns_zip_with_json_pdf_readme(self, gallery_headers):
        r = requests.get(f"{BASE_URL}/api/gdpr/export", headers=gallery_headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/zip")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = set(zf.namelist())
        assert {"gdpr_export.json", "gdpr_export.pdf", "README.txt"}.issubset(names), names
        # Validate the PDF inside
        with zf.open("gdpr_export.pdf") as fp:
            head = fp.read(8)
            assert head[:4] == b"%PDF", f"Inner gdpr_export.pdf is not a PDF: {head!r}"
        # Validate README mentions GDPR čl. 20
        with zf.open("README.txt") as fp:
            readme = fp.read().decode("utf-8")
            assert "GDPR čl. 20" in readme, f"README missing 'GDPR čl. 20': {readme[:200]}"
        # Validate JSON parses & contains expected keys
        import json
        with zf.open("gdpr_export.json") as fp:
            payload = json.loads(fp.read().decode("utf-8"))
            for k in ("export_date", "user_data", "institution_data", "bookings", "schools"):
                assert k in payload, f"Missing key {k} in inner JSON"

    def test_format_json_returns_only_json(self, gallery_headers):
        r = requests.get(f"{BASE_URL}/api/gdpr/export?format=json",
                         headers=gallery_headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/json")
        data = r.json()
        assert "user_data" in data and "bookings" in data and "schools" in data

    def test_format_pdf_returns_only_pdf(self, gallery_headers):
        r = requests.get(f"{BASE_URL}/api/gdpr/export?format=pdf",
                         headers=gallery_headers, timeout=60)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"


# ---- Bulk download bundle -------------------------------------------------

class TestBundleDownload:
    @pytest.fixture(scope="class")
    def bundle_zip(self, gallery_headers):
        r = requests.get(f"{BASE_URL}/api/exports/download-bundle",
                         headers=gallery_headers, timeout=180)
        assert r.status_code == 200, f"Bundle failed: {r.status_code} {r.text[:300]}"
        assert r.headers.get("content-type", "").startswith("application/zip")
        return zipfile.ZipFile(io.BytesIO(r.content))

    def test_bundle_contains_gdpr_json_and_pdf(self, bundle_zip):
        names = set(bundle_zip.namelist())
        assert "07_gdpr_export.json" in names, names
        assert "07_gdpr_export.pdf" in names, names
        with bundle_zip.open("07_gdpr_export.pdf") as fp:
            assert fp.read(4) == b"%PDF"

    def test_bundle_archive_reports_are_pdf_only(self, bundle_zip):
        names = bundle_zip.namelist()
        archive_files = [n for n in names if n.startswith("10_archive_report_")]
        assert len(archive_files) > 0, "Expected at least one 10_archive_report_*.pdf"
        for n in archive_files:
            assert n.endswith(".pdf"), f"Archive report should be PDF: {n}"
            assert not n.endswith(".json"), f"No JSON archive reports allowed: {n}"
            with bundle_zip.open(n) as fp:
                assert fp.read(4) == b"%PDF", f"{n} not a valid PDF"

    def test_bundle_manifest_present(self, bundle_zip):
        assert "MANIFEST.json" in bundle_zip.namelist()

    def test_lecturer_forbidden_from_bundle(self, lecturer_headers):
        r = requests.get(f"{BASE_URL}/api/exports/download-bundle",
                         headers=lecturer_headers, timeout=30)
        assert r.status_code == 403, f"Lecturer should be 403 not {r.status_code}: {r.text[:200]}"
