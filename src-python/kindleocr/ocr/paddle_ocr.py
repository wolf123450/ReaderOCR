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

def _kmeans_1d(cx_list: List[float], k: int) -> List[float]:
    """Fit *k* cluster centres to *cx_list* using 1-D k-means.

    Returns centres sorted ascending.  Converges in at most 30 iterations.
    When k >= n the individual values are returned as their own centres.
    """
    n = len(cx_list)
    k = min(k, n)
    sx = sorted(cx_list)
    # Initialise at evenly-spaced quantile positions.
    # Midpoint-quantile init: place one center in the middle of each equal
    # partition of the sorted data.  This prevents two centers landing in the
    # same cluster (a failure mode of boundary-quantile init when tight
    # clusters are much smaller than inter-cluster gaps).
    centers: List[float] = [sx[int((2 * i + 1) / (2 * k) * (n - 1))] for i in range(k)]

    for _ in range(30):
        clusters: List[List[float]] = [[] for _ in range(k)]
        for cx in cx_list:
            j = min(range(k), key=lambda j, c=cx: abs(c - centers[j]))
            clusters[j].append(cx)
        new_centers: List[float] = [
            sum(cl) / len(cl) if cl else centers[i]
            for i, cl in enumerate(clusters)
        ]
        if new_centers == centers:
            break
        centers = new_centers

    return sorted(centers)


def _total_sq_error(cx_list: List[float], centers: List[float]) -> float:
    """Sum of squared distances from each value to its nearest centre."""
    return sum(min((cx - c) ** 2 for c in centers) for cx in cx_list)


def _best_column_count(cx_list: List[float], max_cols: int) -> int:
    """Choose the number of columns using the Calinski-Harabasz criterion.

    For k = 2 … min(max_cols, n), fits k clusters via 1-D k-means and scores
    with the variance-ratio (CH) index::

        CH(k) = (BSS / (k - 1)) / (WSS / (N - k))

    where BSS is the between-cluster sum of squares and WSS is the
    within-cluster sum of squares.  A higher score is better.  CH is
    scale-invariant so it works correctly whether blocks are 10 px or
    1000 px apart.  Returns 1 when fewer than 2 blocks exist, all
    center-x values coincide, or max_cols == 1.
    """
    n = len(cx_list)
    if n < 2:
        return 1

    # With only 2 blocks CH is undefined (N–k = 0 for k = 2).  Use a simple
    # distance check instead: 50 px is a reasonable minimum column gap.
    if n == 2:
        return 2 if abs(cx_list[0] - cx_list[1]) >= 50.0 else 1

    mean_cx = sum(cx_list) / n
    total_ss = sum((cx - mean_cx) ** 2 for cx in cx_list)
    if total_ss == 0.0:  # all blocks on the same vertical line
        return 1

    # Require N-k >= 2 for n >= 5 to prevent the k=n-1 case from getting a
    # spuriously high CH due to a near-zero denominator (only 1 residual df).
    min_resid = 2 if n >= 5 else 1

    best_k = 1
    best_ch = 0.0
    # Cap k at n // 2 so every cluster has >= 2 samples on average.
    # This prevents CH from being inflated when n-k is tiny (e.g.
    # k=n-1 gives n-k=1, pushing CH extremely high via a near-zero denominator).
    for k in range(2, min(max_cols, n // 2) + 1):
        centers = _kmeans_1d(cx_list, k)
        wss = _total_sq_error(cx_list, centers)
        # Check wss BEFORE the residual guard: a perfect k-cluster fit is
        # always optimal and does not require CH computation.
        if wss == 0.0 and n - k >= 1:
            return k
        if n - k < min_resid:
            continue
        bss = total_ss - wss
        ch = (bss / (k - 1)) / (wss / (n - k))
        if ch > best_ch:
            best_ch = ch
            best_k = k

    return best_k


def _sort_reading_order(blocks: List[TextBlock], max_cols: int = 10) -> List[TextBlock]:
    """Sort blocks into reading order using k-means column detection.

    Automatically determines the best number of columns (up to *max_cols*)
    using the Calinski-Harabasz criterion: 1-D k-means is fitted for
    k = 1 ... max_cols and the model with the highest variance-ratio score
    is chosen.

    Each block's ``col_index`` field is updated in-place so the frontend
    debug view can colour-code by column.  Columns run left-to-right;
    within each column blocks are ordered top-to-bottom then left-to-right.
    """
    if not blocks:
        return blocks

    cx_list: List[float] = [b.bbox.x + b.bbox.width / 2.0 for b in blocks]
    k = _best_column_count(cx_list, max_cols)
    centers = _kmeans_1d(cx_list, k)

    def _column_index(block: TextBlock) -> int:
        cx = block.bbox.x + block.bbox.width / 2.0
        return min(range(len(centers)), key=lambda j: abs(cx - centers[j]))

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

    blocks = _sort_reading_order(blocks, max_cols=params.max_cols)

    raw_text = "\n".join(b.text for b in blocks)
    avg_conf = sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.0

    return OcrPageResult(
        page_index=params.page_index,
        blocks=blocks,
        raw_text=raw_text,
        avg_confidence=avg_conf,
    )
