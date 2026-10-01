"""Phase 1: computer vision (image -> puzzle)."""

from .extract import Extraction, ExtractionError, extract_puzzle
from .overlay import debug_image, overlay_solution

__all__ = ["Extraction", "ExtractionError", "debug_image", "extract_puzzle", "overlay_solution"]
