import pytest

from kenken.generator import generate_puzzle, render_sample
from kenken.pipeline import run
from kenken.solver import solve
from kenken.vision import extract_puzzle


@pytest.mark.parametrize("n,seed", [(4, 1), (6, 2), (9, 3)])
def test_clean_image_roundtrip(n, seed):
    """A clean rendered puzzle must be extracted exactly and solved."""
    puzzle, solution = generate_puzzle(n, seed=seed)
    ex = extract_puzzle(render_sample(puzzle, seed, "none"))
    assert ex.puzzle.size == n
    assert sorted(c.cells for c in ex.puzzle.cages) == sorted(c.cells for c in puzzle.cages)
    res = solve(ex.puzzle)
    assert res.grid == solution


def test_photo_like_image_grid(tmp_path):
    """Perspective / lighting / noise must not break grid and cage detection."""
    puzzle, _ = generate_puzzle(5, seed=7)
    ex = extract_puzzle(render_sample(puzzle, 7, "medium"))
    assert ex.puzzle.size == 5
    assert sorted(c.cells for c in ex.puzzle.cages) == sorted(c.cells for c in puzzle.cages)


def test_pipeline_writes_outputs(tmp_path):
    import cv2

    puzzle, solution = generate_puzzle(4, seed=5)
    img_path = tmp_path / "puzzle.png"
    cv2.imwrite(str(img_path), render_sample(puzzle, 5, "light"))
    result = run(img_path, tmp_path / "out")
    assert result.solve_result.solved
    for key in ("puzzle", "solution", "overlay", "board", "summary", "debug"):
        assert (tmp_path / "out").joinpath(result.outputs[key].split("\\")[-1].split("/")[-1]).exists()
