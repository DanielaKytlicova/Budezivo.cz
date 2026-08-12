import unittest

from scripts import regression_core_smoke


class RegressionCoreSmokeTests(unittest.TestCase):
    def test_report_is_ok_when_all_required_checks_pass(self):
        checks = {name: True for name in regression_core_smoke.REQUIRED_CHECKS}
        report = regression_core_smoke.build_report(checks)
        self.assertEqual(report["status"], "ok")

    def test_report_requires_every_core_check(self):
        checks = {name: True for name in regression_core_smoke.REQUIRED_CHECKS}
        checks["reservation_linked"] = False
        report = regression_core_smoke.build_report(checks)
        self.assertEqual(report["status"], "attention_required")
        self.assertFalse(report["checks"]["reservation_linked"])

    def test_report_does_not_include_passwords(self):
        checks = {name: True for name in regression_core_smoke.REQUIRED_CHECKS}
        rendered = str(regression_core_smoke.build_report(checks))
        self.assertNotIn("password", rendered.lower())


if __name__ == "__main__":
    unittest.main()
