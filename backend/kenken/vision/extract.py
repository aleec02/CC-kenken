"""Phase 1 entry point: image -> Puzzle (the JSON structure consumed by the solver)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..core.cp import tuplas_validas
from ..core.puzzle import Cage, Puzzle
from .grid import GridTopology, detect_topology, merge_across_weakest_border
from .ocr import ClueReading, clue_glyphs, read_clue
from .preprocess import Rectified, rectify, resize_max


class ExtractionError(RuntimeError):
    pass


@dataclass
class Extraction:
    puzzle: Puzzle
    rect: Rectified
    topology: GridTopology
    readings: list[ClueReading]
    clue_cells: list[tuple[int, int]]
    scale: float                      # resize factor applied to the input image
    warnings: list[str] = field(default_factory=list)
    # Per cage: candidate (Cage, OCR cost) readings, used by solver.solve_with_alternatives.
    alternatives: list[list[tuple[Cage, float]]] = field(default_factory=list)


def _cell_box(rect: Rectified, n: int, r: int, c: int, fx=(0.0, 1.0), fy=(0.0, 1.0)):
    cell = rect.size / n
    x0 = rect.margin + (c + fx[0]) * cell
    y0 = rect.margin + (r + fy[0]) * cell
    x1 = rect.margin + (c + fx[1]) * cell
    y1 = rect.margin + (r + fy[1]) * cell
    return int(x0), int(y0), int(x1), int(y1)


def _clue_crop(rect: Rectified, n: int, r: int, c: int) -> np.ndarray:
    # Clues sit in the upper-left part of the cell; include a bit of the borders so that
    # line fragments touch the crop edge and get discarded by the segmenter.
    x0, y0, x1, y1 = _cell_box(rect, n, r, c, fx=(-0.02, 0.92), fy=(-0.02, 0.55))
    return rect.gray[max(0, y0):y1, max(0, x0):x1]


def _clue_ink_amount(rect: Rectified, n: int, cell: tuple[int, int]) -> float:
    """Number of clue-text pixels in the clue region of a cell (0 = no clue)."""
    glyphs = clue_glyphs(_clue_crop(rect, n, *cell), rect.size / n)
    return float(sum(g.mask.sum() for g in glyphs))


def _choose_clue_cell(rect: Rectified, n: int, cells: list[tuple[int, int]]) -> tuple[int, int] | None:
    """By convention the clue is in the top-left cell of the cage; if that cell is
    empty, fall back to the cage cell with the most ink in its clue region. Returns
    None when no cell of the cage contains a clue."""
    anchor = min(cells)
    if _clue_ink_amount(rect, n, anchor) > 0:
        return anchor
    best = max(cells, key=lambda c: _clue_ink_amount(rect, n, c))
    return best if _clue_ink_amount(rect, n, best) > 0 else None


def _fix_clueless_cages(rect: Rectified, topo: GridTopology, warnings: list[str]) -> None:
    """Every KenKen cage has exactly one clue. A cage without any ink means a thin border
    was classified as thick: merge it with its neighbour across its weakest border."""
    for _ in range(topo.n * topo.n):
        empty = next((c for c in topo.cages if _choose_clue_cell(rect, topo.n, c) is None), None)
        if empty is None or not merge_across_weakest_border(topo, empty):
            return
        warnings.append(f"cage {min(empty)} had no clue: merged with a neighbour (border fix)")


def _repair(cage_cells, reading: ClueReading, n: int, warnings: list[str]) -> Cage:
    """Make the OCR reading consistent with the cage geometry. Anything doubtful
    becomes an unknown operator ("?"), which the CP model resolves."""
    k = len(cage_cells)
    target, op = reading.target, reading.op
    if target is None or target <= 0:
        raise ExtractionError(f"Could not read the target of the cage at {min(cage_cells)} (OCR: {reading.text!r})")
    if k == 1:
        return Cage(target, "=", cage_cells)
    if op in "-/" and op != "?" and k != 2:
        warnings.append(f"cage {min(cage_cells)}: '{op}' on {k} cells, operator set to unknown")
        op = "?"
    cage = Cage(target, op, cage_cells)
    if op != "?" and n ** k <= 200_000 and not tuplas_validas(cage, n):
        warnings.append(f"cage {min(cage_cells)}: '{reading.text}' is unsatisfiable, operator set to unknown")
        cage = Cage(target, "?", cage_cells)
    if op == "?":
        warnings.append(f"cage {min(cage_cells)}: operator not read ('{reading.text}'), solver will infer it")
    return cage


UNKNOWN_OP_PENALTY = 1.0


def _alternatives(cells, reading: ClueReading, primary: Cage, n: int) -> list[tuple[Cage, float]]:
    """Valid concrete readings of a cage, cheapest first. Readings that are impossible
    for the cage geometry (wrong operator for the number of cells, unsatisfiable
    target) are discarded; unknown operators are expanded into every candidate."""
    k = len(cells)
    best: dict[tuple[int, str], float] = {}
    raw = reading.alternatives or [(primary.target, primary.op, 0.0)]
    raw = [(primary.target, primary.op, raw[0][2])] + list(raw)
    for target, op, cost in raw:
        if target is None or target <= 0:
            continue
        if k == 1:
            op = "="
        if op in "-/" and k != 2:
            continue
        cand = Cage(target, op, cells)
        ops = cand.candidate_ops()
        extra = UNKNOWN_OP_PENALTY if len(ops) > 1 else 0.0
        for o in ops:
            concrete = Cage(target, o, cells)
            if n ** k <= 200_000 and not tuplas_validas(concrete, n):
                continue
            key = (target, o)
            best[key] = min(best.get(key, np.inf), cost + extra)
    ranked = sorted(best.items(), key=lambda kv: kv[1])
    return [(Cage(t, o, cells), c) for (t, o), c in ranked]


def extract_puzzle(img_bgr: np.ndarray, n: int | None = None) -> Extraction:
    """Run the full vision pipeline. `n` forces the grid size (otherwise detected)."""
    img, scale = resize_max(img_bgr)
    rect = rectify(img)
    topo = detect_topology(rect, n)
    cell_px = rect.size / topo.n

    cages, readings, clue_cells, warnings, alternatives = [], [], [], [], []
    _fix_clueless_cages(rect, topo, warnings)
    for cells in topo.cages:
        clue_cell = _choose_clue_cell(rect, topo.n, cells) or min(cells)
        reading = read_clue(_clue_crop(rect, topo.n, *clue_cell), cell_px, expect_op=len(cells) > 1)
        readings.append(reading)
        clue_cells.append(clue_cell)
        cage = _repair(cells, reading, topo.n, warnings)
        cages.append(cage)
        alternatives.append(_alternatives(cells, reading, cage, topo.n) or [(cage, 0.0)])

    puzzle = Puzzle(topo.n, cages)
    return Extraction(puzzle, rect, topo, readings, clue_cells, scale, warnings, alternatives)
