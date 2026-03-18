"""JSON-RPC 2.0 server for communication with the Tauri frontend.

Reads JSON-RPC requests from stdin (one per line), dispatches to handlers,
and writes JSON-RPC responses to stdout (one per line).
"""
from __future__ import annotations

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
    return JsonRpcServer()


def main() -> None:
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
