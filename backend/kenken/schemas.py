"""Public data contract of the backend.

Every API request/response body and every `kenken ... --json` output is one of these
Pydantic models, so the GUI (Next.js, via FastAPI) and the CLI always exchange exactly
the same JSON. TypeScript types can be generated from the OpenAPI schema
(`/openapi.json`), see docs/API.md.

Conventions
  * cells are [row, col], 0-indexed, row 0 at the top;
  * operators: "+", "-", "*", "/", "=" (single cell), "?" (unknown, the solver infers it);
  * times are in milliseconds;
  * images are PNG data URLs ("data:image/png;base64,...").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Op = Literal["+", "-", "*", "/", "=", "?"]
Encoding = Literal["arith", "table"]
Cell = tuple[int, int]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- puzzle
class Cage(_Model):
    target: int = Field(gt=0, description="Number printed in the cage")
    op: Op = Field(description="Cage operator")
    cells: list[Cell] = Field(min_length=1, description="Cells [row, col] of the cage")


class Puzzle(_Model):
    size: int = Field(ge=3, le=9, description="Grid size N (N x N)")
    cages: list[Cage]


# --------------------------------------------------------------------------- extract
class CageDetection(_Model):
    """How the vision step read one cage (same order as `puzzle.cages`)."""
    clue_cell: Cell = Field(description="Cell where the clue was read")
    ocr_text: str = Field(description='Raw OCR text, e.g. "12+"')
    confidence: float = Field(ge=0, le=1, description="OCR confidence of the reading")


class ExtractTimings(_Model):
    vision_ms: float


class ExtractImages(_Model):
    debug: str = Field(description="Rectified grid with detected borders and readings")


class ExtractResponse(_Model):
    puzzle: Puzzle
    detections: list[CageDetection]
    grid_corners: list[tuple[float, float]] = Field(
        description="Grid corners in the input image pixels: top-left, top-right, bottom-right, bottom-left")
    image_size: tuple[int, int] = Field(description="Input image [width, height] in pixels")
    warnings: list[str]
    timings: ExtractTimings
    images: ExtractImages | None = None


# --------------------------------------------------------------------------- solve
class SolveOptions(_Model):
    encoding: Encoding = Field("arith", description="Cage encoding of the CP model")
    time_limit: float = Field(30.0, gt=0, le=120, description="Solver time limit (seconds)")
    check_unique: bool = Field(True, description="Also verify that the solution is unique")


class SolveRequest(_Model):
    puzzle: Puzzle
    options: SolveOptions = SolveOptions()


class SolverStats(_Model):
    encoding: str
    wall_time_ms: float
    branches: int
    conflicts: int
    num_variables: int
    num_constraints: int


class SolveImages(_Model):
    board: str = Field(description="Clean board with clues and solution")


class SolveResponse(_Model):
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "MODEL_INVALID", "UNKNOWN"]
    solved: bool
    grid: list[list[int]] | None = Field(description="Solution grid[row][col], null if none")
    unique: bool | None = Field(description="null when not checked")
    puzzle: Puzzle = Field(description='The solved puzzle ("?" operators made concrete)')
    stats: SolverStats
    images: SolveImages | None = None


# --------------------------------------------------------------------------- solve-image
class Correction(_Model):
    """A clue the CP optimization model changed because the OCR reading was not solvable."""
    cell: Cell
    read: str = Field(description='What the OCR read, e.g. "10+"')
    corrected: str = Field(description='What the solver chose, e.g. "15+"')


class PipelineTimings(_Model):
    vision_ms: float
    solver_ms: float
    total_ms: float


class SolveImageImages(_Model):
    overlay: str = Field(description="Solution drawn over the input photo")
    board: str = Field(description="Clean board with clues and solution")
    debug: str = Field(description="Rectified grid with detected borders and readings")


class SolveImageResponse(_Model):
    extraction: ExtractResponse
    solution: SolveResponse
    corrections: list[Correction]
    timings: PipelineTimings
    images: SolveImageImages | None = None


# --------------------------------------------------------------------------- misc
class HealthResponse(_Model):
    status: Literal["ok"]
    version: str


class ErrorResponse(_Model):
    error: Literal["invalid_input", "invalid_puzzle", "extraction_failed", "internal_error"]
    message: str
