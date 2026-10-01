# KenKen Solver API — contract

Base URL (development): `http://127.0.0.1:8000` · interactive docs: `/docs` · OpenAPI: `/openapi.json`

Every endpoint has an equivalent CLI command that returns **the same JSON** (`--json`), so
anything you see in the GUI can be reproduced from a terminal:

| Endpoint | CLI | Purpose |
|---|---|---|
| `GET /api/health` | `kenken --version` | Liveness + version |
| `POST /api/extract` | `kenken extract FILE` | Phase 1: image/PDF → puzzle (no solving) |
| `POST /api/solve` | `kenken solve PUZZLE.json` | Phase 2: puzzle → solution |
| `POST /api/solve-image` | `kenken solve-image FILE` | Phases 1–3 in one call |

## Conventions

- **Cells** are `[row, col]`, 0-indexed, row 0 at the top. `grid[row][col]` is the value of a cell.
- **Operators** (`op`): `"+"`, `"-"`, `"*"`, `"/"`, `"="` (single-cell cage), `"?"` (unknown: the solver infers it).
  Display them as `+ − × ÷` (and nothing for `=`).
- **Times** are milliseconds. **Images** are PNG data URLs (`data:image/png;base64,...`), usable directly in `<img src>`.
- Images are only returned when you pass `?images=true` (they are large). CLI: `--images`.
- Uploads: `multipart/form-data` with one field named `file` — `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp` or `.pdf` (first page), max 15 MB.

## Recommended GUI flows

**One shot** — upload → result:
`POST /api/solve-image?images=true` → show `images.overlay` (solution over the photo) or `images.board`.

**With user review** (recommended: the user can fix an OCR mistake before solving):
1. `POST /api/extract` → draw `puzzle` as an editable board; highlight cages with low `detections[i].confidence`.
2. The user edits targets / operators if needed.
3. `POST /api/solve` with the (edited) puzzle → show `grid`.

## `POST /api/extract`

Query: `size` (3–9, optional: force N), `images` (bool).

```bash
curl -F "file=@puzzle.jpg" "http://127.0.0.1:8000/api/extract"
```

Response `ExtractResponse` (real output, cages truncated):

```json
{
  "puzzle": {"size": 4, "cages": [
    {"target": 2, "op": "/", "cells": [[0, 0], [1, 0]]},
    {"target": 3, "op": "+", "cells": [[0, 1], [0, 2]]}
  ]},
  "detections": [
    {"clue_cell": [0, 0], "ocr_text": "2÷", "confidence": 1.0},
    {"clue_cell": [0, 1], "ocr_text": "3+", "confidence": 1.0}
  ],
  "grid_corners": [[114.0, 188.6], [1495.5, 188.6], [1494.0, 1574.4], [114.0, 1573.0]],
  "image_size": [1653, 2339],
  "warnings": [],
  "timings": {"vision_ms": 439.29},
  "images": null
}
```

- `detections[i]` describes `puzzle.cages[i]` (same order). `ocr_text` is the raw OCR (`x` = ×, `-` = −).
- `grid_corners` are in the uploaded image's pixels (top-left, top-right, bottom-right, bottom-left): use them
  to draw the detected grid over the photo. For PDFs the image is the first page rendered at 200 dpi.
- `images.debug` (with `images=true`): rectified grid with detected cage borders (red) and readings (blue).

## `POST /api/solve`

Query: `images` (bool). Body `SolveRequest`:

```json
{
  "puzzle": {"size": 4, "cages": [{"target": 2, "op": "/", "cells": [[0, 0], [1, 0]]}, "..."]},
  "options": {"encoding": "arith", "time_limit": 30, "check_unique": true}
}
```

`options` is optional (defaults shown). `encoding`: `"arith"` (arithmetic + reified constraints) or `"table"`
(table constraints). Response `SolveResponse` (real output, cages truncated):

```json
{
  "status": "OPTIMAL",
  "solved": true,
  "grid": [[4, 2, 1, 3], [2, 1, 3, 4], [3, 4, 2, 1], [1, 3, 4, 2]],
  "unique": true,
  "puzzle": {"size": 4, "cages": ["..."]},
  "stats": {"encoding": "arith", "wall_time_ms": 10.17, "branches": 0, "conflicts": 0,
            "num_variables": 22, "num_constraints": 22},
  "images": null
}
```

- `status`: `OPTIMAL` / `FEASIBLE` (solved), `INFEASIBLE` (clues contradict each other → `solved: false`, `grid: null`), `UNKNOWN` (time limit).
- `unique`: `true` / `false` / `null` (not checked or timed out). A real KenKen has exactly one solution, so
  `false` usually means a clue was misread.
- `puzzle`: the puzzle that was solved, with `"?"` operators replaced by the one the solution satisfies.
- `images.board` (with `images=true`): clean board with clues and solution.

## `POST /api/solve-image`

Query: `size`, `encoding`, `time_limit`, `check_unique`, `images` (same meaning as above). Response `SolveImageResponse` (shape; values illustrative):

```json
{
  "extraction": { "...ExtractResponse..." },
  "solution":   { "...SolveResponse..." },
  "corrections": [{"cell": [0, 4], "read": "30−", "corrected": "3−"}],
  "timings": {"vision_ms": 1332.0, "solver_ms": 29.7, "total_ms": 1393.0},
  "images": {"overlay": "data:image/png;base64,...", "board": "data:...", "debug": "data:..."}
}
```

- `corrections`: clues changed by the solver. When the OCR reading is not a valid KenKen, a constraint
  optimization model picks the most likely alternative readings that are (show these to the user).
- `extraction.puzzle` is the puzzle after corrections; `extraction.detections` keep the raw OCR.

## Errors

All errors share one shape, `ErrorResponse`:

```json
{"error": "invalid_input", "message": "Cannot decode image 'notes.txt' (supported: .png, ...)"}
```

| HTTP | `error` | When | CLI exit code |
|---|---|---|---|
| 400 | `invalid_input` | unreadable / empty / too large file | 2 |
| 422 | `extraction_failed` | no KenKen grid found in the image | 3 |
| 422 | `invalid_puzzle` | puzzle JSON is inconsistent (overlapping/missing cells, `-`/`/` cage without 2 cells, …) | 4 |
| 422 | (FastAPI `detail` list) | request does not match the schema (e.g. `size: 12`) | 2 |
| 200 | — | puzzle valid but without solution: `solved: false` | 1 |

## TypeScript types

Generate them from the running backend (keeps the frontend in sync with the schemas):

```bash
npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/kenken-api.d.ts
```

```ts
import type { components } from "@/lib/kenken-api";
type SolveImageResponse = components["schemas"]["SolveImageResponse"];

export async function solveImage(file: File): Promise<SolveImageResponse> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/solve-image?images=true`, {
    method: "POST",
    body,
  });
  if (!res.ok) throw new Error((await res.json()).message ?? res.statusText);
  return res.json();
}
```

## CORS

Allowed origin by default: `http://localhost:3000` (Next.js dev server). Change it with
`KENKEN_CORS_ORIGINS="https://my-app.vercel.app,http://localhost:3000"` before `kenken serve`.
