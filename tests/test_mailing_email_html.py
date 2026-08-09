from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.mailing_service import _build_campaign_email_html


def test_program_card_links_to_preselected_booking_and_escapes_content():
    rendered = _build_campaign_email_html(
        greeting="Dobrý den,",
        intro_text="Novinky <script>alert(1)</script>",
        programs=[{
            "id": "program-123",
            "name": "Program & dílna",
            "description": "Bezpečný popis",
            "duration": 90,
            "target_groups": ["zs1_7_12"],
        }],
        closing_text="Těšíme se.",
        signature="Tým instituce",
        institution_name="Galerie",
        booking_url="https://www.budezivo.cz/booking/institution-456",
    )

    assert 'href="https://www.budezivo.cz/booking/institution-456?program=program-123"' in rendered
    assert "Vybrat termín" in rendered
    assert "Program &amp; dílna" in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered


def test_program_without_id_is_not_rendered_as_a_broken_link():
    rendered = _build_campaign_email_html(
        greeting="Dobrý den,",
        intro_text="Nabídka",
        programs=[{"name": "Archivní program"}],
        closing_text="Těšíme se.",
        signature="Tým instituce",
        institution_name="Galerie",
        booking_url="https://www.budezivo.cz/booking/institution-456",
    )

    assert "Archivní program" in rendered
    assert "?program=" not in rendered
    assert "Vybrat termín" not in rendered
