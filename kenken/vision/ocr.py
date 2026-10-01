"""Clue OCR: segment the glyphs of a cage clue ("12+", "3÷", "240×") and classify
each glyph with a k-nearest-neighbours model.

The classifier is trained on glyphs rendered from the TrueType fonts installed on the
machine (plus Pillow's bundled font), with small rotations, blur and noise. The
training set is built on first use and cached in ~/.cache/kenken.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from ..fonts import available_fonts, load_font

CLASSES = list("0123456789") + ["+", "-", "x", "/", "÷"]
_CLASS_OF = {"−": "-", "–": "-", "×": "x", "*": "x"}
FEAT_SIZE = 20
CACHE_VERSION = 6


@dataclass
class Glyph:
    x: int
    y: int
    w: int
    h: int
    mask: np.ndarray  # uint8 {0,1} crop of the glyph


# --------------------------------------------------------------------------- segmentation
def segment_glyphs(ink: np.ndarray, min_size: int = 3, drop_border: bool = True) -> list[Glyph]:
    """Connected components of an ink mask -> glyphs sorted left to right.
    Components touching the crop's top/left border (grid lines) are removed, and
    components that overlap horizontally (the dots and bar of '÷') are merged."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    H, W = ink.shape
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 3:  # speckle noise; small parts (÷ dots) are filtered after merging
            continue
        if drop_border and (x == 0 or y == 0 or x + w >= W or y + h >= H):
            continue
        boxes.append([x, y, x + w, y + h, [i]])
    boxes.sort(key=lambda b: b[0])

    merged: list[list] = []
    for b in boxes:
        if merged:
            p = merged[-1]
            overlap = min(p[2], b[2]) - max(p[0], b[0])
            if overlap >= 0.5 * min(p[2] - p[0], b[2] - b[0]):
                p[0], p[1] = min(p[0], b[0]), min(p[1], b[1])
                p[2], p[3] = max(p[2], b[2]), max(p[3], b[3])
                p[4] += b[4]
                continue
        merged.append(b)

    glyphs = []
    for x0, y0, x1, y1, ids in merged:
        if max(x1 - x0, y1 - y0) < min_size:
            continue
        sub = labels[y0:y1, x0:x1]
        mask = np.isin(sub, ids).astype(np.uint8)
        glyphs.append(Glyph(x0, y0, x1 - x0, y1 - y0, mask))
    return glyphs


def _tight(mask: np.ndarray, x: int, y: int) -> Glyph | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return Glyph(x + x0, y + y0, x1 - x0, y1 - y0, mask[y0:y1, x0:x1])


def split_glyph(g: Glyph, k: int) -> list[Glyph]:
    """Split a component into k parts at the columns with the least ink."""
    cols = g.mask.sum(axis=0).astype(np.float32)
    step = g.w / k
    cuts = [0]
    for j in range(1, k):
        lo = max(cuts[-1] + 1, int(j * step - 0.3 * step))
        hi = min(g.w - 1, int(j * step + 0.3 * step) + 1)
        cuts.append(lo + int(np.argmin(cols[lo:hi])) if hi > lo else int(j * step))
    cuts.append(g.w)
    parts = [_tight(g.mask[:, a:b], g.x + a, g.y) for a, b in zip(cuts, cuts[1:])]
    return [q for q in parts if q is not None]


def split_candidates(g: Glyph, ref_h: int) -> list[list[Glyph]]:
    """Alternative segmentations of a possibly-fused component: as is, or split into
    2 or 3 characters when it is wide enough to contain them."""
    options = [[g]]
    if g.h >= 0.6 * ref_h and g.w > 0.85 * g.h:
        options.append(split_glyph(g, 2))
        if g.w > 1.5 * g.h:
            options.append(split_glyph(g, 3))
    return options


def glyph_features(g: Glyph, ref_h: float, ref_cy: float) -> np.ndarray:
    """Shape (normalized FEAT_SIZE x FEAT_SIZE bitmap, aspect preserved) + geometry
    relative to the tallest glyph of the clue."""
    side = max(g.w, g.h)
    canvas = np.zeros((side, side), np.float32)
    oy, ox = (side - g.h) // 2, (side - g.w) // 2
    canvas[oy:oy + g.h, ox:ox + g.w] = g.mask
    img = cv2.resize(canvas, (FEAT_SIZE, FEAT_SIZE), interpolation=cv2.INTER_AREA)
    geo = np.array([
        np.log(g.h / g.w),
        g.h / ref_h,
        g.w / ref_h,
        g.mask.mean(),
        (g.y + g.h / 2 - ref_cy) / ref_h,
    ], np.float32)
    return np.concatenate([img.ravel(), 3.0 * geo])


def _clue_features(glyphs: list[Glyph]) -> np.ndarray:
    ref = max(glyphs, key=lambda g: g.h)
    ref_cy = ref.y + ref.h / 2
    return np.stack([glyph_features(g, ref.h, ref_cy) for g in glyphs])


# --------------------------------------------------------------------------- training data
def _render_clue(text: str, font_path: str | None, size: int, rng: random.Random) -> np.ndarray:
    """Render a clue drawing each character separately with a small gap, so that the
    glyphs never touch (touching glyphs are handled at inference by split_touching)."""
    font = load_font(font_path, size)
    img = Image.new("L", (size * (len(text) + 2), size * 3), 255)
    draw = ImageDraw.Draw(img)
    x = size
    for ch in text:
        draw.text((x, size), ch, fill=0, font=font)
        x += font.getlength(ch) + rng.uniform(0.08, 0.2) * size
    arr = np.array(img)
    if rng.random() < 0.7:
        ang = rng.uniform(-4, 4)
        M = cv2.getRotationMatrix2D((arr.shape[1] / 2, arr.shape[0] / 2), ang, 1.0)
        arr = cv2.warpAffine(arr, M, (arr.shape[1], arr.shape[0]), borderValue=255)
    r = rng.random()
    if r < 0.1:    # ink bleed (bold-looking print)
        arr = cv2.erode(arr, np.ones((2, 2), np.uint8))
    elif r < 0.2:  # thin / light print
        arr = cv2.dilate(arr, np.ones((2, 2), np.uint8))
    if rng.random() < 0.3:  # low resolution: down- then up-sample
        f = rng.uniform(0.45, 0.75)
        small = cv2.resize(arr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        arr = cv2.resize(small, (arr.shape[1], arr.shape[0]), interpolation=cv2.INTER_CUBIC)
    if rng.random() < 0.6:
        arr = cv2.GaussianBlur(arr, (5, 5), rng.uniform(0.3, 1.6))
    arr = np.clip(arr + np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, 6, arr.shape), 0, 255)
    return arr.astype(np.uint8)


def _tokens(text: str) -> list[str]:
    return [_CLASS_OF.get(ch, ch) for ch in text]


def build_training_set(samples_per_font: int = 160, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    fonts: list[str | None] = list(available_fonts()) + [None]
    ops = ["+", "+", "−", "-", "×", "x", "÷", "/", ""]  # balanced per class
    X, y = [], []
    for font in fonts:
        for i in range(samples_per_font):
            digits = str(rng.randint(1, 10 ** rng.randint(1, 3) - 1))
            if i < 10:  # make sure every digit appears for every font
                digits = str(i) + digits
            text = digits + rng.choice(ops)
            size = rng.choice([22, 28, 36, 48])
            arr = _render_clue(text, font, size, rng)
            ink = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
            glyphs = segment_glyphs(ink, min_size=2, drop_border=False)
            labels = _tokens(text)
            if len(glyphs) != len(labels):
                continue  # touching/kerned glyphs: skip this sample
            X.append(_clue_features(glyphs))
            y.extend(CLASSES.index(lb) for lb in labels)
    return np.concatenate(X), np.array(y, np.int32)


# --------------------------------------------------------------------------- classifier
class GlyphClassifier:
    def __init__(self, X: np.ndarray, y: np.ndarray, k: int = 5):
        self.X, self.y, self.k = X.astype(np.float32), y, k
        self._sq = (self.X ** 2).sum(axis=1)

    @classmethod
    def load_or_train(cls, cache_dir: Path | None = None) -> GlyphClassifier:
        cache_dir = cache_dir or Path.home() / ".cache" / "kenken"
        key = hashlib.md5(repr((CACHE_VERSION, available_fonts())).encode()).hexdigest()[:10]
        path = cache_dir / f"glyphs_{key}.npz"
        if path.exists():
            data = np.load(path)
            return cls(data["X"], data["y"])
        X, y = build_training_set()
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, X=X, y=y)
        return cls(X, y)

    def votes(self, feats: np.ndarray) -> tuple[np.ndarray, list[float]]:
        """Distance-weighted kNN votes (rows sum to 1) and nearest-neighbour distances."""
        feats = feats.astype(np.float32)
        d = (feats ** 2).sum(axis=1)[:, None] + self._sq[None, :] - 2 * feats @ self.X.T
        idx = np.argsort(d, axis=1)[:, : self.k]
        dist = np.sqrt(np.maximum(np.take_along_axis(d, idx, axis=1), 0))
        out = np.zeros((len(feats), len(CLASSES)), np.float32)
        for i, (row, di) in enumerate(zip(idx, dist)):
            out[i] = np.bincount(self.y[row], weights=1.0 / (di + 1e-3), minlength=len(CLASSES))
        out /= out.sum(axis=1, keepdims=True)
        return out, dist[:, 0].tolist()

    def predict(self, feats: np.ndarray) -> tuple[list[str], list[float]]:
        votes, self.last_distances = self.votes(feats)
        best = votes.argmax(axis=1)
        return [CLASSES[b] for b in best], [float(votes[i, b]) for i, b in enumerate(best)]


_CLASSIFIER: GlyphClassifier | None = None


def get_classifier() -> GlyphClassifier:
    global _CLASSIFIER
    if _CLASSIFIER is None:
        _CLASSIFIER = GlyphClassifier.load_or_train()
    return _CLASSIFIER


# --------------------------------------------------------------------------- clue reading
@dataclass
class ClueReading:
    text: str
    target: int | None
    op: str            # "+", "-", "*", "/", "=" or "?" (no operator read)
    confidence: float
    # N-best readings [(target, op, cost)], cost = -sum(log p) over glyphs; first = best.
    alternatives: list = field(default_factory=list)


OCR_CELL = 160  # clue crops are rescaled so that a cell measures OCR_CELL pixels


def clue_ink(gray_crop: np.ndarray) -> np.ndarray:
    """Binarize a clue crop (flat-field corrected gray). The threshold is computed with
    Otsu on the text region only (away from the cell borders), so thin grey text is not
    broken by a threshold dominated by the thick black lines. Returns an empty mask when
    the crop contains only paper."""
    h, w = gray_crop.shape
    interior = gray_crop[int(0.18 * h):int(0.95 * h), int(0.15 * w):]
    if interior.size == 0 or float(np.median(interior)) - float(np.percentile(interior, 0.5)) < 50:
        return np.zeros_like(gray_crop)
    thr = cv2.threshold(interior, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[0]
    return (gray_crop < thr).astype(np.uint8) * 255


def _resolve_fused(glyphs: list[Glyph], ref_h: int) -> list[Glyph]:
    """Blur or kerning can fuse neighbouring characters ("5-" -> one blob). For every
    wide component, keep the segmentation (unsplit / split in 2 / split in 3) whose
    pieces are closest to the training glyphs (mean nearest-neighbour distance)."""
    clf = get_classifier()
    result = list(glyphs)
    for i, g in enumerate(glyphs):
        options = split_candidates(g, ref_h)
        if len(options) == 1:
            continue
        best, best_cost = options[0], None
        for j, opt in enumerate(options):
            trial = [q for q in result if q is not g] + opt
            trial.sort(key=lambda q: q.x)
            clf.predict(_clue_features(trial))
            d = clf.last_distances
            cost = float(np.mean([d[trial.index(q)] for q in opt]))
            cost *= 1.0 if j == 0 else 1.1  # prefer not splitting when in doubt
            if best_cost is None or cost < best_cost:
                best, best_cost = opt, cost
        result = [q for q in result if q is not g] + best
        result.sort(key=lambda q: q.x)
    return result


DIGITS = [CLASSES.index(c) for c in "0123456789"]
OPS = [CLASSES.index(c) for c in "+-x/÷"]


MISSING_OP_PENALTY = 2.0   # cost of assuming the operator glyph was lost


def _parse(text: str) -> tuple[int | None, str]:
    digits = "".join(ch for ch in text if ch.isdigit())
    ops = [ch for ch in text if not ch.isdigit()]
    op = {"+": "+", "-": "-", "x": "*", "/": "/", "÷": "/"}[ops[-1]] if ops else "?"
    return (int(digits) if digits else None), op


def _nbest(votes: np.ndarray, expect_op: bool, k: int = 8) -> list[tuple[str, float]]:
    """N-best decoding under the clue grammar  digits+ [op]:  every glyph but the last
    is a digit; the last one is an operator when the cage has several cells (or a digit,
    with a penalty, if the operator glyph was lost). Cost = -sum(log p)."""
    per_pos = []
    for i, v in enumerate(votes):
        last = i == len(votes) - 1
        if last and expect_op and len(votes) >= 2:
            cands = [(CLASSES[c], -np.log(max(v[c], 0.01))) for c in OPS]
            cands += [(CLASSES[c], -np.log(max(v[c], 0.01)) + MISSING_OP_PENALTY) for c in DIGITS]
        else:
            cands = [(CLASSES[c], -np.log(max(v[c], 0.01))) for c in DIGITS]
        cands.sort(key=lambda t: t[1])
        per_pos.append(cands[:3])
    combos = []
    for choice in product(*per_pos):
        text = "".join(ch for ch, _ in choice)
        if text[0] == "0":
            continue  # targets never start with 0
        combos.append((text, float(sum(c for _, c in choice))))
    combos.sort(key=lambda t: t[1])
    return combos[:k]


def clue_glyphs(gray_crop: np.ndarray, cell_px: float) -> list[Glyph]:
    """Glyphs of the clue text in a crop (grid-line fragments and noise removed),
    after rescaling the crop so that a cell measures OCR_CELL pixels."""
    f = OCR_CELL / cell_px
    if abs(f - 1) > 0.05:
        interp = cv2.INTER_CUBIC if f > 1 else cv2.INTER_AREA
        gray_crop = cv2.resize(gray_crop, None, fx=f, fy=f, interpolation=interp)
    ink = clue_ink(gray_crop)
    min_size = int(0.06 * OCR_CELL)
    glyphs = [
        g for g in segment_glyphs(ink, min_size=min_size)
        # Remove long thin fragments of grid lines that survived the border filter.
        if not (max(g.w, g.h) > 0.45 * OCR_CELL and min(g.w, g.h) < 0.1 * OCR_CELL)
    ]
    if not glyphs:
        return []
    # Keep glyphs on the main text line (the tallest glyph defines it).
    ref = max(glyphs, key=lambda g: g.h)
    return [g for g in glyphs if abs((g.y + g.h / 2) - (ref.y + ref.h / 2)) < 0.8 * ref.h]


def read_clue(gray_crop: np.ndarray, cell_px: float, expect_op: bool = True) -> ClueReading:
    """Read the clue of a cage. `expect_op` is False for single-cell cages."""
    glyphs = clue_glyphs(gray_crop, cell_px)
    if not glyphs:
        return ClueReading("", None, "?", 0.0)
    glyphs = _resolve_fused(glyphs, max(g.h for g in glyphs))
    votes, _ = get_classifier().votes(_clue_features(glyphs))
    nbest = _nbest(votes, expect_op)
    if not nbest:
        return ClueReading("", None, "?", 0.0)
    alternatives = [(*_parse(text), cost) for text, cost in nbest]
    text, cost = nbest[0]
    target, op = alternatives[0][:2]
    return ClueReading(text, target, op, float(np.exp(-cost)), alternatives)
