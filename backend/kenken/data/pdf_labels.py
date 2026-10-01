"""Exact ground-truth labels from digital KenKen PDFs (kenkenpuzzle.com exports).

The PDFs are vector documents:
  * the grid border is a stroked rectangle; grid lines are filled rectangles, thin for
    cell separators and thick for cage borders;
  * clues are text spans: digits in Arial Black, operators in Trebuchet MS Bold.
So the puzzle can be read exactly, without any computer vision. Every label is then
validated with the CP solver (one clue per cage, unique solution).
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core.puzzle import Cage, Puzzle

_OPS = {"+": "+", "×": "*", "x": "*", "÷": "/", "―": "-", "—": "-", "–": "-", "−": "-", "-": "-"}
THICK_MIN = 2.0   # points: filled rectangles thicker than this are cage borders


class PdfLabelError(ValueError):
    pass


def _grid_box(page):
    """The grid's outer border: the widest stroked rectangle on the page."""
    boxes = [d["rect"] for d in page.get_drawings()
             if d["type"] == "s" and (d.get("width") or 0) > THICK_MIN]
    if not boxes:
        raise PdfLabelError("no grid border found")
    return max(boxes, key=lambda r: r.width * r.height)


def _thick_rects(page, box, cell):
    """Dark filled rectangles inside the grid that are thick but line-shaped (cell
    backgrounds are also filled rectangles, but white and cell-sized)."""
    out = []
    for d in page.get_drawings():
        r, fill = d["rect"], d.get("fill")
        dark = fill is not None and sum(fill) < 1.5
        if d["type"] == "f" and dark and box.contains(r.tl) \
                and THICK_MIN < min(r.width, r.height) < cell / 4:
            out.append(r)
    return out


def read_pdf_puzzle(path: str | Path) -> tuple[Puzzle, dict]:
    """Return (puzzle, metadata) read from the vector content of a KenKen PDF."""
    import pymupdf

    with pymupdf.open(str(path)) as doc:
        page = doc[0]
        text = page.get_text()
        header = re.search(r"PUZZLE\s+NO\.?\s*(\d+),\s*(\d+)\s*X\s*(\d+),\s*(\w+)", text, re.I)
        if not header:
            raise PdfLabelError("puzzle header (PUZZLE NO. ..., NxN, LEVEL) not found")
        puzzle_id, n, difficulty = header.group(1), int(header.group(2)), header.group(4).lower()

        box = _grid_box(page)
        cell = box.width / n
        thick = _thick_rects(page, box, cell)

        def is_thick(x, y):
            return any(r.x0 - 1 <= x <= r.x1 + 1 and r.y0 - 1 <= y <= r.y1 + 1 for r in thick)

        v_thick = [[is_thick(box.x0 + (c + 1) * cell, box.y0 + (r + 0.5) * cell)
                    for c in range(n - 1)] for r in range(n)]
        h_thick = [[is_thick(box.x0 + (c + 0.5) * cell, box.y0 + (r + 1) * cell)
                    for c in range(n)] for r in range(n - 1)]

        # Clue text per cell: digits (Arial Black) followed by an operator (Trebuchet).
        clues: dict[tuple[int, int], dict] = {}
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    if not (box.x0 <= x0 <= box.x1 and box.y0 <= y0 <= box.y1):
                        continue
                    r = min(n - 1, int(((y0 + y1) / 2 - box.y0) / cell))
                    c = min(n - 1, int((x0 + 1 - box.x0) / cell))
                    entry = clues.setdefault((r, c), {"digits": "", "op": ""})
                    for ch in span["text"].strip():
                        if ch.isdigit():
                            entry["digits"] += ch
                        elif ch in _OPS:
                            entry["op"] = _OPS[ch]

    # Cages: union of cells not separated by a thick border.
    parent = {(r, c): (r, c) for r in range(n) for c in range(n)}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for r in range(n):
        for c in range(n - 1):
            if not v_thick[r][c]:
                parent[find((r, c))] = find((r, c + 1))
    for r in range(n - 1):
        for c in range(n):
            if not h_thick[r][c]:
                parent[find((r, c))] = find((r + 1, c))
    groups: dict = {}
    for cell_rc in parent:
        groups.setdefault(find(cell_rc), []).append(cell_rc)

    cages = []
    for cells in sorted(groups.values(), key=min):
        found = [clues[c] for c in cells if c in clues and clues[c]["digits"]]
        if len(found) != 1:
            raise PdfLabelError(f"cage at {min(cells)} has {len(found)} clues (expected 1)")
        clue = found[0]
        cages.append(Cage(int(clue["digits"]), clue["op"] or "=", cells))
    meta = {"puzzle_id": puzzle_id, "difficulty": difficulty}
    return Puzzle(n, cages), meta
