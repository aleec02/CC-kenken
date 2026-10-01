import pytest

from kenken import schemas, service


def test_solve(example, example_solution):
    res = service.solve(service.to_schema(example), images=True)
    assert res.solved and res.unique and res.grid == example_solution
    assert res.images.board.startswith("data:image/png;base64,")


def test_solve_makes_unknown_operators_concrete(example):
    p = service.to_schema(example)
    p.cages[0].op = "?"
    res = service.solve(p)
    assert res.solved and res.puzzle.cages[0].op == "-"


def test_solve_invalid_puzzle():
    bad = schemas.Puzzle(size=3, cages=[schemas.Cage(target=3, op="+", cells=[(0, 0)])])
    with pytest.raises(service.InvalidPuzzle):
        service.solve(bad)


def test_extract(clean_image):
    data, puzzle, _ = clean_image
    res = service.extract(data, "p.png", images=True)
    assert service.from_schema(res.puzzle).to_dict() == puzzle.to_dict()
    assert len(res.detections) == len(puzzle.cages)
    assert len(res.grid_corners) == 4 and res.images.debug.startswith("data:image/png")


def test_solve_image(clean_image):
    data, puzzle, solution = clean_image
    res = service.solve_image(data, "p.png", images=True)
    assert res.solution.grid == solution and res.solution.unique
    assert res.corrections == []
    assert {"overlay", "board", "debug"} <= set(res.images.model_dump())


def test_bad_inputs():
    with pytest.raises(service.InvalidInput):
        service.extract(b"", "x.png")
    with pytest.raises(service.InvalidInput):
        service.extract(b"not an image", "x.png")
    with pytest.raises(service.InvalidInput):
        service.extract(b"\x89PNG", "x.png", size=12)
