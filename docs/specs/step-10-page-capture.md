# Step 10: Page Capture

**Phase**: 2 — Screen Capture Module  
**Layer**: Rust (Tauri backend)  
**Dependencies**: Steps 8–9 (window enumeration, region selection)

## Objective

Implement a Tauri command that captures a screenshot of a specified screen region and saves it as a PNG file. This is the atomic capture operation used by the batch loop.

## Inputs

```typescript
interface CaptureRequest {
  x: number;           // Screen X coordinate
  y: number;           // Screen Y coordinate
  width: number;       // Capture width in pixels
  height: number;      // Capture height in pixels
  output_path: string; // Absolute path to save the PNG
}
```

## Outputs

```typescript
interface CaptureResult {
  output_path: string;
  width: number;        // Actual captured width
  height: number;       // Actual captured height
  file_size_bytes: number;
}
```

## Algorithm

1. Use the `xcap` crate's `Monitor::from_point()` or `Monitor::all()` to find the monitor containing the region
2. Capture the full monitor screenshot
3. Crop to the specified region (`image` crate)
4. Encode as PNG and write to `output_path`
5. Return metadata

### Why `xcap`?
- Handles GPU-accelerated windows (DirectX, OpenGL) that `BitBlt` misses
- Cross-platform (future Linux/macOS support)
- Active development, Rust-native

## Files to Create/Modify

- `src-tauri/src/capture/region.rs` — `capture_region()` implementation
- `src-tauri/src/capture/mod.rs` — export new function
- `src-tauri/src/lib.rs` — register the Tauri command
- `src-tauri/Cargo.toml` — add `xcap` and `image` crate dependencies

## Edge Cases

- Region extends beyond monitor bounds → crop to available area, return actual dimensions
- Output directory doesn't exist → create it (or return error)
- File already exists at output_path → overwrite
- Monitor DPI scaling → ensure coordinates are in physical pixels (not logical)
- Capture fails (fullscreen exclusive app, DRM overlay) → return descriptive error

## Test Criteria

### Automated (Rust integration test)
1. **Capture produces valid PNG**: Capture a 100×100 region at (0,0) → verify file exists, file size > 0, `image::open()` succeeds with correct dimensions
2. **Creates parent directories**: Capture to a new nested directory → verify file created
3. **Non-zero content**: Captured image should not be all-black (unless screen is black) — verify at least some pixel variation

### Manual verification
4. Open a reader app, capture its content region → verify the saved PNG matches what's on screen
