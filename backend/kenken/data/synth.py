"""Synthetic (secondary) dataset: random puzzles with a unique solution, rendered with
a random style and a photo-like augmentation, saved with their exact labels.

Output: data/secondary/synthetic/<N>x<N>/<k>.jpg + <k>.json
Generation is deterministic for a given seed.
"""

from __future__ import annotations

import cv2

from ..core.generator import generate_puzzle, render_sample
from .dataset import DATA_DIR, Label

AUGMENTATIONS = ("none", "light", "medium", "hard")
SIZES = (3, 4, 5, 6, 7, 8, 9)
SYNTH_DIR = DATA_DIR / "secondary" / "synthetic"


def generate(count: int = 28, seed: int = 0) -> list[str]:
    """Generate `count` samples (sizes and augmentations cycle so all combinations
    appear). Returns the written image paths."""
    written = []
    per_size: dict[int, int] = {}
    for i in range(count):
        n = SIZES[i % len(SIZES)]
        strength = AUGMENTATIONS[i % len(AUGMENTATIONS)]
        puzzle, solution = generate_puzzle(n, seed=seed + i, unique=True)
        img = render_sample(puzzle, seed + i, strength)
        k = per_size[n] = per_size.get(n, 0) + 1
        folder = SYNTH_DIR / f"{n}x{n}"
        folder.mkdir(parents=True, exist_ok=True)
        image_path = folder / f"{k}.jpg"
        cv2.imwrite(str(image_path), img)
        Label(puzzle, solution, {
            "source": "synthetic", "label_source": "generated", "verified": True,
            "seed": seed + i, "augmentation": strength,
        }).save(image_path.with_suffix(".json"))
        written.append(str(image_path))
    return written
