"""Tests for the JSON-RPC server."""
import json
import subprocess
import sys

import pytest

from kindleocr.server import JsonRpcServer


@pytest.fixture()
def server():
    return JsonRpcServer()


class TestHandleMessage:
    def test_ping_returns_ok(self, server: JsonRpcServer):
        resp = server.handle_message(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}})
        )
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert resp["result"]["status"] == "ok"
        assert "version" in resp["result"]
        assert "timestamp" in resp["result"]

    def test_method_not_found(self, server: JsonRpcServer):
        resp = server.handle_message(
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "nonexistent", "params": {}})
        )
        assert resp["error"]["code"] == -32601
        assert "nonexistent" in resp["error"]["message"]

    def test_parse_error_on_invalid_json(self, server: JsonRpcServer):
        resp = server.handle_message("not json at all {{{")
        assert resp["error"]["code"] == -32700

    def test_invalid_request_missing_method(self, server: JsonRpcServer):
        resp = server.handle_message(json.dumps({"jsonrpc": "2.0", "id": 3}))
        assert resp["error"]["code"] == -32600

    def test_invalid_request_non_dict(self, server: JsonRpcServer):
        resp = server.handle_message(json.dumps([1, 2, 3]))
        assert resp["error"]["code"] == -32600

    def test_custom_method_registration(self, server: JsonRpcServer):
        server.register("echo", lambda params: {"echo": params.get("msg", "")})
        resp = server.handle_message(
            json.dumps({"jsonrpc": "2.0", "id": 10, "method": "echo", "params": {"msg": "hello"}})
        )
        assert resp["result"]["echo"] == "hello"

    def test_handler_exception_returns_internal_error(self, server: JsonRpcServer):
        def bad_handler(params):
            raise ValueError("boom")

        server.register("bad", bad_handler)
        resp = server.handle_message(
            json.dumps({"jsonrpc": "2.0", "id": 5, "method": "bad", "params": {}})
        )
        assert resp["error"]["code"] == -32603
        assert "boom" in resp["error"]["message"]


class TestSubprocess:
    """Integration tests that spawn the server as a subprocess."""

    def test_spawn_ping_and_exit(self):
        """Spawn python -m kindleocr, send ping, read response, close stdin."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "kindleocr"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),
        )

        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}) + "\n"
        proc.stdin.write(request.encode())
        proc.stdin.flush()

        line = proc.stdout.readline().decode().strip()
        resp = json.loads(line)
        assert resp["id"] == 1
        assert resp["result"]["status"] == "ok"

        # Close stdin → server should exit
        proc.stdin.close()
        proc.wait(timeout=5)
        assert proc.returncode == 0

    def test_graceful_shutdown_on_stdin_close(self):
        """Server exits cleanly when stdin is closed without sending anything."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "kindleocr"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),
        )
        proc.stdin.close()
        proc.wait(timeout=5)
        assert proc.returncode == 0
