import unittest
from types import SimpleNamespace

from services.collision_service import program_collision_lecturer_ids, reservation_lecturer_ids
from scripts import regression_collision_smoke


class CollisionMultiLecturerHelperTests(unittest.TestCase):
    def test_reservation_lecturer_ids_include_main_and_multi_list(self):
        reservation = SimpleNamespace(
            assigned_lecturer_id="11111111-1111-4111-8111-111111111111",
            assigned_lecturer_ids=[
                "22222222-2222-4222-8222-222222222222",
                "11111111-1111-4111-8111-111111111111",
            ],
        )
        self.assertEqual(
            reservation_lecturer_ids(reservation),
            {
                "11111111-1111-4111-8111-111111111111",
                "22222222-2222-4222-8222-222222222222",
            },
        )

    def test_program_collision_ids_include_manual_default_and_selected(self):
        program = SimpleNamespace(
            assigned_lecturer_id="11111111-1111-4111-8111-111111111111",
            collision_lecturer_ids=["22222222-2222-4222-8222-222222222222"],
        )
        self.assertEqual(
            program_collision_lecturer_ids(program, lecturer_id="33333333-3333-4333-8333-333333333333"),
            {
                "11111111-1111-4111-8111-111111111111",
                "22222222-2222-4222-8222-222222222222",
                "33333333-3333-4333-8333-333333333333",
            },
        )

    def test_smoke_expected_checks_cover_pilot_collision_matrix(self):
        checks = regression_collision_smoke.expected_checks()
        for name in (
            "room_collision_blocked",
            "multilecturer_creation_blocked",
            "blocked_program_blocked",
            "non_parallel_blocked",
            "availability_exception_blocked",
            "assignment_multilecturer_blocked",
        ):
            self.assertIn(name, checks)


if __name__ == "__main__":
    unittest.main()
