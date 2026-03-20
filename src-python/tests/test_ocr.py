"""Tests for OCR engine (Step 16).

Tests that require PaddleOCR are automatically skipped when it is not installed.
"""

from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from kindleocr.ocr.engine import (
    BoundingBox,
    OcrPageResult,
    OcrProcessPageParams,
    TextBlock,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_sample_result(n_blocks: int = 3) -> OcrPageResult:
    blocks = [
        TextBlock(
            type="body",
            text=f"Word {i}",
            confidence=0.9 - i * 0.05,
            bbox=BoundingBox(x=10, y=i * 30, width=100, height=20),
        )
        for i in range(n_blocks)
    ]
    raw = "\n".join(b.text for b in blocks)
    avg = sum(b.confidence for b in blocks) / len(blocks)
    return OcrPageResult(page_index=0, blocks=blocks, raw_text=raw, avg_confidence=avg)


# ---------------------------------------------------------------------------
# Data type / structure tests (no PaddleOCR required)
# ---------------------------------------------------------------------------

class TestOcrDataTypes:
    def test_ocr_page_result_has_required_fields(self):
        result = _make_sample_result()
        assert hasattr(result, "page_index")
        assert hasattr(result, "blocks")
        assert hasattr(result, "raw_text")
        assert hasattr(result, "avg_confidence")

    def test_text_block_has_required_fields(self):
        block = TextBlock(
            type="body",
            text="Hello",
            confidence=0.95,
            bbox=BoundingBox(x=0, y=0, width=50, height=20),
        )
        assert block.text == "Hello"
        assert block.confidence == 0.95
        assert isinstance(block.bbox, BoundingBox)

    def test_confidence_range(self):
        result = _make_sample_result(5)
        for block in result.blocks:
            assert 0.0 <= block.confidence <= 1.0

    def test_bounding_box_values_non_negative(self):
        result = _make_sample_result()
        for block in result.blocks:
            assert block.bbox.x >= 0
            assert block.bbox.y >= 0
            assert block.bbox.width >= 0
            assert block.bbox.height >= 0

    def test_avg_confidence_matches_blocks(self):
        result = _make_sample_result(4)
        expected = sum(b.confidence for b in result.blocks) / len(result.blocks)
        assert abs(result.avg_confidence - expected) < 1e-9

    def test_raw_text_contains_all_block_text(self):
        result = _make_sample_result(3)
        for block in result.blocks:
            assert block.text in result.raw_text

    def test_dataclass_is_serialisable(self):
        """OcrPageResult should convert to dict cleanly via dataclasses.asdict."""
        result = _make_sample_result(2)
        d = dataclasses.asdict(result)
        assert "blocks" in d
        assert "raw_text" in d
        assert isinstance(d["blocks"][0]["bbox"], dict)

    def test_params_defaults(self):
        params = OcrProcessPageParams(image_path="/tmp/img.png")
        assert params.engine == "ppocr"
        assert params.page_index == 0


# ---------------------------------------------------------------------------
# paddle_ocr module tests (using mocked PaddleOCR)
# ---------------------------------------------------------------------------

class TestPaddleOcrModule:
    """Tests that mock PaddleOCR so they run without the actual package."""

    def _mock_paddle_result(self):
        """Build a fake PaddleOCR output structure."""
        # PaddleOCR returns: [[[ [bbox_points, (text, conf)], ... ]]]
        return [
            [
                [[[10, 20], [110, 20], [110, 40], [10, 40]], ("Hello world", 0.97)],
                [[[10, 50], [200, 50], [200, 70], [10, 70]], ("Second line", 0.88)],
                [[[10, 80], [150, 80], [150, 100], [10, 100]], ("Third line", 0.75)],
            ]
        ]

    def test_basic_ocr_returns_blocks(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = self._mock_paddle_result()

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            params = OcrProcessPageParams(image_path="/fake/img.png", page_index=1)
            result = ocr_page_paddle(params)

        assert result.page_index == 1
        assert len(result.blocks) == 3
        assert result.blocks[0].text == "Hello world"

    def test_reading_order_sorted_top_to_bottom(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        # Out-of-order y coordinates
        raw = [
            [
                [[[10, 80], [110, 80], [110, 100], [10, 100]], ("Third", 0.9)],
                [[[10, 20], [110, 20], [110, 40], [10, 40]], ("First", 0.9)],
                [[[10, 50], [110, 50], [110, 70], [10, 70]], ("Second", 0.9)],
            ]
        ]
        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = raw

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            params = OcrProcessPageParams(image_path="/fake/img.png")
            result = ocr_page_paddle(params)

        texts = [b.text for b in result.blocks]
        assert texts == ["First", "Second", "Third"]

    def test_empty_image_returns_empty_result(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = [None]

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            result = ocr_page_paddle(OcrProcessPageParams(image_path="/fake/blank.png"))

        assert result.blocks == []
        assert result.raw_text == ""
        assert result.avg_confidence == 0.0

    def test_avg_confidence_computed_correctly(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        raw = [
            [
                [[[0, 0], [100, 0], [100, 20], [0, 20]], ("A", 0.8)],
                [[[0, 30], [100, 30], [100, 50], [0, 50]], ("B", 0.6)],
            ]
        ]
        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = raw

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            result = ocr_page_paddle(OcrProcessPageParams(image_path="/fake/img.png"))

        assert abs(result.avg_confidence - 0.7) < 1e-9

    def test_confidence_all_in_range(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = self._mock_paddle_result()

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            result = ocr_page_paddle(OcrProcessPageParams(image_path="/fake/img.png"))

        for block in result.blocks:
            assert 0.0 <= block.confidence <= 1.0

    def test_import_error_raised_without_paddleocr(self):
        """_get_ppocr() raises ImportError with helpful message when package is missing."""
        import importlib
        import kindleocr.ocr.paddle_ocr as mod

        # Reset the singleton so the import is re-attempted.
        original = mod._ppocr_instance
        mod._ppocr_instance = None
        try:
            with patch.dict("sys.modules", {"paddleocr": None}):
                with pytest.raises(ImportError, match="PaddleOCR is not installed"):
                    mod._get_ppocr()
        finally:
            mod._ppocr_instance = original

    def test_singleton_not_reinitialised(self):
        """Second call to _get_ppocr should not call PaddleOCR constructor again."""
        import kindleocr.ocr.paddle_ocr as mod

        sentinel = MagicMock()
        original = mod._ppocr_instance
        mod._ppocr_instance = sentinel
        try:
            result = mod._get_ppocr()
            assert result is sentinel
        finally:
            mod._ppocr_instance = original


# ---------------------------------------------------------------------------
# Server integration (JSON-RPC handler) tests
# ---------------------------------------------------------------------------

class TestOcrServerHandler:
    """Verify ocr_page is wired into the JSON-RPC server correctly."""

    def test_ocr_page_method_registered(self):
        from kindleocr.server import create_server

        server = create_server()
        assert "ocr_page" in server._methods

    def test_ocr_page_handler_uses_paddle(self, tmp_path):
        """Handler calls ocr_page_paddle and returns a serialisable dict."""
        from kindleocr.server import create_server
        import json

        # Create a tiny white test image.
        img = Image.new("RGB", (50, 50), 255)
        img_path = str(tmp_path / "test.png")
        img.save(img_path)

        raw = [
            [
                [[[5, 5], [45, 5], [45, 20], [5, 20]], ("Test text", 0.92)],
            ]
        ]
        mock_ocr = MagicMock()
        mock_ocr.ocr.return_value = raw

        import kindleocr.ocr.paddle_ocr as paddle_mod
        original = paddle_mod._ppocr_instance
        paddle_mod._ppocr_instance = mock_ocr
        try:
            server = create_server()
            resp = server.handle_message(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 42,
                    "method": "ocr_page",
                    "params": {"image_path": img_path, "page_index": 0},
                })
            )
        finally:
            paddle_mod._ppocr_instance = original

        assert "result" in resp
        assert resp["result"]["blocks"][0]["text"] == "Test text"
        assert resp["result"]["page_index"] == 0


# ---------------------------------------------------------------------------
# Live PaddleOCR accuracy test (skipped when not installed)
# ---------------------------------------------------------------------------

paddleocr = pytest.importorskip("paddleocr", reason="PaddleOCR not installed")


class TestPaddleOcrLive:
    """Accuracy tests that require PaddleOCR to actually be installed."""

    def test_ocr_fixture_page_extracts_text(self, fixtures_dir):
        """Run real OCR on sample-page-01.png and verify non-empty output."""
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        params = OcrProcessPageParams(
            image_path=str(fixtures_dir / "sample-page-01.png"),
            page_index=0,
        )
        result = ocr_page_paddle(params)
        assert len(result.blocks) > 0
        assert len(result.raw_text) > 10
        assert result.avg_confidence > 0.5

    def test_blank_page_fixture_returns_empty(self, fixtures_dir):
        """blank-page.png should produce no blocks."""
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        result = ocr_page_paddle(
            OcrProcessPageParams(image_path=str(fixtures_dir / "blank-page.png"))
        )
        assert result.blocks == [] or result.avg_confidence < 0.5
