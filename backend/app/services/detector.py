from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image as PILImage


def detect_plates(image_path: Path, max_results: int = 5) -> list[list[list[float]]]:
    """Detect license plate candidates using OpenCV contour analysis.

    Returns a list of quads, each quad being 4 corner points [[x,y], ...] in
    TL, TR, BR, BL order (natural image pixel space).
    """
    pil_img = PILImage.open(image_path).convert("RGB")
    img = np.array(pil_img)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    h, w = gray.shape[:2]
    img_area = h * w

    # Multi-scale approach for robustness
    candidates: list[tuple[float, list[list[float]]]] = []

    for blur_k in (5, 11, 17):
        blurred = cv2.bilateralFilter(gray, blur_k, 75, 75)

        # Adaptive threshold + Canny for edge detection
        edges = cv2.Canny(blurred, 50, 200)

        # Dilate to close gaps in edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filter: plate should be between 0.05% and 15% of image area
            if area < img_area * 0.0005 or area > img_area * 0.15:
                continue

            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            if len(approx) == 4:
                rect = cv2.minAreaRect(cnt)
                rw, rh = rect[1]
                if rw == 0 or rh == 0:
                    continue
                aspect = max(rw, rh) / min(rw, rh)
                # License plates typically have aspect ratio 1.5 - 6.0
                if 1.5 <= aspect <= 6.0:
                    corners = _order_corners(approx.reshape(4, 2).tolist())
                    # Score by area (larger = more likely a plate)
                    candidates.append((area, corners))

        # Also try minAreaRect on all reasonable contours
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < img_area * 0.0005 or area > img_area * 0.15:
                continue

            rect = cv2.minAreaRect(cnt)
            rw, rh = rect[1]
            if rw == 0 or rh == 0:
                continue
            aspect = max(rw, rh) / min(rw, rh)
            if 1.5 <= aspect <= 6.0:
                box = cv2.boxPoints(rect)
                corners = _order_corners(box.tolist())
                candidates.append((area, corners))

    # Deduplicate overlapping detections
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
            # Round coordinates
            rounded = [[round(c[0], 2), round(c[1], 2)] for c in corners]
            final.append(rounded)

    return final


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
