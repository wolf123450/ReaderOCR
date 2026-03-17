# Step 12: Batch Capture Loop

**Phase**: 2 — Screen Capture Module  
**Layer**: Vue.js frontend + Rust backend  
**Dependencies**: Steps 9–11 (region selection, page capture, page turn)

## Objective

Implement a capture workflow that automatically captures pages in sequence: capture screenshot → turn page → wait → repeat. The user controls the loop via Start/Stop/Pause buttons. Each page is saved as a numbered PNG.

## Inputs

```typescript
interface BatchCaptureConfig {
  region: CaptureRegion;        // From step 9
  page_turn: PageTurnConfig;    // From step 11
  output_dir: string;           // Directory for page PNGs
  delay_between_ms: number;     // Delay between captures (default: 1500)
  max_pages: number | null;     // Stop after N pages (null = unlimited)
  file_prefix: string;          // Filename prefix (default: "page")
}
```

## Outputs

Each capture produces: `{output_dir}/{file_prefix}-{NNN}.png` (zero-padded 3 digits)

Progress events emitted to frontend:
```typescript
interface CaptureProgress {
  page_number: number;
  total_pages: number | null;
  image_path: string;
  status: "captured" | "error";
  error_message?: string;
}
```

## State Machine

```
IDLE → (start) → CAPTURING → (pause) → PAUSED → (resume) → CAPTURING
                → (stop)  → STOPPED
  CAPTURING → (max_pages reached) → COMPLETED
  CAPTURING → (duplicate detected) → COMPLETED
  PAUSED → (stop) → STOPPED
```

## Algorithm

1. **Start**: Validate config, create output_dir if needed, set state to CAPTURING
2. **Capture loop** (runs in Tauri async command, sends events to frontend):
   a. Capture screenshot via `capture_region` (step 10)
   b. Save as `{prefix}-{NNN}.png`
   c. Emit progress event to frontend
   d. Check for duplicate (step 13 — optional, integrated later)
   e. Send page turn key via `simulate_key` (step 11)
   f. Wait `delay_between_ms`
   g. Check if paused → wait until resumed or stopped
   h. Check if max_pages reached → stop
   i. Repeat
3. **Stop/Pause**: Set shared atomic flag, loop checks on next iteration

## Files to Create/Modify

- `src/stores/capture.ts` — batch capture state machine, config, progress tracking
- `src/views/CaptureView.vue` — Start/Stop/Pause buttons, progress display, live preview
- `src/components/ProgressTracker.vue` — capture progress bar and page counter
- `src-tauri/src/capture/batch.rs` — async batch capture loop
- `src-tauri/src/capture/mod.rs` — export batch functions

## Edge Cases

- User stops mid-capture → current page still saved, loop exits cleanly
- Output directory runs out of disk space → return error, stop loop
- Page turn doesn't actually change the page (slow reader) → delay may need to be increased; user configurable
- App crashes during capture → partial results preserved (already saved PNGs)
- Very fast capture (delay=0) → may capture before page finishes rendering; enforce minimum 200ms delay

## Test Criteria

### Automated (Vitest — store tests)
1. **State transitions**: IDLE→start→CAPTURING, CAPTURING→pause→PAUSED, PAUSED→resume→CAPTURING, CAPTURING→stop→STOPPED, CAPTURING→complete→COMPLETED
2. **Invalid transitions**: IDLE→pause → rejected, STOPPED→resume → rejected
3. **Page counter**: After 5 captures, page_number === 5
4. **File naming**: Pages named correctly with zero-padded numbers: page-001.png, page-002.png, etc.

### Manual verification
5. Capture 5 pages from a reader → verify 5 distinct PNG files in output directory
6. Pause and resume → verify capture continues from correct page number
