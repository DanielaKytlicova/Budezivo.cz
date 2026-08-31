import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROGRAMS_PAGE = ROOT / "frontend" / "src" / "pages" / "admin" / "ProgramsPage.js"


class ProgramUrlBannerVisibleTests(unittest.TestCase):
    def test_url_generator_button_is_not_hidden_by_plan_limit_banner(self):
        source = PROGRAMS_PAGE.read_text(encoding="utf-8")
        render_list = source.split("const renderProgramList = () => (", 1)[1]
        before_grid = render_list.split("{/* Programs grid */}", 1)[0]

        self.assertIn('data-testid="generate-url-btn"', before_grid)
        self.assertIn("URL generator must stay visible for all plans", before_grid)
        self.assertNotIn("{hasProgramLimit && (", before_grid)


if __name__ == "__main__":
    unittest.main()
