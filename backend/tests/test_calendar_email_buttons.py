"""Test calendar deep-link generation and email rendering."""
from urllib.parse import urlparse, parse_qs

from services.email_service import _compute_calendar_links, _build_email_context
from templates.emails import get_template


BOOKING = {
    "id": "abc-123",
    "date": "2026-05-20",
    "time_block": "09:00-10:30",
    "school_name": "ZŠ Komenského",
    "contact_name": "Jana Nová",
    "contact_email": "jana@example.cz",
    "num_students": 22,
    "num_teachers": 2,
}
PROGRAM = {"name_cs": "Procházka galerií", "duration": 90}
INSTITUTION = {
    "name": "Galerie U Zlatého kohouta",
    "address": "Mlýnská 538, Liberec",
    "email": "galerie@example.cz",
}


def test_compute_calendar_links_returns_both_urls():
    links = _compute_calendar_links(BOOKING, PROGRAM, INSTITUTION)
    assert links["google_calendar_url"].startswith("https://calendar.google.com/calendar/render")
    assert links["outlook_calendar_url"].startswith("https://outlook.office.com/calendar/0/deeplink/compose")


def test_google_url_carries_correct_dates_and_title():
    links = _compute_calendar_links(BOOKING, PROGRAM, INSTITUTION)
    parsed = urlparse(links["google_calendar_url"])
    qs = parse_qs(parsed.query)
    # 09:00 Prague (CEST in May, UTC+2) → 07:00 UTC
    assert qs["dates"][0] == "20260520T070000Z/20260520T083000Z"
    assert qs["text"][0] == "Procházka galerií"
    assert "Galerie U Zlatého kohouta" in qs["details"][0]
    assert "Mlýnská 538, Liberec" in qs["location"][0]


def test_outlook_url_carries_iso_dates():
    links = _compute_calendar_links(BOOKING, PROGRAM, INSTITUTION)
    parsed = urlparse(links["outlook_calendar_url"])
    qs = parse_qs(parsed.query)
    assert qs["startdt"][0] == "2026-05-20T07:00:00+00:00"
    assert qs["enddt"][0] == "2026-05-20T08:30:00+00:00"
    assert qs["subject"][0] == "Procházka galerií"


def test_invalid_date_returns_empty_strings_no_crash():
    bad = {**BOOKING, "date": "not-a-date", "time_block": ""}
    links = _compute_calendar_links(bad, PROGRAM, INSTITUTION)
    assert links == {"google_calendar_url": "", "outlook_calendar_url": ""}


def test_email_context_includes_calendar_urls():
    ctx = _build_email_context(BOOKING, PROGRAM, INSTITUTION)
    assert "google_calendar_url" in ctx
    assert "outlook_calendar_url" in ctx
    assert ctx["google_calendar_url"].startswith("https://calendar.google.com/")


def test_reservation_created_teacher_template_contains_buttons():
    ctx = _build_email_context(BOOKING, PROGRAM, INSTITUTION)
    rendered = get_template("reservation_created_teacher", ctx)
    html = rendered["html"]
    assert "Přidat do Google kalendáře" in html
    assert "Přidat do Outlooku" in html
    assert "https://calendar.google.com/calendar/render" in html
    assert "https://outlook.office.com/calendar/0/deeplink/compose" in html


def test_reservation_confirmed_template_contains_buttons():
    ctx = _build_email_context(BOOKING, PROGRAM, INSTITUTION)
    rendered = get_template("reservation_confirmed", ctx)
    html = rendered["html"]
    assert "Přidat do Google kalendáře" in html
    assert "Přidat do Outlooku" in html


def test_reservation_reminder_template_contains_buttons():
    ctx = _build_email_context(BOOKING, PROGRAM, INSTITUTION)
    rendered = get_template("reservation_reminder_teacher", ctx)
    html = rendered["html"]
    assert "Přidat do Google kalendáře" in html


def test_reservation_rescheduled_template_contains_buttons():
    ctx = _build_email_context(BOOKING, PROGRAM, INSTITUTION)
    ctx["original_date"] = "2026-05-15"
    ctx["original_time"] = "10:00-11:30"
    rendered = get_template("reservation_rescheduled", ctx)
    html = rendered["html"]
    assert "Přidat do Google kalendáře" in html


def test_buttons_hidden_when_calendar_urls_empty():
    """Cancellation flow + invalid dates → buttons should not appear."""
    ctx = _build_email_context({**BOOKING, "date": "bad"}, PROGRAM, INSTITUTION)
    rendered = get_template("reservation_created_teacher", ctx)
    assert "Přidat do Google kalendáře" not in rendered["html"]
    assert "Přidat do Outlooku" not in rendered["html"]
