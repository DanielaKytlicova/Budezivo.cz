import unittest

from scripts.regression_baseline import build_summary


class RegressionBaselineReportTests(unittest.TestCase):
    def test_ok_when_required_tables_columns_and_alembic_exist(self):
        report = build_summary(
            alembic_versions=["abc123"],
            table_counts={
                "alembic_version": 1,
                "institutions": 1,
                "users": 1,
                "programs": 1,
                "reservations": 0,
                "schools": 0,
                "contacts": 0,
                "mailing_campaigns": 0,
                "events": 0,
                "event_dates": 0,
            },
            columns={
                "events": {"registration_deadline"},
                "event_dates": {"registration_deadline_override"},
            },
            write_probe="rolled_back",
        )

        self.assertEqual(report["status"], "ok")
        self.assertTrue(report["checks"]["required_tables_present"])
        self.assertTrue(report["checks"]["required_columns_present"])
        self.assertTrue(report["checks"]["write_probe_rolled_back"])

    def test_attention_required_when_schema_is_incomplete(self):
        report = build_summary(
            alembic_versions=[],
            table_counts={
                "alembic_version": None,
                "institutions": 1,
                "users": 1,
                "programs": 1,
                "reservations": 0,
                "schools": 0,
                "contacts": 0,
                "mailing_campaigns": 0,
                "events": 0,
                "event_dates": 0,
            },
            columns={
                "events": set(),
                "event_dates": set(),
            },
            write_probe="rolled_back",
        )

        self.assertEqual(report["status"], "attention_required")
        self.assertIn("alembic_version", report["missing_tables"])
        self.assertEqual(report["missing_columns"]["events"], ["registration_deadline"])
        self.assertEqual(report["missing_columns"]["event_dates"], ["registration_deadline_override"])


if __name__ == "__main__":
    unittest.main()
