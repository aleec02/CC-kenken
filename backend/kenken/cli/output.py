"""Human-readable output of the CLI (the `--json` flag prints the raw response instead)."""

from __future__ import annotations

import typer

from .. import schemas

_SYMBOL = {"+": "+", "-": "−", "*": "×", "/": "÷", "=": "", "?": "?"}


def label(cage: schemas.Cage) -> str:
    return f"{cage.target}{_SYMBOL[cage.op]}"


def _cells(cells) -> str:
    return " ".join(f"({r},{c})" for r, c in cells)


def print_puzzle(puzzle: schemas.Puzzle, detections: list[schemas.CageDetection] | None = None) -> None:
    typer.echo(f"  {'#':>3}  {'clue':<6} {'ocr':<7} {'conf':>5}  cells")
    for i, cage in enumerate(puzzle.cages, 1):
        det = detections[i - 1] if detections else None
        ocr = f'"{det.ocr_text}"' if det else ""
        conf = f"{det.confidence:.2f}" if det else ""
        typer.echo(f"  {i:>3}  {label(cage):<6} {ocr:<7} {conf:>5}  {_cells(cage.cells)}")


def print_grid(grid: list[list[int]]) -> None:
    for row in grid:
        typer.echo("    " + " ".join(str(v) for v in row))


def _warnings(warnings: list[str]) -> None:
    for w in warnings:
        typer.echo(f"  warning: {w}")


def print_extract(res: schemas.ExtractResponse) -> None:
    p = res.puzzle
    typer.echo(f"Puzzle {p.size}x{p.size} · {len(p.cages)} cages · vision {res.timings.vision_ms:.0f} ms")
    print_puzzle(p, res.detections)
    _warnings(res.warnings)


def print_solve(res: schemas.SolveResponse) -> None:
    unique = {True: "unique", False: "NOT unique", None: "uniqueness not checked"}[res.unique]
    typer.echo(f"Status {res.status} · {unique} · solver {res.stats.wall_time_ms:.1f} ms "
               f"({res.stats.encoding}, {res.stats.branches} branches, {res.stats.conflicts} conflicts)")
    if res.grid:
        print_grid(res.grid)
    else:
        typer.echo("  no solution: the puzzle is inconsistent (check the clues)")


def print_solve_image(res: schemas.SolveImageResponse) -> None:
    print_extract(res.extraction)
    for c in res.corrections:
        typer.echo(f"  corrected by CP: ({c.cell[0]},{c.cell[1]}) {c.read} -> {c.corrected}")
    print_solve(res.solution)
    t = res.timings
    typer.echo(f"Total {t.total_ms:.0f} ms (vision {t.vision_ms:.0f} ms, solver {t.solver_ms:.1f} ms)")


def print_table(rows: list[dict], columns: list[str]) -> None:
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in columns}
    typer.echo("  ".join(c.ljust(widths[c]) for c in columns))
    for r in rows:
        typer.echo("  ".join(str(r[c]).ljust(widths[c]) for c in columns))


def print_bench(rows) -> None:
    from dataclasses import asdict

    print_table([asdict(r) for r in rows], ["size", "encoding", "puzzles", "mean_ms", "max_ms",
                                            "mean_branches", "mean_conflicts", "variables", "constraints"])
