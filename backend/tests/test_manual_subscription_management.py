import pathlib
import unittest
from datetime import datetime, timezone

from services.manual_subscription_service import validate_manual_subscription


MIGRATION = pathlib.Path(
    "backend/alembic/versions/d0e1f2a3b4c5_add_manual_subscription_terms.py"
)
ROUTE = pathlib.Path("backend/routes/superadmin.py")
UI = pathlib.Path("frontend/src/pages/admin/SuperadminPage.js")
SETTINGS_UI = pathlib.Path("frontend/src/pages/admin/SettingsPage.js")
MAIN = pathlib.Path("backend/main.py")


def valid_terms(**overrides):
    values = {
        "price_amount": 49_000,
        "amount_paid": 0,
        "currency": "CZK",
        "billing_cycle": "monthly",
        "renewal_mode": "manual",
        "consent_status": "pending",
        "payment_status": "not_invoiced",
        "due_days": 30,
        "period_start": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "period_end": datetime(2026, 11, 1, tzinfo=timezone.utc),
        "billing_email": "fakturace@example.cz",
        "copy_email": "spravce@example.cz",
    }
    values.update(overrides)
    return values


class ManualSubscriptionValidationTests(unittest.TestCase):
    def test_accepts_valid_manual_terms(self):
        validate_manual_subscription(**valid_terms())

    def test_rejects_negative_amounts(self):
        with self.assertRaisesRegex(ValueError, "Cena"):
            validate_manual_subscription(**valid_terms(price_amount=-1))
        with self.assertRaisesRegex(ValueError, "Uhrazená"):
            validate_manual_subscription(**valid_terms(amount_paid=-1))

    def test_rejects_invalid_period_and_states(self):
        with self.assertRaisesRegex(ValueError, "Konec období"):
            validate_manual_subscription(
                **valid_terms(
                    period_end=datetime(2026, 9, 30, tzinfo=timezone.utc),
                )
            )
        with self.assertRaisesRegex(ValueError, "stav platby"):
            validate_manual_subscription(**valid_terms(payment_status="assumed_paid"))

    def test_rejects_invalid_recipient(self):
        with self.assertRaisesRegex(ValueError, "e-mailová"):
            validate_manual_subscription(**valid_terms(billing_email="invalid"))


class ManualSubscriptionWiringTests(unittest.TestCase):
    def test_migration_is_additive_and_follows_current_head(self):
        source = MIGRATION.read_text()
        self.assertIn('"c8d9e0f1a2b3"', source)
        self.assertIn('"d9e0f1a2b3c4"', source)
        self.assertIn("ADD COLUMN IF NOT EXISTS subscription_price_amount", source)
        self.assertIn("ADD COLUMN IF NOT EXISTS subscription_payment_status", source)

    def test_route_and_ui_explicitly_have_no_external_effect(self):
        route_source = ROUTE.read_text()
        endpoint = route_source.split('async def update_institution_subscription', 1)[1].split(
            '# ---- Manual plan control ----', 1
        )[0]
        self.assertIn('"external_effect": False', endpoint)
        self.assertNotIn("create_billing_order(", endpoint)
        self.assertNotIn("confirm_billing_order(", endpoint)

        ui_source = UI.read_text()
        self.assertIn('data-testid="change-subscription-btn"', ui_source)
        self.assertIn('data-testid="save-subscription"', ui_source)
        self.assertIn("Nevystaví fakturu", ui_source)

    def test_billing_email_is_a_separate_internal_setting(self):
        settings_source = SETTINGS_UI.read_text()
        main_source = MAIN.read_text()
        self.assertIn('data-testid="institution-subscription-billing-email"', settings_source)
        self.assertIn("Nepoužívá se pro rezervace, propagaci ani mailing", settings_source)
        self.assertIn('"subscription_billing_email"', main_source)
        self.assertIn('current_user.get("role") not in ("admin", "spravce")', main_source)
        self.assertNotIn("subscription_billing_email", pathlib.Path("backend/services/mailing_service.py").read_text())


if __name__ == "__main__":
    unittest.main()
