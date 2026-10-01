"""Grid topology: size N, thick (cage) vs thin borders, and cage partition."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .preprocess import Rectified

MIN_N, MAX_N = 3, 9


@dataclass
class GridTopology:
    n: int
    cages: list[list[tuple[int, int]]]
    v_thick: np.ndarray          # (n, n-1) bool: border right of (r, c) is thick
    h_thick: np.ndarray          # (n-1, n) bool: border below (r, c) is thick
    v_strength: np.ndarray
    h_strength: np.ndarray
    size_scores: dict


def _contrast(rect: Rectified) -> np.ndarray:
    """Ink contrast image (0 = paper, 255 = black ink), lightly smoothed."""
    import cv2

    g = cv2.GaussianBlur(rect.gray, (3, 3), 0)
    return 255 - g.astype(np.int16)


def _line_coverage(contrast: np.ndarray, pos: float, band: int, lo: int, hi: int, axis: int, thr: int) -> float:
    """Fraction of positions along a (horizontal if axis=0) line where some pixel in the
    band around `pos` is darker than the threshold."""
    p0, p1 = int(round(pos - band)), int(round(pos + band)) + 1
    if axis == 0:
        strip = contrast[p0:p1, lo:hi]
        hit = strip.max(axis=0) > thr
    else:
        strip = contrast[lo:hi, p0:p1]
        hit = strip.max(axis=1) > thr
    return float(hit.mean())


def detect_size(rect: Rectified, contrast: np.ndarray | None = None) -> tuple[int, dict]:
    """Choose N as the LARGEST N in [MIN_N, MAX_N] whose predicted interior lines
    (k*S/N) are all present. Divisors of the true N also have all their lines present,
    and multiples / unrelated N predict lines through empty cell interiors."""
    c = _contrast(rect) if contrast is None else contrast
    m, S = rect.margin, rect.size
    # Noise-adaptive threshold: the grid interior is mostly blank paper, so its median
    # and MAD (robust sigma) describe the paper noise.
    inner = c[m:m + S, m:m + S]
    med = float(np.median(inner))
    sigma = 1.4826 * float(np.median(np.abs(inner - med)))
    thr = int(np.clip(med + 5 * sigma + 4, 8, 40))
    scores = {}
    for n in range(MIN_N, MAX_N + 1):
        cell = S / n
        band = max(2, int(0.08 * cell))
        lo, hi = int(m + 0.02 * S), int(m + 0.98 * S)
        covs = []
        for k in range(1, n):
            pos = m + k * cell
            covs.append(_line_coverage(c, pos, band, lo, hi, 0, thr))
            covs.append(_line_coverage(c, pos, band, lo, hi, 1, thr))
        scores[n] = min(covs)
    # A candidate is accepted when all its lines are clearly present relative to the
    # noise floor (most candidates predict lines through empty cells -> low coverage).
    floor = float(np.median(list(scores.values())))
    good = [n for n, s in scores.items() if s >= max(0.3, 5 * floor)]
    if not good:
        # Nothing clearly above the noise: take the largest N close to the best score
        # (a divisor of the true N scores at least as high, so prefer the larger one).
        best = max(scores.values())
        good = [n for n, s in scores.items() if s >= 0.9 * best]
    n = max(good)
    return n, scores


def _edge_strength(contrast: np.ndarray, x0: float, y0: float, x1: float, y1: float, win: int) -> float:
    """Ink mass of the line along the segment (x0,y0)-(x1,y1), measured on profiles
    perpendicular to it. For each profile we keep only the contiguous dark run around the
    peak, so nearby clue text separated by white paper is ignored. Returns the median."""
    vertical = abs(x1 - x0) < abs(y1 - y0)
    n_samples = 25
    vals = []
    for t in np.linspace(0.2, 0.8, n_samples):
        x, y = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        if vertical:
            prof = contrast[int(y), max(0, int(x) - win): int(x) + win + 1]
        else:
            prof = contrast[max(0, int(y) - win): int(y) + win + 1, int(x)]
        prof = prof.astype(np.float32)
        if prof.size == 0:
            continue
        # Search the peak close to the expected line position.
        centre = len(prof) // 2
        reach = max(2, win // 2)
        pk = centre - reach + int(np.argmax(prof[centre - reach: centre + reach + 1]))
        peak = prof[pk]
        if peak <= 0:
            vals.append(0.0)
            continue
        half = peak * 0.4
        a = pk
        while a > 0 and prof[a - 1] > half:
            a -= 1
        b = pk
        while b < len(prof) - 1 and prof[b + 1] > half:
            b += 1
        vals.append(float(prof[a:b + 1].sum()))
    return float(np.median(vals)) if vals else 0.0


def _two_class_threshold(values: np.ndarray, thick_ref: float) -> float:
    """Split edge strengths into thin/thick. Uses the outer border (always thick) as the
    thick reference and a low quantile as the thin reference, then refines with 1-D
    2-means in log space."""
    v = np.log(np.maximum(values, 1.0))
    lo = np.log(max(np.percentile(values, 10), 1.0))
    hi = np.log(max(thick_ref, 1.0))
    if hi - lo < np.log(1.25):
        # No clear thin population: every interior edge is as strong as the border.
        return float(np.exp(lo) * 0.7)
    for _ in range(20):
        thr = (lo + hi) / 2
        a, b = v[v <= thr], v[v > thr]
        if len(a) == 0 or len(b) == 0:
            break
        lo, hi = a.mean(), b.mean()
    return float(np.exp((lo + hi) / 2))


def detect_topology(rect: Rectified, n: int | None = None) -> GridTopology:
    contrast = _contrast(rect)
    size_scores = {}
    if n is None:
        n, size_scores = detect_size(rect, contrast)
    m, S = rect.margin, rect.size
    cell = S / n
    win = max(4, int(0.12 * cell))

    def P(i):
        return m + i * cell

    v = np.zeros((n, n - 1))
    h = np.zeros((n - 1, n))
    for r in range(n):
        for c in range(1, n):
            v[r, c - 1] = _edge_strength(contrast, P(c), P(r), P(c), P(r + 1), win)
    for r in range(1, n):
        for c in range(n):
            h[r - 1, c] = _edge_strength(contrast, P(c), P(r), P(c + 1), P(r), win)
    outer = []
    for i in range(n):
        outer.append(_edge_strength(contrast, P(0), P(i), P(0), P(i + 1), win))
        outer.append(_edge_strength(contrast, P(n), P(i), P(n), P(i + 1), win))
        outer.append(_edge_strength(contrast, P(i), P(0), P(i + 1), P(0), win))
        outer.append(_edge_strength(contrast, P(i), P(n), P(i + 1), P(n), win))

    thr = _two_class_threshold(np.concatenate([v.ravel(), h.ravel()]), float(np.median(outer)))
    v_thick, h_thick = v > thr, h > thr
    cages = _cages_from_borders(n, v_thick, h_thick)
    return GridTopology(n, cages, v_thick, h_thick, v, h, size_scores)


def _cages_from_borders(n: int, v_thick: np.ndarray, h_thick: np.ndarray) -> list[list[tuple[int, int]]]:
    """Union-find over cells: neighbours separated by a thin border share a cage."""
    parent = list(range(n * n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

    for r in range(n):
        for c in range(n - 1):
            if not v_thick[r, c]:
                union(r * n + c, r * n + c + 1)
    for r in range(n - 1):
        for c in range(n):
            if not h_thick[r, c]:
                union(r * n + c, (r + 1) * n + c)
    groups: dict[int, list[tuple[int, int]]] = {}
    for r in range(n):
        for c in range(n):
            groups.setdefault(find(r * n + c), []).append((r, c))
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0])


def merge_across_weakest_border(topo: GridTopology, cells: list[tuple[int, int]]) -> bool:
    """A cage without any clue must come from a thin border misclassified as thick:
    turn the weakest thick border around `cells` into a thin one and rebuild the cages.
    Returns False if the cage has no neighbour to merge with."""
    inside = set(cells)
    candidates = []  # (strength, kind, r, c)
    for r, c in cells:
        if c + 1 < topo.n and (r, c + 1) not in inside:
            candidates.append((topo.v_strength[r, c], "v", r, c))
        if c - 1 >= 0 and (r, c - 1) not in inside:
            candidates.append((topo.v_strength[r, c - 1], "v", r, c - 1))
        if r + 1 < topo.n and (r + 1, c) not in inside:
            candidates.append((topo.h_strength[r, c], "h", r, c))
        if r - 1 >= 0 and (r - 1, c) not in inside:
            candidates.append((topo.h_strength[r - 1, c], "h", r - 1, c))
    if not candidates:
        return False
    _, kind, r, c = min(candidates)
    if kind == "v":
        topo.v_thick[r, c] = False
    else:
        topo.h_thick[r, c] = False
    topo.cages = _cages_from_borders(topo.n, topo.v_thick, topo.h_thick)
    return True
