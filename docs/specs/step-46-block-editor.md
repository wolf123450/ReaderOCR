# Step 46: Block-Level Reading Order Editor

**Phase**: 5 — Review & Editing UI  
**Layer**: Vue.js frontend + Python sidecar (block type round-trip)  
**Dependencies**: Step 18 (OCR execution, TextBlock[]), debug view in `OcrSubtab.vue` (already implemented)

## Objective

Evolve the existing "Debug view" in `OcrSubtab.vue` into a fully interactive block editor. Users can see every OCR text block represented as a labelled bounding-box on the image, then directly manipulate reading order, merge or split blocks, annotate block types, and override column assignments — all before downstream text-processing (paragraph reconstruction, EPUB export) consumes the data.

The automatic column detection and reading-order sort are a good heuristic starting point. This step adds the human-in-the-loop override layer.

## Inputs

- `OcrPageResult.blocks: TextBlock[]` — the ordered, column-annotated block list produced by step 18 (currently stored in `ocr.testRunResult` in `src/stores/ocr.ts`)
- Page image file path (for the SVG overlay)

## Outputs

- `EditedPageBlocks` stored per page in the OCR store — a block list that may differ from the raw OCR output in ordering, text content, block type, or column assignment
- This edited list is what all downstream steps (paragraph reconstruction, EPUB assembly) consume

## Block Type Vocabulary

Each block carries a `blockType` field (extends the current implicit "body" default):

| Value | EPUB treatment |
|---|---|
| `body` | Normal `<p>` text (default) |
| `chapter_title` | `<h1>` heading |
| `section_heading` | `<h2>` heading |
| `header` | Excluded from EPUB body |
| `footer` | Excluded from EPUB body |
| `page_number` | Excluded from EPUB body |
| `figure_caption` | `<figcaption>` under adjacent figure |
| `sidebar` | `<aside>` block |
| `excluded` | Omitted entirely |

The layout-analysis heuristics from step 17 pre-populate these; this editor allows manual override.

## UI Layout

The block editor replaces/supersedes the current "Debug view" toggle. It renders in the same location:

```
┌──────────────────────────────────────────────────────────────┐
│ [✔ Show block editor]  Max columns: [10]                     │
├───────────────────────────┬──────────────────────────────────┤
│                           │  SELECTED BLOCK                  │
│   Page image              │  ┌─────────────────────────────┐ │
│   + SVG overlay           │  │ Type: [body ▾]              │ │
│   (blocks as coloured     │  │ Col:  [0 ▾]                 │ │
│    rectangles with        │  │ Text: [editable textarea]   │ │
│    order badges)          │  │ [Merge ↓ with next]         │ │
│                           │  │ [Split at cursor]           │ │
│   Click block → selects   │  │ [Delete block]              │ │
│   it in table + panel     │  └─────────────────────────────┘ │
│                           │                                  │
│                           │  BLOCK ORDER (drag to reorder)   │
│                           │  ┌─────────────────────────────┐ │
│                           │  │ ⠿ 1 | col 0 | 94% | body   │ │
│                           │  │ ⠿ 2 | col 0 | 88% | body   │ │
│                           │  │ ⠿ 3 | col 1 | 96% | body   │ │
│                           │  └─────────────────────────────┘ │
└───────────────────────────┴──────────────────────────────────┘
```

## Algorithm / Interactions

### Block selection
1. Click a block rectangle in the SVG overlay → selects it (highlights with thick border, scrolls table to that row)
2. Click a row in the block order table → selects it (highlights SVG rect, scrolls image to centre on that block's bbox)
3. Selected block's details are shown in the edit panel

### Reading order reorder
1. Block order table rows are drag-and-drop sortable (use `vuedraggable` or native HTML5 drag)
2. Dragging row N above row M swaps reading positions — SVG order-number badges update reactively
3. Reorder is applied to the in-memory `editedBlocks` array
4. "Reset to auto" button reverts to the original OCR-produced order

### Block type override
1. Type dropdown per selected block — changes `blockType`
2. SVG overlay optionally uses different outline styles per type (solid for body, dashed for excluded, double for heading)
3. A filter chip bar at top of table allows hiding/showing blocks by type

### Column assignment override
1. Column dropdown in the edit panel allows reassigning a block to a different column index
2. SVG rectangle stroke colour updates immediately

### Merge adjacent blocks
1. Select a block → "Merge ↓ with next" button
2. Combines text of block N and N+1 (space-separated), uses the bounding hull of both bboxes, removes block N+1
3. Resulting block retains the lower block's `blockType` if it was non-default, else keeps the upper's type

### Split block
1. Place text cursor inside the editable textarea at the split point, click "Split at cursor"
2. Creates two blocks: first with text before cursor, second with text after
3. Bboxes are estimated by proportional y-split (top half → block A, bottom half → block B)
4. Both new blocks inherit the original's `col_index` and `blockType`

### Text editing
1. The editable textarea in the selection panel allows direct text correction per block
2. Changes are saved immediately to `editedBlocks` on input (no save button needed)

### Persistence
1. Edited blocks are stored in `editedBlocks: Record<pageId, TextBlock[]>` in the OCR Pinia store
2. A "modified" badge appears in the filmstrip thumbnail and block table header when edits exist
3. "Reset to raw" reverts to the OCR-produced block list for that page

## Files to Create/Modify

- `src/views/OcrSubtab.vue` — Evolve debug view into block editor (selection, reorder, edit panel)
- `src/stores/ocr.ts` — Add `editedBlocks` map, `setEditedBlocks(pageId, blocks)`, `resetEditedBlocks(pageId)`
- `src/composables/useBlockEditor.ts` — Block selection state, merge/split logic, reorder
- `src/components/BlockEditorPanel.vue` — The selected block detail/edit panel (right side)
- `src/components/BlockOrderTable.vue` — Sortable block table (left/bottom side)
- `src-python/kindleocr/ocr/engine.py` — Add `block_type: str = "body"` to `TextBlock` dataclass
- `src-tauri/src/lib.rs` — Add `block_type: String` to `SidecarTextBlock` struct; forward in response
- `src/stores/ocr.ts` — Expose `blockType` in `TextBlock` TypeScript interface

## Edge Cases

- OCR result has 0 blocks → editor shows empty state with message
- User merges a `header` block with a `body` block → merged block type prompts confirmation or uses a sensible default
- Split leaves one half empty (cursor at start/end) → silently cancel, show tooltip
- editedBlocks for a page are stale after re-running OCR on that page → re-run OCR clears the edited blocks for that page (with an "overwrite" confirmation if edits exist)
- Very long text block in textarea → textarea auto-grows; table cell truncates with tooltip

## Test Criteria

### Automated (vitest)
1. **Reorder**: Move block 3 to position 1 → editedBlocks[pageId][0] is the formerly-third block
2. **Merge**: Merge blocks at index 1+2 → editedBlocks has one fewer entry; combined text is block 1 text + " " + block 2 text
3. **Split**: Split block "hello world" at character 5 → two blocks: "hello" and "world"; bboxes are top/bottom halves of original
4. **Type change**: Set blockType to "excluded" → block appears struck-through in table; downstream `editedBlocks` shows `blockType: "excluded"`
5. **Reset**: After edits, resetEditedBlocks(pageId) → store returns original OCR blocks for that page
6. **OCR re-run clears edits**: `setPageOcrResult(pageId, result)` removes any existing `editedBlocks[pageId]` entry (signals re-run)
7. **Column override**: Change col_index from 0 to 2 → SVG rect uses colour of column 2

### Manual
8. **Drag reorder**: Drag row 4 above row 1; SVG badges re-number correctly and the text-view assembles in the new order
9. **Click-to-select sync**: Click SVG block → correct row highlights and scrolls into view; click table row → SVG rect highlights
10. **Text edit persists across navigation**: Edit block 2 text, navigate to next page, navigate back → edits preserved
