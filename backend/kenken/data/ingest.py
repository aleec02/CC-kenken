"""Create missing labels and (re)build the manifest.

  digital   -> exact label read from the PDF vectors (label_source "pdf", verified)
  printed   -> draft label from the vision pipeline (label_source "draft", NOT verified);
               a person must check it (`kenken data review`) and set meta.verified = true
  synthetic -> labels are written by the generator

Existing labels are never overwritten (they may contain manual corrections), unless
`overwrite_drafts` is set, which only replaces unverified drafts.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..core import cp
from ..core.render import RenderStyle, render_puzzle
from .dataset import Label, Sample, save_manifest, scan
from .pdf_labels import read_pdf_puzzle


@dataclass
class IngestReport:
    samples: int
    created: list[str]
    kept: list[str]
    failed: dict[str, str]


def _solution(puzzle) -> tuple[list[list[int]] | None, bool | None]:
    res = cp.resolver(puzzle)
    return res.grilla, res.unica


def label_digital(sample: Sample) -> Label:
    puzzle, meta = read_pdf_puzzle(sample.path)
    grid, unique = _solution(puzzle)
    if not unique:
        raise ValueError("PDF label does not have a unique solution")
    return Label(puzzle, grid, {"source": "digital", "label_source": "pdf", "verified": True, **meta})


def label_draft(sample: Sample) -> Label:
    from .. import service  # lazy: loads the vision models

    res = service.solve_image(sample.path.read_bytes(), sample.path.name, images=False)
    puzzle = service.from_schema(res.solution.puzzle)
    return Label(puzzle, res.solution.grid, {
        "source": sample.source, "label_source": "draft", "verified": False,
        "note": "Draft from the vision pipeline: check it against the image "
                "(kenken data review) and set verified to true.",
    })


def ingest(overwrite_drafts: bool = False) -> IngestReport:
    samples = scan()
    created, kept, failed = [], [], {}
    for s in samples:
        if s.has_label():
            label = s.load_label()
            if not (overwrite_drafts and not label.verified):
                kept.append(s.id)
                continue
        try:
            if s.source == "digital":
                label = label_digital(s)
            elif s.source == "printed":
                label = label_draft(s)
            else:
                failed[s.id] = "label missing (synthetic labels are written by `kenken data synth`)"
                continue
            label.save(s.label_path)
            created.append(s.id)
        except Exception as e:  # one bad sample must not stop the ingest
            failed[s.id] = f"{type(e).__name__}: {e}"
    samples = scan()  # refresh label metadata
    save_manifest(samples)
    return IngestReport(len(samples), created, kept, failed)


def review_image(sample: Sample) -> np.ndarray:
    """Input image next to the board drawn from its label, for checking a label by eye."""
    from ..vision.preprocess import load_image

    photo = load_image(str(sample.path))
    label = sample.load_label()
    board = cv2.cvtColor(render_puzzle(label.puzzle, RenderStyle(cell=90), label.solution), cv2.COLOR_RGB2BGR)
    h = 900

    def fit(img):
        return cv2.resize(img, (int(img.shape[1] * h / img.shape[0]), h), interpolation=cv2.INTER_AREA)

    status = "VERIFIED" if label.verified else "NOT VERIFIED"
    out = np.hstack([fit(photo), np.full((h, 20, 3), 255, np.uint8), fit(board)])
    cv2.putText(out, f"{sample.id}  label: {label.meta.get('label_source')}  {status}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 200), 2, cv2.LINE_AA)
    return out
