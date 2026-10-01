"""End-to-end pipeline: image -> (Phase 1) Puzzle JSON -> (Phase 2) CP solution ->
(Phase 3) visualization. No manual intervention between phases."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .puzzle import Puzzle
from .solver import SolveResult, solve, solve_with_alternatives
from .vision import Extraction, debug_image, extract_puzzle
from .vision.preprocess import load_image
from .visualize import clean_board, overlay_solution, side_by_side


@dataclass
class PipelineResult:
    image_path: str
    extraction: Extraction | None
    solve_result: SolveResult | None
    timings: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)

    @property
    def puzzle(self) -> Puzzle | None:
        return self.extraction.puzzle if self.extraction else None


def _imwrite(path: Path, img: np.ndarray) -> None:
    # imencode + tofile supports non-ASCII paths on Windows.
    ok, buf = cv2.imencode(path.suffix or ".png", img)
    if not ok:
        raise IOError(f"Cannot write {path}")
    buf.tofile(str(path))


def run(image_path: str | Path, out_dir: str | Path | None = None, encoding: str = "arith",
        size: int | None = None, time_limit: float = 30.0) -> PipelineResult:
    image_path = Path(image_path)
    result = PipelineResult(str(image_path), None, None)

    t0 = time.perf_counter()
    img = load_image(str(image_path))
    ex = extract_puzzle(img, n=size)
    result.extraction = ex
    result.timings["vision"] = time.perf_counter() - t0

    sol = solve(ex.puzzle, encoding=encoding, time_limit=time_limit, check_unique=True)
    if not sol.solved:
        # The most likely OCR reading is not a valid KenKen: let the CP optimization model
        # pick the most likely combination of alternative readings that is solvable.
        sol, corrected = solve_with_alternatives(ex.puzzle.size, ex.alternatives, time_limit)
        if corrected is not None:
            ex.warnings.extend(f"OCR corrected by CP: {c}" for c in sol.stats["corrections"])
            ex.puzzle = corrected
    result.solve_result = sol
    result.timings["solver"] = sol.wall_time

    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = image_path.stem
        paths = {
            "puzzle": out / f"{stem}_puzzle.json",
            "debug": out / f"{stem}_debug.png",
        }
        ex.puzzle.save(paths["puzzle"])
        _imwrite(paths["debug"], debug_image(ex))
        if sol.solved:
            paths["solution"] = out / f"{stem}_solution.json"
            paths["overlay"] = out / f"{stem}_overlay.png"
            paths["board"] = out / f"{stem}_board.png"
            paths["summary"] = out / f"{stem}_summary.png"
            paths["solution"].write_text(json.dumps({
                "grid": sol.grid, "status": sol.status, "unique": sol.stats.get("unique"),
                "timings": result.timings, "solver_stats": sol.stats, "warnings": ex.warnings,
            }, indent=2), encoding="utf-8")
            overlay = overlay_solution(img, ex, sol.grid)
            board = clean_board(ex, sol.grid)
            _imwrite(paths["overlay"], overlay)
            _imwrite(paths["board"], board)
            _imwrite(paths["summary"], side_by_side(overlay, board))
        result.outputs = {k: str(v) for k, v in paths.items()}
    return result
