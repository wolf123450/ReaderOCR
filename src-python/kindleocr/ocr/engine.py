"""OCR engine protocol, data types, and shared structures (Step 16)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class TextBlock:
    type: str           # "body" | "header" | "footer" | "page_number" | "title"
    text: str
    confidence: float   # 0.0 – 1.0
    bbox: BoundingBox
    col_index: int = 0  # 0-based column index assigned by reading-order sort


@dataclass
class OcrPageResult:
    page_index: int
    blocks: List[TextBlock]
    raw_text: str
    avg_confidence: float


@dataclass
class OcrProcessPageParams:
    image_path: str
    engine: str = "ppocr"       # "ppocr" | "ppocr_vl"
    page_index: int = 0


# ---------------------------------------------------------------------------
# Engine protocol
# ---------------------------------------------------------------------------

class OcrEngine(Protocol):
    """Structural interface that all OCR engine implementations must satisfy."""

    def ocr_page(self, params: OcrProcessPageParams) -> OcrPageResult:
        ...
