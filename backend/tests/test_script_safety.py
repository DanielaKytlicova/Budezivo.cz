import os
import unittest
from unittest.mock import patch

from scripts.safety import require_test_database_url


class ScriptSafetyTests(unittest.TestCase):
    def test_requires_test_app_env(self):
        env = {
            "APP_ENV": "production",
            "TEST_DATABASE_URL": "postgresql://postgres.test:pw@example.test:5432/postgres",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "APP_ENV=test"):
                require_test_database_url("example.py")

    def test_requires_test_database_url(self):
        with patch.dict(os.environ, {"APP_ENV": "test"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TEST_DATABASE_URL"):
                require_test_database_url("example.py")

    def test_rejects_known_production_project(self):
        env = {
            "APP_ENV": "test",
            "TEST_DATABASE_URL": (
                "postgresql://postgres.dhuujqpxazadbbdlwago:pw"
                "@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"
            ),
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "production Supabase project"):
                require_test_database_url("example.py")

    def test_accepts_test_database_url(self):
        url = "postgresql://postgres.testproject:pw@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"
        with patch.dict(os.environ, {"APP_ENV": "test", "TEST_DATABASE_URL": url}, clear=True):
            self.assertEqual(require_test_database_url("example.py"), url)


if __name__ == "__main__":
    unittest.main()
