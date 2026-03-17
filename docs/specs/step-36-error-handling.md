# Step 36: Error Handling & Recovery

**Phase**: 7 — Distribution & Polish  
**Layer**: All layers (Tauri, Vue.js, Python)  
**Dependencies**: All previous steps

## Objective

Implement comprehensive error handling across all layers. Ensure every failure mode has a user-friendly error message and recovery path. No unhandled exceptions should reach the user as raw stack traces.

## Inputs

- All existing code modules
- Error code definitions from protocol (step 4)

## Outputs

- Global error boundary in Vue.js
- Structured error responses from Python sidecar
- Tauri-layer error handling for system calls
- User-facing error notifications

## Algorithm

### Vue.js error handling
1. **Global error handler**: `app.config.errorHandler` catches uncaught Vue errors
2. **Error boundary component**: Wraps each major section, shows friendly message on crash
3. **Toast notifications**: Non-fatal errors show as dismissible toast messages
4. **Error state in stores**: Each store has error state for async operation failures

### Python sidecar error handling
1. **JSON-RPC error responses**: All errors return structured `JsonRpcErrorResponse` with code/message/data
2. **Exception hierarchy**:
   ```python
   class KindleOcrError(Exception): ...
   class OcrEngineError(KindleOcrError): code = -32001
   class ImageNotFoundError(KindleOcrError): code = -32002
   class EpubBuildError(KindleOcrError): code = -32003
   class OllamaUnavailableError(KindleOcrError): code = -32004
   ```
3. **Top-level try/except in server**: Never let exceptions crash the sidecar process
4. **Stderr logging**: Errors logged to stderr (captured by Tauri) for debugging

### Tauri error handling
1. **Command results**: All Tauri commands return `Result<T, String>` 
2. **Sidecar lifecycle**: Detect sidecar crash → attempt restart (max 3 retries)
3. **System API failures**: Window enumeration, screenshot failures → specific error messages

### Recovery strategies
1. **Sidecar crash**: Auto-restart with exponential backoff (1s, 2s, 4s)
2. **OCR failure on single page**: Skip page, mark as failed, continue batch
3. **Network error (Ollama)**: Retry once, then mark as unavailable
4. **File system errors**: Show path and suggest permissions fix
5. **GPU/CUDA errors**: Fall back to CPU mode for OCR

## Files to Create/Modify

- `src/components/ErrorBoundary.vue` — Vue error boundary wrapper
- `src/components/ToastNotification.vue` — Toast message component
- `src/composables/useErrorHandler.ts` — Global error handling logic
- `src-python/kindleocr/errors.py` — Exception hierarchy
- `src-python/kindleocr/server.py` — Top-level error handling in RPC server
- `src-tauri/src/lib.rs` — Sidecar lifecycle management with auto-restart

## Edge Cases

- Multiple simultaneous errors → queue toasts, show sequentially
- Error during error handling → log to console, show generic "something went wrong"
- Sidecar restart loop → after 3 failed restarts, show "Sidecar failed" and offer manual restart
- Disk full during EPUB write → detect, show specific message about disk space

## Test Criteria

### Automated (vitest + pytest)
1. **Vue error boundary**: Child component throws → error boundary catches, shows fallback UI
2. **Toast display**: Error event → toast appears with message, auto-dismisses after timeout
3. **Python exception mapping**: Each exception class maps to correct JSON-RPC error code
4. **Server catch-all**: Unexpected exception → returns INTERNAL_ERROR (-32603), doesn't crash
5. **Sidecar restart**: Mock sidecar exit → Tauri attempts restart
6. **OCR batch skip**: OCR fails on page 3 of 5 → pages 1,2,4,5 succeed, page 3 marked failed
