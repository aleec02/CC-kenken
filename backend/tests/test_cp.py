import pytest

from kenken.core import cp
from kenken.core.generator import generate_puzzle
from kenken.core.puzzle import Cage, Puzzle


@pytest.mark.parametrize("codificacion", ["arith", "table"])
def test_example_unique(example, example_solution, codificacion):
    r = cp.resolver(example, codificacion=codificacion)
    assert r.estado == "OPTIMAL"
    assert r.grilla == example_solution
    assert r.unica is True


@pytest.mark.parametrize("n", [3, 5, 7, 9])
@pytest.mark.parametrize("codificacion", ["arith", "table"])
def test_generated_puzzles(n, codificacion):
    puzzle, solution = generate_puzzle(n, seed=n)
    r = cp.resolver(puzzle, codificacion=codificacion)
    assert r.grilla == solution and r.unica


def test_counts_two_solutions_when_ambiguous():
    # one "6+" cage per row: every 3x3 Latin square satisfies it -> many solutions
    p = Puzzle(3, [Cage(6, "+", [(r, 0), (r, 1), (r, 2)]) for r in range(3)])
    r = cp.resolver(p)
    assert r.resuelto and r.unica is False


def test_unknown_operator_is_inferred():
    puzzle, _ = generate_puzzle(5, seed=3)
    for cage in puzzle.cages:
        if len(cage.cells) > 1:
            cage.op = "?"
    r = cp.resolver(puzzle)
    assert r.resuelto and puzzle.check_solution(r.grilla)


def test_infeasible_puzzle():
    p = Puzzle(3, [Cage(9, "+", [(0, 0), (0, 1)])] +
               [Cage(1, "=", [(r, c)]) for r in range(3) for c in range(3) if (r, c) not in ((0, 0), (0, 1))])
    assert cp.resolver(p).estado == "INFEASIBLE"


def test_cop_corrects_a_wrong_reading():
    puzzle, solution = generate_puzzle(4, seed=11)
    k, cage = next((k, c) for k, c in enumerate(puzzle.cages) if len(c.cells) > 1)
    wrong = Cage(cage.target + 50, cage.op, cage.cells)
    alternativas = [[(c, 0.0)] for c in puzzle.cages]
    alternativas[k] = [(wrong, 0.1), (cage, 1.0)]   # the wrong reading is the most likely
    r, corregido, cambios = cp.resolver_con_alternativas(4, alternativas)
    assert r.resuelto and corregido.check_solution(r.grilla)
    assert corregido.cages[k].target == cage.target
    assert cambios == [(wrong, cage)]


def test_invalid_puzzle_is_rejected():
    bad = Puzzle(3, [Cage(3, "-", [(0, 0), (0, 1), (0, 2)])])
    errors = bad.validate()
    assert any("exactly 2 cells" in e for e in errors)
    assert any("not covered" in e for e in errors)
    with pytest.raises(ValueError):
        cp.resolver(bad)
