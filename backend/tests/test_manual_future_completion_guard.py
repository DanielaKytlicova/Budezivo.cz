import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class ManualFutureCompletionGuardTests(unittest.TestCase):
    def test_backend_requires_explicit_override_for_future_completion(self):
        source = (ROOT / "backend/routes/bookings.py").read_text()
        self.assertIn("override_future_completion: bool = False", source)
        self.assertIn('"future_completion_requires_confirmation"', source)
        self.assertIn("_completion_requires_override(booking)", source)

    def test_bulk_endpoint_has_the_same_guard(self):
        source = (ROOT / "backend/routes/bookings.py").read_text()
        self.assertIn("request.override_future_completion", source)
        self.assertIn("future_confirmed = [", source)

    def test_frontend_requires_confirmation_before_completion(self):
        source = (ROOT / "frontend/src/pages/admin/BookingsPage.js").read_text()
        self.assertIn("setCompletionPrompt", source)
        self.assertIn('data-testid="keep-booking-confirmed"', source)
        self.assertIn('data-testid="override-future-completion"', source)
        self.assertIn("override_future_completion: overrideFutureCompletion", source)


if __name__ == "__main__":
    unittest.main()
