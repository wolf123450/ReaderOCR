# Step 41: Enhanced Page Management UI

**Phase**: 8 — UI Workflow Redesign  
**Layer**: Vue.js frontend  
**Dependencies**: Step 39 (tab shell), Step 40 (session reconciliation)

## Objective

Replace the current `CapturedPagesPanel.vue` (filename-only list) with a full page management UI: thumbnail filmstrip sidebar, drag-and-drop reordering, insert/recapture workflows, and live renumbering.

## Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Pages]  [OCR]  [Review]  [Edit]                                    │
├─────────────────┬────────────────────────────────────────────────────┤
│ ┌─────────────┐ │                                                    │
│ │  1 [thumb]  │ │  Page 3 of 47                     [⚙ Page actions]│
│ │  ▲ text     │ │  ┌────────────────────────────────────────────────┐│
│ │             │ │  │                                                ││
│ │  2 [thumb]  │ │  │   Thumbnail (larger)                          ││
│ │  ▲ text     │ │  │                                                ││
│ │             │ │  │                                                ││
│ │► 3 [thumb]  │ │  └────────────────────────────────────────────────┘│
│ │  ▲ text     │ │                                                    │
│ │  (selected) │ │  Type: [text ▼]   Status: ✅ ok                   │
│ │             │ │                                                    │
│ │  4 [thumb]  │ │  [🔄 Recapture]  [➕ Insert before]  [🗑 Delete] │
│ │             │ │                                                    │
│ │  [+ Add]    │ │                                                    │
└─────────────────┴────────────────────────────────────────────────────┘
```

## Filmstrip Sidebar (`FilmstripSidebar.vue`)

### Features
- Vertical scrollable list of thumbnail cards
- Each card shows:
  - Thumbnail image (loaded via `convertFileSrc()`)
  - Sequential page number (post-reorder)
  - Page type badge (cover, illustration, TOC, etc.)
  - Status indicator: ✅ ok / ⚠ needs recapture / ❌ missing
  - OCR status icon: 🔤 done / ⏳ pending / — not run
- Selected page highlighted with accent border
- Drag-and-drop reorder (use `@vueuse/core` `useDraggable` or `vue-draggable-next`)
- Right-click context menu: Insert Before, Insert After, Mark Recapture, Delete, Set Type

### Drag-and-Drop Reordering
1. User drags a thumbnail card to a new position
2. Pages array reordered in store
3. All page numbers reassigned sequentially (1, 2, 3, …)
4. Session JSON updated (debounced 500ms auto-save)
5. Filenames on disk are **not** renamed — the session JSON stores the mapping from logical page number → file path

## Page Detail Pane (`PageDetailPane.vue`)

Shown to the right of the filmstrip when a page is selected:
- Larger thumbnail preview
- Page type selector (step 42)
- Status fields (ok / needs recapture / missing)
- Action buttons:
  - **Recapture**: marks the page with `status: "needs_recapture"`, switches to Capture tab with the page pre-queued
  - **Insert Before / After**: opens `InsertPageDialog` (choose: capture a new page, or import an image from file)
  - **Delete**: confirmation dialog; removes from page list; tombstones the PNG file path (does not delete the file)

## Insert Page Dialog (`InsertPageDialog.vue`)

```
┌──────────────────────────────────────┐
│  Insert page at position 3           │
├──────────────────────────────────────┤
│  ○ Capture a new page now            │
│    (switches to Capture tab)         │
│                                      │
│  ○ Import image from file…           │
│    [Browse…]                         │
│                                      │
│  [Insert]  [Cancel]                  │
└──────────────────────────────────────┘
```

## Renumbering Logic

Page numbers are **logical display numbers**, not tied to filenames:
- Internal store index (0-based) drives all array operations
- `displayPageNumber(index)` = `index + 1`
- `formatPageFilename` maps index → existing file path at that position
- After reorder: all `CapturedPage.pageNumber` values update to match new 1-based position

## Files to Create/Modify

- `src/components/FilmstripSidebar.vue` — NEW: thumbnail list with drag-drop
- `src/components/PageDetailPane.vue` — NEW: selected page detail + actions
- `src/components/InsertPageDialog.vue` — NEW: insert choice dialog
- `src/components/CapturedPagesPanel.vue` — REPLACE with `FilmstripSidebar` + `PageDetailPane` composition
- `src/stores/capture.ts` — add `reorderPages(fromIndex, toIndex)`, `insertPageAt(index, page)`, `deletePage(index)`, `renumber()` actions

## Test Criteria

### Vitest — `src/__tests__/capture.store.spec.ts` additions

1. `reorderPages(2, 0)` on [A,B,C,D] → [C,A,B,D]; all `pageNumber` values = 1,2,3,4
2. `deletePage(1)` on [A,B,C] → [A,C]; pageNumbers = 1,2
3. `insertPageAt(1, newPage)` on [A,B,C] → [A,new,B,C]; pageNumbers = 1,2,3,4
4. Reorder + delete + renumber: final array is gapless starting from 1
5. `renumber()` idempotent: calling twice gives same result

### Vitest — component tests

6. `FilmstripSidebar` renders correct number of cards from mock store
7. Clicking a card calls `selectPage(index)`
8. Card shows correct status badge for `"needs_recapture"` status
9. Right-click context menu items are present
