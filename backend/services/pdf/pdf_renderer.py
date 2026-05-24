"""Production PDF renderer — premium editorial archive reports.

Public API: ``render_program_report(data, custom_text=None) -> bytes``.

The function consumes the **exact same payload shape** already produced by
``GET /api/programs/{id}/archive-report?format=pdf`` (see the endpoint in
``routes/programs.py``) so no caller, model, route or migration has to change.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, KeepTogether,
)

from . import pdf_styles as S
from . import pdf_charts as charts
from .pdf_components import (
    HeroCover, kpi_cards, info_grid, light_card, gallery_grid,
    schools_table, bookings_table, quote_card, section_header, CONTENT_W,
)
from .pdf_helpers import (
    resolve_local_image, center_crop_to_aspect, fmt_int, fmt_date,
    fmt_period, truncate,
)


logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
MARGIN_X = 20 * mm
MARGIN_TOP = 22 * mm
MARGIN_BOTTOM = 22 * mm
CONTENT_H = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM


# ─────────────────────────────────────────────────────────────────────
# Page template callbacks
# ─────────────────────────────────────────────────────────────────────


def _draw_cover_background(canvas, _doc):
    """Cover page has no decorations — the HeroCover flowable fills everything."""
    pass


def _draw_content_chrome(canvas, doc):
    """Footer for every body page: thin hairline + page number + watermark."""
    canvas.saveState()

    # Hairline divider
    canvas.setStrokeColor(S.BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_X, 14 * mm, PAGE_W - MARGIN_X, 14 * mm)

    # Page number (centered)
    canvas.setFont(S.font_base(), 8)
    canvas.setFillColor(S.TEXT_LIGHT)
    canvas.drawCentredString(PAGE_W / 2, 9 * mm, str(doc.page))

    # Watermark (right)
    canvas.setFont(S.font_base(), 7.5)
    canvas.setFillColor(colors.HexColor("#A5B0BF"))
    canvas.drawRightString(PAGE_W - MARGIN_X, 9 * mm, "Budeživo.cz")

    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────
# Helpers operating on the payload dict
# ─────────────────────────────────────────────────────────────────────


def _collect_photo_paths(prog: dict, fotografie: list) -> tuple[Optional[str], list[str]]:
    """Return (main_image_path, gallery_paths).

    The legacy payload only carries ``program.image_url`` — that is the main
    cover. The new payload may also include a ``fotografie`` list of
    ``{path, is_main, caption}`` records. Both are tolerated.

    The main image is whichever ``is_main`` photo resolves locally; falls back
    to ``program.image_url``. Gallery is every other resolved photo.
    """
    main: Optional[str] = None
    gallery: list[str] = []

    # Try the fotografie array first
    for record in fotografie or []:
        if not isinstance(record, dict):
            continue
        path = record.get("path") or record.get("url") or record.get("image_url")
        local = resolve_local_image(path)
        if not local:
            continue
        if record.get("is_main") and not main:
            main = local
        else:
            gallery.append(local)

    if not main:
        main = resolve_local_image(prog.get("image_url"))

    return main, gallery


def _stats_kpi_items(stats: dict, feedback_count: int) -> list[tuple[str, str, colors.Color]]:
    """Map raw stats dict to KPI tuples ``(number, label, accent_color)``."""
    items: list[tuple[str, str, colors.Color]] = []

    total = int(stats.get("total_reservations") or 0)
    items.append((fmt_int(total), "Rezervací celkem", S.SECONDARY))

    students = int(stats.get("total_students") or 0)
    items.append((fmt_int(students), "Studentů", S.ACCENT))

    schools_n = int(stats.get("unique_schools") or 0)
    items.append((fmt_int(schools_n), "Škol", S.PRIMARY))

    if int(stats.get("total_teachers") or 0) > 0:
        items.append((fmt_int(stats.get("total_teachers")), "Pedagogů", S.SECONDARY))

    if feedback_count > 0:
        items.append((fmt_int(feedback_count), "Zpětných vazeb", S.ACCENT))

    return items


def _format_feedback_quote(fb: dict) -> Optional[dict]:
    """Convert a feedback row to a renderable quote dict, or None to skip."""
    comments = (fb.get("additional_comments") or "").strip()
    answers = fb.get("answers") or {}

    # Pull any free-text answer from the answers blob.
    free_text_parts = []
    if isinstance(answers, dict):
        for v in answers.values():
            if isinstance(v, str) and len(v.strip()) >= 12:
                free_text_parts.append(v.strip())
    text = comments or " ".join(free_text_parts[:1])
    if not text:
        return None

    return {
        "text": truncate(text, 380),
        "rating": fb.get("overall_rating"),
    }


# ─────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────


def render_program_report(data: dict, custom_text: Optional[str] = None) -> bytes:
    """Render the full premium archive report PDF and return it as bytes.

    The function accepts the same payload as ``build_archive_report_pdf`` in
    the legacy ``export_service`` module, so callers do NOT have to change.
    Optional ``custom_text`` is added as a curatorial note section.
    """
    prog = data.get("program", {}) or {}
    inst = data.get("institution", {}) or {}
    stats = data.get("statistics", {}) or {}
    schools = data.get("schools", {}) or {}
    bookings = data.get("bookings", []) or []
    feedbacks = data.get("feedbacks", []) or []
    fotografie = data.get("fotografie", []) or []
    feedback_count = int(data.get("feedback_count") or len(feedbacks))

    main_image, gallery_images = _collect_photo_paths(prog, fotografie)

    # ── Build the story ────────────────────────────────────────────
    story = []
    styles = S.make_styles()

    period_str = fmt_period(prog.get("start_date"), prog.get("end_date"))

    # ── COVER (always present — image or solid fallback) ──
    story.append(HeroCover(
        main_image,
        title=prog.get("name") or "Archivní zpráva programu",
        period=period_str,
        institution=inst.get("name") or "",
        age_group=prog.get("age_group") or "",
    ))
    story.append(NextPageTemplate("Content"))
    story.append(PageBreak())

    # ── PAGE 2+: Intro block ──
    story.append(Paragraph("ARCHIVNÍ ZPRÁVA", styles["Eyebrow"]))
    story.append(Paragraph(prog.get("name") or "Program", styles["H1"]))
    sub = []
    if inst.get("name"):
        sub.append(inst["name"])
    generated = data.get("report_generated_at") or datetime.utcnow().isoformat()
    sub.append("Vygenerováno " + fmt_date(generated[:10]))
    story.append(Paragraph(" &nbsp;·&nbsp; ".join(sub), styles["BodyMuted"]))
    story.append(Spacer(0, 6 * mm))

    # ── Section 1: Přehled programu ──
    overview_pairs = [
        ("Věková skupina", prog.get("age_group")),
        ("Délka programu",
         f"{prog.get('duration')} min" if prog.get("duration") else None),
        ("Kapacita", prog.get("capacity")),
        ("Cena", prog.get("pricing_info") or
         (f"{prog.get('price')} Kč" if prog.get("price") else None)),
        ("Období", period_str if period_str else None),
        ("Instituce", inst.get("name")),
        ("Status", _translate_status(prog.get("status"))),
        ("Archivováno", fmt_date(prog.get("archived_at")) if prog.get("archived_at") else None),
    ]
    if any(v for _, v in overview_pairs):
        story.append(section_header("Sekce 01", "Přehled programu"))
        story.append(Spacer(0, 2 * mm))
        story.append(info_grid(overview_pairs))
        story.append(Spacer(0, 6 * mm))

    # ── Section 2: KPI ──
    kpi_items = _stats_kpi_items(stats, feedback_count)
    if kpi_items and any(int((stats.get(k) or 0)) for k in
                         ("total_reservations", "total_students", "unique_schools")):
        story.append(section_header("Sekce 02", "Klíčové ukazatele"))
        story.append(Spacer(0, 2 * mm))
        # Cap at 4 cards per row to keep things breathable
        story.append(kpi_cards(kpi_items[:4]))
        story.append(Spacer(0, 6 * mm))

    # ── Section 3: O programu ──
    desc = (prog.get("description") or "").strip()
    if desc or (custom_text and custom_text.strip()):
        story.append(section_header("Sekce 03", "O programu"))
        story.append(Spacer(0, 2 * mm))
        flowables = []
        if desc:
            flowables.append(Paragraph(
                desc.replace("&", "&amp;").replace("\n", "<br/>"),
                styles["Body"],
            ))
        if custom_text and custom_text.strip():
            if flowables:
                flowables.append(Spacer(0, 3 * mm))
            flowables.append(Paragraph("KURÁTORSKÁ POZNÁMKA", styles["Eyebrow"]))
            flowables.append(Paragraph(
                custom_text.strip().replace("&", "&amp;").replace("\n", "<br/>"),
                styles["Body"],
            ))
        story.append(light_card(flowables))
        story.append(Spacer(0, 6 * mm))

    # ── Section 4: Galerie ──
    if gallery_images:
        story.append(section_header("Sekce 04", "Fotogalerie"))
        story.append(Spacer(0, 2 * mm))
        grid = gallery_grid(gallery_images[:9], columns=3)
        if grid is not None:
            story.append(grid)
            story.append(Spacer(0, 4 * mm))

    # ── Section 5: Statistiky (charts) ──
    if int(stats.get("total_reservations") or 0) > 0 or schools:
        story.append(section_header("Sekce 05", "Statistiky a návštěvnost"))
        story.append(Spacer(0, 2 * mm))

        donut_png = charts.status_donut_png(stats)
        bar_png = charts.top_schools_bar_png(schools)
        chart_cells = []
        if donut_png:
            donut_path = charts.png_bytes_to_tempfile(donut_png)
            chart_cells.append(_image_with_caption(donut_path,
                                                   "Rozložení rezervací podle stavu",
                                                   width=80 * mm, height=52 * mm))
        if bar_png:
            bar_path = charts.png_bytes_to_tempfile(bar_png)
            chart_cells.append(_image_with_caption(bar_path,
                                                   "Top školy podle počtu návštěv",
                                                   width=80 * mm, height=52 * mm))

        if len(chart_cells) == 2:
            from reportlab.platypus import Table, TableStyle
            t = Table([chart_cells], colWidths=[CONTENT_W / 2 - 2 * mm,
                                                 CONTENT_W / 2 - 2 * mm],
                      hAlign="LEFT")
            t.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(t)
        elif chart_cells:
            story.append(chart_cells[0])
        story.append(Spacer(0, 6 * mm))

    # ── Section 6: Školy ──
    schools_tbl = schools_table(schools)
    if schools_tbl is not None:
        story.append(section_header("Sekce 06", "Přehled škol"))
        story.append(Spacer(0, 2 * mm))
        story.append(schools_tbl)
        story.append(Spacer(0, 6 * mm))

    # ── Section 7: Rezervace ──
    bookings_tbl = bookings_table(bookings)
    if bookings_tbl is not None:
        story.append(section_header("Sekce 07",
                                    f"Rezervace ({len(bookings)})"))
        story.append(Spacer(0, 2 * mm))
        story.append(bookings_tbl)
        if len(bookings) > 80:
            story.append(Spacer(0, 2 * mm))
            story.append(Paragraph(
                f"<i>Zobrazeno prvních 80 z {len(bookings)} rezervací.</i>",
                styles["BodyMuted"],
            ))
        story.append(Spacer(0, 6 * mm))

    # ── Section 8: Zpětná vazba ──
    quotes = [_format_feedback_quote(fb) for fb in feedbacks]
    quotes = [q for q in quotes if q]
    if quotes:
        story.append(section_header("Sekce 08", "Zpětná vazba pedagogů"))
        story.append(Spacer(0, 2 * mm))
        for i, q in enumerate(quotes[:6]):
            story.append(quote_card(q["text"], rating=q.get("rating")))
            if i < len(quotes[:6]) - 1:
                story.append(Spacer(0, 3 * mm))
        story.append(Spacer(0, 4 * mm))

    # ── Build ──
    return _build_document(story)


def _translate_status(status: Optional[str]) -> Optional[str]:
    if not status:
        return None
    return {
        "active": "Aktivní",
        "draft": "Návrh",
        "archived": "Archivován",
        "inactive": "Neaktivní",
    }.get(str(status).lower(), str(status))


def _image_with_caption(image_path: str, caption: str, *,
                        width: float, height: float):
    """Wrap an Image + caption in a tight inner Table flowable."""
    from reportlab.platypus import Image as _Image, Table, TableStyle
    styles = S.make_styles()
    img = _Image(image_path, width=width, height=height)
    t = Table(
        [[img], [Paragraph(caption, styles["Caption"])]],
        colWidths=[width],
    )
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 1 * mm),
        ("BOTTOMPADDING", (0, 1), (0, 1), 0),
    ]))
    return t


def _build_document(story: list) -> bytes:
    """Configure the BaseDocTemplate (cover + content templates) and build."""
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="Archivní zpráva — Budeživo.cz",
        author="Budeživo.cz",
    )

    # Cover frame: 0-margin full-bleed
    cover_frame = Frame(0, 0, PAGE_W, PAGE_H,
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0, id="cover")
    cover_tpl = PageTemplate(id="Cover", frames=[cover_frame],
                             onPage=_draw_cover_background)

    # Content frame with reading margins; footer drawn by onPage callback
    content_frame = Frame(MARGIN_X, MARGIN_BOTTOM, CONTENT_W, CONTENT_H,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0, id="content")
    content_tpl = PageTemplate(id="Content", frames=[content_frame],
                               onPage=_draw_content_chrome)

    doc.addPageTemplates([cover_tpl, content_tpl])
    doc.build(story)
    return buf.getvalue()
