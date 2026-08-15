import json
import unittest

from scripts.production_smoke import build_url, collect_report, parse_csv_paths


def fake_fetch_ok(url, timeout):
    if url.endswith("/ready"):
        return 200, json.dumps({"status": "ok", "ready": True})
    return 200, "<html>Budezivo</html>"


def fake_fetch_ready_not_ready(url, timeout):
    if url.endswith("/ready"):
        return 503, json.dumps({"status": "not_ready", "ready": False})
    return 200, "<html>Budezivo</html>"


class ProductionSmokeTests(unittest.TestCase):
    def test_parse_csv_paths_trims_empty_items(self):
        self.assertEqual(
            parse_csv_paths(" /booking/abc, ,https://x.test/events/1 "),
            ["/booking/abc", "https://x.test/events/1"],
        )

    def test_build_url_accepts_absolute_url(self):
        self.assertEqual(build_url("https://www.budezivo.cz", "https://example.test/x"), "https://example.test/x")

    def test_build_url_combines_base_and_path(self):
        self.assertEqual(build_url("https://www.budezivo.cz", "/gdpr"), "https://www.budezivo.cz/gdpr")

    def test_report_ok_without_booking_paths(self):
        report = collect_report(
            api_base_url="https://api.example.test",
            frontend_base_url="https://www.example.test",
            booking_paths=[],
            fetch=fake_fetch_ok,
        )

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["booking_paths"], "skipped")

    def test_report_ok_with_booking_paths(self):
        report = collect_report(
            api_base_url="https://api.example.test",
            frontend_base_url="https://www.example.test",
            booking_paths=["/booking/abc"],
            fetch=fake_fetch_ok,
        )

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["booking_paths"], "checked")
        self.assertTrue(any(check["name"] == "booking:/booking/abc" for check in report["checks"]))

    def test_ready_failure_requires_attention(self):
        report = collect_report(
            api_base_url="https://api.example.test",
            frontend_base_url="https://www.example.test",
            booking_paths=[],
            fetch=fake_fetch_ready_not_ready,
        )

        self.assertEqual(report["status"], "attention_required")
        ready = next(check for check in report["checks"] if check["name"] == "api_ready")
        self.assertEqual(ready["status"], "failed")


if __name__ == "__main__":
    unittest.main()
