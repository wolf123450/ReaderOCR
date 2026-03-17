# Step 37: Logging & Diagnostics

**Phase**: 7 — Distribution & Polish  
**Layer**: All layers  
**Dependencies**: Step 36 (error handling)

## Objective

Implement structured logging across all layers for debugging and diagnostics. Logs should help diagnose issues without exposing sensitive data. Support configurable log levels.

## Inputs

- All modules across Tauri, Vue.js, and Python layers

## Outputs

- Rotating log files in user's app data directory
- In-app log viewer (optional, for power users)
- Console output for development

## Algorithm

### Log levels
- **ERROR**: Unrecoverable failures, exceptions
- **WARN**: Recoverable issues, degraded functionality
- **INFO**: Key operations (OCR started, EPUB exported, sidecar launched)
- **DEBUG**: Detailed operation data (page timings, confidence scores)
- **TRACE**: Very verbose (full JSON-RPC messages, pixel data summaries)

### Rust/Tauri logging
1. Use `tauri-plugin-log` (already added)
2. Configure: file rotation (5 files, 5 MB each), stderr output in dev
3. Log file location: `%APPDATA%\com.kindleocr.app\logs\`
4. Key log points: app launch, sidecar start/stop, window capture, plugin init

### Python sidecar logging
1. Use Python `logging` module with structured format
2. JSON format for machine parsing: `{"timestamp": "...", "level": "...", "module": "...", "message": "..."}`
3. Output to stderr (captured by Tauri as sidecar output)
4. Key log points: RPC request/response (DEBUG), OCR timings, error details

### Vue.js logging
1. Lightweight logger utility (no heavy library needed)
2. Console output in development, silent in production
3. Key log points: route changes, store mutations, user actions

### Log file management
1. Rotate logs at 5 MB per file, keep last 5 files
2. Include timestamp, log level, module name, message
3. Never log sensitive data (file paths are OK, file content is not)

## Files to Create/Modify

- `src-tauri/src/lib.rs` — Configure tauri-plugin-log with rotation
- `src-python/kindleocr/logging_config.py` — Python logging setup
- `src/utils/logger.ts` — Frontend logging utility
- `src/components/LogViewer.vue` — Optional in-app log viewer (dev tools)

## Edge Cases

- Log directory doesn't exist → create it on first run
- Disk full → log rotation should prevent this; if still full, stop writing gracefully
- Very fast logging (OCR on 100 pages) → don't log per-pixel data, only summaries
- Multi-process logging → each process (Tauri, sidecar) writes to separate streams

## Test Criteria

### Automated (pytest + vitest)
1. **Python logger setup**: Logger initializes without errors, outputs to stderr
2. **Log format**: Log output matches expected JSON structure
3. **Log level filtering**: DEBUG messages hidden when level is INFO
4. **Frontend logger**: Logger calls don't throw in production mode
5. **No sensitive data**: OCR log entry contains page number but not full text content
