"""Dataset checks (skipped when the data folder is not available)."""

import pytest

from kenken.core import cp
from kenken.data.dataset import DATA_DIR, load_manifest, select
from kenken.data.pdf_labels import read_pdf_puzzle

pytestmark = pytest.mark.skipif(not (DATA_DIR / "manifest.json").exists(), reason="no dataset")


def test_pdf_labels_match_saved_labels():
    for s in select(load_manifest(), source="digital"):
        puzzle, meta = read_pdf_puzzle(s.path)
        label = s.load_label()
        assert puzzle.to_dict() == label.puzzle.to_dict(), s.id
        assert meta["puzzle_id"] == label.meta["puzzle_id"]


def test_verified_labels_are_consistent():
    for s in load_manifest():
        if not s.verified:
            continue
        label = s.load_label()
        assert label.puzzle.size == s.size, s.id
        assert not label.puzzle.validate(), s.id
        assert label.solution and label.puzzle.check_solution(label.solution), s.id


def test_test_split_is_fully_verified():
    test = select(load_manifest(), split="test")
    assert test and all(s.verified for s in test)
    assert cp.resolver(test[0].load_label().puzzle).unica
