"""Regression tests for the archive-report PDF generator after iter74:

  * HERO variant (full-bleed-ish cover page when ``program.image_url``
    points at a usable image).
  * STANDARD variant (no cover page) when there is no image.
  * Optional ``custom_text`` rendered as a "Poznámka" section between the
    program overview and statistics.
  * Description still rendered as "O programu — co se žáci naučí".
"""
import os
import tempfile

import pytest
from PIL import Image

from services.export_service import build_archive_report_pdf


@pytest.fixture(scope="module")
def hero_image_path():
    """Generate a small valid JPEG once and reuse it across tests."""
    path = os.path.join(tempfile.gettempdir(), "_test_archive_hero.jpg")
    Image.new("RGB", (1200, 800), (90, 122, 174)).save(path, "JPEG")
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _base_payload(image_url=None):
    return {
        "report_generated_at": "2026-04-28T20:00:00Z",
        "institution": {"name": "Galerie U Zlatého kohouta"},
        "program": {
            "name": "Barvy kolem nás",
            "description": "Interaktivní výtvarný program pro 1. stupeň ZŠ.\nDruhý odstavec.",
            "age_group": "I. stupeň ZŠ (7-12)",
            "duration": 60,
            "capacity": "10-24",
            "pricing_info": "30 Kč / žák, pedagog zdarma",
            "status": "archived",
            "archived_at": "2026-04-15",
            "archive_reason": "Konec sezóny",
            "image_url": image_url,
        },
        "statistics": {
            "total_reservations": 17,
            "confirmed": 12,
            "completed": 5,
            "cancelled": 0,
            "total_students": 218,
            "total_teachers": 17,
            "unique_schools": 10,
            "date_range": {"from": "2026-03-30", "to": "2026-04-15"},
        },
        "schools": {"ZŠ Lhota": {"visits": 3, "students": 60, "last_visit": "2026-04-10"}},
        "feedback_count": 0,
        "bookings": [],
    }


def _is_pdf(buf: bytes) -> bool:
    return buf.startswith(b"%PDF") and buf.rstrip(b"\n\r ").endswith(b"%%EOF")


def test_standard_variant_without_image_url():
    pdf = build_archive_report_pdf(_base_payload(image_url=None))
    assert _is_pdf(pdf)
    assert len(pdf) > 5000  # reasonable lower bound for a multi-section report


def test_standard_variant_with_unreachable_image_url():
    """Bad URL should fall back to standard, never raise."""
    pdf = build_archive_report_pdf(_base_payload(image_url="/uploads/programs/does_not_exist.jpg"))
    assert _is_pdf(pdf)


def test_hero_variant_with_local_image(hero_image_path):
    payload = _base_payload(image_url=hero_image_path)
    pdf = build_archive_report_pdf(payload)
    assert _is_pdf(pdf)
    # Hero variant embeds an image → byte count is materially larger than
    # the standard variant of the same payload.
    standard_payload = _base_payload(image_url=None)
    standard_pdf = build_archive_report_pdf(standard_payload)
    assert len(pdf) > len(standard_pdf) + 5000


def test_custom_text_is_embedded(hero_image_path):
    """A non-empty custom note must produce a larger PDF than the same
    payload rendered without it (additional Paragraph + spacer)."""
    payload = _base_payload(image_url=hero_image_path)
    note = (
        "Tento program byl realizován v rámci výstavy ABC. "
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed "
        "do eiusmod tempor incididunt ut labore et dolore magna aliqua."
    )
    pdf_with = build_archive_report_pdf(payload, custom_text=note)
    pdf_without = build_archive_report_pdf(payload)
    assert _is_pdf(pdf_with) and _is_pdf(pdf_without)
    assert len(pdf_with) > len(pdf_without) + 100  # extra section payload


def test_custom_text_empty_string_is_ignored():
    """Empty / whitespace-only ``custom_text`` must NOT add a Poznámka section."""
    pdf_a = build_archive_report_pdf(_base_payload(), custom_text="")
    pdf_b = build_archive_report_pdf(_base_payload(), custom_text="   \n  ")
    pdf_none = build_archive_report_pdf(_base_payload(), custom_text=None)
    # All three should be roughly the same size — empty strings get treated
    # like None at the renderer level.
    assert _is_pdf(pdf_a) and _is_pdf(pdf_b) and _is_pdf(pdf_none)
    assert abs(len(pdf_a) - len(pdf_none)) < 200
    assert abs(len(pdf_b) - len(pdf_none)) < 200


def test_description_section_renders_when_present():
    """Description should be present even without custom_text or image."""
    pdf = build_archive_report_pdf(_base_payload(image_url=None))
    assert _is_pdf(pdf)
    # No exception → renderer accepted the description Paragraph.


def test_description_empty_does_not_break_layout():
    payload = _base_payload(image_url=None)
    payload["program"]["description"] = ""
    pdf = build_archive_report_pdf(payload)
    assert _is_pdf(pdf)
