"""Data structures shared by every phase of the pipeline.

A puzzle is serialized as JSON (the bridge between Phase 1 and Phase 2):

    {
      "size": 4,
      "cages": [
        {"target": 7, "op": "+", "cells": [[0, 0], [0, 1], [1, 0]]},
        {"target": 2, "op": "/", "cells": [[0, 2], [0, 3]]},
        ...
      ]
    }

Cells are (row, col), 0-indexed. Operators: "+", "-", "*", "/", "=" (single cell) and
"?" (operator unknown, e.g. OCR could not read it: the solver chooses a consistent one).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

OPERATORS = ("+", "-", "*", "/", "=", "?")

# Aliases accepted when reading puzzles (OCR output, hand-written JSON, ...).
_OP_ALIASES = {
    "+": "+", "-": "-", "−": "-", "–": "-",
    "*": "*", "x": "*", "X": "*", "×": "*",
    "/": "/", "÷": "/", ":": "/",
    "=": "=", "": "=", "?": "?",
}


def normalize_op(op: str) -> str:
    try:
        return _OP_ALIASES[op.strip()]
    except KeyError:
        raise ValueError(f"Unknown cage operator: {op!r}") from None


@dataclass
class Cage:
    target: int
    op: str
    cells: list[tuple[int, int]]

    def __post_init__(self):
        self.op = normalize_op(self.op)
        self.cells = sorted((int(r), int(c)) for r, c in self.cells)
        if len(self.cells) == 1:
            self.op = "="

    @property
    def anchor(self) -> tuple[int, int]:
        """Top-left cell, where the clue is printed."""
        return self.cells[0]

    @property
    def label(self) -> str:
        symbol = {"+": "+", "-": "−", "*": "×", "/": "÷", "=": "", "?": "?"}[self.op]
        return f"{self.target}{symbol}"

    def candidate_ops(self) -> list[str]:
        """Operators this cage may have (more than one only when op is unknown)."""
        if self.op != "?":
            return [self.op]
        if len(self.cells) == 1:
            return ["="]
        return ["+", "*", "-", "/"] if len(self.cells) == 2 else ["+", "*"]

    def resolved(self, values: list[int]) -> Cage:
        """For an unknown operator ("?"), the cage with the operator that the solved
        values satisfy; otherwise the cage itself."""
        if self.op != "?":
            return self
        for op in self.candidate_ops():
            cage = Cage(self.target, op, self.cells)
            if cage.evaluate(values):
                return cage
        return self

    def evaluate(self, values: list[int]) -> bool:
        if self.op == "?":
            return any(Cage(self.target, op, self.cells).evaluate(values) for op in self.candidate_ops())
        if self.op == "=":
            return values[0] == self.target
        if self.op == "+":
            return sum(values) == self.target
        if self.op == "*":
            prod = 1
            for v in values:
                prod *= v
            return prod == self.target
        a, b = max(values), min(values)
        if self.op == "-":
            return a - b == self.target
        return b != 0 and a == self.target * b


@dataclass
class Puzzle:
    size: int
    cages: list[Cage] = field(default_factory=list)

    # ---- serialization -------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "cages": [
                {"target": c.target, "op": c.op, "cells": [list(x) for x in c.cells]}
                for c in self.cages
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Puzzle:
        return cls(
            size=int(data["size"]),
            cages=[Cage(int(c["target"]), c.get("op", "="), c["cells"]) for c in data["cages"]],
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8", newline="\n")

    @classmethod
    def load(cls, path: str | Path) -> Puzzle:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    # ---- helpers -------------------------------------------------------
    def cage_map(self) -> list[list[int]]:
        """Grid where each entry is the index of the cage that owns the cell."""
        grid = [[-1] * self.size for _ in range(self.size)]
        for k, cage in enumerate(self.cages):
            for r, c in cage.cells:
                grid[r][c] = k
        return grid

    def validate(self) -> list[str]:
        """Return a list of structural problems (empty list = well formed)."""
        errors = []
        n = self.size
        seen: dict[tuple[int, int], int] = {}
        for k, cage in enumerate(self.cages):
            if not cage.cells:
                errors.append(f"cage {k} has no cells")
            for cell in cage.cells:
                r, c = cell
                if not (0 <= r < n and 0 <= c < n):
                    errors.append(f"cage {k}: cell {cell} out of the {n}x{n} grid")
                elif cell in seen:
                    errors.append(f"cell {cell} belongs to cages {seen[cell]} and {k}")
                else:
                    seen[cell] = k
            if cage.op in "-/" and len(cage.cells) != 2:
                errors.append(f"cage {k}: '{cage.op}' needs exactly 2 cells, got {len(cage.cells)}")
            if cage.target <= 0:
                errors.append(f"cage {k}: target must be positive")
        missing = n * n - len(seen)
        if missing > 0:
            errors.append(f"{missing} cells are not covered by any cage")
        return errors

    def check_solution(self, grid: list[list[int]]) -> bool:
        n = self.size
        full = set(range(1, n + 1))
        if any(set(row) != full for row in grid):
            return False
        if any({grid[r][c] for r in range(n)} != full for c in range(n)):
            return False
        return all(cage.evaluate([grid[r][c] for r, c in cage.cells]) for cage in self.cages)
