"""Small utilities shared across the premium PDF render layer.

* image resolve & download (mirroring legacy export_service behaviour)
* center-crop helper for cover hero & gallery thumbs
* safe truncate for table cells & captions
"""
from __future__ import annotations

import logging
import os
import tempfile
import urllib.request
from typing import Optional

from PIL import Image, ImageOps


logger = logging.getLogger(__name__)


def resolve_local_image(url_or_path: Optional[str]) -> Optional[str]:
    """Return a local filesystem path for an image referenced by URL or path.

    Behaviour matches the legacy ``_resolve_local_image`` so existing data
    (program.image_url stored as ``/uploads/...`` or absolute path or external
    URL) keeps working unchanged.
    """
    if not url_or_path:
        return None
    p = str(url_or_path).strip()
    if not p:
        return None

    # Absolute server-side path or "/uploads/..." style reference.
    if p.startswith("/") and not p.startswith("//"):
        if os.path.exists(p):
            return p
        backend_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        candidate = os.path.join(backend_root, p.lstrip("/"))
        if os.path.exists(candidate):
            return candidate
        return None

    # Remote URL — download to a tempfile.
    if p.startswith("http://") or p.startswith("https://"):
        try:
            suffix = ".jpg"
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                if p.lower().split("?")[0].endswith(ext):
                    suffix = ext
                    break
            req = urllib.request.Request(p, headers={"User-Agent": "BudeZivo-PDF/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
                data = resp.read()
            tmp = tempfile.NamedTemporaryFile(prefix="bz_pdf_", suffix=suffix, delete=False)
            tmp.write(data)
            tmp.close()
            return tmp.name
        except Exception as e:
            logger.warning(f"Could not fetch image {p!r}: {e}")
            return None

    return None


def center_crop_to_aspect(src_path: str, target_w: int, target_h: int) -> str:
    """Open ``src_path``, center-crop to the requested aspect ratio, save as
    JPEG into a tempfile and return its path. Returns ``src_path`` unchanged
    on any failure so the caller can still render the original image.

    The function never modifies the source file.
    """
    try:
        img = Image.open(src_path)
        img = ImageOps.exif_transpose(img)  # honour camera orientation tags

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        src_ratio = img.width / img.height
        target_ratio = target_w / target_h

        if src_ratio > target_ratio:
            # crop horizontally
            new_w = int(img.height * target_ratio)
            offset = (img.width - new_w) // 2
            img = img.crop((offset, 0, offset + new_w, img.height))
        else:
            # crop vertically
            new_h = int(img.width / target_ratio)
            offset = (img.height - new_h) // 2
            img = img.crop((0, offset, img.width, offset + new_h))

        # Downscale if the source is huge — keeps PDF size sane.
        max_side = 2400
        if max(img.width, img.height) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)

        tmp = tempfile.NamedTemporaryFile(prefix="bz_pdf_crop_", suffix=".jpg", delete=False)
        img.save(tmp.name, "JPEG", quality=88, optimize=True)
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"center_crop_to_aspect failed for {src_path!r}: {e}")
        return src_path


def truncate(text: Optional[str], length: int) -> str:
    """Truncate ``text`` to ``length`` chars (with ellipsis) — None-safe."""
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "…"


def fmt_int(n) -> str:
    """Format an integer with Czech thousand-separators (narrow space)."""
    try:
        return f"{int(n):,}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return "—"


def fmt_date(iso: Optional[str]) -> str:
    """Format ``YYYY-MM-DD`` (or ISO) as ``D. M. YYYY``."""
    if not iso:
        return "—"
    s = str(iso)[:10]
    try:
        y, m, d = s.split("-")
        return f"{int(d)}. {int(m)}. {y}"
    except Exception:
        return s


def fmt_period(start: Optional[str], end: Optional[str]) -> str:
    """Render two dates as a "1. 9. 2025 – 30. 6. 2026" range, gracefully
    handling missing values.
    """
    a, b = fmt_date(start), fmt_date(end)
    if a == "—" and b == "—":
        return ""
    if a != "—" and b != "—":
        return f"{a} – {b}"
    return a if a != "—" else b
