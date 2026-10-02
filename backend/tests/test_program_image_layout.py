import pathlib
import unittest

from pydantic import ValidationError

from models.schemas import ProgramCreate


def valid_program(**overrides):
    data = {
        "name_cs": "Program",
        "name_en": "Program",
        "description_cs": "Popis",
        "description_en": "Description",
        "duration": 60,
        "age_group": "zs1_7_12",
        "target_groups": ["zs1_7_12"],
        "target_group": "schools",
    }
    data.update(overrides)
    return data


class ProgramImageLayoutTests(unittest.TestCase):
    def test_defaults_preserve_existing_centered_hero(self):
        program = ProgramCreate(**valid_program())
        self.assertEqual(program.image_layout, "hero")
        self.assertEqual(program.image_focus_x, 50)
        self.assertEqual(program.image_focus_y, 50)

    def test_layout_and_focal_point_are_validated(self):
        with self.assertRaises(ValidationError):
            ProgramCreate(**valid_program(image_layout="overlay"))
        with self.assertRaises(ValidationError):
            ProgramCreate(**valid_program(image_focus_x=101))

    def test_booking_card_uses_non_overlapping_square_column(self):
        source = pathlib.Path("frontend/src/pages/public/BookingPage.js").read_text()
        self.assertIn("md:grid-cols-[minmax(0,1fr)_12rem]", source)
        self.assertIn("imageLayout === 'square'", source)
        self.assertIn("objectPosition: imagePosition", source)

    def test_admin_exposes_layout_and_crop_editor(self):
        source = pathlib.Path("frontend/src/pages/admin/ProgramsPage.js").read_text()
        self.assertIn('data-testid="program-photo-layout-hero"', source)
        self.assertIn('data-testid="program-photo-layout-square"', source)
        self.assertIn('data-testid="program-photo-crop-editor"', source)

    def test_statistics_default_to_semester(self):
        source = pathlib.Path("frontend/src/pages/admin/StatisticsPage.js").read_text()
        self.assertIn("useState('semester')", source)


if __name__ == "__main__":
    unittest.main()
