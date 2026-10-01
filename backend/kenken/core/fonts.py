"""Locate TrueType fonts on Windows / macOS / Linux (used for rendering and OCR training)."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

# Preferred sans/serif families commonly used by puzzle sites and newspapers.
_CANDIDATES = [
    # fonts of kenkenpuzzle.com (digits: Arial Black, operators: Trebuchet MS Bold)
    "ariblk.ttf", "Arial Black.ttf", "trebucbd.ttf", "Trebuchet MS Bold.ttf",
    "arial.ttf", "arialbd.ttf", "Arial.ttf", "Arial Bold.ttf",
    "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSerif.ttf",
    "verdana.ttf", "verdanab.ttf", "tahoma.ttf", "calibri.ttf", "calibrib.ttf",
    "segoeui.ttf", "segoeuib.ttf", "times.ttf", "timesbd.ttf", "georgia.ttf",
    "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf", "LiberationSerif-Regular.ttf",
    "Helvetica.ttc", "HelveticaNeue.ttc", "Times.ttc", "Verdana.ttf", "Georgia.ttf",
    "FreeSans.ttf", "FreeSansBold.ttf", "NotoSans-Regular.ttf", "NotoSans-Bold.ttf",
]


def _font_dirs() -> list[Path]:
    if sys.platform.startswith("win"):
        windir = os.environ.get("WINDIR", r"C:\Windows")
        dirs = [Path(windir) / "Fonts"]
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
        return dirs
    if sys.platform == "darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"]


@lru_cache(maxsize=1)
def available_fonts() -> tuple[str, ...]:
    """Paths of the candidate fonts installed on this machine (may be empty)."""
    wanted = {name.lower() for name in _CANDIDATES}
    found = {}
    for d in _font_dirs():
        if not d.exists():
            continue
        for path in d.rglob("*"):
            name = path.name.lower()
            if name in wanted and name not in found:
                found[name] = str(path)
    return tuple(found[n.lower()] for n in _CANDIDATES if n.lower() in found)


def load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    """Load a font by path; None (or a failure) falls back to Pillow's bundled font."""
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def default_font_path() -> str | None:
    fonts = available_fonts()
    return fonts[0] if fonts else None
