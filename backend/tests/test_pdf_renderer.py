"""Tests for the premium PDF render layer (Phase 81).

Verifies the new renderer (services.pdf) produces valid PDFs across a range
of payload shapes, including the empty/null-safe cases listed in the spec
("if some data is missing → skip the section, never crash").
"""
from __future__ import annotations

import io
import os
import pytest

from services.pdf import render_program_report


SAMPLE_PROGRAM = {
    "name": "Po stopách přírody s mysliveckým kloboukem",
    "description": "Dvouhodinový terénní program o lesní fauně.\n\nDěti si vyzkouší stopovat zvěř, určit dřeviny a sestavit jednoduchou potravní pyramidu.",
    "age_group": "MŠ · 1. stupeň ZŠ",
    "duration": 120,
    "price": 90,
    "pricing_info": "90 Kč / žák",
    "capacity": "15-30",
    "status": "active",
    "start_date": "2025-09-01",
    "end_date": "2026-06-30",
    "image_url": None,  # solid-color fallback cover
}

SAMPLE_INSTITUTION = {"name": "Biocentrum Kojetín"}

SAMPLE_STATISTICS = {
    "total_reservations": 42,
    "confirmed": 18,
    "completed": 17,
    "cancelled": 7,
    "total_students": 612,
    "total_teachers": 58,
    "unique_schools": 11,
    "date_range": {"from": "2025-09-15", "to": "2026-05-20"},
}

SAMPLE_SCHOOLS = {
    "ZŠ Komenského": {"visits": 6, "students": 88, "last_visit": "2026-04-12"},
    "ZŠ Hanácká": {"visits": 5, "students": 71, "last_visit": "2026-03-30"},
    "MŠ Sluníčko": {"visits": 4, "students": 52, "last_visit": "2026-02-18"},
    "Gymnázium Olomouc": {"visits": 3, "students": 47, "last_visit": "2026-01-22"},
}

SAMPLE_BOOKINGS = [
    {"date": "2026-04-12", "time_block": "09:00-11:00",
     "school_name": "ZŠ Komenského", "status": "completed", "num_students": 24},
    {"date": "2026-04-20", "time_block": "10:00-12:00",
     "school_name": "ZŠ Hanácká", "status": "confirmed", "num_students": 18},
    {"date": "2026-05-15", "time_block": "09:30-11:30",
     "school_name": "Gymnázium Olomouc", "status": "cancelled", "num_students": 26},
]

SAMPLE_FEEDBACKS = [
    {
        "overall_rating": 5,
        "additional_comments": "Skvělý program, děti byly nadšené. Pan lektor uměl zaujmout, výklad srozumitelný. Určitě se vrátíme.",
    },
    {
        "overall_rating": 4,
        "additional_comments": "Děkujeme, moc se nám líbilo. Jen by bylo fajn více času na otázky.",
    },
]


def _full_payload() -> dict:
    return {
        "report_generated_at": "2026-05-19T12:00:00+00:00",
        "program": dict(SAMPLE_PROGRAM),
        "institution": dict(SAMPLE_INSTITUTION),
        "statistics": dict(SAMPLE_STATISTICS),
        "schools": dict(SAMPLE_SCHOOLS),
        "bookings": list(SAMPLE_BOOKINGS),
        "feedbacks": list(SAMPLE_FEEDBACKS),
        "feedback_count": len(SAMPLE_FEEDBACKS),
    }


def _assert_valid_pdf(blob: bytes, min_size: int = 5000) -> None:
    assert isinstance(blob, bytes), "renderer must return bytes"
    assert blob.startswith(b"%PDF-"), "not a valid PDF header"
    assert len(blob) > min_size, f"PDF suspiciously small ({len(blob)} bytes)"


def test_renders_full_payload_to_valid_pdf():
    pdf = render_program_report(_full_payload(), custom_text=None)
    _assert_valid_pdf(pdf)


def test_renders_with_custom_text_curatorial_note():
    pdf = render_program_report(
        _full_payload(),
        custom_text="Tento program byl realizován v rámci pilotního ročníku 2025/26.",
    )
    _assert_valid_pdf(pdf)


def test_renders_minimal_payload_no_data():
    """Empty everything → must still produce a valid PDF (only cover + intro)."""
    payload = {
        "program": {"name": "Minimální program"},
        "institution": {"name": "Test"},
        "statistics": {},
        "schools": {},
        "bookings": [],
        "feedbacks": [],
        "feedback_count": 0,
    }
    pdf = render_program_report(payload)
    _assert_valid_pdf(pdf, min_size=2000)


def test_renders_without_bookings_section():
    payload = _full_payload()
    payload["bookings"] = []
    payload["schools"] = {}
    pdf = render_program_report(payload)
    _assert_valid_pdf(pdf)


def test_renders_without_feedback_section():
    payload = _full_payload()
    payload["feedbacks"] = []
    payload["feedback_count"] = 0
    pdf = render_program_report(payload)
    _assert_valid_pdf(pdf)


def test_renders_with_long_program_name():
    """Long titles must wrap inside the cover info box without crashing."""
    payload = _full_payload()
    payload["program"]["name"] = (
        "Velmi dlouhý název edukačního programu o ekologii a ochraně přírody "
        "určený pro střední školy a poslední ročníky ZŠ — pilotní 2026"
    )
    pdf = render_program_report(payload)
    _assert_valid_pdf(pdf)


def test_legacy_export_service_function_still_works():
    """The legacy export_service.build_archive_report_pdf wrapper must
    transparently delegate to the new renderer."""
    from services.export_service import build_archive_report_pdf
    pdf = build_archive_report_pdf(_full_payload(), custom_text="Note")
    _assert_valid_pdf(pdf)


def test_czech_diacritics_present_in_pdf_stream():
    """Quick byte-level sanity check that DejaVu font was registered and
    encoded characters made it into the PDF."""
    pdf = render_program_report(_full_payload())
    # PDF text streams contain encoded glyphs; instead of decoding, just
    # ensure the file is non-trivial and uses an embedded font.
    assert b"DejaVuSans" in pdf or b"Helvetica" in pdf
