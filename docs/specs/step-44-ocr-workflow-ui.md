# Step 44: OCR Workflow UI

**Phase**: 8 — UI Workflow Redesign  
**Layer**: Vue.js frontend + Python sidecar  
**Dependencies**: Step 39 (tab shell), Step 42 (page metadata/ocrStatus), Step 16 (OCR execution)

## Objective

Build the OCR subtab UI: an "auto-OCR after capture" toggle, a single-page test-run button, and a full-batch OCR run with per-page progress. Support re-running OCR on individual pages from the filmstrip context menu.

## UI Layout — OCR Subtab

```
┌────────────────────────────────────────────────────────────────────┐
│  [Pages]  [OCR]  [Review]  [Edit]                                  │
├──────────────────────────────────────────────────────────────────┬─┤
│  OCR Settings                                                    │F│
│  ──────────────────────────────────────────────────────────      │i│
│  ☑ Auto-OCR new pages after capture                              │l│
│                                                                  │m│
│  Engine: [PaddleOCR PP-OCRv5 ▼]                                  │s│
│  Language: [English ▼]                                           │t│
│                                                                  │r│
│  ──────────────────────────────────────────────────────────      │i│
│  Test Run                                                        │p│
│  Run OCR on the selected page before committing to full batch.   │ │
│  [ Test OCR on page 3]                                           │ │
│                                                                  │ │
│  ──────────────────────────────────────────────────────────      │ │
│  Batch OCR                               Progress: 12 / 47  26%  │ │
│  [Run OCR — All Pages]     [Pause]   [Stop]                      │ │
│                                                                  │ │
│  ████████████░░░░░░░░░░░░░░░░░░  12 / 47                         │ │
│                                                                  │ │
│  Recent results:                                                 │ │
│  ☑ p.1 — 94.2% confidence                                        │ │
│  ☑ p.2 — 97.8% confidence                                        │ │
│  ⚠ p.3 — 71.5% confidence  (low — review recommended)            │ │
│    p.4 — running…                                                │ │
└──────────────────────────────────────────────────────────────────┴─┘
```

## Auto-OCR After Capture

- A checkbox in the OCR subtab (and mirrored in the Settings store, persisted to disk — step 38)
- When checked: after each page is successfully captured in the batch loop, the Tauri backend queues a `ocr_page` call to the Python sidecar immediately (non-blocking — OCR runs concurrently with capture delay)
- When unchecked: OCR only runs when the user explicitly triggers it

### Concurrency model
Capture and OCR can overlap: while the app waits `delayBetweenMs` before capturing the next page, it can be OCR-ing the previous page. The sidecar handles one request at a time; queue depth ≤ 2.

## Test-Run (Single Page)

1. User selects a page in the filmstrip
2. Clicks "Test OCR on page N"
3. App calls `ocr_page` for that page; shows a spinner
4. Result displayed inline: raw text preview + confidence score + bounding boxes overlaid on the thumbnail
5. If the result looks good → user can proceed with batch; if not → user can adjust settings or page type

## Batch OCR Run

### State machine

```
idle → queued → running → paused → running → completed
                       ↘ stopped
```

### Actions
- `startBatchOcr()` — set all `ocrStatus: "pending"` pages to a queue; dispatch first page
- `pauseBatchOcr()` — after current page finishes, pause
- `stopBatchOcr()` — cancel remaining queue; pages stay as `"pending"`
- `resumeBatchOcr()` — continue from first `"pending"` page

### Per-page handling
- On success: set `ocrStatus: "done"`, store `OcrPageResult` in pages store
- On error: set `ocrStatus: "error"`, store error message; continue to next page (don't abort batch)
- On skip (page type is `illustration`, `blank`, `excluded`): set `ocrStatus: "skipped"`; don't call sidecar

### Progress tracking
- `batchOcrProgress: { current: number, total: number, errors: number }`
- Live-updated as each page completes
- After batch: show summary "47 pages OCR'd — 2 with low confidence, 1 error"

## Re-run Single Page (from filmstrip context menu)

Available at any time (before or after batch). Sets that page's `ocrStatus: "pending"` and immediately dispatches it (not queued with the batch).

## Files to Create/Modify

- `src/stores/ocr.ts` — NEW: batch OCR state machine, `ocrQueue`, `batchOcrProgress`, actions
- `src/stores/settings.ts` — add `autoOcrAfterCapture: boolean`, `ocrEngine: string`, `ocrLanguage: string`
- `src/views/OcrSubtab.vue` — NEW: OCR subtab content (settings + test run + batch controls)
- `src/components/OcrProgressBar.vue` — NEW: batch progress with per-page status list
- `src-tauri/src/lib.rs` — extend batch capture loop to optionally queue OCR after each page (if `autoOcrAfterCapture` enabled)

## Test Criteria

### Vitest — `src/__tests__/ocr.store.spec.ts`

1. `startBatchOcr()` with 5 pending pages → `batchOcrProgress.total` = 5, state = `"running"`
2. On page success callback → `batchOcrProgress.current` increments; page `ocrStatus` = `"done"`
3. On page error callback → `batchOcrProgress.errors` increments; page `ocrStatus` = `"error"`; batch continues
4. `pauseBatchOcr()` → state = `"paused"`; no more pages dispatched
5. `resumeBatchOcr()` → state = `"running"`; continues from next pending
6. `stopBatchOcr()` → remaining pages stay `"pending"`; state = `"stopped"`
7. Pages with `pageType: "blank"` or `"excluded"` → auto-skipped, `ocrStatus` = `"skipped"`
8. `autoOcrAfterCapture` = false → batch not started automatically on page capture
9. `autoOcrAfterCapture` = true → batch entry queued automatically after capture event

### Vitest — settings store

10. `autoOcrAfterCapture` defaults to `false`
11. Toggling persists to settings JSON (mock the Tauri persist call)
