# Step 24: Side-by-Side Viewer

**Phase**: 5 — Review & Editing UI  
**Layer**: Tauri + Vue.js frontend  
**Dependencies**: Step 10 (captured images), Step 18 (extracted text)

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
1. Display OCR text in a `<textarea>` or rich text editor
2. Track dirty state per page (modified vs original)
3. Auto-save edits to in-memory state on debounced input (500ms)

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
3. **Dirty tracking**: Editing text marks page as dirty in store
4. **Zoom state**: Zoom in/out updates CSS transform value
5. **Edge page navigation**: Can't go below page 1 or above max page

### Manual
6. **Visual**: Image and text display correctly side by side
7. **Scroll sync**: Scrolling one panel optionally scrolls the other
