import cv2
import pytest

from kenken.core.generator import generate_puzzle, render_sample
from kenken.core.puzzle import Cage, Puzzle

# 4x4 hand-made example; its unique solution is:
#   1 3 4 2 / 4 1 2 3 / 3 2 1 4 / 2 4 3 1   (rows)
EXAMPLE = Puzzle(4, [
    Cage(2, "-", [(0, 0), (0, 1)]),
    Cage(2, "/", [(0, 2), (0, 3)]),
    Cage(3, "-", [(1, 0), (1, 1)]),
    Cage(3, "+", [(1, 2), (2, 2)]),
    Cage(1, "-", [(1, 3), (2, 3)]),
    Cage(6, "*", [(2, 0), (3, 0)]),
    Cage(2, "/", [(2, 1), (3, 1)]),
    Cage(4, "+", [(3, 2), (3, 3)]),
])
EXAMPLE_SOLUTION = [[1, 3, 4, 2], [4, 1, 2, 3], [3, 2, 1, 4], [2, 4, 3, 1]]


@pytest.fixture
def example():
    return EXAMPLE


@pytest.fixture
def example_solution():
    return EXAMPLE_SOLUTION


@pytest.fixture(scope="session")
def clean_image():
    """(png bytes, puzzle, solution) of a rendered 5x5 puzzle without augmentation."""
    puzzle, solution = generate_puzzle(5, seed=2)
    ok, buf = cv2.imencode(".png", render_sample(puzzle, 2, "none"))
    assert ok
    return buf.tobytes(), puzzle, solution
