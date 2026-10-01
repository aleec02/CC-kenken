"""Dataset layout, label files and the manifest."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..core.puzzle import Puzzle

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.environ.get("KENKEN_DATA", REPO_ROOT / "data"))
MANIFEST_PATH = DATA_DIR / "manifest.json"
IMAGE_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")

# source folder (relative to DATA_DIR) -> (source name, split)
SOURCES = {
    "primary/digital": ("digital", "dev"),
    "primary/printed": ("printed", "test"),
    "secondary/synthetic": ("synthetic", "synthetic"),
}
SPLITS = ("dev", "test", "synthetic")


@dataclass
class Label:
    """Ground truth of one sample: the puzzle, its solution and metadata."""
    puzzle: Puzzle
    solution: list[list[int]] | None = None
    meta: dict = field(default_factory=dict)

    @property
    def verified(self) -> bool:
        return bool(self.meta.get("verified"))

    def to_dict(self) -> dict:
        data = self.puzzle.to_dict()
        data["solution"] = self.solution
        data["meta"] = self.meta
        return data

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Label:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(Puzzle.from_dict(data), data.get("solution"), data.get("meta", {}))


@dataclass
class Sample:
    id: str                 # e.g. "printed-8x8-02"
    file: str               # path relative to DATA_DIR
    label: str              # label path relative to DATA_DIR
    source: str             # digital | printed | synthetic
    split: str              # dev | test | synthetic
    size: int
    label_source: str = ""  # pdf | manual | draft | generated
    verified: bool = False

    @property
    def path(self) -> Path:
        return DATA_DIR / self.file

    @property
    def label_path(self) -> Path:
        return DATA_DIR / self.label

    def has_label(self) -> bool:
        return self.label_path.exists()

    def load_label(self) -> Label:
        return Label.load(self.label_path)


def _index(stem: str) -> int:
    m = re.search(r"\d+", stem)
    return int(m.group()) if m else 0


def scan() -> list[Sample]:
    """Find every sample file in the dataset folders (labels may still be missing)."""
    samples = []
    for folder, (source, split) in SOURCES.items():
        root = DATA_DIR / folder
        if not root.exists():
            continue
        for size_dir in sorted(root.iterdir(), key=lambda p: p.name):
            m = re.fullmatch(r"(\d+)x\1", size_dir.name)
            if not (size_dir.is_dir() and m):
                continue
            files = [f for f in size_dir.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS]
            for f in sorted(files, key=lambda p: _index(p.stem)):
                label = f.with_suffix(".json")
                samples.append(Sample(
                    id=f"{source}-{size_dir.name}-{_index(f.stem):02d}",
                    file=f.relative_to(DATA_DIR).as_posix(),
                    label=label.relative_to(DATA_DIR).as_posix(),
                    source=source, split=split, size=int(m.group(1)),
                ))
    for s in samples:
        if s.has_label():
            meta = s.load_label().meta
            s.label_source, s.verified = meta.get("label_source", ""), bool(meta.get("verified"))
    return samples


def save_manifest(samples: list[Sample]) -> Path:
    data = {"version": 1, "samples": [asdict(s) for s in samples]}
    MANIFEST_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return MANIFEST_PATH


def load_manifest() -> list[Sample]:
    """Samples from data/manifest.json (run `kenken data ingest` to create it)."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"{MANIFEST_PATH} not found: run `kenken data ingest` first")
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [Sample(**s) for s in data["samples"]]


def select(samples: list[Sample], split: str | None = None, source: str | None = None,
           size: int | None = None, ids: list[str] | None = None) -> list[Sample]:
    return [s for s in samples
            if (split is None or s.split == split)
            and (source is None or s.source == source)
            and (size is None or s.size == size)
            and (not ids or s.id in ids)]
