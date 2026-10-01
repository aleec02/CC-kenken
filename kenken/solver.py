"""Phase 2: Constraint Programming model of KenKen (OR-Tools CP-SAT).

Formal model
------------
Variables:   x[r][c]  for r, c in 0..n-1
Domains:     x[r][c] in {1, ..., n}
Constraints:
  * AllDifferent(x[r][0..n-1])            for every row r        (global)
  * AllDifferent(x[0..n-1][c])            for every column c     (global)
  * For each cage C with target t and operator op:
      "="  x_a = t
      "+"  sum(x_i for i in C) = t                                (global: linear sum)
      "*"  prod(x_i for i in C) = t                               (global: multiplication)
      "-"  |x_a - x_b| = t   -> reified: b => x_a - x_b = t,  not b => x_b - x_a = t
      "/"  max/min = t       -> reified: b => x_a = t*x_b,    not b => x_b = t*x_a
      "?"  operator unknown (OCR miss): one Boolean per candidate operator,
           ExactlyOne(bools), each operator constraint reified on its Boolean.

Two cage encodings are available (compare them in the report):
  * "arith": the arithmetic constraints above (reification for - and /).
  * "table": every non-trivial cage becomes a table constraint (AddAllowedAssignments)
    listing the tuples that satisfy the arithmetic AND the row/column distinctness inside
    the cage. This gives stronger propagation (generalized arc consistency per cage).
    Cages whose tuple space is too large fall back to "arith".
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .puzzle import Cage, Puzzle

MAX_TABLE_TUPLES = 200_000


@dataclass
class SolveResult:
    status: str
    grid: list[list[int]] | None
    wall_time: float
    stats: dict = field(default_factory=dict)

    @property
    def solved(self) -> bool:
        return self.grid is not None


def _cage_tuples(cage: Cage, n: int) -> list[tuple[int, ...]]:
    """All value tuples for the cage cells that satisfy its arithmetic and are
    distinct for cells sharing a row or column."""
    cells = cage.cells
    conflicts = [
        (i, j)
        for i, j in itertools.combinations(range(len(cells)), 2)
        if cells[i][0] == cells[j][0] or cells[i][1] == cells[j][1]
    ]
    tuples = []
    for values in itertools.product(range(1, n + 1), repeat=len(cells)):
        if any(values[i] == values[j] for i, j in conflicts):
            continue
        if cage.evaluate(list(values)):
            tuples.append(values)
    return tuples


def _add_arith_cage(model: cp_model.CpModel, cage: Cage, xs: list, k: int, n: int) -> None:
    """Post the arithmetic constraint of a cage. If the operator is unknown ("?"), one
    Boolean per candidate operator is created (ExactlyOne) and each operator's constraint
    is reified on its Boolean."""
    t = cage.target
    ops = cage.candidate_ops()
    if len(ops) == 1:
        _post_op(model, ops[0], t, xs, k, n, enforce=None)
        return
    choice = [model.NewBoolVar(f"cage{k}_is_{op}") for op in ops]
    model.AddExactlyOne(choice)
    for op, lit in zip(ops, choice):
        _post_op(model, op, t, xs, k, n, enforce=lit)


def _post_op(model, op, t, xs, k, n, enforce):
    def add(ct):
        return ct.OnlyEnforceIf(enforce) if enforce is not None else ct

    if op == "=":
        add(model.Add(xs[0] == t))
    elif op == "+":
        add(model.Add(sum(xs) == t))
    elif op == "*":
        if enforce is None:
            model.AddMultiplicationEquality(t, xs)
        else:
            # Multiplication does not accept enforcement literals: reify through an
            # auxiliary product variable.
            prod = model.NewIntVar(1, n ** len(xs), f"cage{k}_prod")
            model.AddMultiplicationEquality(prod, xs)
            add(model.Add(prod == t))
    elif op in "-/":
        a, b = xs
        order = model.NewBoolVar(f"cage{k}_{'sub' if op == '-' else 'div'}_order")
        if op == "-":
            first, second = a - b == t, b - a == t
        else:
            first, second = a == t * b, b == t * a
        lits = [order] if enforce is None else [order, enforce]
        model.Add(first).OnlyEnforceIf(lits)
        lits = [order.Not()] if enforce is None else [order.Not(), enforce]
        model.Add(second).OnlyEnforceIf(lits)
    else:
        raise ValueError(f"Unsupported operator {op!r}")


def build_model(puzzle: Puzzle, encoding: str = "arith"):
    """Build the CP-SAT model. Returns (model, x) where x[r][c] are the cell variables."""
    if encoding not in ("arith", "table"):
        raise ValueError("encoding must be 'arith' or 'table'")
    errors = puzzle.validate()
    if errors:
        raise ValueError("Invalid puzzle:\n  " + "\n  ".join(errors))

    n = puzzle.size
    model = cp_model.CpModel()
    x = [[model.NewIntVar(1, n, f"x_{r}_{c}") for c in range(n)] for r in range(n)]

    for i in range(n):
        model.AddAllDifferent(x[i])
        model.AddAllDifferent([x[r][i] for r in range(n)])

    for k, cage in enumerate(puzzle.cages):
        xs = [x[r][c] for r, c in cage.cells]
        use_table = (
            encoding == "table"
            and cage.op != "="
            and n ** len(cage.cells) <= MAX_TABLE_TUPLES
        )
        if use_table:
            tuples = _cage_tuples(cage, n)
            if not tuples:
                # No assignment satisfies this cage: make the model trivially infeasible.
                model.AddBoolOr([])
            else:
                model.AddAllowedAssignments(xs, tuples)
        else:
            _add_arith_cage(model, cage, xs, k, n)
    return model, x


def solve(
    puzzle: Puzzle,
    encoding: str = "arith",
    time_limit: float = 30.0,
    check_unique: bool = False,
    workers: int = 8,
) -> SolveResult:
    """Solve the puzzle. With check_unique=True the solver also searches for a
    second solution and reports stats['unique']."""
    t0 = time.perf_counter()
    model, x = build_model(puzzle, encoding)
    n = puzzle.size

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    status = solver.Solve(model)
    status_name = solver.StatusName(status)

    grid = None
    stats = {
        "encoding": encoding,
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "solver_wall_time": solver.WallTime(),
        "num_variables": len(model.Proto().variables),
        "num_constraints": len(model.Proto().constraints),
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        grid = [[solver.Value(x[r][c]) for c in range(n)] for r in range(n)]
        if check_unique:
            # Forbid the found solution and look for another one.
            diffs = []
            for r in range(n):
                for c in range(n):
                    b = model.NewBoolVar("")
                    model.Add(x[r][c] != grid[r][c]).OnlyEnforceIf(b)
                    model.Add(x[r][c] == grid[r][c]).OnlyEnforceIf(b.Not())
                    diffs.append(b)
            model.AddBoolOr(diffs)
            second = cp_model.CpSolver()
            second.parameters.max_time_in_seconds = time_limit
            second.parameters.num_workers = workers
            stats["unique"] = second.Solve(model) == cp_model.INFEASIBLE
    return SolveResult(status_name, grid, time.perf_counter() - t0, stats)


def solve_with_alternatives(
    size: int,
    alternatives: list[list[tuple[Cage, float]]],
    time_limit: float = 30.0,
    workers: int = 8,
) -> tuple[SolveResult, Puzzle | None]:
    """Constraint OPTIMIZATION model that fixes OCR errors.

    Every cage k comes with candidate readings a (target, operator) and an OCR cost
    c_ka = -log p(reading). One Boolean y_ka per candidate:
        ExactlyOne(y_k*)                          for every cage k
        y_ka  =>  cage constraint of reading a    (reified)
        minimize  sum_ka  c_ka * y_ka
    The solver returns the most likely reading of the image that is a valid KenKen.
    Returns (result, corrected puzzle)."""
    t0 = time.perf_counter()
    n = size
    model = cp_model.CpModel()
    x = [[model.NewIntVar(1, n, f"x_{r}_{c}") for c in range(n)] for r in range(n)]
    for i in range(n):
        model.AddAllDifferent(x[i])
        model.AddAllDifferent([x[r][i] for r in range(n)])

    choice_vars = []
    cost_terms = []
    for k, alts in enumerate(alternatives):
        xs = [x[r][c] for r, c in alts[0][0].cells]
        if len(alts) == 1:
            _add_arith_cage(model, alts[0][0], xs, k, n)
            choice_vars.append(None)
            continue
        lits = [model.NewBoolVar(f"cage{k}_alt{a}") for a in range(len(alts))]
        model.AddExactlyOne(lits)
        for a, ((cage, cost), lit) in enumerate(zip(alts, lits)):
            _post_op(model, cage.op, cage.target, xs, f"{k}_{a}", n, enforce=lit)
            cost_terms.append(int(round(cost * 100)) * lit)
        choice_vars.append(lits)
    if cost_terms:
        model.Minimize(sum(cost_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    status = solver.Solve(model)
    stats = {
        "encoding": "cop-alternatives",
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "solver_wall_time": solver.WallTime(),
        "num_variables": len(model.Proto().variables),
        "num_constraints": len(model.Proto().constraints),
    }
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResult(solver.StatusName(status), None, time.perf_counter() - t0, stats), None

    grid = [[solver.Value(x[r][c]) for c in range(n)] for r in range(n)]
    cages, corrections = [], []
    for alts, lits in zip(alternatives, choice_vars):
        if lits is None:
            cages.append(alts[0][0])
            continue
        chosen = next(a for a, lit in enumerate(lits) if solver.Value(lit))
        cage = alts[chosen][0]
        if chosen != 0:
            corrections.append(f"{cage.anchor}: {alts[0][0].label} -> {cage.label}")
        cages.append(cage)
    stats["corrections"] = corrections
    stats["objective"] = solver.ObjectiveValue() / 100 if cost_terms else 0.0
    return SolveResult(solver.StatusName(status), grid, time.perf_counter() - t0, stats), Puzzle(n, cages)
