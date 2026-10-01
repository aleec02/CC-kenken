"""Phase 3 images: the solution projected onto the input photo, and the debug view of
what the vision step detected."""

from __future__ import annotations

import cv2
import numpy as np

from .extract import Extraction


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


def debug_image(ex: Extraction) -> np.ndarray:
    """Rectified grid with detected thick borders (red) and OCR readings (blue)."""
    n, rect = ex.topology.n, ex.rect
    img = cv2.cvtColor(rect.gray, cv2.COLOR_GRAY2BGR)
    cell = rect.size / n
    m = rect.margin
    for r in range(n):
        for c in range(n - 1):
            if ex.topology.v_thick[r, c]:
                x = int(m + (c + 1) * cell)
                cv2.line(img, (x, int(m + r * cell)), (x, int(m + (r + 1) * cell)), (0, 0, 255), 3)
    for r in range(n - 1):
        for c in range(n):
            if ex.topology.h_thick[r, c]:
                y = int(m + (r + 1) * cell)
                cv2.line(img, (int(m + c * cell), y), (int(m + (c + 1) * cell), y), (0, 0, 255), 3)
    for (r, c), cage in zip(ex.clue_cells, ex.puzzle.cages):
        org = (int(m + c * cell + 0.1 * cell), int(m + r * cell + 0.8 * cell))
        cv2.putText(img, cage.label.replace("−", "-").replace("×", "x").replace("÷", "/"),
                    org, cv2.FONT_HERSHEY_SIMPLEX, cell / 110, (200, 80, 0), 2, cv2.LINE_AA)
    return img
