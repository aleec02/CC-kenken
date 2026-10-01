"""The API and the CLI must return the same JSON for the same request."""

import json

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from kenken import service
from kenken.api import app
from kenken.cli import app as cli

runner = CliRunner()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _strip_times(d):
    """Remove fields that legitimately differ between two runs (timings)."""
    if isinstance(d, dict):
        return {k: _strip_times(v) for k, v in d.items()
                if k not in ("timings", "wall_time_ms", "branches", "conflicts")}
    if isinstance(d, list):
        return [_strip_times(v) for v in d]
    return d


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    out = runner.invoke(cli, ["--version"])
    assert r.json()["version"] in out.stdout


def test_solve_api_equals_cli(client, example, tmp_path):
    body = {"puzzle": service.to_schema(example).model_dump(mode="json")}
    api = client.post("/api/solve", json=body)
    assert api.status_code == 200
    path = tmp_path / "puzzle.json"
    path.write_text(json.dumps(body))
    out = runner.invoke(cli, ["solve", str(path), "--json"])
    assert out.exit_code == 0
    assert _strip_times(json.loads(out.stdout)) == _strip_times(api.json())


def test_extract_api_equals_cli(client, clean_image, tmp_path):
    data, _, _ = clean_image
    api = client.post("/api/extract", files={"file": ("p.png", data, "image/png")})
    assert api.status_code == 200
    path = tmp_path / "p.png"
    path.write_bytes(data)
    out = runner.invoke(cli, ["extract", str(path), "--json"])
    assert out.exit_code == 0
    assert _strip_times(json.loads(out.stdout)) == _strip_times(api.json())


def test_solve_image_api_equals_cli(client, clean_image, tmp_path):
    data, _, solution = clean_image
    api = client.post("/api/solve-image?images=true", files={"file": ("p.png", data, "image/png")})
    assert api.status_code == 200 and api.json()["solution"]["grid"] == solution
    path = tmp_path / "p.png"
    path.write_bytes(data)
    out = runner.invoke(cli, ["solve-image", str(path), "--json", "--images"])
    assert out.exit_code == 0
    cli_json = json.loads(out.stdout)
    assert cli_json["images"].keys() == api.json()["images"].keys()
    assert _strip_times(cli_json) == _strip_times(api.json())


def test_cli_out_writes_files(clean_image, tmp_path):
    data, _, _ = clean_image
    path = tmp_path / "p.png"
    path.write_bytes(data)
    out = runner.invoke(cli, ["solve-image", str(path), "--out", str(tmp_path / "out")])
    assert out.exit_code == 0
    names = {p.name for p in (tmp_path / "out").iterdir()}
    assert names == {"p_solveimage.json", "p_overlay.png", "p_board.png", "p_debug.png"}


def test_errors_have_the_same_shape(client, tmp_path):
    api = client.post("/api/extract", files={"file": ("x.png", b"garbage", "image/png")})
    assert api.status_code == 400 and api.json()["error"] == "invalid_input"
    bad = {"puzzle": {"size": 3, "cages": [{"target": 3, "op": "+", "cells": [[0, 0]]}]}}
    api = client.post("/api/solve", json=bad)
    assert api.status_code == 422 and api.json()["error"] == "invalid_puzzle"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    out = runner.invoke(cli, ["solve", str(path)])
    assert out.exit_code == 4
