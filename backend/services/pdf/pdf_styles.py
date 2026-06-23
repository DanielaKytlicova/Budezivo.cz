"""Design tokens — colors, fonts, paragraph styles.

Single source of truth for the visual identity of premium archive PDFs.
Inspired by editorial / museum annual-report design systems.
"""
from __future__ import annotations

import os
import logging

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily


logger = logging.getLogger(__name__)


# ── Design tokens ───────────────────────────────────────────────────

PRIMARY     = colors.HexColor("#303E4F")   # deep slate-navy
ACCENT      = colors.HexColor("#C0AC8B")   # warm gold
SECONDARY   = colors.HexColor("#596F9C")   # muted royal blue
LIGHT_BG    = colors.HexColor("#F4F6F9")   # off-white section background
TEXT        = colors.HexColor("#3E4A59")   # body text
TEXT_LIGHT  = colors.HexColor("#6B7A8D")   # supporting / metadata
BORDER      = colors.HexColor("#DDE2EA")   # hairline dividers
WHITE       = colors.white
OVERLAY     = colors.Color(0.05, 0.10, 0.18, alpha=0.55)   # cover image scrim
INFOBOX     = colors.Color(0.12, 0.16, 0.24, alpha=0.92)   # cover info-box bg

# Matplotlib chart palette — muted, harmonious
CHART_PALETTE = ["#596F9C", "#C0AC8B", "#7E96BD", "#A89473", "#9CB1D3", "#D9C5A4"]


# ── Font registration (DejaVu Sans for full Czech diacritics) ──────

_FONT_BASE = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"


def _register_fonts() -> None:
    """Register DejaVu Sans (regular + bold) for reportlab. Falls back to
    Helvetica if the bundled fonts are missing — although then Czech diacritics
    may break, the report still renders without crashing.
    """
    global _FONT_BASE, _FONT_BOLD
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate_dirs = [
        os.path.join(base_dir, "fonts"),
        "/usr/share/fonts/truetype/dejavu",
    ]
    for d in candidate_dirs:
        regular = os.path.join(d, "DejaVuSans.ttf")
        bold = os.path.join(d, "DejaVuSans-Bold.ttf")
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
                if "DejaVuSans-Bold" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
                registerFontFamily(
                    "DejaVuSans",
                    normal="DejaVuSans",
                    bold="DejaVuSans-Bold",
                    italic="DejaVuSans",
                    boldItalic="DejaVuSans-Bold",
                )
                _FONT_BASE = "DejaVuSans"
                _FONT_BOLD = "DejaVuSans-Bold"
                return
            except Exception as e:
                logger.warning(f"Failed to register DejaVu fonts from {d}: {e}")
    logger.warning("DejaVu Sans not found — Czech diacritics may break in PDF.")


_register_fonts()


def font_base() -> str:
    return _FONT_BASE


def font_bold() -> str:
    return _FONT_BOLD


# ── Paragraph styles ────────────────────────────────────────────────


def make_styles() -> dict:
    """Return a ready-to-use dict of premium ParagraphStyles.

    Returned as a plain dict (not StyleSheet) so callers can do ``s['BodyXL']``
    without colliding with the default reportlab styles.
    """
    styles: dict[str, ParagraphStyle] = {}

    styles["Eyebrow"] = ParagraphStyle(
        name="Eyebrow", fontName=_FONT_BOLD, fontSize=8,
        textColor=ACCENT, leading=11, spaceAfter=4,
        # ReportLab does not expose CSS letter-spacing, so we fake the
        # "eyebrow" feel by upper-casing the source text in code.
    )
    styles["H1"] = ParagraphStyle(
        name="H1", fontName=_FONT_BOLD, fontSize=26,
        textColor=PRIMARY, leading=30, spaceAfter=10,
    )
    styles["H2"] = ParagraphStyle(
        name="H2", fontName=_FONT_BOLD, fontSize=16,
        textColor=PRIMARY, leading=20, spaceBefore=14, spaceAfter=8,
    )
    styles["H3"] = ParagraphStyle(
        name="H3", fontName=_FONT_BOLD, fontSize=12,
        textColor=PRIMARY, leading=15, spaceBefore=8, spaceAfter=4,
    )
    styles["Body"] = ParagraphStyle(
        name="Body", fontName=_FONT_BASE, fontSize=10,
        textColor=TEXT, leading=15, spaceAfter=4,
    )
    styles["BodyMuted"] = ParagraphStyle(
        name="BodyMuted", fontName=_FONT_BASE, fontSize=9.5,
        textColor=TEXT_LIGHT, leading=14, spaceAfter=2,
    )
    styles["KpiNumber"] = ParagraphStyle(
        name="KpiNumber", fontName=_FONT_BOLD, fontSize=24,
        textColor=PRIMARY, leading=26, alignment=0,
    )
    styles["KpiLabel"] = ParagraphStyle(
        name="KpiLabel", fontName=_FONT_BASE, fontSize=8.5,
        textColor=TEXT_LIGHT, leading=11,
    )
    styles["InfoLabel"] = ParagraphStyle(
        name="InfoLabel", fontName=_FONT_BOLD, fontSize=8,
        textColor=TEXT_LIGHT, leading=11,
    )
    styles["InfoValue"] = ParagraphStyle(
        name="InfoValue", fontName=_FONT_BASE, fontSize=11,
        textColor=PRIMARY, leading=14,
    )
    styles["Quote"] = ParagraphStyle(
        name="Quote", fontName=_FONT_BASE, fontSize=10.5,
        textColor=PRIMARY, leading=16, spaceAfter=4,
        leftIndent=10, rightIndent=10,
    )
    styles["QuoteAttribution"] = ParagraphStyle(
        name="QuoteAttribution", fontName=_FONT_BOLD, fontSize=8.5,
        textColor=TEXT_LIGHT, leading=11, leftIndent=10,
    )
    styles["Caption"] = ParagraphStyle(
        name="Caption", fontName=_FONT_BASE, fontSize=8,
        textColor=TEXT_LIGHT, leading=11, alignment=1,
    )
    styles["PillStatus"] = ParagraphStyle(
        name="PillStatus", fontName=_FONT_BOLD, fontSize=7.5,
        textColor=WHITE, leading=9, alignment=1,
    )

    # Inherit the default helvetica-based stylesheet for any legacy callers
    # that still rely on the "Normal" / "BodyText" names; we don't actively
    # use them, but keep them around for safety.
    sample = getSampleStyleSheet()
    styles["_sample"] = sample
    return styles


# ── Pill colors per booking status ──────────────────────────────────

STATUS_COLORS = {
    "confirmed": (colors.HexColor("#3F8F5F"), WHITE),
    "completed": (colors.HexColor("#596F9C"), WHITE),
    "pending":   (colors.HexColor("#C0AC8B"), WHITE),
    "cancelled": (colors.HexColor("#B85C5C"), WHITE),
    "draft":     (BORDER, TEXT_LIGHT),
}


def status_pill_colors(status: str | None):
    """Return (bg, fg) for a booking status pill."""
    return STATUS_COLORS.get((status or "").lower(), (BORDER, TEXT_LIGHT))
