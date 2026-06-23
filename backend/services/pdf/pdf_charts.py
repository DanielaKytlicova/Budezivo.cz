"""Minimalist Stripe / Notion-style charts rendered with matplotlib.

Each public function returns a ``BytesIO`` (or temp PNG path) that can be
embedded in reportlab as an ``Image`` flowable. Charts use the muted palette
from ``pdf_styles`` and strip away matplotlib's default chrome (top/right
spines, grid background, etc.).
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
from typing import Iterable, Optional

# Matplotlib must be imported headless (no GUI backend on server).
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from . import pdf_styles as S


logger = logging.getLogger(__name__)


def _register_chart_font() -> str:
    """Register DejaVu Sans with matplotlib for proper Czech diacritics."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for d in (os.path.join(base_dir, "fonts"), "/usr/share/fonts/truetype/dejavu"):
        regular = os.path.join(d, "DejaVuSans.ttf")
        if os.path.exists(regular):
            try:
                font_manager.fontManager.addfont(regular)
                return "DejaVu Sans"
            except Exception:
                pass
    return "DejaVu Sans"


_CHART_FONT = _register_chart_font()


def _apply_minimalist_style(ax) -> None:
    """Strip matplotlib chrome to achieve the Stripe/Notion analytics aesthetic."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#DDE2EA")
    ax.spines["bottom"].set_color("#DDE2EA")
    ax.tick_params(colors="#6B7A8D", which="both", labelsize=8)
    ax.grid(axis="y", color="#F0F2F6", linewidth=0.8)
    ax.set_axisbelow(True)


def status_donut_png(stats: dict, *, width_in: float = 3.6, height_in: float = 2.4) -> Optional[bytes]:
    """Render a donut chart of booking statuses (confirmed/completed/cancelled).

    Returns ``None`` when no booking data exists so the caller can skip the
    whole chart section instead of rendering an empty figure.
    """
    confirmed = int(stats.get("confirmed") or 0)
    completed = int(stats.get("completed") or 0)
    cancelled = int(stats.get("cancelled") or 0)
    pending = max(
        0,
        int(stats.get("total_reservations") or 0) - confirmed - completed - cancelled,
    )
    parts = [(completed, "Dokončené"), (confirmed, "Potvrzené"),
             (pending, "Čekající"), (cancelled, "Zrušené")]
    parts = [(v, lbl) for v, lbl in parts if v > 0]
    if not parts:
        return None

    values = [v for v, _ in parts]

    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=160)
    fig.patch.set_facecolor("white")
    colors_seq = S.CHART_PALETTE[: len(parts)]
    wedges, _texts = ax.pie(
        values,
        colors=colors_seq,
        startangle=90,
        wedgeprops=dict(width=0.32, edgecolor="white", linewidth=2),
    )
    ax.set_aspect("equal")
    ax.axis("off")

    # Center label — total bookings
    total = sum(values)
    ax.text(0, 0.1, str(total), ha="center", va="center",
            fontsize=20, color="#303E4F", fontweight="bold",
            fontname=_CHART_FONT)
    ax.text(0, -0.18, "rezervací", ha="center", va="center",
            fontsize=8, color="#6B7A8D", fontname=_CHART_FONT)

    # Legend on the right
    ax.legend(
        wedges, [f"{lbl} ({v})" for v, lbl in parts],
        loc="center left", bbox_to_anchor=(1.05, 0.5),
        frameon=False, fontsize=8.5,
        prop={"family": _CHART_FONT},
        labelcolor="#3E4A59",
    )

    return _fig_to_png_bytes(fig)


def top_schools_bar_png(schools: dict, *, top_n: int = 7,
                       width_in: float = 6.6, height_in: float = 2.6) -> Optional[bytes]:
    """Horizontal bar chart of top N schools by visit count."""
    if not schools:
        return None
    items = sorted(
        ((name, info.get("visits", 0)) for name, info in schools.items()),
        key=lambda x: -x[1],
    )[:top_n]
    items = [(n, v) for n, v in items if v > 0]
    if not items:
        return None

    names = [n[:34] + ("…" if len(n) > 34 else "") for n, _ in items][::-1]
    values = [v for _, v in items][::-1]

    fig, ax = plt.subplots(figsize=(width_in, height_in), dpi=160)
    fig.patch.set_facecolor("white")
    bars = ax.barh(names, values, color=S.CHART_PALETTE[0], height=0.6,
                   edgecolor="white", linewidth=0)
    _apply_minimalist_style(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(left=False)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

    # value labels at the end of each bar
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.015,
                bar.get_y() + bar.get_height() / 2,
                str(v), va="center", fontsize=8.5,
                color="#3E4A59", fontname=_CHART_FONT)

    for label in ax.get_yticklabels():
        label.set_fontname(_CHART_FONT)
    for label in ax.get_xticklabels():
        label.set_fontname(_CHART_FONT)

    ax.set_xlim(0, max(values) * 1.18)
    fig.tight_layout(pad=0.5)
    return _fig_to_png_bytes(fig)


def _fig_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white", dpi=160)
    plt.close(fig)
    return buf.getvalue()


def png_bytes_to_tempfile(png: bytes) -> str:
    """Persist a PNG payload to a tempfile so reportlab.Image can read it."""
    tmp = tempfile.NamedTemporaryFile(prefix="bz_chart_", suffix=".png", delete=False)
    tmp.write(png)
    tmp.close()
    return tmp.name
