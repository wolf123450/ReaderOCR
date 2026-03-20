"""PaddleOCR engine implementation.

Uses a lazy singleton so the model is loaded at most once per process.
Falls back gracefully when PaddleOCR is not installed.
"""

from __future__ import annotations

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

        # show_log=False suppresses verbose model-loading output.
        _ppocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            use_gpu=True,
            show_log=False,
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
    raw = ocr.ocr(params.image_path, cls=True)

    # PaddleOCR returns [[line, ...]] or [None] for blank images.
    if not raw or raw[0] is None:
        return OcrPageResult(
            page_index=params.page_index,
            blocks=[],
            raw_text="",
            avg_confidence=0.0,
        )

    blocks: List[TextBlock] = []
    for line in raw[0]:
        if line is None:
            continue
        points, (text, confidence) = line
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x = int(min(xs))
        y = int(min(ys))
        w = int(max(xs)) - x
        h = int(max(ys)) - y
        blocks.append(
            TextBlock(
                type="body",
                text=text,
                confidence=float(confidence),
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
