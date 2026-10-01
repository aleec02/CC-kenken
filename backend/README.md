# Backend — `kenken` Python package

Computer vision (Phase 1) → constraint programming (Phase 2) → visualization (Phase 3),
exposed through **one service layer** with two thin interfaces that mirror each other:
an HTTP API (FastAPI, for the Next.js GUI) and a CLI (`kenken`).

## Install

Python ≥ 3.10. From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -e "backend[dev]"
kenken data train-ocr                  # once: builds backend/models/ocr_glyphs.npz (~1 min)
```

Without the trained model the OCR falls back to a fonts-only model built in memory
(works, slightly less accurate on kenkenpuzzle.com puzzles).

## CLI

```
kenken extract FILE          Phase 1: image/PDF -> puzzle            == POST /api/extract
kenken solve PUZZLE.json     Phase 2: puzzle -> solution             == POST /api/solve
kenken solve-image FILE      Phases 1-3: image/PDF -> solution       == POST /api/solve-image
kenken serve                 start the HTTP API (docs at /docs)
kenken bench                 solver benchmark (report)
kenken data ...              dataset: ingest, list, review, synth, train-ocr, eval
kenken --version             == GET /api/health
```

Shared options (same names as the API parameters): `--size N`, `--encoding arith|table`,
`--time-limit S`, `--unique/--no-unique`, `--images`. Output: human-readable by default,
`--json` prints exactly the API response body, `--out DIR` saves the JSON and the images.
Exit codes: `0` ok · `1` no solution · `2` invalid input · `3` extraction failed · `4` invalid puzzle.

```bash
kenken solve-image ../data/primary/printed/6x6/1.jpeg --out ../output
kenken extract ../data/primary/digital/8x8/1.pdf --json > puzzle.json   # edit it, then:
kenken solve puzzle.json
```

## API

`kenken serve` → `http://127.0.0.1:8000` (`/docs` interactive, `/openapi.json` schema).
The full contract with examples is in [docs/API.md](../docs/API.md).

## Package layout

```
kenken/
  schemas.py        Pydantic models: the JSON contract of API and CLI
  service.py        use cases: extract(), solve(), solve_image()   <- API and CLI call only this
  api/              FastAPI app (routes, error mapping, CORS)
  cli/              Typer CLI (mirrored commands, data commands, human output)
  core/
    puzzle.py       Puzzle / Cage data model, validation
    cp.py           Phase 2: CP-SAT model (course style: X, D, C; COP for OCR correction)
    render.py       board drawing;  generator.py  random puzzles + photo augmentation
  vision/           Phase 1: preprocess (perspective), grid (size, borders, cages), ocr, extract
                    Phase 3 images: overlay.py (solution over the photo, debug view)
  data/             dataset layout + manifest, PDF labels, ingest, OCR training, evaluation, bench
```

## Phase 2 — CP model (`kenken/core/cp.py`)

- **X**: `grilla[i][j]`, **D**: `{1..N}`.
- **C1/C2**: `AllDifferent` per row and per column (global).
- **C3** per cage: `=` unary; `+` linear sum (global); `×` `AddMultiplicationEquality` (global);
  `−` and `÷` reified on an order Boolean (`b ⇒ a−b=t`, `¬b ⇒ b−a=t`); unknown operator `?`:
  one Boolean per candidate operator + `ExactlyOne`, each constraint reified.
- Alternative encoding `table`: one `AddAllowedAssignments` per cage (generalized arc consistency).
- Uniqueness: solution counter callback (course `VarArraySolutionPrinter` pattern) stopping at 2.
- **COP** (`resolver_con_alternativas`): when the OCR reading is infeasible, choose one candidate
  reading per cage (`ExactlyOne`, reified) minimizing `Σ −log p(reading)`.

Benchmark (`kenken bench --count 10`, 10 random unique puzzles per N, mean wall time):

| N | arith ms | arith branches | table ms | table branches |
|---|---|---|---|---|
| 4 | 15.4 | 0 | 11.9 | 0 |
| 6 | 25.7 | 0 | 21.7 | 0 |
| 7 | 39.1 | 358.6 | 25.0 | 0 |
| 8 | 41.5 | 0 | 33.4 | 0 |
| 9 | 57.4 | 423.0 | 40.8 | 0 |

With the table encoding, propagation alone solves every instance (0 branches).

## Data workflow

See [data/README.md](../data/README.md). In short:

```bash
kenken data ingest                         # labels (exact for PDFs, drafts for photos) + manifest
kenken data train-ocr                      # fonts + glyphs from the dev split
kenken data review --unverified -o review  # check photo drafts by eye, set meta.verified = true
kenken data eval --split test              # report numbers (held-out photos)
```

## Tests and lint

```bash
cd backend
python -m pytest -q        # CP, service, API==CLI parity, dataset consistency
ruff check kenken tests
```
