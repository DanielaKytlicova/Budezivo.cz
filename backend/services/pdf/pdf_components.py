"""Reusable visual building blocks for premium archive PDF reports.

Each public function returns a reportlab flowable (Table / Image / Paragraph)
ready to be appended to the document story. All blocks use the design tokens
defined in :mod:`pdf_styles` — never hard-code colors here.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable, Image, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)
from reportlab.lib.pagesizes import A4

from . import pdf_styles as S
from .pdf_helpers import (
    center_crop_to_aspect, fmt_int, truncate, fmt_date,
)


logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 40 * mm   # 170 mm — content frame width on body pages


# ── Hero cover (full-bleed flowable for page 1) ─────────────────────


class HeroCover(Flowable):
    """Full-page A4 cover with cinematic image, dark scrim and info box.

    Designed to render inside a 0-margin Frame (see ``pdf_renderer``). The
    flowable consumes the entire page; a ``PageBreak`` should follow it in
    the story.
    """

    def __init__(self, image_path: Optional[str], *, title: str, period: str,
                 institution: str, age_group: str, watermark: str = "Budeživo.cz"):
        super().__init__()
        self.image_path = image_path
        self.title = title or ""
        self.period = period or ""
        self.institution = institution or ""
        self.age_group = age_group or ""
        self.watermark = watermark
        # Pre-crop image to A4 aspect for crisp full-bleed rendering
        if image_path:
            self.cropped = center_crop_to_aspect(image_path,
                                                 int(PAGE_W), int(PAGE_H))
        else:
            self.cropped = None

    def wrap(self, _w, _h):
        return PAGE_W, PAGE_H

    def draw(self):
        c = self.canv

        # ── 1. Full-bleed image (or solid colour fallback) ──
        if self.cropped:
            try:
                c.drawImage(self.cropped, 0, 0, width=PAGE_W, height=PAGE_H,
                            preserveAspectRatio=False, mask="auto")
            except Exception as e:
                logger.warning(f"Cover image draw failed: {e}")
                self._draw_solid_fallback(c)
        else:
            self._draw_solid_fallback(c)

        # ── 2. Dark gradient-style scrim for legibility ──
        c.setFillColor(S.OVERLAY)
        c.rect(0, 0, PAGE_W, PAGE_H * 0.55, fill=1, stroke=0)
        # Stronger band along the bottom where the info box sits
        c.setFillColor(colors.Color(0, 0, 0, alpha=0.25))
        c.rect(0, 0, PAGE_W, PAGE_H * 0.30, fill=1, stroke=0)

        # ── 3. Info box in the lower-right ──
        box_w = 105 * mm
        box_h = 60 * mm
        box_x = PAGE_W - box_w - 18 * mm
        box_y = 22 * mm

        c.setFillColor(S.INFOBOX)
        c.roundRect(box_x, box_y, box_w, box_h, 6 * mm, fill=1, stroke=0)

        # Gold accent strip on top of the box
        c.setFillColor(S.ACCENT)
        c.roundRect(box_x, box_y + box_h - 1.6 * mm, box_w, 1.6 * mm,
                    0.6 * mm, fill=1, stroke=0)

        # ── Content inside info box ──
        pad_l = box_x + 9 * mm
        pad_r = box_x + box_w - 9 * mm
        text_w = pad_r - pad_l

        cursor_y = box_y + box_h - 9 * mm

        # Eyebrow: ARCHIVNÍ ZPRÁVA
        c.setFont(S.font_bold(), 7.5)
        c.setFillColor(S.ACCENT)
        c.drawString(pad_l, cursor_y, "ARCHIVNÍ ZPRÁVA · PROGRAM")
        cursor_y -= 8 * mm

        # Title — wraps if too long
        c.setFillColor(colors.white)
        title_lines = _wrap_text(self.title, S.font_bold(), 18, text_w, c)
        c.setFont(S.font_bold(), 18)
        for line in title_lines[:3]:
            c.drawString(pad_l, cursor_y, line)
            cursor_y -= 7 * mm

        cursor_y -= 2 * mm

        # Thin divider
        c.setStrokeColor(colors.Color(1, 1, 1, alpha=0.18))
        c.setLineWidth(0.4)
        c.line(pad_l, cursor_y, pad_r, cursor_y)
        cursor_y -= 5 * mm

        c.setFont(S.font_base(), 9.5)
        c.setFillColor(colors.Color(1, 1, 1, alpha=0.92))
        if self.period:
            c.drawString(pad_l, cursor_y, self.period)
            cursor_y -= 5 * mm
        if self.institution:
            c.drawString(pad_l, cursor_y, truncate(self.institution, 48))
            cursor_y -= 5 * mm
        if self.age_group:
            c.setFillColor(colors.Color(1, 1, 1, alpha=0.7))
            c.drawString(pad_l, cursor_y, self.age_group)

        # ── 4. Watermark in the bottom-right ──
        c.setFont(S.font_base(), 7.5)
        c.setFillColor(colors.Color(1, 1, 1, alpha=0.45))
        c.drawRightString(PAGE_W - 12 * mm, 10 * mm, self.watermark)

    def _draw_solid_fallback(self, c) -> None:
        """Gradient-like solid fill when no cover image is supplied."""
        # Bottom = primary navy, top = a slightly lighter shade
        c.setFillColor(S.PRIMARY)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        # Decorative accent band
        c.setFillColor(S.ACCENT)
        c.rect(0, PAGE_H - 0.6 * mm, PAGE_W, 0.6 * mm, fill=1, stroke=0)


def _wrap_text(text: str, font_name: str, font_size: float,
               max_width: float, canvas) -> list[str]:
    """Naive greedy word-wrap that respects ``stringWidth`` on the canvas."""
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        if canvas.stringWidth(trial, font_name, font_size) <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


# ── KPI dashboard cards ─────────────────────────────────────────────


def kpi_cards(items: list[tuple[str, str, colors.Color]],
              *, total_width: float = CONTENT_W) -> Table:
    """Render a row of KPI dashboard cards.

    ``items`` is a list of ``(number, label, accent_color)`` tuples — typically
    3–5 cards. Each card is a Table with the big number on top and a small
    grey label underneath. The accent colour shows as a 2 mm coloured strip
    on the left edge.
    """
    styles = S.make_styles()
    n = len(items)
    if n == 0:
        return Spacer(0, 0)

    gap = 4 * mm
    card_w = (total_width - gap * (n - 1)) / n

    cell_rows = []
    for col, (num, label, accent) in enumerate(items):
        inner = Table(
            [
                [Paragraph(num, styles["KpiNumber"])],
                [Paragraph(label.upper(), styles["KpiLabel"])],
            ],
            colWidths=[card_w - 6 * mm],
            rowHeights=[12 * mm, None],
        )
        inner.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (0, 0), 4 * mm),
            ("BOTTOMPADDING", (0, 0), (0, 0), 0),
            ("TOPPADDING", (0, 1), (0, 1), 0),
            ("BOTTOMPADDING", (0, 1), (0, 1), 4 * mm),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LINEBEFORE", (0, 0), (0, -1), 2.4, accent),
            ("BOX", (0, 0), (-1, -1), 0.4, S.BORDER),
        ]))
        cell_rows.append(inner)

    row = [cell_rows]
    if n > 1:
        col_widths = []
        for i in range(n):
            col_widths.append(card_w)
            if i < n - 1:
                col_widths.append(gap)
        # interleave spacers
        new_row = []
        for i, c in enumerate(cell_rows):
            new_row.append(c)
            if i < n - 1:
                new_row.append("")
        row = [new_row]
    else:
        col_widths = [card_w]

    t = Table(row, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


# ── Info grid (label/value pairs in 2 columns) ──────────────────────


def info_grid(pairs: list[tuple[str, Optional[str]]],
              *, total_width: float = CONTENT_W,
              columns: int = 2) -> Table:
    """Render label/value metadata in a clean 2-column grid (no borders)."""
    styles = S.make_styles()
    pairs = [(lbl, val) for lbl, val in pairs if val not in (None, "", "—")]
    if not pairs:
        return Spacer(0, 0)

    rows = []
    for i in range(0, len(pairs), columns):
        row_pairs = pairs[i : i + columns]
        cells = []
        for lbl, val in row_pairs:
            cell = Table(
                [[Paragraph(lbl.upper(), styles["InfoLabel"])],
                 [Paragraph(str(val), styles["InfoValue"])]],
                colWidths=[(total_width / columns) - 6 * mm],
            )
            cell.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
                ("TOPPADDING", (0, 0), (0, 0), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 1 * mm),
                ("TOPPADDING", (0, 1), (0, 1), 0),
                ("BOTTOMPADDING", (0, 1), (0, 1), 0),
            ]))
            cells.append(cell)
        # pad shorter rows so columns line up
        while len(cells) < columns:
            cells.append("")
        rows.append(cells)

    t = Table(rows, colWidths=[total_width / columns] * columns)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, S.BORDER),
    ]))
    return t


# ── Light "card" wrapper around any flowable ────────────────────────


def light_card(content_flowables: list, *, total_width: float = CONTENT_W) -> Table:
    """Wrap arbitrary content in a soft rounded card (light bg + hairline)."""
    inner = Table([[f] for f in content_flowables], colWidths=[total_width - 14 * mm])
    inner.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
    ]))
    wrapper = Table([[inner]], colWidths=[total_width])
    wrapper.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), S.LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.4, S.BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
    ]))
    return wrapper


# ── Photo gallery grid ──────────────────────────────────────────────


def gallery_grid(image_paths: list[str], *,
                 total_width: float = CONTENT_W,
                 columns: int = 3,
                 thumb_aspect_w: int = 4, thumb_aspect_h: int = 3) -> Optional[Table]:
    """Build a uniform photo grid with center-cropped thumbnails."""
    if not image_paths:
        return None

    gap = 3 * mm
    col_w = (total_width - gap * (columns - 1)) / columns
    col_h = col_w * thumb_aspect_h / thumb_aspect_w

    cells = []
    for p in image_paths:
        cropped = center_crop_to_aspect(p, thumb_aspect_w * 100, thumb_aspect_h * 100)
        try:
            img = Image(cropped, width=col_w, height=col_h)
        except Exception as e:
            logger.warning(f"Gallery thumb load failed for {p!r}: {e}")
            continue
        cells.append(img)

    if not cells:
        return None

    # Chunk into rows of ``columns``
    rows = []
    for i in range(0, len(cells), columns):
        row = cells[i : i + columns]
        while len(row) < columns:
            row.append("")
        rows.append(row)

    col_widths = []
    for i in range(columns):
        col_widths.append(col_w)
        if i < columns - 1:
            col_widths.append(gap)

    # interleave gaps in each row
    spaced_rows = []
    for row in rows:
        new_row = []
        for i, c in enumerate(row):
            new_row.append(c)
            if i < columns - 1:
                new_row.append("")
        spaced_rows.append(new_row)

    t = Table(spaced_rows, colWidths=col_widths,
              rowHeights=[col_h + gap] * len(spaced_rows))
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), gap),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


# ── Status pill (used inside booking tables) ────────────────────────


def status_pill_table(label: str, status: str) -> Table:
    """Render a single rounded pill for booking status."""
    bg, fg = S.status_pill_colors(status)
    txt = Paragraph(label, S.make_styles()["PillStatus"])
    txt.style.textColor = fg
    t = Table([[txt]], colWidths=[24 * mm], rowHeights=[5.5 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5 * mm),
        ("ROUNDEDCORNERS", [2.7 * mm] * 4),
    ]))
    return t


# Local ParagraphStyle import — needed for status pill
from reportlab.lib.styles import ParagraphStyle  # noqa: E402, F401


# ── Tables: schools & bookings ──────────────────────────────────────


def schools_table(schools: dict, *, total_width: float = CONTENT_W,
                  max_rows: int = 25) -> Optional[Table]:
    """Render a clean zebra-row table summarising schools."""
    if not schools:
        return None

    styles = S.make_styles()
    header = ["Škola", "Návštěv", "Studentů", "Poslední"]
    rows = [header]
    sorted_schools = sorted(
        schools.items(), key=lambda x: -x[1].get("visits", 0)
    )[:max_rows]
    for sn, info in sorted_schools:
        rows.append([
            Paragraph(truncate(sn, 56), styles["Body"]),
            fmt_int(info.get("visits", 0)),
            fmt_int(info.get("students", 0)),
            fmt_date(info.get("last_visit")),
        ])

    col_widths = [total_width * 0.50, total_width * 0.13,
                  total_width * 0.18, total_width * 0.19]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), S.font_bold()),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), S.TEXT_LIGHT),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, S.PRIMARY),
        ("FONTNAME", (1, 1), (-1, -1), S.font_base()),
        ("FONTSIZE", (1, 1), (-1, -1), 9),
        ("TEXTCOLOR", (1, 1), (-1, -1), S.TEXT),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6 * mm),
    ]
    # zebra rows
    for r in range(1, len(rows)):
        if r % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, r), (-1, r), S.LIGHT_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


def bookings_table(bookings: list[dict], *, total_width: float = CONTENT_W,
                   max_rows: int = 80) -> Optional[Table]:
    """Render a clean booking list with colour pill statuses."""
    if not bookings:
        return None

    styles = S.make_styles()
    header = ["Datum", "Čas", "Škola", "Status", "Žáků"]
    rows = [header]
    for b in bookings[:max_rows]:
        status = (b.get("status") or "").lower()
        status_label = {
            "confirmed": "Potvrzeno",
            "completed": "Dokončeno",
            "pending":   "Čeká",
            "cancelled": "Zrušeno",
            "draft":     "Návrh",
        }.get(status, status.upper() or "—")
        rows.append([
            fmt_date(b.get("date")),
            b.get("time_block") or "—",
            Paragraph(truncate(b.get("school_name"), 38), styles["Body"]),
            status_pill_table(status_label, status),
            fmt_int(b.get("num_students")) if b.get("num_students") else "—",
        ])

    col_widths = [total_width * 0.13, total_width * 0.15,
                  total_width * 0.38, total_width * 0.18, total_width * 0.16]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), S.font_bold()),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), S.TEXT_LIGHT),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, S.PRIMARY),
        ("FONTNAME", (0, 1), (-1, -1), S.font_base()),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), S.TEXT),
        ("ALIGN", (0, 1), (1, -1), "LEFT"),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4 * mm),
    ]
    for r in range(1, len(rows)):
        if r % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, r), (-1, r), S.LIGHT_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


# ── Quote cards (teacher feedback) ──────────────────────────────────


def quote_card(text: str, *, attribution: Optional[str] = None,
               rating: Optional[int] = None,
               total_width: float = CONTENT_W) -> Table:
    """Elegant italic quote card with optional attribution and rating stars."""
    styles = S.make_styles()
    # Italic-ish quote — DejaVu doesn't have a true italic, so we lean on
    # gold quotation-mark accents instead of synthetic italic to keep
    # diacritics legible.
    quote_text = text.replace("\n", "<br/>")
    body = Paragraph(
        f'<font color="#C0AC8B" size="14">“</font> {quote_text} '
        f'<font color="#C0AC8B" size="14">”</font>',
        styles["Quote"],
    )

    rows = [[body]]
    if rating is not None:
        try:
            r = max(0, min(5, int(rating)))
            stars = "★" * r + "<font color='#DDE2EA'>" + "★" * (5 - r) + "</font>"
            rows.append([Paragraph(
                f"<font color='#C0AC8B' size='10'>{stars}</font>",
                styles["QuoteAttribution"],
            )])
        except (TypeError, ValueError):
            pass
    if attribution:
        rows.append([Paragraph(f"— {attribution}", styles["QuoteAttribution"])])

    inner = Table(rows, colWidths=[total_width - 14 * mm])
    inner.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    wrap = Table([[inner]], colWidths=[total_width])
    wrap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, S.ACCENT),
        ("BOX", (0, 0), (-1, -1), 0.4, S.BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5 * mm),
    ]))
    return wrap


# ── Section header (eyebrow + H2 + thin gold rule) ──────────────────


def section_header(eyebrow: str, title: str) -> Table:
    """Eyebrow + headline + accent rule — used to introduce a major section."""
    styles = S.make_styles()
    rows = [
        [Paragraph(eyebrow.upper(), styles["Eyebrow"])],
        [Paragraph(title, styles["H2"])],
    ]
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, 0), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), -2),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 1 * mm),
        ("LINEBELOW", (0, 1), (-1, 1), 1.2, S.ACCENT),
    ]))
    return t
