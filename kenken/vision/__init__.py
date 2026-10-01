"""Phase 1: computer vision (image -> Puzzle)."""

from .extract import Extraction, ExtractionError, debug_image, extract_puzzle

__all__ = ["Extraction", "ExtractionError", "debug_image", "extract_puzzle"]
