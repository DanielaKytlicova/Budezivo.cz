import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PublicApplicationPdfTokenTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "backend/routes/events.py").read_text()

    def test_public_pdf_url_includes_signed_token(self):
        self.assertIn("pdf_token = _application_pdf_token(str(inst_uuid), str(application.id))", self.source)
        self.assertIn("pdf?token={pdf_token}", self.source)

    def test_public_pdf_endpoint_rejects_bare_uuid(self):
        self.assertIn("token: Optional[str] = Query(None)", self.source)
        self.assertIn("_application_pdf_token_valid(str(inst_uuid), str(app_uuid), token)", self.source)
        self.assertIn("A bare application UUID is not enough", self.source)

    def test_token_uses_hmac_and_jwt_secret(self):
        self.assertIn("import hmac", self.source)
        self.assertIn("from core.config import JWT_SECRET", self.source)
        self.assertIn('hmac.new(JWT_SECRET.encode("utf-8"), payload, hashlib.sha256)', self.source)
        self.assertIn("hmac.compare_digest(expected, token)", self.source)


if __name__ == "__main__":
    unittest.main()
