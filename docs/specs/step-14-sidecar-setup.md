# Step 14: Sidecar Setup

**Phase**: 3 — OCR Pipeline  
**Layer**: Rust (Tauri backend) + Python sidecar  
**Dependencies**: Steps 3–4 (Python project, JSON-RPC protocol)

## Objective

Configure Tauri to spawn the Python sidecar process and communicate via JSON-RPC 2.0 over stdin/stdout. Implement the Python-side JSON-RPC server loop and a Rust-side client for sending requests and receiving responses.

## Inputs

Tauri app startup triggers sidecar spawn. JSON-RPC requests are sent from Rust to Python.

## Outputs

Bidirectional JSON-RPC communication:
- Rust → Python: `{ "jsonrpc": "2.0", "id": 1, "method": "ping", "params": {} }`
- Python → Rust: `{ "jsonrpc": "2.0", "id": 1, "result": { "status": "ok", "version": "0.1.0", "timestamp": 1234567890 } }`

## Algorithm

### Python side (server.py)
1. Read lines from stdin in a loop
2. Parse each line as JSON-RPC request
3. Dispatch to method handler based on `method` field
4. Serialize response as JSON, write to stdout (one line), flush
5. Handle errors: parse error, method not found, internal error

### Rust side (sidecar module)
1. On app startup, spawn the Python process: `python -m kindleocr.server`
2. Hold stdin/stdout handles
3. Provide `async fn call_sidecar<P, R>(method: &str, params: P) -> Result<R>`:
   a. Serialize request as JSON line
   b. Write to sidecar stdin
   c. Read response line from sidecar stdout
   d. Deserialize and return result (or error)
4. On app shutdown, send SIGTERM / close stdin to trigger graceful exit

### Tauri sidecar configuration
- Configure in `tauri.conf.json` under `"app" > "sidecar"` or spawn manually via `Command::new()`
- For development: spawn `python` directly pointing to the module
- For production: spawn the PyInstaller-bundled exe (step 34)

## Files to Create/Modify

- `src-python/kindleocr/server.py` — JSON-RPC server implementation
- `src-python/kindleocr/__main__.py` — entry point for `python -m kindleocr`
- `src-tauri/src/sidecar/mod.rs` — sidecar lifecycle + JSON-RPC client
- `src-tauri/src/lib.rs` — spawn sidecar on app setup
- `src-python/tests/test_server.py` — server protocol tests

## Edge Cases

- Python not installed / not on PATH → clear error message to user
- Sidecar crashes → detect process exit, offer restart
- Sidecar sends malformed response → return parse error to caller
- Concurrent requests → use request IDs to match responses; queue or serialize requests
- Large responses (OCR results with many blocks) → ensure no line-length limits
- Sidecar startup is slow (loading PaddleOCR models) → don't block app startup; show "loading" state

## Test Criteria

### Automated (Python — pytest)
1. **Ping/pong**: Send `{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}` to server → receive `{"jsonrpc":"2.0","id":1,"result":{"status":"ok",...}}`
2. **Method not found**: Send unknown method → receive error with code -32601
3. **Parse error**: Send invalid JSON → receive error with code -32700
4. **Invalid request**: Send JSON without `method` field → receive error with code -32600

### Automated (Rust — integration test)  
5. **Spawn and ping**: Spawn Python subprocess, send ping, verify pong response
6. **Graceful shutdown**: Close stdin → verify Python process exits

### Manual verification
7. Start Tauri app → verify sidecar spawns (check process list)
8. Close Tauri app → verify sidecar process is cleaned up
