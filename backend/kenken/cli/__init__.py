"""Command line interface. It mirrors the HTTP API one-to-one:

    kenken extract FILE          ==  POST /api/extract        (multipart file)
    kenken solve PUZZLE.json     ==  POST /api/solve          (JSON body)
    kenken solve-image FILE      ==  POST /api/solve-image    (multipart file)
    kenken --version             ==  GET  /api/health

Same options, same names (--size, --encoding, --time-limit, --no-unique, --images) and
`--json` prints exactly the API response body. `--out DIR` saves the response JSON and
its images as files. Plus backend commands: `serve`, `bench` and `data ...`.

Exit codes: 0 ok · 1 no solution · 2 invalid input/usage · 3 extraction failed ·
4 invalid puzzle.
"""

from __future__ import annotations

import base64
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import ValidationError

from .. import __version__, schemas, service
from . import output

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="KenKen solver: photo/PDF -> computer vision -> constraint programming -> solution.")

EXIT_NO_SOLUTION, EXIT_INVALID_INPUT, EXIT_EXTRACTION, EXIT_INVALID_PUZZLE = 1, 2, 3, 4
_EXIT = {"invalid_input": EXIT_INVALID_INPUT, "extraction_failed": EXIT_EXTRACTION,
         "invalid_puzzle": EXIT_INVALID_PUZZLE}


class EncodingOpt(str, Enum):
    arith = "arith"
    table = "table"


# Options shared with the API (same names as schemas.SolveOptions / query parameters)
FileArg = Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Image (.png/.jpg) or PDF")]
SizeOpt = Annotated[Optional[int], typer.Option("--size", min=3, max=9, help="Force the grid size N")]
EncOpt = Annotated[EncodingOpt, typer.Option("--encoding", help="Cage encoding of the CP model")]
TimeOpt = Annotated[float, typer.Option("--time-limit", min=0.1, max=120, help="Solver time limit (s)")]
UniqueOpt = Annotated[bool, typer.Option("--unique/--no-unique", help="Verify the solution is unique")]
ImagesOpt = Annotated[bool, typer.Option("--images", help="Include images (base64 PNG) in the response")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Print the API response body (JSON)")]
OutOpt = Annotated[Optional[Path], typer.Option("--out", "-o", file_okay=False,
                                                help="Save the response JSON and images in this folder")]


def _version(value: bool):
    if value:
        typer.echo(f"kenken {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True,
                                          help="Show the version and exit")] = False,
):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _fail(error: service.ServiceError):
    typer.echo(f"error ({error.code}): {error}", err=True)
    raise typer.Exit(_EXIT.get(error.code, 1))


def _save(out: Path, stem: str, response) -> list[Path]:
    """Write <stem>_<kind>.json and every image of the response as <stem>_<name>.png."""
    out.mkdir(parents=True, exist_ok=True)
    data = response.model_dump(mode="json")
    written = []
    images = {}
    for holder in (data, data.get("extraction") or {}, data.get("solution") or {}):
        images.update(holder.pop("images", None) or {})
    for name, url in images.items():
        path = out / f"{stem}_{name}.png"
        path.write_bytes(base64.b64decode(url.split(",", 1)[1]))
        written.append(path)
    path = out / f"{stem}_{type(response).__name__.removesuffix('Response').lower()}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return [path] + written


def _emit(response, as_json: bool, out: Path | None, stem: str, human) -> None:
    if as_json:
        typer.echo(response.model_dump_json(indent=2))
    else:
        human(response)
    if out is not None:
        for path in _save(out, stem, response):
            if not as_json:
                typer.echo(f"  saved {path}")


def _options(encoding: EncodingOpt, time_limit: float, unique: bool) -> schemas.SolveOptions:
    return schemas.SolveOptions(encoding=encoding.value, time_limit=time_limit, check_unique=unique)


# --------------------------------------------------------------------------- mirrored commands
@app.command("extract")
def extract_cmd(file: FileArg, size: SizeOpt = None, images: ImagesOpt = False,
                as_json: JsonOpt = False, out: OutOpt = None):
    """Phase 1: read the puzzle (size, cages, clues) from an image or PDF.  [POST /api/extract]"""
    try:
        res = service.extract(file.read_bytes(), file.name, size=size, images=images or out is not None)
    except service.ServiceError as e:
        _fail(e)
    _emit(res, as_json, out, file.stem, output.print_extract)


@app.command("solve")
def solve_cmd(
    puzzle_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False,
                                                help="Puzzle JSON ({size, cages}) or SolveRequest JSON")],
    encoding: EncOpt = EncodingOpt.arith, time_limit: TimeOpt = 30.0, unique: UniqueOpt = True,
    images: ImagesOpt = False, as_json: JsonOpt = False, out: OutOpt = None,
):
    """Phase 2: solve a puzzle given as JSON with the CP model.  [POST /api/solve]"""
    try:
        data = json.loads(puzzle_file.read_text(encoding="utf-8"))
        if "puzzle" in data:   # a SolveRequest body
            request = schemas.SolveRequest.model_validate(data)
            puzzle, options = request.puzzle, request.options
        else:                  # a bare puzzle (label files may carry extra keys)
            puzzle = schemas.Puzzle.model_validate({"size": data.get("size"), "cages": data.get("cages")})
            options = _options(encoding, time_limit, unique)
    except (ValueError, ValidationError) as e:
        _fail(service.InvalidInput(f"invalid puzzle JSON: {e}"))
    try:
        res = service.solve(puzzle, options, images=images or out is not None)
    except service.ServiceError as e:
        _fail(e)
    _emit(res, as_json, out, puzzle_file.stem, output.print_solve)
    if not res.solved:
        raise typer.Exit(EXIT_NO_SOLUTION)


@app.command("solve-image")
def solve_image_cmd(file: FileArg, size: SizeOpt = None, encoding: EncOpt = EncodingOpt.arith,
                    time_limit: TimeOpt = 30.0, unique: UniqueOpt = True, images: ImagesOpt = False,
                    as_json: JsonOpt = False, out: OutOpt = None):
    """Phases 1-3: image or PDF -> solution, drawn over the image.  [POST /api/solve-image]"""
    try:
        res = service.solve_image(file.read_bytes(), file.name, _options(encoding, time_limit, unique),
                                  size=size, images=images or out is not None)
    except service.ServiceError as e:
        _fail(e)
    _emit(res, as_json, out, file.stem, output.print_solve_image)
    if not res.solution.solved:
        raise typer.Exit(EXIT_NO_SOLUTION)


# --------------------------------------------------------------------------- backend commands
@app.command("serve")
def serve_cmd(
    host: Annotated[str, typer.Option(help="Interface to listen on")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port")] = 8000,
    reload: Annotated[bool, typer.Option(help="Reload on code changes (development)")] = False,
):
    """Start the HTTP API (docs at /docs, OpenAPI schema at /openapi.json)."""
    import uvicorn

    uvicorn.run("kenken.api:app", host=host, port=port, reload=reload)


@app.command("bench")
def bench_cmd(
    sizes: Annotated[str, typer.Option(help="Comma-separated grid sizes")] = "4,5,6,7,8,9",
    count: Annotated[int, typer.Option(min=1, help="Random puzzles per size")] = 10,
    seed: Annotated[int, typer.Option(help="Random seed")] = 0,
    as_json: JsonOpt = False,
):
    """Solver benchmark: time/branches/conflicts per N and cage encoding (for the report)."""
    from ..data import bench

    rows = bench.run([int(s) for s in sizes.split(",")], count, seed)
    if as_json:
        typer.echo(json.dumps(bench.as_dicts(rows), indent=2))
    else:
        output.print_bench(rows)


from .data import data_app  # noqa: E402  (registers the `data` command group)

app.add_typer(data_app, name="data")


def main() -> None:
    app()
