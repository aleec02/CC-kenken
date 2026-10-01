"""Random KenKen generator + photo-like augmentations.

Used to build a labelled synthetic dataset (image + ground-truth JSON) so the vision
pipeline can be evaluated automatically. Real photos / screenshots should be added
to the dataset as well (see README).
"""

from __future__ import annotations

import random

import cv2
import numpy as np

from .fonts import available_fonts
from .puzzle import Cage, Puzzle
from .render import RenderStyle, render_puzzle
from .solver import solve


def random_latin_square(n: int, rng: random.Random) -> list[list[int]]:
    base = [[(r + c) % n + 1 for c in range(n)] for r in range(n)]
    rng.shuffle(base)
    cols = list(range(n))
    rng.shuffle(cols)
    symbols = list(range(1, n + 1))
    rng.shuffle(symbols)
    return [[symbols[row[c] - 1] for c in cols] for row in base]


def _random_regions(n: int, rng: random.Random, max_size: int = 4) -> list[list[tuple[int, int]]]:
    unassigned = {(r, c) for r in range(n) for c in range(n)}
    regions = []
    while unassigned:
        start = min(unassigned)  # scan order keeps regions compact
        target = rng.choices([1, 2, 3, 4], weights=[1, 5, 4, 2])[0]
        target = min(target, max_size)
        region = [start]
        unassigned.remove(start)
        while len(region) < target:
            frontier = [
                (r + dr, c + dc)
                for r, c in region
                for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))
                if (r + dr, c + dc) in unassigned
            ]
            if not frontier:
                break
            nxt = rng.choice(frontier)
            unassigned.remove(nxt)
            region.append(nxt)
        regions.append(region)
    return regions


def _choose_op(values: list[int], rng: random.Random) -> tuple[str, int]:
    if len(values) == 1:
        return "=", values[0]
    if len(values) == 2:
        a, b = max(values), min(values)
        options = [("+", a + b), ("*", a * b), ("-", a - b)]
        if a % b == 0:
            options += [("/", a // b)] * 2
        return rng.choice(options)
    prod = int(np.prod(values))
    if prod <= 999 and rng.random() < 0.4:
        return "*", prod
    return "+", sum(values)


def generate_puzzle(n: int, seed: int | None = None, unique: bool = True, tries: int = 50):
    """Return (puzzle, solution). With unique=True, retries until the solution is unique."""
    rng = random.Random(seed)
    for _ in range(tries):
        sol = random_latin_square(n, rng)
        cages = []
        for region in _random_regions(n, rng):
            values = [sol[r][c] for r, c in region]
            op, target = _choose_op(values, rng)
            cages.append(Cage(target, op, region))
        puzzle = Puzzle(n, cages)
        if not unique:
            return puzzle, sol
        result = solve(puzzle, encoding="table", check_unique=True, time_limit=10)
        if result.stats.get("unique"):
            return puzzle, sol
    return puzzle, sol


def random_style(rng: random.Random) -> RenderStyle:
    fonts = list(available_fonts()) or [None]
    cell = rng.choice([70, 80, 90, 100, 120])
    grey = rng.choice([0, 0, 90, 140, 170])
    thin = rng.choice([1, 2, 2, 3])
    return RenderStyle(
        cell=cell,
        margin=rng.randint(15, 60),
        thin=thin,
        thick=max(2 * thin, rng.choice([4, 5, 6, 8])),
        thin_color=(grey, grey, grey),
        clue_font=rng.choice(fonts),
        clue_scale=rng.uniform(0.20, 0.28),
        op_style=rng.choice(["unicode", "ascii"]),
    )


# --------------------------------------------------------------------------- augmentations
def augment(img: np.ndarray, rng: random.Random, strength: str = "medium") -> np.ndarray:
    """Simulate a phone photo of a printed puzzle: background, perspective, rotation,
    uneven lighting, blur and sensor noise. strength: "none" | "light" | "medium" | "hard"."""
    if strength == "none":
        return img
    k = {"light": 0.5, "medium": 1.0, "hard": 1.6}[strength]
    h, w = img.shape[:2]

    # Place the page on a random, textured background.
    pad = int(0.15 * max(h, w))
    bg_color = np.array([rng.randint(60, 200) for _ in range(3)], dtype=np.float32)
    canvas = np.ones((h + 2 * pad, w + 2 * pad, 3), np.float32) * bg_color
    canvas += np.random.default_rng(rng.randint(0, 2**31)).normal(0, 8, canvas.shape)
    canvas[pad:pad + h, pad:pad + w] = img
    H, W = canvas.shape[:2]

    # Perspective: jitter the corners of the page.
    j = 0.06 * k * min(h, w)
    src = np.float32([[pad, pad], [pad + w, pad], [pad + w, pad + h], [pad, pad + h]])
    dst = src + np.float32([[rng.uniform(-j, j), rng.uniform(-j, j)] for _ in range(4)])
    # Small in-plane rotation around the centre.
    ang = np.deg2rad(rng.uniform(-8, 8) * k)
    ctr = np.float32([W / 2, H / 2])
    rot = np.float32([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    dst = (dst - ctr) @ rot.T + ctr
    M = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
    out = cv2.warpPerspective(canvas, M, (W, H), borderMode=cv2.BORDER_REPLICATE)

    # Uneven illumination: linear gradient + vignette-like falloff.
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    gx, gy = rng.uniform(-1, 1), rng.uniform(-1, 1)
    grad = 1 + 0.35 * k * (gx * (xx / W - 0.5) + gy * (yy / H - 0.5))
    tint = np.array([rng.uniform(0.85, 1.05) for _ in range(3)], np.float32)
    out = out * grad[..., None] * tint * rng.uniform(0.7, 1.05)

    # Blur + noise.
    if rng.random() < 0.8:
        ks = rng.choice([3, 3, 5]) if k >= 1 else 3
        out = cv2.GaussianBlur(out, (ks, ks), 0)
    out += np.random.default_rng(rng.randint(0, 2**31)).normal(0, 6 * k, out.shape)
    out = np.clip(out, 0, 255).astype(np.uint8)

    # JPEG compression artifacts.
    q = rng.randint(55, 90)
    ok, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.imdecode(enc, cv2.IMREAD_COLOR) if ok else out


def render_sample(puzzle: Puzzle, seed: int, strength: str = "medium") -> np.ndarray:
    """Render a puzzle with a random style and augmentation. Returns a BGR image."""
    rng = random.Random(seed)
    rgb = render_puzzle(puzzle, random_style(rng))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return augment(bgr, rng, strength)
