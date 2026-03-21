# Step 24: Side-by-Side Viewer

**Phase**: 5 — Review & Editing UI  
**Layer**: Tauri + Vue.js frontend  
**Dependencies**: Step 10 (captured images), Step 18 (extracted text), Step 46 (block editor — provides the image overlay panel)

> **Note on implementation approach**: The SVG bounding-box overlay built for the OCR debug view in `OcrSubtab.vue` already provides the image panel foundation (image display, SVG overlay, `convertFileSrc` loading, natural-size tracking). The side-by-side viewer should reuse or promote that infrastructure rather than building a separate `ImagePanel.vue` from scratch. The "Debug view" toggle in the OCR tab evolves into step 46 (Block Editor). This step (24) focuses on the page-navigation wrapper and the editable text panel that shows the blocks in reading order — consumed from `editedBlocks` when present, falling back to the raw `OcrPageResult.blocks`.

## Objective

Build a split-pane view where the user sees the original page image on the left and the OCR'd text on the right. Users can scroll through pages, compare text with the source image, and make inline edits.

## Inputs

- Array of captured page images (file paths)
- Array of OCR'd text results per page (OcrPageResult[])

## Outputs

- Vue component `SideBySideViewer.vue` rendered in the main window
- User-edited text persisted in application state

## UI Layout

```
┌──────────────────────────────────────────────────┐
│ [◀ Prev]  Page 3 of 42  [Next ▶]   [Zoom: 100%] │
├────────────────────┬─────────────────────────────┤
│                    │                             │
│   Page Image       │   OCR Text (editable)       │
│   (scrollable,     │   (contenteditable or       │
│    zoomable)        │    <textarea>)              │
│                    │                             │
│                    │                             │
├────────────────────┴─────────────────────────────┤
│ Status: OCR confidence 94.2%  │ Chapter: "III"   │
└──────────────────────────────────────────────────┘
```

## Algorithm

### Image display
1. Load page image via Tauri `convertFileSrc()` for secure local file access
2. Support zoom (50%–300%) via CSS transform + mouse wheel
3. Synchronize scroll position between image and text panels (optional, can be toggled)

### Text editing
1. Display OCR text assembled from the `editedBlocks` for the page (step 46) — blocks of type `excluded`, `header`, `footer`, `page_number` are greyed out and marked, not omitted, so the user can see what will be filtered
2. The text panel shows blocks as a list of individually-editable entries (mirroring the block order table in step 46) rather than a single flat `<textarea>`; editing a block here is equivalent to editing it in the block editor
3. Track dirty state per page (modified vs original from raw OCR)
4. Auto-save edits to in-memory state on debounced input (500ms)
5. **Click-to-link**: Clicking a block row in the text panel highlights the corresponding bbox in the SVG overlay and scrolls the image to centre on it (same behaviour as clicking in the block table in step 46)

### Navigation
1. Page forward/back with keyboard shortcuts (Arrow Left/Right, Page Up/Down)
2. Jump to specific page via page number input
3. Display current page / total pages

## Files to Create/Modify

- `src/components/SideBySideViewer.vue` — Main split-pane component
- `src/components/ImagePanel.vue` — Zoomable, scrollable image display
- `src/components/TextPanel.vue` — Editable text panel with dirty tracking
- `src/components/PageNavigation.vue` — Page navigation controls
- `src/stores/pages.ts` — Pinia store for page state management
- `src/App.vue` — Integration of viewer into main layout

## Edge Cases

- Very large images → use CSS `object-fit` and lazy loading, only load visible page + neighbors
- No OCR text for page → show empty text panel with "Not yet processed" message
- User navigates away without saving → warn if dirty pages exist
- Page image file deleted → show placeholder image with error message

## Test Criteria

### Automated (vitest + vue-test-utils)
1. **Component mounts**: SideBySideViewer renders with image and text panels
2. **Page navigation**: Store state updates correctly on page change
3. **Dirty tracking**: Editing a block's text marks the page as dirty in the OCR store's `editedBlocks`
4. **Zoom state**: Zoom in/out updates CSS transform value
5. **Edge page navigation**: Can't go below page 1 or above max page
6. **editedBlocks fallback**: When `editedBlocks[pageId]` is absent, text panel renders from raw `OcrPageResult.blocks`; when present, renders from edited version
7. **Excluded blocks visible**: Block with `blockType: "excluded"` renders in the text panel with a visual marker, not removed

### Manual
8. **Visual**: Image and text display correctly side by side
9. **Scroll sync**: Scrolling one panel optionally scrolls the other
10. **Click-to-highlight**: Clicking a text panel block highlights and centres the matching SVG bbox
