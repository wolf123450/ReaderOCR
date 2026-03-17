"""
JSON-RPC 2.0 protocol types for Tauri ↔ Python sidecar communication.

Mirrors the TypeScript definitions in src/protocol.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Literal, Optional, Union


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 base types
# ---------------------------------------------------------------------------


@dataclass
class JsonRpcRequest:
    jsonrpc: str
    id: Union[int, str]
    method: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class JsonRpcSuccessResponse:
    jsonrpc: str
    id: Union[int, str]
    result: Any

    @classmethod
    def create(cls, id: Union[int, str], result: Any) -> "JsonRpcSuccessResponse":
        return cls(jsonrpc="2.0", id=id, result=result)


@dataclass
class JsonRpcErrorData:
    code: int
    message: str
    data: Optional[Any] = None


@dataclass
class JsonRpcErrorResponse:
    jsonrpc: str
    id: Optional[Union[int, str]]
    error: JsonRpcErrorData

    @classmethod
    def create(
        cls,
        id: Optional[Union[int, str]],
        code: int,
        message: str,
        data: Optional[Any] = None,
    ) -> "JsonRpcErrorResponse":
        return cls(jsonrpc="2.0", id=id, error=JsonRpcErrorData(code, message, data))


# ---------------------------------------------------------------------------
# Standard error codes
# ---------------------------------------------------------------------------


class JsonRpcErrorCode(IntEnum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Application-defined errors
    OCR_ENGINE_ERROR = -32001
    IMAGE_NOT_FOUND = -32002
    EPUB_BUILD_ERROR = -32003
    OLLAMA_UNAVAILABLE = -32004


# ---------------------------------------------------------------------------
# Shared domain types
# ---------------------------------------------------------------------------

BlockType = Literal["body", "header", "footer", "page_number", "table", "figure"]


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass
class TextBlock:
    type: BlockType
    text: str
    confidence: float
    bbox: BoundingBox


@dataclass
class OcrPageResult:
    page_index: int
    blocks: List[TextBlock]
    raw_text: str
    avg_confidence: float


@dataclass
class ChapterBoundary:
    page_index: int
    title: str
    confidence: float


@dataclass
class EpubMetadata:
    title: str
    authors: List[str]
    language: str
    publisher: Optional[str] = None
    description: Optional[str] = None
    isbn: Optional[str] = None
    cover_image_path: Optional[str] = None


# ---------------------------------------------------------------------------
# RPC method params
# ---------------------------------------------------------------------------


@dataclass
class PingParams:
    timestamp: Optional[int] = None


@dataclass
class PingResult:
    status: str = "ok"
    version: str = ""
    timestamp: int = 0


@dataclass
class OcrProcessPageParams:
    image_path: str
    engine: Literal["ppocr", "ppocr_vl"] = "ppocr"


@dataclass
class PreprocessImageParams:
    image_path: str
    output_path: str
    auto_crop: bool = True
    deskew: bool = True
    normalize_contrast: bool = True


@dataclass
class PreprocessImageResult:
    output_path: str
    original_size: tuple
    processed_size: tuple


@dataclass
class CleanupParams:
    pages: List[OcrPageResult]
    remove_page_numbers: bool = True
    remove_headers_footers: bool = True


@dataclass
class CleanupResult:
    pages: List[OcrPageResult]
    removed_headers: List[str] = field(default_factory=list)
    removed_footers: List[str] = field(default_factory=list)


@dataclass
class ReconstructParagraphsParams:
    pages: List[OcrPageResult]


@dataclass
class ReconstructParagraphsResult:
    text: str
    paragraph_breaks: List[int]


@dataclass
class DetectChaptersParams:
    pages: List[OcrPageResult]


@dataclass
class DetectChaptersResult:
    chapters: List[ChapterBoundary]


@dataclass
class EpubBuildParams:
    metadata: EpubMetadata
    chapters: List[Dict[str, str]]
    output_path: str
    css: Optional[str] = None


@dataclass
class EpubBuildResult:
    output_path: str
    file_size_bytes: int
    chapter_count: int


@dataclass
class OllamaPostprocessParams:
    text: str
    task: Literal["fix_errors", "detect_paragraphs", "detect_chapters"]
    model: str = "llama3"
    endpoint: str = "http://localhost:11434"


@dataclass
class OllamaPostprocessResult:
    corrected_text: str
    changes_made: int
