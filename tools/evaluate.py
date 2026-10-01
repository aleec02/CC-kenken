"""Evaluate the vision pipeline against ground truth.

Two modes:
  * --synthetic N : generate N random puzzles on the fly (sizes 3-9) and render them
                    with each augmentation strength.
  * --dataset DIR : evaluate every image in DIR that has a sibling <name>.json with the
                    ground-truth puzzle (e.g. the dataset produced by make_dataset.py, or
                    your own photos annotated by hand).

Reported metrics (use them in the report):
  size_acc   grid size N correctly detected
  cage_acc   cage partition exactly correct (whole puzzle)
  edge_acc   interior borders correctly classified thin/thick (per edge)
  clue_acc   cage clues (target + operator) correctly read (per cage, when partition OK)
  solve_acc  end-to-end: solver output equals the true solution
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kenken.generator import generate_puzzle, render_sample  # noqa: E402
from kenken.puzzle import Puzzle  # noqa: E402
from kenken.solver import solve, solve_with_alternatives  # noqa: E402
from kenken.vision import ExtractionError, extract_puzzle  # noqa: E402
from kenken.vision.preprocess import load_image  # noqa: E402


def _edges(p: Puzzle):
    own = p.cage_map()
    n = p.size
    v = [own[r][c] != own[r][c + 1] for r in range(n) for c in range(n - 1)]
    h = [own[r][c] != own[r + 1][c] for r in range(n - 1) for c in range(n)]
    return v + h


def evaluate_one(img, truth: Puzzle) -> dict:
    res = {"size": 0, "cages": 0, "edges": 0, "n_edges": 0, "clues": 0, "n_clues": 0, "solved": 0,
           "error": "", "details": []}
    t0 = time.perf_counter()
    try:
        ex = extract_puzzle(img)
    except (ExtractionError, RuntimeError, ValueError) as e:
        res["error"] = str(e)
        res["vision_time"] = time.perf_counter() - t0
        return res
    res["vision_time"] = time.perf_counter() - t0
    got = ex.puzzle
    res["size"] = int(got.size == truth.size)
    if not res["size"]:
        return res
    ge, te = _edges(got), _edges(truth)
    res["edges"] = sum(a == b for a, b in zip(ge, te))
    res["n_edges"] = len(te)
    true_cages = {tuple(c.cells): c for c in truth.cages}
    res["cages"] = int(sorted(true_cages) == sorted(tuple(c.cells) for c in got.cages))
    for cage, reading in zip(got.cages, ex.readings):
        t = true_cages.get(tuple(cage.cells))
        if t is None:
            continue
        res["n_clues"] += 1
        ok = cage.target == t.target and cage.op == t.op
        res["clues"] += ok
        if not ok:
            res["details"].append(f"{cage.anchor}: read {reading.text!r} -> {cage.label}, truth {t.label}")
    sol = solve(got, time_limit=10)
    if not sol.solved:
        sol, _ = solve_with_alternatives(got.size, ex.alternatives, time_limit=10)
        res["corrected"] = 1
    res["solve_time"] = sol.wall_time
    if sol.solved:
        # Valid for the TRUE puzzle (random synthetic puzzles may have several solutions).
        res["solved"] = int(truth.check_solution(sol.grid))
    return res


def summarize(rows: list[dict], label: str) -> None:
    k = len(rows)
    if not k:
        return
    s = lambda key: sum(r[key] for r in rows)  # noqa: E731
    edge = s("edges") / max(1, s("n_edges"))
    clue = s("clues") / max(1, s("n_clues"))
    vt = sum(r.get("vision_time", 0) for r in rows) / k
    print(f"{label:<12} n={k:<4} size_acc={s('size') / k:.3f} cage_acc={s('cages') / k:.3f} "
          f"edge_acc={edge:.4f} clue_acc={clue:.4f} solve_acc={s('solved') / k:.3f} "
          f"vision_time={vt:.2f}s")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", type=int, default=0, help="number of random puzzles")
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--dataset", type=Path, help="folder with images + ground-truth JSON")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    groups = defaultdict(list)
    if args.synthetic:
        for i in range(args.synthetic):
            seed = args.seed + i
            n = random.Random(seed).randint(3, 9)
            puzzle, _ = generate_puzzle(n, seed=seed, unique=False)
            for strength in ("none", "light", "medium", "hard"):
                row = evaluate_one(render_sample(puzzle, seed, strength), puzzle)
                groups[strength].append(row)
                groups[f"N={n}"].append(row)
                if args.verbose and (row["error"] or row["details"] or not row["solved"]):
                    print(f"seed={seed} n={n} {strength}: {row['error']} {row['details']}")
    if args.dataset:
        for img_path in sorted(args.dataset.iterdir()):
            if img_path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            gt = img_path.with_suffix(".json")
            if not gt.exists():
                continue
            data = json.loads(gt.read_text(encoding="utf-8"))
            truth = Puzzle.from_dict(data)
            row = evaluate_one(load_image(str(img_path)), truth)
            groups["dataset"].append(row)
            if args.verbose or row["error"] or row["details"] or not row["solved"]:
                print(f"{img_path.name}: solved={row['solved']} {row['error']} {row['details']}")

    all_rows = [r for key in groups if not key.startswith("N=") for r in groups[key]]
    for key in sorted(groups):
        summarize(groups[key], key)
    summarize(all_rows, "TOTAL")


if __name__ == "__main__":
    main()
