from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image as PILImage


def detect_plates(image_path: Path, max_results: int = 1) -> list[list[list[float]]]:
    """Detect the single best license plate candidate using OpenCV.

    Returns a list with at most one quad: 4 corner points [[x,y], ...] in
    TL, TR, BR, BL order (natural image pixel space).
    """
    pil_img = PILImage.open(image_path).convert("RGB")
    img = np.array(pil_img)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]
    img_area = h * w

    # Plate area constraints — typically 0.1% to 5% of the image
    min_plate_area = img_area * 0.001
    max_plate_area = img_area * 0.05

    candidates: list[tuple[float, list[list[float]]]] = []

    # --- Apply CLAHE for contrast enhancement (helps on dark vehicles) ---
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    for blur_k in (7, 11):
        blurred = cv2.bilateralFilter(enhanced, blur_k, 75, 75)
        edges = cv2.Canny(blurred, 30, 200)

        # Rectangular kernel — plates are wider than tall
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
        edges = cv2.dilate(edges, kernel, iterations=2)
        edges = cv2.erode(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_plate_area or area > max_plate_area:
                continue

            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            if len(approx) == 4:
                score = _score_candidate(cnt, approx, gray, h, w, img_area)
                if score > 0:
                    corners = _order_corners(approx.reshape(4, 2).tolist())
                    candidates.append((score, corners))

            # Also try minAreaRect for slightly irregular contours
            rect = cv2.minAreaRect(cnt)
            rw, rh = rect[1]
            if rw == 0 or rh == 0:
                continue
            aspect = max(rw, rh) / min(rw, rh)
            if 1.5 <= aspect <= 7.0:
                rect_area = rw * rh
                if rect_area < min_plate_area or rect_area > max_plate_area:
                    continue
                box = cv2.boxPoints(rect)
                score = _score_candidate(cnt, box, gray, h, w, img_area)
                if score > 0:
                    corners = _order_corners(box.tolist())
                    candidates.append((score, corners))

    if not candidates:
        return []

    # Return only the single best candidate
    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0][1]
    rounded = [[round(c[0], 2), round(c[1], 2)] for c in best]
    return [rounded]


def _score_candidate(
    cnt: np.ndarray,
    approx: np.ndarray,
    gray: np.ndarray,
    h: int,
    w: int,
    img_area: int,
) -> float:
    """Score a plate candidate. Higher = more likely a real plate. Returns 0 to reject."""
    rect = cv2.minAreaRect(cnt)
    rw, rh = rect[1]
    if rw == 0 or rh == 0:
        return 0

    aspect = max(rw, rh) / min(rw, rh)
    # License plates typically 2:1 to 5:1
    if aspect < 1.5 or aspect > 7.0:
        return 0

    area = cv2.contourArea(cnt)
    score = 0.0

    # Aspect ratio score — peak around 3:1 (common plate ratio)
    aspect_score = 1.0 - abs(aspect - 3.0) / 4.0
    score += max(0, aspect_score) * 40

    # Rectangularity — how close the contour fills its bounding rect
    rect_area = rw * rh
    if rect_area > 0:
        rectangularity = area / rect_area
        score += rectangularity * 30

    # Position score — plates are usually in the bottom 60% of the image
    cy = rect[0][1]
    if cy > h * 0.4:
        score += 20
    if cy > h * 0.6:
        score += 10

    # Contrast score — plates tend to be brighter than surroundings
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillConvexPoly(mask, approx.reshape(-1, 2).astype(np.int32), 255)
    inner_mean = cv2.mean(gray, mask=mask)[0]

    dilated = cv2.dilate(mask, np.ones((15, 15), np.uint8), iterations=1)
    border_mask = cv2.subtract(dilated, mask)
    outer_mean = cv2.mean(gray, mask=border_mask)[0]

    contrast = abs(inner_mean - outer_mean)
    score += min(contrast, 80) * 0.5

    return score


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
