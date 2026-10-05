"""Entrypoint for Vercel's Python runtime (serverless deploy of the FastAPI app).

Vercel looks for a top-level `app` (ASGI instance) in index.py/app.py/server.py/main.py
at the project root. This file only re-exports the real app from kenken.api so that
`kenken serve` / `uvicorn kenken.api:app` keep working unchanged for local development.
"""

import sys
from pathlib import Path

# Make sure the `kenken` package (this file's sibling directory) is importable
# regardless of how the Vercel runtime invokes this module.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kenken.api import app  # noqa: E402

__all__ = ["app"]
