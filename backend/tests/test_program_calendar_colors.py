from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "admin" / "programCalendarColors.js"


class ProgramCalendarColorTests(unittest.TestCase):
    def test_color_map_assigns_sorted_programs_by_position(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("keys.reduce((map, key, index)", source)
        self.assertIn("programCalendarColorForPosition(index)", source)
        self.assertNotIn("map[key] = PROGRAM_CALENDAR_COLORS[programCalendarColorIndex(key)]", source)

    def test_extra_program_colours_are_generated_instead_of_repeating_palette(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("const generatedProgramColor = (index)", source)
        self.assertIn("137.508", source)
        self.assertIn("PROGRAM_CALENDAR_COLORS[index] || generatedProgramColor", source)


if __name__ == "__main__":
    unittest.main()
