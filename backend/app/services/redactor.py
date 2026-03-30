from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image as PILImage

from ..models import Image, Plate


async def redact_image(
    image: Image, plates: list[Plate], originals_dir: Path, processed_dir: Path
) -> Path:
    """Apply redaction to an image based on its plate annotations.

    Loads the image with Pillow (broader format support), converts to numpy
    array for OpenCV processing, then saves the result.
    """
    original_path = originals_dir / image.original_path
    pil_img = PILImage.open(original_path).convert("RGB")
    img_array = np.array(pil_img)
    # PIL gives RGB, OpenCV uses BGR
    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    for plate in plates:
        corners = json.loads(plate.corners)
        corners_np = np.array(corners, dtype=np.int32)

        mask = np.zeros(img_array.shape[:2], dtype=np.uint8)
        cv2.fillConvexPoly(mask, corners_np, 255)

        if plate.redact_mode == "white":
            img_array[mask == 255] = (255, 255, 255)
        elif plate.redact_mode == "blur":
            blurred = cv2.GaussianBlur(img_array, (51, 51), 30)
            img_array = np.where(mask[:, :, np.newaxis] == 255, blurred, img_array)
        elif plate.redact_mode == "color_match":
            img_array = _color_match_redact(img_array, corners_np, mask)

    output_filename = image.original_path
    output_path = processed_dir / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(str(output_path), img_array)
    return output_path


def _color_match_redact(
    img: np.ndarray,
    corners: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    """Redact a plate region with a solid color averaged from the 4 corners.

    Samples the color at each corner point (small patch average), then fills
    the entire plate quad with the average of those 4 colors.
    """
    h, w = img.shape[:2]
    patch_size = 5  # sample a small patch around each corner

    colors = []
    for corner in corners:
        cx, cy = int(corner[0]), int(corner[1])
        # Clamp patch bounds to image
        y1 = max(0, cy - patch_size)
        y2 = min(h, cy + patch_size + 1)
        x1 = max(0, cx - patch_size)
        x2 = min(w, cx + patch_size + 1)
        patch = img[y1:y2, x1:x2]
        if patch.size > 0:
            colors.append(patch.mean(axis=(0, 1)))

    if not colors:
        return img

    avg_color = np.mean(colors, axis=0).astype(np.uint8)

    result = img.copy()
    result[mask == 255] = avg_color
    return result
