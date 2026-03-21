"""PaddleOCR engine implementation.

Uses a lazy singleton so the model is loaded at most once per process.
Falls back gracefully when PaddleOCR is not installed.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from kindleocr.ocr.engine import BoundingBox, OcrPageResult, OcrProcessPageParams, TextBlock

# Ensure OneDNN/MKL-DNN flags are set before PaddlePaddle is imported.
# These env vars tell PaddlePaddle's C++ layer to skip the OneDNN backend.
# The primary API-level fix is enable_mkldnn=False in PaddleOCR() below;
# the env vars provide a secondary safeguard for any early internal imports.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_DISABLE_MKLDNN", "1")

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

_ppocr_instance: Optional[Any] = None


def _get_ppocr() -> Any:
    """Return the shared PaddleOCR instance, initialising on first call."""
    global _ppocr_instance
    if _ppocr_instance is None:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "PaddleOCR is not installed. "
                "Install with: pip install paddleocr paddlepaddle"
            ) from exc

        # Silence verbose PaddleOCR/PaddleX log output via Python logging.
        for _log_name in ("paddleocr", "ppocr", "paddlex"):
            logging.getLogger(_log_name).setLevel(logging.WARNING)

        # Disable OneDNN (MKL-DNN) via the PaddleOCR API.
        # PaddlePaddle 3.x defaults to enable_mkldnn=True on CPU, which causes
        # the PIR executor to compile OneDNN ops.  When those ops hit an
        # unimplemented attribute converter (onednn_instruction.cc:118) the
        # entire predict() call raises NotImplementedError.  Passing
        # enable_mkldnn=False tells PaddleX to call config.disable_mkldnn() so
        # the model is compiled with plain CPU ops instead.
        _ppocr_instance = PaddleOCR(
            lang="en",
            device="cpu",
            enable_mkldnn=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _ppocr_instance


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ocr_page_paddle(params: OcrProcessPageParams) -> OcrPageResult:
    """Run PaddleOCR on one image and return structured results.

    Blocks are sorted in reading order (top-to-bottom, left-to-right).
    Returns empty blocks with avg_confidence=0.0 when no text is found.
    """
    ocr = _get_ppocr()
    # PaddleOCR 3.x uses predict() which returns an iterable of result objects.
    results = list(ocr.predict(params.image_path))

    if not results:
        return OcrPageResult(
            page_index=params.page_index,
            blocks=[],
            raw_text="",
            avg_confidence=0.0,
        )

    # predict() yields one OCRResult per page; take the first for single images.
    # The result is a dict-like object whose keys include rec_texts, rec_scores,
    # and rec_polys directly (no nested "res" wrapper in PaddleOCR 3.x / PaddleX).
    result_obj = results[0]
    rec_texts: List[str] = result_obj.get("rec_texts", [])
    rec_scores = result_obj.get("rec_scores", [])
    rec_polys = result_obj.get("rec_polys", [])  # list of numpy (N, 2) polygon arrays

    blocks: List[TextBlock] = []
    for text, score, poly in zip(rec_texts, rec_scores, rec_polys):
        if not text:
            continue
        xs = [int(p[0]) for p in poly]
        ys = [int(p[1]) for p in poly]
        x = min(xs)
        y = min(ys)
        w = max(xs) - x
        h = max(ys) - y
        blocks.append(
            TextBlock(
                type="body",
                text=text,
                confidence=float(score),
                bbox=BoundingBox(x=x, y=y, width=w, height=h),
            )
        )

    # Reading order: primary sort by row (y), secondary by column (x).
    blocks.sort(key=lambda b: (b.bbox.y, b.bbox.x))

    raw_text = "\n".join(b.text for b in blocks)
    avg_conf = sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.0

    return OcrPageResult(
        page_index=params.page_index,
        blocks=blocks,
        raw_text=raw_text,
        avg_confidence=avg_conf,
    )
