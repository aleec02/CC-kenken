"""Use cases of the system. The API (kenken.api) and the CLI (kenken.cli) are thin
adapters over these three functions, so both interfaces behave identically:

    extract(file)        Phase 1      image/PDF -> puzzle          POST /api/extract
    solve(puzzle)        Phase 2      puzzle    -> solution        POST /api/solve
    solve_image(file)    Phases 1-3   image/PDF -> solution        POST /api/solve-image

All inputs and outputs are the models of kenken.schemas.
"""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np

from . import __version__, schemas
from .core import cp
from .core.puzzle import Cage, Puzzle
from .core.render import RenderStyle, render_puzzle
from .vision import Extraction, ExtractionError, debug_image, extract_puzzle
from .vision.overlay import overlay_solution
from .vision.preprocess import decode_image


# --------------------------------------------------------------------------- errors
class ServiceError(Exception):
    """Base error; `code` matches schemas.ErrorResponse.error."""
    code = "internal_error"


class InvalidInput(ServiceError):
    code = "invalid_input"


class InvalidPuzzle(ServiceError):
    code = "invalid_puzzle"


class ExtractionFailed(ServiceError):
    code = "extraction_failed"


# --------------------------------------------------------------------------- conversions
def to_schema(puzzle: Puzzle) -> schemas.Puzzle:
    return schemas.Puzzle(size=puzzle.size, cages=[
        schemas.Cage(target=c.target, op=c.op, cells=[tuple(x) for x in c.cells]) for c in puzzle.cages])


def from_schema(puzzle: schemas.Puzzle) -> Puzzle:
    return Puzzle(puzzle.size, [Cage(c.target, c.op, [tuple(x) for x in c.cells]) for c in puzzle.cages])


def png_data_url(img_bgr: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img_bgr)
    if not ok:
        raise ServiceError("could not encode image")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def board_image(puzzle: Puzzle, grid: list[list[int]] | None = None) -> np.ndarray:
    rgb = render_puzzle(puzzle, RenderStyle(cell=90), solution=grid)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


COP_TIME_LIMIT = 10.0   # s; the COP returns its best solution found when the limit is hit


def _ms(seconds: float) -> float:
    return round(seconds * 1000, 2)


# --------------------------------------------------------------------------- phase 1
def _decode(data: bytes, filename: str) -> np.ndarray:
    if not data:
        raise InvalidInput("empty file")
    try:
        return decode_image(data, filename)
    except ValueError as e:
        raise InvalidInput(str(e)) from None


def _extract(img: np.ndarray, size: int | None) -> tuple[Extraction, float]:
    if size is not None and not 3 <= size <= 9:
        raise InvalidInput("size must be between 3 and 9")
    t0 = time.perf_counter()
    try:
        ex = extract_puzzle(img, n=size)
    except (ExtractionError, RuntimeError) as e:
        raise ExtractionFailed(str(e)) from None
    return ex, time.perf_counter() - t0


def _extract_response(img: np.ndarray, ex: Extraction, seconds: float, images: bool) -> schemas.ExtractResponse:
    corners = ex.rect.corners / ex.scale
    return schemas.ExtractResponse(
        puzzle=to_schema(ex.puzzle),
        detections=[
            schemas.CageDetection(clue_cell=tuple(cell), ocr_text=r.text, confidence=round(r.confidence, 3))
            for cell, r in zip(ex.clue_cells, ex.readings)
        ],
        grid_corners=[(round(float(x), 1), round(float(y), 1)) for x, y in corners],
        image_size=(img.shape[1], img.shape[0]),
        warnings=list(ex.warnings),
        timings=schemas.ExtractTimings(vision_ms=_ms(seconds)),
        images=schemas.ExtractImages(debug=png_data_url(debug_image(ex))) if images else None,
    )


def extract(data: bytes, filename: str = "", size: int | None = None,
            images: bool = False) -> schemas.ExtractResponse:
    """Phase 1: read the puzzle (grid size, cages, clues) from an image or PDF."""
    img = _decode(data, filename)
    ex, seconds = _extract(img, size)
    return _extract_response(img, ex, seconds, images)


# --------------------------------------------------------------------------- phase 2
def _solve_response(puzzle: Puzzle, res: cp.ResultadoCP, encoding: str,
                    images: bool) -> schemas.SolveResponse:
    if res.resuelto:
        # make "?" operators concrete with the operator the solution satisfies
        puzzle = Puzzle(puzzle.size, [c.resolved([res.grilla[r][k] for r, k in c.cells])
                                      for c in puzzle.cages])
    e = res.estadisticas
    return schemas.SolveResponse(
        status=res.estado,
        solved=res.resuelto,
        grid=res.grilla,
        unique=res.unica,
        puzzle=to_schema(puzzle),
        stats=schemas.SolverStats(
            encoding=encoding, wall_time_ms=_ms(res.walltime), branches=e["branches"],
            conflicts=e["conflicts"], num_variables=e["num_variables"],
            num_constraints=e["num_restricciones"]),
        images=schemas.SolveImages(board=png_data_url(board_image(puzzle, res.grilla))) if images else None,
    )


def _solve(puzzle: Puzzle, options: schemas.SolveOptions) -> cp.ResultadoCP:
    errors = puzzle.validate()
    if errors:
        raise InvalidPuzzle("; ".join(errors))
    return cp.resolver(puzzle, codificacion=options.encoding, tiempo_limite=options.time_limit,
                       verificar_unicidad=options.check_unique)


def solve(puzzle: schemas.Puzzle, options: schemas.SolveOptions | None = None,
          images: bool = False) -> schemas.SolveResponse:
    """Phase 2: solve a puzzle with the CP model."""
    options = options or schemas.SolveOptions()
    core = from_schema(puzzle)
    return _solve_response(core, _solve(core, options), options.encoding, images)


# --------------------------------------------------------------------------- phases 1-3
def solve_image(data: bytes, filename: str = "", options: schemas.SolveOptions | None = None,
                size: int | None = None, images: bool = True) -> schemas.SolveImageResponse:
    """Full pipeline: extract, solve (correcting OCR errors with the COP model when the
    reading is not solvable) and render the solution over the input image."""
    options = options or schemas.SolveOptions()
    t0 = time.perf_counter()
    img = _decode(data, filename)
    ex, vision_s = _extract(img, size)

    puzzle, encoding = ex.puzzle, options.encoding
    res = _solve(puzzle, options)
    corrections: list[schemas.Correction] = []
    solver_s = res.walltime
    if not res.resuelto:
        # The most likely reading is not a valid KenKen: choose the most likely
        # combination of alternative readings that is (COP).
        cop, corrected, changes = cp.resolver_con_alternativas(
            puzzle.size, ex.alternatives, tiempo_limite=min(options.time_limit, COP_TIME_LIMIT))
        solver_s += cop.walltime
        if corrected is not None:
            puzzle, encoding = corrected, "cop-alternatives"
            res = cp.resolver(corrected, codificacion=options.encoding,
                              tiempo_limite=options.time_limit,
                              verificar_unicidad=options.check_unique)
            solver_s += res.walltime
            corrections = [schemas.Correction(cell=tuple(old.anchor), read=old.label, corrected=new.label)
                           for old, new in changes]
            ex.puzzle = corrected

    solution = _solve_response(puzzle, res, encoding, images=False)
    extraction = _extract_response(img, ex, vision_s, images=False)
    imgs = None
    if images:
        solved_puzzle = from_schema(solution.puzzle)
        imgs = schemas.SolveImageImages(
            overlay=png_data_url(overlay_solution(img, ex, res.grilla) if res.resuelto else img),
            board=png_data_url(board_image(solved_puzzle, res.grilla)),
            debug=png_data_url(debug_image(ex)),
        )
    return schemas.SolveImageResponse(
        extraction=extraction,
        solution=solution,
        corrections=corrections,
        timings=schemas.PipelineTimings(vision_ms=_ms(vision_s), solver_ms=_ms(solver_s),
                                        total_ms=_ms(time.perf_counter() - t0)),
        images=imgs,
    )


def health() -> schemas.HealthResponse:
    return schemas.HealthResponse(status="ok", version=__version__)
