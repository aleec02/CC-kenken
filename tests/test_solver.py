import pytest

from kenken.generator import generate_puzzle
from kenken.puzzle import Cage, Puzzle
from kenken.solver import solve, solve_with_alternatives

# 4x4 hand-made example; one valid solution is:
#   1 2 3 4
#   3 4 1 2
#   2 3 4 1
#   4 1 2 3
EXAMPLE = Puzzle(4, [
    Cage(1, "-", [(0, 0), (0, 1)]),
    Cage(24, "*", [(0, 2), (0, 3), (1, 3)]),
    Cage(1, "-", [(1, 0), (2, 0)]),
    Cage(5, "+", [(1, 1), (1, 2)]),
    Cage(3, "/", [(2, 1), (3, 1)]),
    Cage(4, "=", [(2, 2)]),
    Cage(3, "/", [(2, 3), (3, 3)]),
    Cage(4, "=", [(3, 0)]),
    Cage(2, "=", [(3, 2)]),
])


@pytest.mark.parametrize("encoding", ["arith", "table"])
def test_solves_example(encoding):
    res = solve(EXAMPLE, encoding=encoding, check_unique=True)
    assert res.solved
    assert EXAMPLE.check_solution(res.grid)


@pytest.mark.parametrize("n", [3, 5, 7, 9])
@pytest.mark.parametrize("encoding", ["arith", "table"])
def test_generated_unique_puzzles(n, encoding):
    puzzle, solution = generate_puzzle(n, seed=n)
    res = solve(puzzle, encoding=encoding, check_unique=True)
    assert res.grid == solution
    assert res.stats["unique"]


def test_unknown_operator_is_inferred():
    puzzle, solution = generate_puzzle(5, seed=3)
    for cage in puzzle.cages:
        if len(cage.cells) > 1:
            cage.op = "?"
    res = solve(puzzle)
    assert res.solved
    assert puzzle.check_solution(res.grid)


def test_cop_corrects_wrong_reading():
    puzzle, solution = generate_puzzle(4, seed=11)
    k, cage = next((k, c) for k, c in enumerate(puzzle.cages) if len(c.cells) > 1)
    wrong = Cage(cage.target + 50, cage.op, cage.cells)
    alternatives = [[(c, 0.0)] for c in puzzle.cages]
    alternatives[k] = [(wrong, 0.1), (cage, 1.0)]  # the wrong reading is the "most likely"
    res, corrected = solve_with_alternatives(4, alternatives)
    assert res.solved and corrected.check_solution(res.grid)
    assert corrected.cages[k].target == cage.target


def test_validation_detects_problems():
    bad = Puzzle(3, [Cage(3, "-", [(0, 0), (0, 1), (0, 2)])])
    errors = bad.validate()
    assert any("exactly 2 cells" in e for e in errors)
    assert any("not covered" in e for e in errors)
    with pytest.raises(ValueError):
        solve(bad)


def test_json_roundtrip(tmp_path):
    path = tmp_path / "p.json"
    EXAMPLE.save(path)
    assert Puzzle.load(path).to_dict() == EXAMPLE.to_dict()
