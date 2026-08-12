import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts import regression_role_isolation_smoke


class RegressionRoleIsolationSmokeTests(unittest.TestCase):
    def test_report_is_ok_when_all_required_checks_pass(self):
        checks = {name: True for name in regression_role_isolation_smoke.REQUIRED_CHECKS}
        report = regression_role_isolation_smoke.build_report(checks)
        self.assertEqual(report["status"], "ok")

    def test_report_requires_every_isolation_check(self):
        checks = {name: True for name in regression_role_isolation_smoke.REQUIRED_CHECKS}
        checks["direct_foreign_id_probes_blocked"] = False
        report = regression_role_isolation_smoke.build_report(checks)
        self.assertEqual(report["status"], "attention_required")
        self.assertFalse(report["checks"]["direct_foreign_id_probes_blocked"])

    def test_second_seed_uses_test_domain_only(self):
        self.assertTrue(regression_role_isolation_smoke.SECOND_ADMIN_EMAIL.endswith("@example.test"))
        self.assertTrue(regression_role_isolation_smoke.SECOND_CASHIER_EMAIL.endswith("@example.test"))
        self.assertTrue(regression_role_isolation_smoke.SECOND_SCHOOL_EMAIL.endswith("@example.test"))

    def test_second_seed_reservation_includes_required_phone(self):
        source = Path(regression_role_isolation_smoke.__file__).read_text(encoding="utf-8")
        self.assertIn('"contact_phone": "+420000000001"', source)

    def test_role_matrix_static_parser_covers_expected_sets(self):
        self.assertTrue(regression_role_isolation_smoke.role_matrix_static_ok())


if __name__ == "__main__":
    unittest.main()
