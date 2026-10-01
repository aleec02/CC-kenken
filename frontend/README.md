# Frontend (Next.js)

The web GUI lives here. It talks only to the backend HTTP API — the complete contract
(endpoints, JSON examples, errors, TypeScript types) is in **[docs/API.md](../docs/API.md)**.

## Run the backend locally

From the repository root (see [backend/README.md](../backend/README.md) for details):

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e "backend[dev]"
kenken serve                    # http://127.0.0.1:8000  (docs at /docs)
```

## Connect Next.js

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# types generated from the backend schemas (re-run when the API changes)
npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/kenken-api.d.ts
```

CORS already allows `http://localhost:3000`.

## Screens ↔ API ↔ CLI

The GUI and the CLI are two views of the same operations; keep the same names in the UI:

| GUI action | API | CLI equivalent |
|---|---|---|
| Upload a photo/PDF and see what was detected | `POST /api/extract?images=true` | `kenken extract FILE --images` |
| Edit a cage (target/operator) and solve | `POST /api/solve` | `kenken solve PUZZLE.json` |
| One-click solve, show the solution over the photo | `POST /api/solve-image?images=true` | `kenken solve-image FILE --out DIR` |
| Show backend version | `GET /api/health` | `kenken --version` |

Useful fields for the UI:
- `detections[i].confidence` → highlight cages the OCR is unsure about;
- `corrections` → tell the user which clues the solver corrected;
- `unique === false` → warn that a clue is probably misread;
- `images.overlay` / `images.board` / `images.debug` → ready-to-use `<img src>` values.

Sample inputs to try: `data/primary/digital/**.pdf` and `data/primary/printed/**.jpeg`.
