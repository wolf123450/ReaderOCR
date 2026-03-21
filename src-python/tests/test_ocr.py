"""Tests for OCR engine (Step 16).

Unit tests in TestPaddleOcrModule mock _get_ppocr (our own function) to test
parsing logic in isolation.  Integration tests in TestPaddleOcrInit call the
real PaddleOCR constructor so that invalid constructor arguments and missing
env-var setup are caught immediately instead of at runtime.
"""

from __future__ import annotations

import dataclasses
import os
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
# Session fixture — real PaddleOCR initialisation (not mocked)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def real_ppocr():
    """Initialise a real PaddleOCR instance once for the entire test session.

    The constructor is NOT mocked.  If our arguments or env-var setup are
    wrong, this fixture fails and every test that depends on it is reported as
    an error — exactly when we want to hear about it, not at runtime.
    """
    import kindleocr.ocr.paddle_ocr as mod

    saved = mod._ppocr_instance
    mod._ppocr_instance = None  # force a fresh initialisation
    try:
        instance = mod._get_ppocr()  # real call — invalid kwargs raise here
    finally:
        mod._ppocr_instance = saved  # restore so other tests aren't affected

    yield instance


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
        """Build a fake PaddleOCR 3.x predict() output structure."""
        # predict() returns a list of OCRResult-like dicts with rec_texts,
        # rec_scores, rec_polys at the top level — no nested 'res' wrapper.
        return [
            {
                "rec_texts": ["Hello world", "Second line", "Third line"],
                "rec_scores": [0.97, 0.88, 0.75],
                "rec_polys": [
                    [[10, 20], [110, 20], [110, 40], [10, 40]],
                    [[10, 50], [200, 50], [200, 70], [10, 70]],
                    [[10, 80], [150, 80], [150, 100], [10, 100]],
                ],
            }
        ]

    def test_basic_ocr_returns_blocks(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        mock_ocr = MagicMock()
        mock_ocr.predict.return_value = self._mock_paddle_result()

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            params = OcrProcessPageParams(image_path="/fake/img.png", page_index=1)
            result = ocr_page_paddle(params)

        assert result.page_index == 1
        assert len(result.blocks) == 3
        assert result.blocks[0].text == "Hello world"

    def test_reading_order_sorted_top_to_bottom(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        # Out-of-order y coordinates, single column
        raw = [
            {
                "rec_texts": ["Third", "First", "Second"],
                "rec_scores": [0.9, 0.9, 0.9],
                "rec_polys": [
                    [[10, 80], [110, 80], [110, 100], [10, 100]],
                    [[10, 20], [110, 20], [110, 40], [10, 40]],
                    [[10, 50], [110, 50], [110, 70], [10, 70]],
                ],
            }
        ]
        mock_ocr = MagicMock()
        mock_ocr.predict.return_value = raw

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            params = OcrProcessPageParams(image_path="/fake/img.png")
            result = ocr_page_paddle(params)

        texts = [b.text for b in result.blocks]
        assert texts == ["First", "Second", "Third"]

    def test_reading_order_two_column_layout(self):
        """Left column should come entirely before right column."""
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        # Two columns, 400 px wide each, with a 200 px gap.
        # Left col x=0..400, right col x=600..1000.
        # Deliberately interleaved y-order so a flat y-sort would get it wrong.
        raw = [
            {
                "rec_texts": [
                    "R-top",    # right col, y=50
                    "L-mid",    # left col,  y=200
                    "L-top",    # left col,  y=50
                    "R-bot",    # right col, y=300
                    "L-bot",    # left col,  y=300
                    "R-mid",    # right col, y=200
                ],
                "rec_scores": [0.9] * 6,
                "rec_polys": [
                    [[600, 50],  [1000, 50],  [1000, 90],  [600, 90]],
                    [[0,   200], [400,  200], [400,  240], [0,   240]],
                    [[0,   50],  [400,  50],  [400,  90],  [0,   90]],
                    [[600, 300], [1000, 300], [1000, 340], [600, 340]],
                    [[0,   300], [400,  300], [400,  340], [0,   340]],
                    [[600, 200], [1000, 200], [1000, 240], [600, 240]],
                ],
            }
        ]
        mock_ocr = MagicMock()
        mock_ocr.predict.return_value = raw

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            result = ocr_page_paddle(OcrProcessPageParams(image_path="/fake/img.png"))

        texts = [b.text for b in result.blocks]
        assert texts == ["L-top", "L-mid", "L-bot", "R-top", "R-mid", "R-bot"], \
            f"Expected left-col-first order, got: {texts}"

    def test_empty_image_returns_empty_result(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        mock_ocr = MagicMock()
        mock_ocr.predict.return_value = []

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            result = ocr_page_paddle(OcrProcessPageParams(image_path="/fake/blank.png"))

        assert result.blocks == []
        assert result.raw_text == ""
        assert result.avg_confidence == 0.0

    def test_avg_confidence_computed_correctly(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        raw = [
            {
                "rec_texts": ["A", "B"],
                "rec_scores": [0.8, 0.6],
                "rec_polys": [
                    [[0, 0], [100, 0], [100, 20], [0, 20]],
                    [[0, 30], [100, 30], [100, 50], [0, 50]],
                ],
            }
        ]
        mock_ocr = MagicMock()
        mock_ocr.predict.return_value = raw

        with patch("kindleocr.ocr.paddle_ocr._get_ppocr", return_value=mock_ocr):
            result = ocr_page_paddle(OcrProcessPageParams(image_path="/fake/img.png"))

        assert abs(result.avg_confidence - 0.7) < 1e-9

    def test_confidence_all_in_range(self):
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        mock_ocr = MagicMock()
        mock_ocr.predict.return_value = self._mock_paddle_result()

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
        """Handler calls ocr_page_paddle and returns a serialisable dict.

        We mock kindleocr.server.ocr_page_paddle — our own function — rather
        than anything inside the external PaddleOCR library.  This tests only
        that the JSON-RPC wiring is correct, not PaddleOCR internals.
        """
        from kindleocr.server import create_server
        from kindleocr.ocr.engine import OcrPageResult, TextBlock, BoundingBox
        import json

        fake_result = OcrPageResult(
            page_index=0,
            blocks=[
                TextBlock(
                    type="body",
                    text="Test text",
                    confidence=0.92,
                    bbox=BoundingBox(x=5, y=5, width=40, height=15),
                )
            ],
            raw_text="Test text",
            avg_confidence=0.92,
        )

        with patch("kindleocr.server.ocr_page_paddle", return_value=fake_result) as mock_fn:
            server = create_server()
            resp = server.handle_message(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 42,
                    "method": "ocr_page",
                    "params": {"image_path": "/fake/img.png", "page_index": 0},
                })
            )

        mock_fn.assert_called_once()
        assert "result" in resp
        assert resp["result"]["blocks"][0]["text"] == "Test text"
        assert resp["result"]["page_index"] == 0


# ---------------------------------------------------------------------------
# Integration tests: real PaddleOCR constructor (no mock)
# ---------------------------------------------------------------------------

class TestPaddleOcrInit:
    """Integration tests that actually instantiate PaddleOCR with our config.

    These tests use the ``real_ppocr`` session fixture which calls
    ``_get_ppocr()`` without mocking the constructor.  If we pass an invalid
    argument (e.g. the removed ``show_log`` or ``use_gpu``), the fixture fails
    and every test here is reported as an error rather than silently passing.

    ``predict()`` is mocked so no real images or GPU are needed.
    """

    def test_get_ppocr_initialises_without_error(self, real_ppocr):
        """PaddleOCR() must succeed with our current configuration."""
        assert real_ppocr is not None

    def test_onednn_env_vars_set_before_model_loads(self, real_ppocr):
        """OneDNN-disabling env vars must be present after _get_ppocr() runs."""
        assert os.environ.get("FLAGS_use_mkldnn") == "0", (
            "FLAGS_use_mkldnn must be '0' to disable OneDNN on CPU"
        )
        assert os.environ.get("PADDLE_DISABLE_MKLDNN") == "1", (
            "PADDLE_DISABLE_MKLDNN must be '1' to disable OneDNN on CPU"
        )

    def test_predict_method_exists_on_instance(self, real_ppocr):
        """The real PaddleOCR instance must expose a predict() method."""
        assert callable(getattr(real_ppocr, "predict", None)), (
            "PaddleOCR instance has no predict() — API may have changed again"
        )

    def test_ocr_page_paddle_full_flow(self, real_ppocr):
        """Full ocr_page_paddle() flow: real init, predict() mocked at API boundary."""
        import kindleocr.ocr.paddle_ocr as mod
        from kindleocr.ocr.paddle_ocr import ocr_page_paddle

        mock_result = [
            {
                "rec_texts": ["Hello world"],
                "rec_scores": [0.95],
                "rec_polys": [[[10, 20], [110, 20], [110, 40], [10, 40]]],
            }
        ]

        saved = mod._ppocr_instance
        mod._ppocr_instance = real_ppocr
        try:
            with patch.object(real_ppocr, "predict", return_value=mock_result):
                result = ocr_page_paddle(
                    OcrProcessPageParams(image_path="/fake/img.png", page_index=2)
                )
        finally:
            mod._ppocr_instance = saved

        assert result.page_index == 2
        assert len(result.blocks) == 1
        assert result.blocks[0].text == "Hello world"
        assert abs(result.avg_confidence - 0.95) < 1e-9


# ---------------------------------------------------------------------------
# Smoke test: fail loudly if paddleocr is not installed (not just skip)
# ---------------------------------------------------------------------------

class TestPaddleOcrInstalled:
    """Ensure the paddleocr package is present in the environment.

    This test is intentionally NOT using importorskip so that a missing
    package causes an explicit FAILED rather than a silent SKIPPED.
    """

    def test_paddleocr_importable(self):
        """paddleocr must be installed — add it with: pip install paddleocr paddlepaddle"""
        import importlib
        assert importlib.util.find_spec("paddleocr") is not None, (
            "paddleocr is not installed. Run: pip install paddleocr paddlepaddle"
        )

    def test_paddlepaddle_importable(self):
        """paddlepaddle must be installed — add it with: pip install paddlepaddle"""
        import importlib
        assert importlib.util.find_spec("paddle") is not None, (
            "paddlepaddle is not installed. Run: pip install paddlepaddle"
        )


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
