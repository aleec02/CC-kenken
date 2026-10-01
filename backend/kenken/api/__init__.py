"""HTTP API (FastAPI). Thin adapter over kenken.service; the CLI mirrors every endpoint.

    GET  /api/health          -> HealthResponse        (kenken --version)
    POST /api/extract         -> ExtractResponse       (kenken extract FILE)
    POST /api/solve           -> SolveResponse         (kenken solve PUZZLE.json)
    POST /api/solve-image     -> SolveImageResponse    (kenken solve-image FILE)

Run:  kenken serve   (or: uvicorn kenken.api:app)
Docs: http://127.0.0.1:8000/docs  ·  schema: /openapi.json  ·  contract: docs/API.md
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import __version__, schemas, service

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
_STATUS = {"invalid_input": 400, "invalid_puzzle": 422, "extraction_failed": 422, "internal_error": 500}
ERRORS = {code: {"model": schemas.ErrorResponse} for code in (400, 413, 422)}


@asynccontextmanager
async def lifespan(_: FastAPI):
    from ..vision.ocr import get_classifier

    get_classifier()   # load the OCR model once at startup, not on the first request
    yield


app = FastAPI(
    title="KenKen Solver API",
    version=__version__,
    description="Computer vision + constraint programming KenKen solver. "
                "Every endpoint has an equivalent `kenken` CLI command with the same JSON.",
    lifespan=lifespan,
)

# Next.js dev server by default; set KENKEN_CORS_ORIGINS="https://a.com,https://b.com" to change.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("KENKEN_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(service.ServiceError)
async def service_error_handler(_: Request, exc: service.ServiceError):
    body = schemas.ErrorResponse(error=exc.code, message=str(exc))
    return JSONResponse(status_code=_STATUS.get(exc.code, 500), content=body.model_dump())


async def _read(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise service.InvalidInput(f"file larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    return data


# Query parameters with the same names as the CLI options
SizeQ = Annotated[int | None, Query(ge=3, le=9, description="Force the grid size N")]
ImagesQ = Annotated[bool, Query(description="Include images (PNG data URLs) in the response")]
UploadF = Annotated[UploadFile, File(description="Puzzle image (.png/.jpg) or PDF")]


@app.get("/api/health", response_model=schemas.HealthResponse, tags=["meta"])
def health() -> schemas.HealthResponse:
    return service.health()


@app.post("/api/extract", response_model=schemas.ExtractResponse, responses=ERRORS, tags=["kenken"])
async def extract(file: UploadF, size: SizeQ = None, images: ImagesQ = False) -> schemas.ExtractResponse:
    """Phase 1: read the puzzle (size, cages, clues) from an image or PDF.
    The client may let the user fix the result and then call /api/solve."""
    return service.extract(await _read(file), file.filename or "", size=size, images=images)


@app.post("/api/solve", response_model=schemas.SolveResponse, responses=ERRORS, tags=["kenken"])
def solve(request: schemas.SolveRequest, images: ImagesQ = False) -> schemas.SolveResponse:
    """Phase 2: solve a puzzle (e.g. the result of /api/extract, possibly edited)."""
    return service.solve(request.puzzle, request.options, images=images)


@app.post("/api/solve-image", response_model=schemas.SolveImageResponse, responses=ERRORS, tags=["kenken"])
async def solve_image(
    file: UploadF,
    size: SizeQ = None,
    encoding: Annotated[schemas.Encoding, Query(description="Cage encoding of the CP model")] = "arith",
    time_limit: Annotated[float, Query(gt=0, le=120, description="Solver time limit (s)")] = 30.0,
    check_unique: Annotated[bool, Query(description="Verify the solution is unique")] = True,
    images: ImagesQ = False,
) -> schemas.SolveImageResponse:
    """Phases 1-3: image or PDF -> solution (OCR errors corrected by the CP model)."""
    options = schemas.SolveOptions(encoding=encoding, time_limit=time_limit, check_unique=check_unique)
    return service.solve_image(await _read(file), file.filename or "", options, size=size, images=images)
