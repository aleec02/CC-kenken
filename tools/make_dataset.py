"""Generate a labelled synthetic KenKen dataset: <name>.png + <name>.json (ground truth).

Each puzzle has a unique solution and is rendered with a random style (font, line
widths, grey thin lines, unicode/ascii operators) and a photo-like augmentation
(background, perspective, rotation, uneven lighting, blur, noise, JPEG).

    python tools/make_dataset.py --out data/synthetic --count 12
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kenken.generator import generate_puzzle, render_sample  # noqa: E402

STRENGTHS = ["none", "light", "medium", "hard"]
SIZES = [3, 4, 5, 6, 7, 8, 9]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        seed = args.seed + i
        n = SIZES[i % len(SIZES)]
        strength = STRENGTHS[i % len(STRENGTHS)]
        puzzle, solution = generate_puzzle(n, seed=seed, unique=True)
        img = render_sample(puzzle, seed, strength)
        name = f"synth_{i:02d}_{n}x{n}_{strength}"
        cv2.imwrite(str(args.out / f"{name}.jpg"), img)
        data = puzzle.to_dict()
        data["solution"] = solution
        data["augmentation"] = strength
        (args.out / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"{name}.jpg  ({len(puzzle.cages)} cages)")


if __name__ == "__main__":
    main()
