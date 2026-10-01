"""Solver benchmark (report: complexity and response times of the CP model).

For each grid size N, `count` random puzzles with a unique solution are solved with both
cage encodings ("arith" and "table"). Reported per (N, encoding): mean / max wall time,
mean branches and conflicts, and model size.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass

from ..core import cp
from ..core.generator import generate_puzzle


@dataclass
class BenchRow:
    size: int
    encoding: str
    puzzles: int
    mean_ms: float
    max_ms: float
    mean_branches: float
    mean_conflicts: float
    variables: float
    constraints: float


def run(sizes: list[int], count: int = 10, seed: int = 0) -> list[BenchRow]:
    rows = []
    for n in sizes:
        puzzles = [generate_puzzle(n, seed=seed + 1000 * n + i)[0] for i in range(count)]
        for encoding in ("arith", "table"):
            results = [cp.resolver(p, codificacion=encoding, verificar_unicidad=False) for p in puzzles]
            ms = [r.walltime * 1000 for r in results]
            rows.append(BenchRow(
                size=n, encoding=encoding, puzzles=count,
                mean_ms=round(statistics.mean(ms), 2), max_ms=round(max(ms), 2),
                mean_branches=round(statistics.mean(r.estadisticas["branches"] for r in results), 1),
                mean_conflicts=round(statistics.mean(r.estadisticas["conflicts"] for r in results), 1),
                variables=round(statistics.mean(r.estadisticas["num_variables"] for r in results), 1),
                constraints=round(statistics.mean(r.estadisticas["num_restricciones"] for r in results), 1),
            ))
    return rows


def as_dicts(rows: list[BenchRow]) -> list[dict]:
    return [asdict(r) for r in rows]
