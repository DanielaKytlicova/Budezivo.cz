import unittest

from services.readiness_service import check_environment, collect_readiness


def _test_statement():
    return "SELECT 1"


class _OkConnection:
    async def execute(self, statement):
        return None


class _OkBegin:
    async def __aenter__(self):
        return _OkConnection()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _OkEngine:
    def begin(self):
        return _OkBegin()


class _BrokenBegin:
    async def __aenter__(self):
        raise ConnectionError("database is unavailable")

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _BrokenEngine:
    def begin(self):
        return _BrokenBegin()


class ReadinessServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_environment_reports_names_not_secret_values(self):
        env = {
            "DATABASE_URL": "postgresql://user:secret@example.test/db",
            "JWT_SECRET": "super-secret-token",
            "RESEND_API_KEY": "re_secret",
        }

        result = check_environment(env)
        rendered = repr(result)

        self.assertEqual(result["status"], "ok")
        self.assertIn("DATABASE_URL", rendered)
        self.assertIn("JWT_SECRET", rendered)
        self.assertNotIn("super-secret-token", rendered)
        self.assertNotIn("postgresql://user:secret@example.test/db", rendered)
        self.assertNotIn("re_secret", rendered)

    async def test_collect_readiness_is_ok_when_required_and_optional_checks_pass(self):
        env = {
            "DATABASE_URL": "postgresql://user:pw@example.test/db",
            "JWT_SECRET": "secret",
            "RESEND_API_KEY": "re_secret",
        }

        result = await collect_readiness(_OkEngine(), env, _test_statement)

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["ready"])
        self.assertEqual(result["checks"]["database"]["status"], "ok")

    async def test_collect_readiness_degrades_for_missing_optional_resend_key(self):
        env = {
            "DATABASE_URL": "postgresql://user:pw@example.test/db",
            "JWT_SECRET": "secret",
        }

        result = await collect_readiness(_OkEngine(), env, _test_statement)

        self.assertEqual(result["status"], "degraded")
        self.assertTrue(result["ready"])
        self.assertEqual(result["checks"]["email"]["status"], "degraded")
        self.assertIn("RESEND_API_KEY", result["checks"]["environment"]["missing_optional"])

    async def test_collect_readiness_fails_for_missing_required_env(self):
        result = await collect_readiness(_OkEngine(), {"JWT_SECRET": "secret"}, _test_statement)

        self.assertEqual(result["status"], "not_ready")
        self.assertFalse(result["ready"])
        self.assertIn("DATABASE_URL", result["checks"]["environment"]["missing_required"])

    async def test_collect_readiness_fails_for_database_error(self):
        env = {
            "DATABASE_URL": "postgresql://user:pw@example.test/db",
            "JWT_SECRET": "secret",
            "RESEND_API_KEY": "re_secret",
        }

        result = await collect_readiness(_BrokenEngine(), env, _test_statement)

        self.assertEqual(result["status"], "not_ready")
        self.assertFalse(result["ready"])
        self.assertEqual(result["checks"]["database"]["detail"], "ConnectionError")


if __name__ == "__main__":
    unittest.main()
