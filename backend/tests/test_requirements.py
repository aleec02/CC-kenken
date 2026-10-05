"""requirements.txt (repository root) must list the same packages and constraints as
backend/pyproject.toml, which stays the source of truth (the Vercel deploy installs from it)."""

import re
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")  # standard library from Python 3.11

ROOT = Path(__file__).resolve().parents[2]


def _normalize(req: str) -> str:
    return re.sub(r"\s+", "", req).lower()


def test_requirements_match_pyproject():
    pyproject = tomllib.loads((ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    expected = {_normalize(r) for r in project["dependencies"] + project["optional-dependencies"]["dev"]}

    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    listed = {_normalize(line) for line in lines if line.strip() and not line.lstrip().startswith(("#", "-e"))}

    assert listed == expected, f"missing: {expected - listed} | extra: {listed - expected}"
    assert any(line.strip() == "-e ./backend" for line in lines), "requirements.txt must install the kenken package"
