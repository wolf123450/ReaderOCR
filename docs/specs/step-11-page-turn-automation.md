# Step 11: Page Turn Automation

**Phase**: 2 — Screen Capture Module  
**Layer**: Rust (Tauri backend)  
**Dependencies**: Step 8 (window enumeration — need window handle for focus)

## Objective

Implement a Tauri command that simulates a keypress to turn the page in the target reader application. The key and delay are configurable.

## Inputs

```typescript
interface PageTurnConfig {
  window_handle: number;     // Target window to receive the key event
  key: string;               // Key name: "Right", "Left", "PageDown", "PageUp", "Space"
  delay_before_ms?: number;  // Delay before sending key (default: 0)
}
```

## Outputs

```typescript
interface PageTurnResult {
  success: boolean;
  key_sent: string;
}
```

## Algorithm

1. Parse the key name string into a win32 virtual key code (VK_RIGHT, VK_NEXT, etc.)
2. Bring the target window to the foreground via `SetForegroundWindow(hwnd)`
3. Wait `delay_before_ms` if specified
4. Use `SendInput` to send a key-down + key-up event sequence
5. Return success

### Key mapping
| Config string | Virtual key code |
|--------------|-----------------|
| `"Right"` | `VK_RIGHT` (0x27) |
| `"Left"` | `VK_LEFT` (0x25) |
| `"PageDown"` | `VK_NEXT` (0x22) |
| `"PageUp"` | `VK_PRIOR` (0x21) |
| `"Space"` | `VK_SPACE` (0x20) |

## Files to Create/Modify

- `src-tauri/src/keyboard/mod.rs` — key simulation implementation
- `src-tauri/src/lib.rs` — register the command
- `src-tauri/Cargo.toml` — may already have `windows` crate; ensure `Win32_UI_Input_KeyboardAndMouse` feature

## Edge Cases

- Target window no longer exists → return error
- Target window belongs to elevated process → `SetForegroundWindow` may fail; attempt `AllowSetForegroundWindow` or fall back to `keybd_event`
- Unknown key string → return error with list of valid keys
- Multiple rapid key sends → caller manages timing (this command is synchronous, single-shot)

## Test Criteria

### Automated (Rust unit test)
1. **Key name parsing**: "Right" → VK_RIGHT, "PageDown" → VK_NEXT, etc. All valid names parse correctly.
2. **Invalid key name**: "InvalidKey" → returns error

### Manual verification
3. Open Notepad, send "Right" → cursor moves right
4. Open Kindle reader, send "Right" → page turns
