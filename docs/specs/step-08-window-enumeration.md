# Step 08: Window Enumeration

**Phase**: 2 — Screen Capture Module  
**Layer**: Rust (Tauri backend)  
**Dependencies**: Steps 1–5 (project scaffold)

## Objective

Implement a Tauri command that enumerates all visible, top-level windows on the system and returns their metadata (title, handle, position, size) to the Vue frontend. This enables the user to select which application window contains the book they want to capture.

## Inputs

None (system call). Optionally, a filter string to match window titles.

## Outputs

```typescript
interface WindowInfo {
  handle: number;       // OS window handle (HWND cast to u64)
  title: string;        // Window title text
  x: number;            // Window position
  y: number;
  width: number;        // Window dimensions
  height: number;
  process_name: string; // Owning process name (e.g., "Kindle.exe")
}
```

Returns `WindowInfo[]` — sorted by title, filtered to exclude:
- Windows with empty titles
- Windows with zero width or height
- Invisible windows (not `IsWindowVisible`)
- The KindleOCR window itself

## Algorithm

1. Use the `windows` crate to call `EnumWindows` (win32 API)
2. For each HWND callback:
   a. Check `IsWindowVisible(hwnd)` — skip if false
   b. Get window title via `GetWindowTextW` — skip if empty
   c. Get window rect via `GetWindowRect` — skip if zero-area
   d. Get process ID via `GetWindowThreadProcessId`
   e. Get process name via `OpenProcess` + `QueryFullProcessImageNameW`
   f. Exclude own process (compare PID)
3. Collect into `Vec<WindowInfo>`, sort by title
4. Expose as Tauri command: `#[tauri::command] fn list_windows() -> Result<Vec<WindowInfo>, String>`

## Files to Create/Modify

- `src-tauri/src/capture/mod.rs` — module declaration
- `src-tauri/src/capture/windows.rs` — `list_windows()` implementation
- `src-tauri/src/lib.rs` — register the command with Tauri
- `src-tauri/Cargo.toml` — add `windows` crate dependency with required features

## Edge Cases

- Window title contains non-UTF-8 characters → use lossy conversion
- Process handle cannot be opened (elevated process) → return process_name as "Unknown"
- Window is in the process of closing (race condition) → skip gracefully on error
- Multiple monitors → window coordinates may be negative (monitor to the left)
- Minimized windows → still returned (they have valid dimensions) but flagged if needed
- UWP apps (Windows Store apps) → may have wrapper windows; ensure real title is captured

## Test Criteria

### Automated (Rust unit tests)
1. **At least one window returned**: call `list_windows()` in test → assert `result.len() >= 1` (there's always at least the test runner console)
2. **No empty titles**: assert all returned windows have `!title.is_empty()`
3. **No zero-area windows**: assert all returned windows have `width > 0 && height > 0`
4. **Self-exclusion**: assert no returned window has the current process PID

### Manual verification
5. Open Kindle/Calibre viewer, run command → verify the reader window appears in the list with correct title
