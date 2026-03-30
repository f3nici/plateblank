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
    """Redact a plate region by filling it with colors sampled from the border area.

    Samples colors from a band just outside the plate quad, then uses
    inpainting to smoothly fill the plate region with the surrounding colors.
    This makes the redaction blend in with the vehicle body.
    """
    # Expand the mask slightly to get the border region for sampling
    dilated = cv2.dilate(mask, np.ones((15, 15), np.uint8), iterations=2)
    border_mask = cv2.subtract(dilated, mask)

    # Get the mean color of the border region
    mean_color = cv2.mean(img, mask=border_mask)[:3]

    # First pass: fill with the mean border color
    result = img.copy()
    result[mask == 255] = mean_color

    # Second pass: use inpainting for smoother blending at edges
    # This blends the filled area naturally with the surrounding pixels
    inpainted = cv2.inpaint(result, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

    # Use the inpainted result only in the masked region
    result = np.where(mask[:, :, np.newaxis] == 255, inpainted, img)

    # Apply a very subtle blur just at the edges for seamless blending
    edge_kernel = np.ones((5, 5), np.uint8)
    edge_mask = cv2.dilate(mask, edge_kernel, iterations=1)
    edge_only = cv2.subtract(edge_mask, cv2.erode(mask, edge_kernel, iterations=1))
    blended = cv2.GaussianBlur(result, (7, 7), 2)
    result = np.where(edge_only[:, :, np.newaxis] == 255, blended, result)

    return result
