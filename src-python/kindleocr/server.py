"""JSON-RPC 2.0 server for communication with the Tauri frontend.

Reads JSON-RPC requests from stdin (one per line), dispatches to handlers,
and writes JSON-RPC responses to stdout (one per line).
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time
from dataclasses import asdict
from typing import Any, Callable, Dict, Optional

from kindleocr import __version__
from kindleocr.protocol import (
    JsonRpcErrorCode,
    JsonRpcErrorResponse,
    JsonRpcSuccessResponse,
)
from kindleocr.ocr.preprocessing import PreprocessImageParams, preprocess_image
from kindleocr.ocr.engine import BoundingBox, OcrPageResult, OcrProcessPageParams, TextBlock
from kindleocr.ocr.paddle_ocr import ocr_page_paddle
from kindleocr.epub.builder import EpubBuildParams, EpubMetadata, build_epub


class JsonRpcServer:
    """A simple JSON-RPC 2.0 server over stdin/stdout."""

    def __init__(self) -> None:
        self._methods: Dict[str, Callable[..., Any]] = {}
        self.register("ping", self._handle_ping)

    def register(self, method: str, handler: Callable[..., Any]) -> None:
        """Register a method handler."""
        self._methods[method] = handler

    def _handle_ping(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "timestamp": int(time.time()),
        }

    def _make_error(
        self,
        req_id: Any,
        code: int,
        message: str,
        data: Any = None,
    ) -> Dict[str, Any]:
        resp = JsonRpcErrorResponse.create(req_id, code, message, data)
        return asdict(resp)

    def _make_success(self, req_id: Any, result: Any) -> Dict[str, Any]:
        resp = JsonRpcSuccessResponse.create(req_id, result)
        return asdict(resp)

    def handle_message(self, raw: str) -> Dict[str, Any]:
        """Parse and dispatch a single JSON-RPC message, returning a response dict."""
        # Parse JSON
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return self._make_error(None, JsonRpcErrorCode.PARSE_ERROR, "Parse error")

        # Validate request structure
        if not isinstance(msg, dict):
            return self._make_error(None, JsonRpcErrorCode.INVALID_REQUEST, "Invalid request")

        req_id = msg.get("id")
        method = msg.get("method")

        if not method or not isinstance(method, str):
            return self._make_error(req_id, JsonRpcErrorCode.INVALID_REQUEST, "Missing method")

        # Dispatch
        handler = self._methods.get(method)
        if handler is None:
            return self._make_error(
                req_id,
                JsonRpcErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {method}",
            )

        try:
            params = msg.get("params", {})
            result = handler(params)
            return self._make_success(req_id, result)
        except Exception as exc:
            return self._make_error(
                req_id,
                JsonRpcErrorCode.INTERNAL_ERROR,
                str(exc),
            )

    def run(self) -> None:
        """Main server loop: read stdin lines, dispatch, write stdout lines."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            response = self.handle_message(line)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


def create_server() -> JsonRpcServer:
    """Create and configure the server with all method handlers."""
    server = JsonRpcServer()
    server.register("preprocess_image", _handle_preprocess_image)
    server.register("ocr_page", _handle_ocr_page)
    server.register("build_epub", _handle_build_epub)
    return server


def main() -> None:
    server = create_server()
    server.run()


# ---------------------------------------------------------------------------
# Method handlers
# ---------------------------------------------------------------------------

def _handle_preprocess_image(params: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-RPC handler for 'preprocess_image'."""
    p = PreprocessImageParams(
        image_path=params["image_path"],
        output_path=params["output_path"],
        auto_crop=params.get("auto_crop", True),
        deskew=params.get("deskew", True),
        normalize_contrast=params.get("normalize_contrast", True),
    )
    result = preprocess_image(p)
    return dataclasses.asdict(result)


# Engine values accepted as PaddleOCR (the only implemented engine).
_PADDLE_ENGINE_ALIASES = frozenset({"ppocr", "ppocr_vl", "paddleocr-pp-ocrv5"})


def _handle_ocr_page(params: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-RPC handler for 'ocr_page'."""
    engine = params.get("engine", "ppocr")
    if engine not in _PADDLE_ENGINE_ALIASES:
        raise ValueError(
            f"Unsupported OCR engine: {engine!r}. "
            f"Supported engines: {sorted(_PADDLE_ENGINE_ALIASES)}"
        )
    p = OcrProcessPageParams(
        image_path=params["image_path"],
        engine="ppocr",  # normalise to canonical name; alias already validated
        page_index=params.get("page_index", 0),
        max_cols=int(params.get("max_cols", 10)),
    )
    result = ocr_page_paddle(p)
    return dataclasses.asdict(result)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# build_epub handler
# ---------------------------------------------------------------------------

def _handle_build_epub(params: Dict[str, Any]) -> Dict[str, Any]:
    """JSON-RPC handler for 'build_epub'.

    Expected params shape::

        {
          "metadata": {
            "title": "...", "author": "...", "language": "en",
            "description": "", "publisher": "", "isbn": "",
            "cover_image_path": ""
          },
          "chapters": [...],   // ChapterSegment[]
          "pages": [           // OcrPageResult[]
            {
              "page_index": 0,
              "blocks": [{"type": "body", "text": "...", "confidence": 0.9,
                          "bbox": {"x": 0, "y": 0, "width": 100, "height": 20},
                          "col_index": 0}],
              "raw_text": "...",
              "avg_confidence": 0.9
            }, ...
          ],
          "output_path": "/path/to/output.epub",
          "edited_blocks": {   // optional: page_index (str) → block list
            "0": [...]
          }
        }
    """
    meta_raw = params["metadata"]
    metadata = EpubMetadata(
        title=meta_raw["title"],
        author=meta_raw["author"],
        language=meta_raw.get("language", "en"),
        description=meta_raw.get("description", ""),
        publisher=meta_raw.get("publisher", ""),
        isbn=meta_raw.get("isbn", ""),
        cover_image_path=meta_raw.get("cover_image_path", ""),
    )

    pages: list[OcrPageResult] = []
    for p_raw in params.get("pages", []):
        blocks: list[TextBlock] = []
        for b_raw in p_raw.get("blocks", []):
            bbox_raw = b_raw.get("bbox") or {}
            blocks.append(TextBlock(
                type=b_raw.get("type", "body"),
                text=b_raw.get("text", ""),
                confidence=float(b_raw.get("confidence") or 1.0),
                bbox=BoundingBox(
                    x=float(bbox_raw.get("x") or 0),
                    y=float(bbox_raw.get("y") or 0),
                    width=float(bbox_raw.get("width") or 0),
                    height=float(bbox_raw.get("height") or 0),
                ),
                col_index=int(b_raw.get("col_index") or 0),
            ))
        raw_page_index = p_raw.get("page_index")
        pages.append(OcrPageResult(
            page_index=int(raw_page_index) if raw_page_index is not None else 0,
            blocks=blocks,
            raw_text=p_raw.get("raw_text", ""),
            avg_confidence=float(p_raw.get("avg_confidence", 1.0)),
        ))

    # edited_blocks: keys are str (JSON) → convert to int
    edited_blocks: Dict[int, list[TextBlock]] | None = None
    if "edited_blocks" in params and params["edited_blocks"]:
        edited_blocks = {}
        for page_key, block_list in params["edited_blocks"].items():
            eb: list[TextBlock] = []
            for b_raw in block_list:
                bbox_raw = b_raw.get("bbox", {})
                eb.append(TextBlock(
                    type=b_raw["type"],
                    text=b_raw["text"],
                    confidence=float(b_raw.get("confidence", 1.0)),
                    bbox=BoundingBox(
                        x=float(bbox_raw.get("x", 0)),
                        y=float(bbox_raw.get("y", 0)),
                        width=float(bbox_raw.get("width", 0)),
                        height=float(bbox_raw.get("height", 0)),
                    ),
                    col_index=int(b_raw.get("col_index", 0)),
                ))
            edited_blocks[int(page_key)] = eb

    build_params = EpubBuildParams(
        metadata=metadata,
        chapters=params.get("chapters", []),
        pages=pages,
        output_path=params["output_path"],
        edited_blocks=edited_blocks,
    )

    result = build_epub(build_params)
    return dataclasses.asdict(result)
