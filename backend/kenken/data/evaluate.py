"""Evaluate the pipeline on labelled samples (metrics for the report).

Per sample, two runs of the public service:
  * extract()      -> vision metrics (before any solver correction)
  * solve_image()  -> end-to-end result (with the COP correction of OCR errors)

Metrics
  size_acc     grid size N detected correctly                      (per sample)
  cage_acc     cage partition exactly correct                      (per sample)
  edge_acc     interior borders classified correctly thin/thick    (per edge)
  clue_acc     target and operator read correctly                  (per cage, matched cages)
  solve_acc    end-to-end: the returned grid solves the TRUE puzzle (per sample)
  vision_ms / solver_ms  mean times
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field

from .. import service
from ..core.puzzle import Puzzle
from .dataset import Sample


@dataclass
class SampleResult:
    id: str
    split: str
    size: int
    size_ok: bool = False
    cages_ok: bool = False
    edges_ok: int = 0
    edges: int = 0
    clues_ok: int = 0
    clues: int = 0
    solved: bool = False
    corrections: int = 0
    vision_ms: float = 0.0
    solver_ms: float = 0.0
    error: str = ""
    clue_errors: list[str] = field(default_factory=list)


@dataclass
class Summary:
    group: str
    samples: int
    size_acc: float
    cage_acc: float
    edge_acc: float
    clue_acc: float
    solve_acc: float
    vision_ms: float
    solver_ms: float


def _edges(p: Puzzle) -> list[bool]:
    own, n = p.cage_map(), p.size
    return ([own[r][c] != own[r][c + 1] for r in range(n) for c in range(n - 1)]
            + [own[r][c] != own[r + 1][c] for r in range(n - 1) for c in range(n)])


def evaluate_sample(sample: Sample) -> SampleResult:
    truth = sample.load_label().puzzle
    data = sample.path.read_bytes()
    res = SampleResult(sample.id, sample.split, sample.size)
    try:
        ext = service.extract(data, sample.path.name)
        full = service.solve_image(data, sample.path.name, images=False)
    except service.ServiceError as e:
        res.error = f"{e.code}: {e}"
        return res
    got = service.from_schema(ext.puzzle)
    res.vision_ms, res.solver_ms = full.timings.vision_ms, full.timings.solver_ms
    res.corrections = len(full.corrections)
    res.size_ok = got.size == truth.size
    if res.size_ok:
        ge, te = _edges(got), _edges(truth)
        res.edges, res.edges_ok = len(te), sum(a == b for a, b in zip(ge, te))
        true_cages = {tuple(c.cells): c for c in truth.cages}
        res.cages_ok = sorted(true_cages) == sorted(tuple(c.cells) for c in got.cages)
        for cage, det in zip(got.cages, ext.detections):
            t = true_cages.get(tuple(cage.cells))
            if t is None:
                continue
            res.clues += 1
            if cage.target == t.target and cage.op == t.op:
                res.clues_ok += 1
            else:
                res.clue_errors.append(f"{cage.anchor}: read {det.ocr_text!r} -> {cage.label}, truth {t.label}")
    grid = full.solution.grid
    res.solved = grid is not None and grid_ok(truth, grid)
    return res


def grid_ok(truth: Puzzle, grid: list[list[int]]) -> bool:
    return len(grid) == truth.size and truth.check_solution(grid)


def summarize(results: list[SampleResult], group: str) -> Summary:
    k = max(1, len(results))

    def mean(values):
        values = list(values)
        return round(sum(values) / max(1, len(values)), 4)

    return Summary(
        group=group, samples=len(results),
        size_acc=mean(r.size_ok for r in results),
        cage_acc=mean(r.cages_ok for r in results),
        edge_acc=round(sum(r.edges_ok for r in results) / max(1, sum(r.edges for r in results)), 4),
        clue_acc=round(sum(r.clues_ok for r in results) / max(1, sum(r.clues for r in results)), 4),
        solve_acc=mean(r.solved for r in results),
        vision_ms=round(sum(r.vision_ms for r in results) / k, 1),
        solver_ms=round(sum(r.solver_ms for r in results) / k, 1),
    )


def evaluate(samples: list[Sample]) -> tuple[list[SampleResult], list[Summary]]:
    results = [evaluate_sample(s) for s in samples]
    groups: dict[str, list[SampleResult]] = defaultdict(list)
    for r in results:
        groups[r.split].append(r)
        groups[f"{r.split} {r.size}x{r.size}"].append(r)
    summaries = [summarize(groups[g], g) for g in sorted(groups)]
    summaries.append(summarize(results, "all"))
    return results, summaries


def as_dict(results: list[SampleResult], summaries: list[Summary]) -> dict:
    return {"summary": [asdict(s) for s in summaries], "samples": [asdict(r) for r in results]}
