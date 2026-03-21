"""PaddleOCR engine implementation.

Uses a lazy singleton so the model is loaded at most once per process.
Falls back gracefully when PaddleOCR is not installed.
"""

from __future__ import annotations

import logging
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
                "Install with: pip install paddleocr paddlepaddle-gpu"
            ) from exc

        import paddle

        # Silence verbose PaddleOCR/PaddleX log output via Python logging.
        for _log_name in ("paddleocr", "ppocr", "paddlex"):
            logging.getLogger(_log_name).setLevel(logging.WARNING)

        # Use GPU if available, fall back to CPU otherwise.
        # On CPU: enable_mkldnn=False avoids a PaddlePaddle 3.x PIR bug where
        # OneDNN ops hit an unimplemented attribute converter at runtime.
        if paddle.device.cuda.device_count() > 0:
            device = "gpu"
            extra_kwargs: dict = {}
        else:
            device = "cpu"
            extra_kwargs = {"enable_mkldnn": False}

        _ppocr_instance = PaddleOCR(
            lang="en",
            device=device,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            **extra_kwargs,
        )
    return _ppocr_instance


# ---------------------------------------------------------------------------
# Reading-order helpers
# ---------------------------------------------------------------------------

def _sort_reading_order(blocks: List[TextBlock]) -> List[TextBlock]:
    """Sort blocks into reading order using a column-aware heuristic.

    Works on both single- and multi-column layouts:
    - Detects column boundaries by finding large horizontal gaps between
      block centres.
    - Within each column, blocks are sorted top-to-bottom by their y
      coordinate.
    - Columns themselves are ordered left-to-right.

    The gap threshold is adaptive: a gap must be at least `min_gap_ratio`
    times the median block width before it is treated as a column separator.
    This prevents narrow inter-word spaces from being mistaken for columns.
    """
    if not blocks:
        return blocks

    # Compute centre-x for every block.
    centres = sorted(set(b.bbox.x + b.bbox.width // 2 for b in blocks))

    # Adaptive gap threshold: 60 % of the median block width, minimum 20 px.
    median_width: float = sorted(b.bbox.width for b in blocks)[len(blocks) // 2]
    min_gap: float = max(20.0, median_width * 0.6)

    # Find column boundary positions (x values where a large gap occurs).
    boundaries: List[float] = []
    for i in range(1, len(centres)):
        if centres[i] - centres[i - 1] >= min_gap:
            boundaries.append((centres[i - 1] + centres[i]) / 2.0)

    def _column_index(block: TextBlock) -> int:
        cx = block.bbox.x + block.bbox.width // 2
        for col, boundary in enumerate(boundaries):
            if cx < boundary:
                return col
        return len(boundaries)  # last column

    # Annotate each block with its computed column index so callers
    # (and the frontend debug view) can colour-code by column.
    for block in blocks:
        block.col_index = _column_index(block)

    blocks.sort(key=lambda b: (b.col_index, b.bbox.y, b.bbox.x))
    return blocks


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

    # Reading order: column-aware sort.
    #
    # A simple (y, x) sort breaks on multi-column layouts: a block in the
    # right column at y=100 would appear before a left-column block at y=200,
    # even though readers encounter the left column first.
    #
    # Algorithm:
    # 1. Compute the horizontal center of each block.
    # 2. Sort those centers and look for the largest gap(s).  A gap wider than
    #    `column_gap_threshold` separates distinct columns.
    # 3. Assign each block to a column by its center-x.
    # 4. Sort blocks by (column_index, y).  Within a single-column page this
    #    degenerates to a pure y sort, preserving the previous behaviour.
    blocks = _sort_reading_order(blocks)

    raw_text = "\n".join(b.text for b in blocks)
    avg_conf = sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.0

    return OcrPageResult(
        page_index=params.page_index,
        blocks=blocks,
        raw_text=raw_text,
        avg_confidence=avg_conf,
    )
