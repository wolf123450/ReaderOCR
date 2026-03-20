"""Image preprocessing for OCR: auto-crop, deskew, contrast normalisation.

Processing order: auto-crop → deskew → normalise contrast.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageOps


@dataclass
class PreprocessImageParams:
    image_path: str
    output_path: str
    auto_crop: bool = True
    deskew: bool = True
    normalize_contrast: bool = True


@dataclass
class PreprocessImageResult:
    output_path: str
    original_size: Tuple[int, int]
    processed_size: Tuple[int, int]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _auto_crop(img: Image.Image) -> Image.Image:
    """Remove uniform background borders.

    Converts to grayscale, inverts (so content is white), finds the bounding
    box of non-zero content, pads 10 px, then crops.  Returns the original
    image unchanged if no meaningful border is found.
    """
    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    bbox = inverted.getbbox()

    if bbox is None:
        # All-white (or all-black) image — nothing to crop.
        return img

    pad = 10
    w, h = img.size
    x0 = max(0, bbox[0] - pad)
    y0 = max(0, bbox[1] - pad)
    x1 = min(w, bbox[2] + pad)
    y1 = min(h, bbox[3] + pad)

    # Skip crop if the result would be tiny.
    if (x1 - x0) < 50 or (y1 - y0) < 50:
        return img

    return img.crop((x0, y0, x1, y1))


def _deskew(img: Image.Image) -> Image.Image:
    """Detect and correct small rotation angles using projection profiling.

    Iterates over candidate angles in [-5°, +5°] in 0.5° steps.  For each
    angle, rotates a binarised, downscaled copy and computes row-projection
    variance.  The angle that maximises variance corresponds to horizontal
    text alignment.  If the best angle is < 0.1° the image is returned
    unchanged.
    """
    gray = img.convert("L")
    arr = np.array(gray, dtype=np.uint8)

    # Binarise: text (dark pixels) → 255, background → 0.
    binary = np.where(arr < 128, 255, 0).astype(np.uint8)
    bin_img = Image.fromarray(binary)

    # Downscale for speed while keeping enough resolution for angle detection.
    max_dim = max(bin_img.size)
    if max_dim > 800:
        scale = 800 / max_dim
        small = bin_img.resize(
            (int(bin_img.width * scale), int(bin_img.height * scale)),
            Image.NEAREST,
        )
    else:
        small = bin_img

    best_angle = 0.0
    best_score = -1.0

    for angle in np.arange(-5.0, 5.1, 0.5):
        rotated = small.rotate(float(angle), expand=False, fillcolor=0)
        proj = np.array(rotated).sum(axis=1, dtype=np.float64)
        score = float(np.var(proj))
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    if abs(best_angle) < 0.1:
        return img

    return img.rotate(best_angle, expand=False, fillcolor=255)


def _normalize_contrast(img: Image.Image) -> Image.Image:
    """Stretch histogram to full 0–255 range (auto-levels / autocontrast).

    Operates channel-by-channel to preserve colour balance.  The alpha
    channel (if present) is left unchanged.
    """
    mode = img.mode

    if mode == "L":
        return ImageOps.autocontrast(img)

    if mode in ("RGB", "RGBA"):
        channels = img.split()
        processed = tuple(ImageOps.autocontrast(c) for c in channels[:3])
        if mode == "RGBA":
            return Image.merge("RGBA", (*processed, channels[3]))
        return Image.merge("RGB", processed)

    # Fallback: convert to L, normalise, convert back.
    gray = ImageOps.autocontrast(img.convert("L"))
    return gray.convert(mode)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess_image(params: PreprocessImageParams) -> PreprocessImageResult:
    """Run the full preprocessing pipeline on one image file.

    Creates the output directory if it does not exist.  Always writes the
    result as PNG regardless of the input format.
    """
    img = Image.open(params.image_path)
    original_size: Tuple[int, int] = img.size

    if params.auto_crop:
        img = _auto_crop(img)
    if params.deskew:
        img = _deskew(img)
    if params.normalize_contrast:
        img = _normalize_contrast(img)

    Path(params.output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(params.output_path)

    return PreprocessImageResult(
        output_path=params.output_path,
        original_size=original_size,
        processed_size=img.size,
    )
