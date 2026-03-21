"""PaddleOCR engine implementation.

Uses a lazy singleton so the model is loaded at most once per process.
Falls back gracefully when PaddleOCR is not installed.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from kindleocr.ocr.engine import BoundingBox, OcrPageResult, OcrProcessPageParams, TextBlock

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

        # Disable heavy document preprocessing — not needed for book page images.
        # Silence verbose PaddleOCR/PaddleX log output via Python logging.
        for _log_name in ("paddleocr", "ppocr", "paddlex"):
            logging.getLogger(_log_name).setLevel(logging.WARNING)

        # Disable OneDNN (MKL-DNN) backend — it has unimplemented ops in the
        # current PaddlePaddle 3.x PIR compiler on CPU and causes runtime errors
        # like "ConvertPirAttribute2RuntimeAttribute not support ArrayAttribute".
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        os.environ.setdefault("PADDLE_DISABLE_MKLDNN", "1")

        _ppocr_instance = PaddleOCR(
            lang="en",
            device="cpu",
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

    # predict() yields one result per page; take the first for single images.
    res = results[0]["res"]
    rec_texts: List[str] = res.get("rec_texts", [])
    rec_scores = res.get("rec_scores", [])
    rec_polys = res.get("rec_polys", [])  # shape (N, 4, 2) — four corner points each

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
