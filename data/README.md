# Data

| Folder | Source | Samples | Split | Labels |
|---|---|---|---|---|
| `primary/digital/` | kenkenpuzzle.com PDFs (data teammate) | 12 (4×4, 6×6, 8×8 · 4 each) | `dev` | exact, read from the PDF vectors |
| `primary/printed/` | phone photos of printed puzzles (data teammate) | 18 (4×4, 6×6, 8×8 · 6 each) | `test` | vision draft, checked by eye |
| `secondary/synthetic/` | generated (`kenken data synth`) | 28 (3×3 … 9×9) | `synthetic` | exact (generator) |

**Primary data is the main source**: the report's headline metrics are on the held-out `test` split.
`dev` may be used to tune/train the OCR (its glyphs are used by `kenken data train-ocr`),
`test` is never used for tuning. `synthetic` is for stress tests (perspective, lighting, blur, fonts).

## Layout

```
data/
  manifest.json                     index of all samples (generated: kenken data ingest)
  primary/digital/<N>x<N>/<k>.pdf   + <k>.json label
  primary/printed/<N>x<N>/<k>.jpeg  + <k>.json label
  secondary/synthetic/<N>x<N>/<k>.jpg + <k>.json label
```

Sample ids: `<source>-<N>x<N>-<k>`, e.g. `printed-8x8-02`. Raw files are never modified.

## Label format

Same puzzle schema as the API (`size`, `cages`), plus the solution and metadata:

```json
{
  "size": 4,
  "cages": [{"target": 2, "op": "/", "cells": [[0, 0], [1, 0]]}, "..."],
  "solution": [[4, 2, 1, 3], [2, 1, 3, 4], [3, 4, 2, 1], [1, 3, 4, 2]],
  "meta": {"source": "digital", "label_source": "pdf", "verified": true,
           "puzzle_id": "221608", "difficulty": "easy"}
}
```

`label_source`: `pdf` (exact), `draft` (vision draft), `manual` (corrected by hand), `generated` (synthetic).
Every verified label is checked by the CP solver: valid puzzle, unique solution equal to `solution`
(`backend/tests/test_data.py`).

## How the labels were made

- **digital**: the PDFs are vector documents — cage borders are thick filled rectangles and clues are
  text (digits Arial Black, operators Trebuchet MS Bold), so `kenken data ingest` reads them exactly
  (`backend/kenken/data/pdf_labels.py`).
- **printed**: `kenken data ingest` drafts each label with the vision pipeline; each draft was reviewed
  against its photo (`kenken data review`): every clue and its cell matched to the photo, number of cages =
  number of printed clues, and a unique CP solution. 17/18 drafts were correct; `printed-8x8-02` had 11
  misread clues and was corrected by hand (`label_source: manual`).

## Adding data

1. Put the file in the right folder, named `<k>.<ext>` inside `<N>x<N>/`.
2. `kenken data ingest` → label created (exact for PDFs, draft for photos).
3. For photos: `kenken data review <id> -o review`, fix the JSON if needed, set `"verified": true`.
4. `kenken data ingest` again to refresh the manifest.
