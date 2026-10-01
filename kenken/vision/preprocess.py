"""Image preprocessing: illumination correction, binarization, grid localization and
perspective correction."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

WARP_SIZE = 900      # side of the rectified grid, in pixels
WARP_MARGIN = 30     # white margin kept around the rectified grid


@dataclass
class Rectified:
    gray: np.ndarray        # flat-field corrected grayscale of the rectified grid (uint8)
    binary: np.ndarray      # ink mask of the rectified grid (uint8, 255 = ink)
    H: np.ndarray           # homography original -> rectified
    corners: np.ndarray     # 4x2 grid corners in the original image (tl, tr, br, bl)
    size: int = WARP_SIZE
    margin: int = WARP_MARGIN


def load_image(path: str) -> np.ndarray:
    # np.fromfile + imdecode supports non-ASCII paths on Windows.
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot read image: {path}")
    return img


def resize_max(img: np.ndarray, max_side: int = 1600) -> tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img, scale


def flatten_illumination(gray: np.ndarray) -> np.ndarray:
    """Divide by a heavily blurred copy (background estimate) to remove shadows and
    lighting gradients. Paper becomes ~255, ink stays dark."""
    k = max(31, (min(gray.shape) // 8) | 1)
    # Closing removes the dark ink before estimating the background.
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
    bg = cv2.GaussianBlur(bg, (k, k), 0)
    norm = cv2.divide(gray, bg, scale=255)
    return norm


def binarize(gray: np.ndarray) -> np.ndarray:
    block = max(15, (min(gray.shape) // 40) | 1)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block, 10
    )


def _order_corners(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(-1, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def _quad_from_points(pts: np.ndarray) -> np.ndarray:
    hull = cv2.convexHull(pts)
    peri = cv2.arcLength(hull, True)
    for eps in (0.01, 0.02, 0.03, 0.05, 0.08):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4:
            return _order_corners(approx)
    return _order_corners(cv2.boxPoints(cv2.minAreaRect(hull)))


def find_grid_corners(binary: np.ndarray) -> np.ndarray:
    """Locate the KenKen grid: the connected ink component with the most ink *inside*
    its own convex hull. The grid lines form one big connected component whose interior
    is full of lines; a page border or table edge only has ink on its perimeter."""
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    img_area = binary.shape[0] * binary.shape[1]
    best, best_score = None, 0.0
    for i in np.argsort(-stats[1:, cv2.CC_STAT_AREA])[:15] + 1:
        x, y, w, h, area = stats[i]
        if w * h < 0.04 * img_area or min(w, h) < 0.5 * max(w, h):
            continue
        comp = (labels[y:y + h, x:x + w] == i).astype(np.uint8)
        # Ink in the inner 70% of the bounding box = internal grid lines.
        iy, ix = int(0.15 * h), int(0.15 * w)
        inner = comp[iy:h - iy, ix:w - ix].sum()
        score = inner / np.sqrt(w * h)
        if score > best_score:
            best, best_score = i, score
    if best is None:
        raise RuntimeError("Could not find a KenKen grid in the image")
    ys, xs = np.nonzero(labels == best)
    pts = np.stack([xs, ys], axis=1).astype(np.int32)
    return _quad_from_points(pts)


def rectify(img_bgr: np.ndarray) -> Rectified:
    """Full preprocessing: grayscale -> illumination correction -> binarization ->
    grid localization -> perspective warp to a WARP_SIZE square."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if img_bgr.ndim == 3 else img_bgr
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    flat = flatten_illumination(gray)
    binary = binarize(flat)
    corners = find_grid_corners(binary)

    m, S = WARP_MARGIN, WARP_SIZE
    dst = np.float32([[m, m], [m + S, m], [m + S, m + S], [m, m + S]])
    H = cv2.getPerspectiveTransform(corners, dst)
    out = (S + 2 * m, S + 2 * m)
    warped = cv2.warpPerspective(flat, H, out, flags=cv2.INTER_LINEAR, borderValue=255)
    warped_bin = cv2.threshold(warped, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    return Rectified(warped, warped_bin, H, corners)
