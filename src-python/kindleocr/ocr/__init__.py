"""OCR engine modules."""

from kindleocr.ocr.engine import (
    BoundingBox,
    OcrEngine,
    OcrPageResult,
    OcrProcessPageParams,
    TextBlock,
)
from kindleocr.ocr.preprocessing import (
    PreprocessImageParams,
    PreprocessImageResult,
    preprocess_image,
)

__all__ = [
    "BoundingBox",
    "OcrEngine",
    "OcrPageResult",
    "OcrProcessPageParams",
    "TextBlock",
    "PreprocessImageParams",
    "PreprocessImageResult",
    "preprocess_image",
]
