"""Train the clue OCR model: font-rendered glyphs + real glyphs harvested from the dev
split (digital PDFs, whose labels are exact). The test split is never used here.

Harvesting: for each dev sample the vision pipeline locates the grid; each labelled
cage's clue crop is segmented into glyphs and, when the number of glyphs matches the
label text (e.g. "12+" -> 3 glyphs), the glyphs are added with their true classes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..vision import ocr
from ..vision.extract import _clue_crop, extract_puzzle
from ..vision.preprocess import load_image
from .dataset import load_manifest, select

_OP_GLYPH = {"+": "+", "-": "-", "*": "x", "/": "÷"}   # how kenkenpuzzle.com prints them


@dataclass
class TrainReport:
    font_glyphs: int
    real_glyphs: int
    samples_used: list[str]
    path: str


def harvest_glyphs(split: str = "dev") -> tuple[np.ndarray, np.ndarray, list[str]]:
    X, y, used = [], [], []
    for sample in select(load_manifest(), split=split):
        if not (sample.has_label() and sample.verified):
            continue
        label = sample.load_label()
        ex = extract_puzzle(load_image(str(sample.path)), n=label.puzzle.size)
        cell_px = ex.rect.size / label.puzzle.size
        for cage in label.puzzle.cages:
            text = str(cage.target) + (_OP_GLYPH.get(cage.op, "") if len(cage.cells) > 1 else "")
            glyphs = ocr.clue_glyphs(_clue_crop(ex.rect, label.puzzle.size, *cage.anchor), cell_px)
            if len(glyphs) != len(text):
                continue
            X.append(ocr._clue_features(glyphs))
            y.extend(ocr.CLASSES.index(ch) for ch in text)
        used.append(sample.id)
    if not X:
        return np.zeros((0, ocr.FEAT_SIZE ** 2 + 5), np.float32), np.zeros(0, np.int32), used
    return np.concatenate(X), np.array(y, np.int32), used


def train(use_dev: bool = True) -> TrainReport:
    Xr, yr, used = harvest_glyphs("dev") if use_dev else (None, None, [])
    clf = ocr.train_classifier((Xr, yr) if use_dev else None)
    real = 0 if Xr is None else len(Xr)
    clf.save(ocr.MODEL_PATH, {"real_glyphs": real, "samples": used})
    ocr.set_classifier(clf)
    return TrainReport(len(clf.X) - real, real, used, str(ocr.MODEL_PATH))
