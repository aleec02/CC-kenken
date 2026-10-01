"""Command line interface.

    python -m kenken photo.jpg                   # solve a photo, outputs in ./output
    python -m kenken photo.jpg -o results --show # also open a window with the result
    python -m kenken --json puzzle.json          # solve a puzzle given as JSON (Phase 2 only)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .puzzle import Puzzle
from .solver import solve


def _print_grid(grid: list[list[int]]) -> None:
    for row in grid:
        print("  " + " ".join(str(v) for v in row))


def _print_puzzle(p: Puzzle) -> None:
    print(f"  {p.size}x{p.size} grid, {len(p.cages)} cages")
    for cage in p.cages:
        cells = " ".join(f"({r},{c})" for r, c in cage.cells)
        print(f"    {cage.label:>6}  {cells}")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="python -m kenken", description="KenKen solver: photo -> CP -> solution.")
    ap.add_argument("images", nargs="*", type=Path, help="puzzle images (.png/.jpg)")
    ap.add_argument("--json", type=Path, help="solve a puzzle JSON directly (skip vision)")
    ap.add_argument("-o", "--out", type=Path, default=Path("output"), help="output folder (default: output)")
    ap.add_argument("--encoding", choices=["arith", "table"], default="arith",
                    help="cage encoding in the CP model (default: arith)")
    ap.add_argument("--size", type=int, help="force the grid size N instead of detecting it")
    ap.add_argument("--time-limit", type=float, default=30.0, help="solver time limit in seconds")
    ap.add_argument("--show", action="store_true", help="open a window with the result")
    args = ap.parse_args(argv)

    if args.json:
        puzzle = Puzzle.load(args.json)
        res = solve(puzzle, encoding=args.encoding, time_limit=args.time_limit, check_unique=True)
        print(f"Status: {res.status}  ({res.wall_time * 1000:.1f} ms, unique={res.stats.get('unique')})")
        if res.solved:
            _print_grid(res.grid)
        return 0 if res.solved else 1

    if not args.images:
        ap.print_help()
        return 2

    from .pipeline import run  # imported lazily: loads OpenCV

    exit_code = 0
    for image in args.images:
        print(f"\n=== {image}")
        try:
            result = run(image, args.out, encoding=args.encoding, size=args.size, time_limit=args.time_limit)
        except Exception as e:  # report and continue with the next image
            print(f"  FAILED: {e}")
            exit_code = 1
            continue
        _print_puzzle(result.puzzle)
        for w in result.extraction.warnings:
            print(f"  warning: {w}")
        sol = result.solve_result
        print(f"  vision {result.timings['vision']:.2f}s | solver {result.timings['solver'] * 1000:.1f} ms "
              f"| status {sol.status} | unique={sol.stats.get('unique')}")
        if sol.solved:
            _print_grid(sol.grid)
        else:
            exit_code = 1
            print("  No solution: check the debug image (likely an OCR/border detection error).")
        for kind, path in result.outputs.items():
            print(f"  {kind:>8}: {path}")
        if args.show and "summary" in result.outputs:
            import cv2
            from .vision.preprocess import load_image

            cv2.imshow(f"KenKen - {image.name}", load_image(result.outputs["summary"]))
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
