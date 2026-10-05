"""Draw KenKen boards: clean puzzle images (dataset) and solved boards (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from .fonts import available_fonts, default_font_path, load_font
from .puzzle import Puzzle


@dataclass
class RenderStyle:
    cell: int = 100              # cell size in pixels
    margin: int = 30             # white margin around the board
    thin: int = 2                # thin (in-cage) line width
    thick: int = 6               # cage border / outer border width
    thin_color: tuple = (0, 0, 0)
    ink: tuple = (0, 0, 0)
    paper: tuple = (255, 255, 255)
    clue_font: str | None = None
    clue_scale: float = 0.24     # clue text height relative to the cell
    op_style: str = "unicode"    # "unicode" (× ÷ −) or "ascii" (x / -)


_UNICODE = {"+": "+", "-": "−", "*": "×", "/": "÷", "=": "", "?": "?"}
_ASCII = {"+": "+", "-": "-", "*": "x", "/": "/", "=": "", "?": "?"}


def _covers(font, chars: str) -> bool:
    """True if `font` has a real glyph for every char (Pillow draws a .notdef box
    for missing glyphs; we compare each mask against an unassigned codepoint)."""
    notdef = np.asarray(font.getmask("￿"))
    for ch in chars:
        m = np.asarray(font.getmask(ch))
        if m.size == 0 or (m.shape == notdef.shape and np.array_equal(m, notdef)):
            return False
    return True


def _pick_clue_font(s: "RenderStyle") -> tuple[str | None, dict]:
    """Font path + op map for clue text: the first installed font that actually
    contains the op glyphs. If none does, fall back to ASCII ops so clues never
    render as empty boxes."""
    ops = _UNICODE if s.op_style == "unicode" else _ASCII
    need = "".join(ops.values()) or "+-x/"
    for path in dict.fromkeys([s.clue_font or default_font_path(), *available_fonts()]):
        if _covers(load_font(path, 24), need):
            return path, ops
    return None, _ASCII


def _borders(puzzle: Puzzle):
    """Yield (orientation, r, c, is_thick) for every interior edge.
    'v' edge is between (r, c-1) and (r, c); 'h' edge is between (r-1, c) and (r, c)."""
    owner = puzzle.cage_map()
    n = puzzle.size
    for r in range(n):
        for c in range(1, n):
            yield "v", r, c, owner[r][c - 1] != owner[r][c]
    for r in range(1, n):
        for c in range(n):
            yield "h", r, c, owner[r - 1][c] != owner[r][c]


def render_puzzle(
    puzzle: Puzzle,
    style: RenderStyle | None = None,
    solution: list[list[int]] | None = None,
    solution_color: tuple = (20, 90, 200),
) -> np.ndarray:
    """Render the puzzle (and optionally the solution digits). Returns an RGB array."""
    s = style or RenderStyle()
    n, cell, m = puzzle.size, s.cell, s.margin
    side = n * cell + 2 * m
    img = Image.new("RGB", (side, side), s.paper)
    draw = ImageDraw.Draw(img)

    def px(i: int) -> int:
        return m + i * cell

    # Thin grid first, thick cage borders on top.
    edges = list(_borders(puzzle))
    for thick_pass in (False, True):
        for orient, r, c, thick in edges:
            if thick != thick_pass:
                continue
            w = s.thick if thick else s.thin
            color = s.ink if thick else s.thin_color
            if orient == "v":
                draw.line([(px(c), px(r) - s.thick // 2), (px(c), px(r + 1) + s.thick // 2)], fill=color, width=w)
            else:
                draw.line([(px(c) - s.thick // 2, px(r)), (px(c + 1) + s.thick // 2, px(r))], fill=color, width=w)
    half = s.thick // 2
    draw.rectangle([px(0) - half, px(0) - half, px(n) + half, px(n) + half], outline=s.ink, width=s.thick)

    font_path, ops = _pick_clue_font(s)
    clue_font = load_font(font_path, max(8, int(cell * s.clue_scale)))
    for cage in puzzle.cages:
        r, c = cage.anchor
        text = f"{cage.target}{ops[cage.op]}"
        draw.text((px(c) + s.thick + cell * 0.04, px(r) + s.thick + cell * 0.02), text, fill=s.ink, font=clue_font)

    if solution is not None:
        big = load_font(font_path, int(cell * 0.5))
        for r in range(n):
            for c in range(n):
                cx, cy = px(c) + cell / 2, px(r) + cell * 0.6
                draw.text((cx, cy), str(solution[r][c]), fill=solution_color, font=big, anchor="mm")
    return np.array(img)
