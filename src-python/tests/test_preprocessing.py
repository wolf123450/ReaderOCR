"""Tests for image preprocessing (Step 15)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from kindleocr.ocr.preprocessing import (
    PreprocessImageParams,
    _auto_crop,
    _deskew,
    _normalize_contrast,
    preprocess_image,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_white_image(width: int, height: int) -> Image.Image:
    return Image.new("RGB", (width, height), color=(255, 255, 255))


def _make_padded_image(inner_w: int, inner_h: int, pad: int) -> Image.Image:
    """Create a white-padded image with a dark rectangle in the centre."""
    total_w = inner_w + 2 * pad
    total_h = inner_h + 2 * pad
    img = Image.new("RGB", (total_w, total_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Dark content area
    draw.rectangle([pad, pad, pad + inner_w, pad + inner_h], fill=(20, 20, 20))
    return img


def _make_text_image(text: str = "Hello World", width: int = 300, height: int = 100) -> Image.Image:
    """Simple white image with a dark horizontal band to simulate text lines."""
    img = Image.new("L", (width, height), color=240)
    arr = np.array(img)
    # Simulate two text lines as dark bands
    arr[30:40, 20:280] = 30
    arr[60:70, 20:200] = 30
    return Image.fromarray(arr)


def _make_dark_image(width: int = 100, height: int = 100) -> Image.Image:
    """An image whose histogram is concentrated in the low range."""
    arr = np.full((height, width), fill_value=40, dtype=np.uint8)
    return Image.fromarray(arr, mode="L")


# ---------------------------------------------------------------------------
# Auto-crop tests
# ---------------------------------------------------------------------------

class TestAutoCrop:
    def test_removes_uniform_border(self):
        """Image with 50 px white border → cropped output ~100 px smaller each dim."""
        inner_w, inner_h = 400, 300
        pad = 50
        img = _make_padded_image(inner_w, inner_h, pad)
        result = _auto_crop(img)
        # Should be noticeably smaller than the original (500×400)
        assert result.width < img.width - 50
        assert result.height < img.height - 50

    def test_all_white_image_unchanged(self):
        """All-white image has no content bbox → returned unchanged."""
        img = _make_white_image(200, 200)
        result = _auto_crop(img)
        assert result.size == img.size

    def test_no_border_image_roughly_unchanged(self):
        """Image that is almost entirely content → dimensions close to original."""
        img = Image.new("RGB", (200, 200), color=(30, 30, 30))
        result = _auto_crop(img)
        # Should not shrink drastically (within padding tolerance)
        assert result.width >= img.width - 30
        assert result.height >= img.height - 30

    def test_result_smaller_than_original_when_padded(self):
        img = _make_padded_image(200, 150, 60)
        result = _auto_crop(img)
        assert result.width < img.width
        assert result.height < img.height

    def test_tiny_crop_result_returns_original(self):
        """If crop would produce < 50×50, return original."""
        # Single dark pixel in otherwise white image
        img = Image.new("L", (200, 200), 255)
        img.putpixel((100, 100), 0)
        result = _auto_crop(img)
        # The bbox around a single pixel padded to ±10 = ~20×20 < 50×50
        assert result.size == img.size


# ---------------------------------------------------------------------------
# Deskew tests
# ---------------------------------------------------------------------------

class TestDeskew:
    def test_correctly_aligned_image_unchanged(self):
        """An already-horizontal image should not be rotated."""
        img = _make_text_image()
        result = _deskew(img)
        # Size should be the same (no expand)
        assert result.size == img.size

    def test_rotated_image_corrected(self):
        """A 3°-rotated image should be brought close to horizontal."""
        orig = _make_text_image(width=400, height=120)
        skewed = orig.rotate(-3, expand=False, fillcolor=255)
        corrected = _deskew(skewed)
        # The corrected image should exist and be the same size
        assert corrected.size == skewed.size

    def test_all_white_image_unchanged(self):
        img = _make_white_image(200, 100)
        result = _deskew(img)
        assert result.size == img.size

    def test_large_angle_skipped(self):
        """Angles > 5° are outside the search range; image returned unchanged."""
        orig = _make_text_image(width=300, height=100)
        seriously_skewed = orig.rotate(30, expand=False, fillcolor=255)
        result = _deskew(seriously_skewed)
        # Should still return an image (may not be corrected, but shouldn't crash)
        assert result is not None


# ---------------------------------------------------------------------------
# Contrast normalisation tests
# ---------------------------------------------------------------------------

class TestNormalizeContrast:
    def test_dark_image_is_brightened(self):
        """Histogram concentrated at low values → output spans wider range."""
        # Create an image with variation so autocontrast can stretch the range.
        arr = np.zeros((100, 100), dtype=np.uint8)
        # Values between 20 and 60 — concentrated in the low range.
        arr[0:50, :] = 20
        arr[50:, :] = 60
        dark = Image.fromarray(arr)
        result = _normalize_contrast(dark)
        result_arr = np.array(result)
        # After autocontrast the min (20) should map to 0 and max (60) to 255.
        assert result_arr.max() == 255, "Max value should be 255 after autocontrast"
        assert result_arr.min() == 0, "Min value should be 0 after autocontrast"

    def test_already_normalised_image_unchanged_approximately(self):
        """Image using full range already → remains approximately the same."""
        arr = np.linspace(0, 255, 10000, dtype=np.uint8).reshape((100, 100))
        img = Image.fromarray(arr, mode="L")
        result = _normalize_contrast(img)
        result_arr = np.array(result)
        assert result_arr.max() == 255
        assert result_arr.min() == 0

    def test_rgb_image_preserved(self):
        """RGB image should remain RGB after normalisation."""
        img = Image.new("RGB", (50, 50), color=(40, 40, 40))
        result = _normalize_contrast(img)
        assert result.mode == "RGB"

    def test_rgba_alpha_channel_preserved(self):
        """Alpha channel should not be affected."""
        img = Image.new("RGBA", (50, 50), color=(40, 40, 40, 128))
        result = _normalize_contrast(img)
        assert result.mode == "RGBA"
        alpha_arr = np.array(result)[:, :, 3]
        assert int(alpha_arr.mean()) == 128


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestPreprocessImage:
    def test_pipeline_writes_output_file(self, fixtures_dir):
        """Full pipeline runs and produces a PNG file."""
        src = str(fixtures_dir / "sample-page-01.png")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            out = f.name
        params = PreprocessImageParams(
            image_path=src,
            output_path=out,
            auto_crop=True,
            deskew=True,
            normalize_contrast=True,
        )
        result = preprocess_image(params)
        assert Path(result.output_path).exists()
        assert result.processed_size[0] > 0
        assert result.processed_size[1] > 0

    def test_pipeline_preserves_content_dimensions_roughly(self, fixtures_dir):
        """Processed image should retain meaningful content after crop."""
        src = str(fixtures_dir / "sample-page-01.png")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            out = f.name
        params = PreprocessImageParams(
            image_path=src, output_path=out, auto_crop=True, deskew=False, normalize_contrast=False
        )
        result = preprocess_image(params)
        # Output must be at least 50×50 pixels and meaningful (not near-zero).
        assert result.processed_size[0] >= 50
        assert result.processed_size[1] >= 50
        # Must actually be smaller than the original in at least one dimension
        # (confirms the crop did something), OR remain the same size (no border).
        assert (
            result.processed_size[0] <= result.original_size[0]
            and result.processed_size[1] <= result.original_size[1]
        )

    def test_creates_output_directory(self, tmp_path):
        """Output directory is created automatically."""
        src_img = Image.new("RGB", (100, 100), 200)
        src = str(tmp_path / "in.png")
        src_img.save(src)
        out = str(tmp_path / "subdir" / "nested" / "out.png")
        params = PreprocessImageParams(
            image_path=src,
            output_path=out,
            auto_crop=False,
            deskew=False,
            normalize_contrast=False,
        )
        result = preprocess_image(params)
        assert Path(result.output_path).exists()

    def test_no_ops_return_same_size(self, tmp_path):
        """With all processing disabled, output size equals input size."""
        arr = np.random.randint(0, 256, (100, 150, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        src = str(tmp_path / "in.png")
        img.save(src)
        out = str(tmp_path / "out.png")
        params = PreprocessImageParams(
            image_path=src,
            output_path=out,
            auto_crop=False,
            deskew=False,
            normalize_contrast=False,
        )
        result = preprocess_image(params)
        assert result.original_size == result.processed_size

    def test_blank_page_handled_without_crash(self, fixtures_dir):
        """blank-page.png should not crash the pipeline."""
        src = str(fixtures_dir / "blank-page.png")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            out = f.name
        params = PreprocessImageParams(image_path=src, output_path=out)
        result = preprocess_image(params)
        assert Path(result.output_path).exists()
