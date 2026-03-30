from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image as PILImage


def detect_plates(image_path: Path, max_results: int = 3) -> list[list[list[float]]]:
    """Detect license plate candidates using OpenCV contour analysis.

    Uses a multi-stage approach: color-based segmentation to find bright
    rectangular regions, combined with edge-based detection. Tuned for
    typical single-plate vehicle photos.

    Returns a list of quads, each quad being 4 corner points [[x,y], ...] in
    TL, TR, BR, BL order (natural image pixel space).
    """
    pil_img = PILImage.open(image_path).convert("RGB")
    img = np.array(pil_img)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    h, w = gray.shape[:2]
    img_area = h * w

    # Plate area constraints relative to image
    min_plate_area = img_area * 0.0008
    max_plate_area = img_area * 0.08

    candidates: list[tuple[float, list[list[float]]]] = []

    # --- Stage 1: Color-based detection ---
    # License plates are typically bright/light-colored rectangles.
    # Look for high-value, low-to-mid saturation regions (white, light blue, yellow plates).
    value_channel = hsv[:, :, 2]
    sat_channel = hsv[:, :, 1]

    # Threshold for bright regions
    _, bright_mask = cv2.threshold(value_channel, 150, 255, cv2.THRESH_BINARY)
    # Exclude highly saturated areas (e.g. red brake lights, colored signs)
    low_sat_mask = cv2.inRange(sat_channel, 0, 180)
    plate_mask = cv2.bitwise_and(bright_mask, low_sat_mask)

    # Clean up with morphological operations
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_CLOSE, kernel_close)
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_OPEN, kernel_open)

    contours, _ = cv2.findContours(
        plate_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    _extract_plate_candidates(
        contours, img_area, min_plate_area, max_plate_area, candidates
    )

    # --- Stage 2: Edge-based detection (multi-scale) ---
    for blur_k in (7, 13):
        blurred = cv2.bilateralFilter(gray, blur_k, 75, 75)

        # Apply CLAHE for better contrast in dark images
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)

        edges = cv2.Canny(enhanced, 30, 150)

        # Use rectangular kernel to favor horizontal structures (plates are wider than tall)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
        edges = cv2.dilate(edges, kernel, iterations=2)
        edges = cv2.erode(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        _extract_plate_candidates(
            contours, img_area, min_plate_area, max_plate_area, candidates
        )

    # --- Stage 3: Bottom-half focused detection ---
    # Most vehicle photos have the plate in the bottom half
    bottom_half = gray[h // 2 :, :]
    blurred_bottom = cv2.bilateralFilter(bottom_half, 11, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced_bottom = clahe.apply(blurred_bottom)
    edges_bottom = cv2.Canny(enhanced_bottom, 20, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 3))
    edges_bottom = cv2.dilate(edges_bottom, kernel, iterations=2)

    contours_bottom, _ = cv2.findContours(
        edges_bottom, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    # Offset contour points to full-image coordinates
    offset_contours = []
    for cnt in contours_bottom:
        offset_cnt = cnt.copy()
        offset_cnt[:, :, 1] += h // 2
        offset_contours.append(offset_cnt)
    _extract_plate_candidates(
        offset_contours,
        img_area,
        min_plate_area,
        max_plate_area,
        candidates,
        score_boost=1.5,
    )

    # --- Deduplicate and rank ---
    candidates.sort(key=lambda x: x[0], reverse=True)
    final: list[list[list[float]]] = []
    for _, corners in candidates:
        if len(final) >= max_results:
            break
        cx = sum(c[0] for c in corners) / 4
        cy = sum(c[1] for c in corners) / 4
        duplicate = False
        for existing in final:
            ecx = sum(c[0] for c in existing) / 4
            ecy = sum(c[1] for c in existing) / 4
            dist = ((cx - ecx) ** 2 + (cy - ecy) ** 2) ** 0.5
            if dist < min(w, h) * 0.05:
                duplicate = True
                break
        if not duplicate:
            rounded = [[round(c[0], 2), round(c[1], 2)] for c in corners]
            final.append(rounded)

    return final


def _extract_plate_candidates(
    contours: list[np.ndarray],
    img_area: int,
    min_area: float,
    max_area: float,
    candidates: list[tuple[float, list[list[float]]]],
    score_boost: float = 1.0,
) -> None:
    """Extract plate-shaped quadrilateral candidates from contours."""
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        if len(approx) == 4:
            rect = cv2.minAreaRect(cnt)
            rw, rh = rect[1]
            if rw == 0 or rh == 0:
                continue
            aspect = max(rw, rh) / min(rw, rh)
            if 1.5 <= aspect <= 7.0:
                corners = _order_corners(approx.reshape(4, 2).tolist())
                candidates.append((area * score_boost, corners))

        # Also try minAreaRect for rotated plates
        rect = cv2.minAreaRect(cnt)
        rw, rh = rect[1]
        if rw == 0 or rh == 0:
            continue
        aspect = max(rw, rh) / min(rw, rh)
        if 1.5 <= aspect <= 7.0:
            rect_area = rw * rh
            if rect_area < min_area or rect_area > max_area:
                continue
            box = cv2.boxPoints(rect)
            corners = _order_corners(box.tolist())
            candidates.append((rect_area * score_boost, corners))


def _order_corners(pts: list[list[float]]) -> list[list[float]]:
    """Order 4 points as TL, TR, BR, BL."""
    pts_arr = np.array(pts, dtype=np.float32)
    s = pts_arr.sum(axis=1)
    d = np.diff(pts_arr, axis=1).flatten()

    tl = pts_arr[np.argmin(s)]
    br = pts_arr[np.argmax(s)]
    tr = pts_arr[np.argmin(d)]
    bl = pts_arr[np.argmax(d)]

    return [tl.tolist(), tr.tolist(), br.tolist(), bl.tolist()]
