# Step 27: Batch Operations

**Phase**: 5 — Review & Editing UI  
**Layer**: Vue.js frontend  
**Dependencies**: Steps 24–26 (viewer, highlighting, chapter editor)

## Objective

Allow users to perform bulk actions across multiple pages: re-run OCR on selected pages, apply text cleanup, accept all suggestions, or discard and re-capture.

## Inputs

- Page selection (checkbox per page or select-all)
- Available batch operations based on page state

## Outputs

- Batch operation dispatched to Python sidecar for processing pages
- Progress feedback in UI

## UI Layout

```
┌────────────────────────────────────────────┐
│ Batch Operations          [Select All] [☐] │
├────────────────────────────────────────────┤
│ Selected: 5 pages (p.3, p.7, p.12–14)     │
│                                            │
│ [🔄 Re-run OCR]  [🧹 Re-clean Text]       │
│ [✓ Accept All]   [✕ Discard Selected]      │
│ [📷 Re-capture]                            │
│                                            │
│ ████████████░░░░░ 3/5 pages processed      │
└────────────────────────────────────────────┘
```

## Algorithm

### Page selection
1. Checkbox per page in a page thumbnail sidebar
2. Shift-click for range selection
3. Select all / deselect all toggle
4. Filter: show only pages with low confidence / unreviewed / edited

### Batch operations
1. **Re-run OCR**: Send selected page images back through OCR pipeline
2. **Re-clean text**: Re-apply post-processing (steps 19–22) on already-OCR'd text
3. **Accept all**: Mark selected pages as reviewed (no further changes needed)
4. **Discard selected**: Remove selected pages from the project
5. **Re-capture**: Queue selected pages for re-screenshot (sends command to Tauri)

### Progress tracking
1. Each batch operation runs sequentially per page via JSON-RPC
2. Update progress bar after each page completes
3. Allow cancel midway — already-processed pages keep their results
4. On error, skip page and continue, collect errors for summary

## Files to Create/Modify

- `src/components/BatchOperations.vue` — Batch action panel with progress
- `src/components/PageThumbnails.vue` — Thumbnail sidebar with selection checkboxes
- `src/composables/useBatchProcess.ts` — Batch processing logic with progress/cancel
- `src/stores/pages.ts` — Add selection state and review status per page

## Edge Cases

- No pages selected → disable all batch buttons
- Batch operation on 100+ pages → show estimated time, run in background
- User navigates away during batch → warn and offer to cancel or continue in background
- Python sidecar crashes during batch → report which pages succeeded and which failed
- Cancel during operation → partial results preserved, un-processed pages unchanged

## Test Criteria

### Automated (vitest)
1. **Selection state**: Selecting pages updates store correctly
2. **Range selection**: Shift-click selects contiguous range
3. **Select all/none**: Toggle selects/deselects all pages
4. **Progress tracking**: Mock batch of 5 pages → progress increments from 0% to 100%
5. **Cancel mid-batch**: Cancel after 3 of 5 → first 3 have new results, last 2 unchanged
6. **Empty selection**: Batch buttons disabled when no pages selected

### Manual
7. **End-to-end batch re-OCR**: Select 3 pages, re-run OCR, verify text updates
