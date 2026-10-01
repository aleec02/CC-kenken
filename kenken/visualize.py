"""Phase 3: project the solution back onto the photo, and draw a clean solved board."""

from __future__ import annotations

import cv2
import numpy as np

from .render import RenderStyle, render_puzzle
from .vision.extract import Extraction


def overlay_solution(original_bgr: np.ndarray, ex: Extraction, grid: list[list[int]],
                     color=(40, 160, 0)) -> np.ndarray:
    """Draw the solution digits in the rectified (top-down) frame and warp them back
    onto the original photo with the inverse homography, so they follow the
    perspective of the paper."""
    rect, n = ex.rect, ex.topology.n
    side = rect.size + 2 * rect.margin
    cell = rect.size / n
    layer = np.zeros((side, side, 3), np.uint8)
    mask = np.zeros((side, side), np.uint8)
    scale = cell / 50
    thick = max(2, int(cell / 22))
    for r in range(n):
        for c in range(n):
            text = str(grid[r][c])
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thick)
            x = int(rect.margin + (c + 0.5) * cell - tw / 2)
            y = int(rect.margin + (r + 0.62) * cell + th / 2)
            for canvas, col in ((layer, color), (mask, 255)):
                cv2.putText(canvas, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, col, thick, cv2.LINE_AA)

    # Homography original -> rectified. The extraction may have run on a resized copy.
    S = np.diag([ex.scale, ex.scale, 1.0])
    H_inv = np.linalg.inv(rect.H @ S)
    h, w = original_bgr.shape[:2]
    layer_w = cv2.warpPerspective(layer, H_inv, (w, h))
    mask_w = cv2.warpPerspective(mask, H_inv, (w, h)).astype(np.float32)[..., None] / 255
    out = original_bgr.astype(np.float32) * (1 - mask_w) + layer_w.astype(np.float32) * mask_w

    # Outline the detected grid.
    corners = (ex.rect.corners / ex.scale).astype(np.int32)
    cv2.polylines(out, [corners], True, (0, 140, 255), max(2, w // 400), cv2.LINE_AA)
    return out.astype(np.uint8)


def clean_board(ex: Extraction, grid: list[list[int]]) -> np.ndarray:
    """Clean redrawn board (BGR) with the clues and the solution."""
    rgb = render_puzzle(ex.puzzle, RenderStyle(cell=90), solution=grid)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def side_by_side(left: np.ndarray, right: np.ndarray, height: int = 720) -> np.ndarray:
    def fit(img):
        f = height / img.shape[0]
        return cv2.resize(img, (int(img.shape[1] * f), height), interpolation=cv2.INTER_AREA)

    a, b = fit(left), fit(right)
    gap = np.full((height, 16, 3), 255, np.uint8)
    return np.hstack([a, gap, b])
