# KenKen: Visión Computacional + Constraint Programming

CC58 – Tópicos en Ciencias de la Computación · Trabajo 1.

End-to-end system: **photo or PDF of a KenKen → computer vision (grid, cages, clues) →
constraint programming model (OR-Tools CP-SAT) → solution drawn over the photo**,
available as a web API (for the Next.js GUI) and as a CLI with identical behaviour.

```
CC-kenken/
├── backend/     Python package `kenken`: vision, CP model, service, FastAPI API, CLI, tests
├── frontend/    Next.js GUI (consumes the API)
├── data/        primary (real photos + PDFs) and secondary (synthetic) datasets, with labels
└── docs/        API contract (API.md) and report material
```

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate                       # macOS/Linux: source .venv/bin/activate
pip install -e "backend[dev]"
kenken data train-ocr                        # once (~1 min)

kenken solve-image data/primary/printed/6x6/1.jpeg --out output   # CLI
kenken serve                                                      # API on http://127.0.0.1:8000/docs
```

| Read | For |
|---|---|
| [backend/README.md](backend/README.md) | install, CLI reference, architecture, CP model, benchmark |
| [docs/API.md](docs/API.md) | HTTP API contract (frontend) |
| [frontend/README.md](frontend/README.md) | how the GUI connects to the backend |
| [data/README.md](data/README.md) | datasets, splits, label format and provenance |

## Pipeline

1. **Vision** — illumination correction, adaptive binarization, grid localization and perspective
   correction (homography); grid size from line coverage; thin/thick borders by line ink mass (2-means);
   cages by union-find; clue OCR with a k-NN glyph classifier (fonts + real glyphs), segmentation by
   recognition for touching glyphs, clue grammar `digits+ op` and N-best readings.
2. **Constraint programming** — `AllDifferent` rows/columns, sum and multiplication global
   constraints, reified constraints for `−`, `÷` and unreadable operators, optional table encoding,
   uniqueness check; a COP picks the most likely valid readings when the OCR result is infeasible.
3. **Integration and visualization** — automatic hand-off from 1 to 2; the solution is warped back onto
   the photo with the inverse homography, plus a clean board and a debug view.

## Results (`kenken data eval`)

| Split | Images | Grid size | Cages | Clues | Solved end-to-end |
|---|---|---|---|---|---|
| **test** — printed photos | 18 | 100% | 100% | 100% | **100%** (18/18) |
| dev — digital PDFs (used for OCR training) | 12 | 100% | 100% | 100% | 100% |
| synthetic — generated, photo-like augmentation | 28 | 100% | 100% | 93.6% | 82.1% |

Mean time per photo: ~0.5 s vision + ~15–30 ms solver.

**Evaluation note.** The first evaluation of the held-out test split gave **17/18 (94.4%)**, clues 99.7%:
in `printed-8x8-02` the clue `3−` was read as `30−` because the digit and the dash touch and were cut
in the wrong place. After this error analysis *on the test split*, glyph segmentation was changed to
"segmentation by recognition" (several cut positions scored by the classifier and the clue grammar);
its only parameter (`SPLIT_PENALTY`) was tuned on the synthetic and dev splits only. The 18/18 above
is therefore no longer a fully unbiased estimate — report both numbers.
