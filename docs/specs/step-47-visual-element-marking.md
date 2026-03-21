# Step 47: Visual Element Region Marking

**Phase**: 5 — Review & Editing UI  
**Layer**: Vue.js frontend + Python sidecar (region crop at export time)  
**Dependencies**: Step 46 (block editor — SVG overlay infrastructure), Step 30 (EPUB assembly — embeds the cropped images)

## Objective

Allow users to mark non-text areas on a page image (illustrations, diagrams, maps, tables rendered as images, decorative elements) so those regions are preserved in the EPUB as embedded images rather than being silently skipped. Users draw bounding boxes directly on the page image, give each region a label, and the system crops the image at those coordinates and embeds it in the EPUB at the correct reading-order position.

This addresses a core limitation of OCR-only pipelines: purely visual content and text-heavy images (tables, charts) are lost unless explicitly preserved.

## Inputs

- Page image file path (for display and later cropping)
- Existing `editedBlocks: TextBlock[]` for the page (from step 46) — figure regions interleave with text blocks

## Outputs

- `FigureRegion[]` stored per page:
  ```typescript
  interface FigureRegion {
    id: string;             // UUID
    bbox: BoundingBox;      // x, y, width, height in image pixels
    label: string;          // e.g. "Figure 1", "Map", "Table 3.2"
    altText: string;        // EPUB accessibility alt text
    captionBlockId?: string; // Optional: ID of a text block that is the caption for this figure
  }
  ```
- Cropped image files written to the session output directory at EPUB-generation time: `{session}-fig-{pageIndex}-{figureId}.png`

## UI Integration (extends Step 46 block editor)

The visual element marking tool is an additional mode within the block editor's image panel. A toolbar toggle switches between "Select blocks" mode and "Mark figure" mode:

```
┌──────────────────────────────────────────────────────────────┐
│ Image panel toolbar:                                         │
│  [☞ Select block]  [⬚ Mark figure region]                   │
│                                                              │
│   Page image + SVG overlay                                   │
│   In "Mark figure" mode:                                     │
│     - Text block rects are shown dimmed (non-interactive)    │
│     - User click-drags to draw a new dashed rectangle        │
│     - On release: "Label this figure" inline prompt appears  │
│     - Figure regions shown with purple dashed border + icon  │
│                                                              │
│   Existing figure regions show:                              │
│     [image icon] [label] [✎ edit] [✕ remove]                │
└──────────────────────────────────────────────────────────────┘
```

Figure regions also appear in the block order table (step 46) as their own row type, interspersed with text blocks. Users can drag them to set their position in reading order relative to surrounding text — this determines where the `<img>` appears in the EPUB chapter HTML.

## Algorithm

### Drawing a figure region
1. User selects "Mark figure" mode from the image panel toolbar
2. Mouse down on image → start drawing rectangle (rubber-band selection)
3. Mouse up → rectangle finalised; inline prompt appears: "Label:" input + "Alt text:" input + [Save] [Cancel]
4. On Save: `FigureRegion` added to store; appears in block order table as a figure-type row
5. SVG renders the figure region as a dashed purple rectangle with the label

### Editing a figure region
1. Click the figure rectangle in SVG → selects it, shows edit panel (same right-side panel as block editor)
2. Label and alt text are editable
3. Resize handles on the SVG rectangle allow adjusting the bbox (optional for V1; can be delete+redraw)
4. "Assign caption" button: click a text block in the overlay to link it as the figure's caption; that block auto-changes to `blockType: "figure_caption"`

### Reading order placement
- Figure regions appear in the block order table alongside text blocks
- A figure inserted above a text block renders before it in the EPUB
- Default placement: figure region is inserted at the estimated Y-midpoint position relative to surrounding text blocks

### Image cropping (at export time)
- Python sidecar receives a `crop_figure_regions` RPC call with the page image path + list of `FigureRegion` bboxes
- Uses Pillow: `Image.open(path).crop((x, y, x+w, y+h)).save(output_path, "PNG")`
- Returns list of cropped image paths
- Called during EPUB assembly (step 30), not during editing (lazy evaluation)

### EPUB embedding (step 30 integration)
- For each figure region in reading order, EPUB assembly emits:
  ```html
  <figure>
    <img src="../images/{figId}.png" alt="{altText}" />
    <figcaption>{captionText if any}</figcaption>
  </figure>
  ```
- Cropped images are added to the EPUB manifest as image items

## Files to Create/Modify

- `src/views/OcrSubtab.vue` (or `BlockEditorPanel.vue` from step 46) — Add toolbar mode toggle, rubber-band draw on SVG, figure region rendering
- `src/stores/ocr.ts` — Add `figureRegions: Record<pageId, FigureRegion[]>`, `addFigureRegion()`, `updateFigureRegion()`, `removeFigureRegion()`
- `src/composables/useFigureDraw.ts` — Mouse event tracking for rubber-band draw; bbox coordinate mapping (SVG viewBox → image pixels)
- `src/components/FigureRegionPanel.vue` — Edit panel for selected figure (label, alt text, caption link)
- `src-python/kindleocr/epub/figures.py` — `crop_figure_regions(page_path, regions)` → cropped image paths
- `src-python/kindleocr/server.py` — `crop_figures` RPC handler
- `src-tauri/src/lib.rs` — `crop_figures` Tauri command (thin wrapper)
- `src-python/kindleocr/epub/builder.py` — Embed figure images in EPUB HTML and manifest (step 30 update)

## Edge Cases

- Figure region drawn outside image bounds → clamp to image dimensions
- Zero-size region (accidental click without drag) → discard silently
- Figure region overlaps a text block significantly → warn "Region covers existing text blocks; those blocks will be hidden in EPUB"; user confirms
- No label entered → default to "Figure {N}" where N is the count on that page
- Alt text empty → use label as alt text fallback
- Page image deleted/missing before export → skip figure crop, log warning; EPUB section renders placeholder `[figure unavailable]`
- Very large crop region (e.g. entire page) → no size limit; Pillow handles it
- Figure region assigned a caption block → caption block is excluded from main body text stream in EPUB (emitted only inside `<figcaption>`)

## Test Criteria

### Automated (vitest)
1. **Add figure region**: `addFigureRegion(pageId, region)` → `figureRegions[pageId]` has 1 entry with correct bbox
2. **Remove region**: `removeFigureRegion(pageId, id)` → entry removed; block order table no longer contains it
3. **Caption link**: Setting `captionBlockId` on a figure → the referenced text block's `blockType` updates to `"figure_caption"` in `editedBlocks`
4. **Reading order with figure**: Figure region inserted between block 2 and 3 → reading order array is [...block1, ...block2, figureRegion, block3, ...]
5. **Bbox clamping**: Passing a region with `x=-10` to the composable → clamped to `x=0`
6. **Default label**: Saving a region with empty label → label becomes "Figure 1" (first on page)

### Automated (pytest)
7. **Pillow crop**: `crop_figure_regions(image_path, [{bbox: {x:10,y:10,width:100,height:50}}])` → output PNG is 100×50 pixels, valid image file
8. **Crop bounds clamping in Python**: Bbox that extends beyond image dimensions → clamped to image bounds, no exception
9. **Missing image path**: `crop_figure_regions` with non-existent path → raises `FileNotFoundError` with clear message

### Manual
10. **Draw and label**: Draw a rubber-band box over an illustration, enter label → purple dashed rect appears; block table shows the figure row
11. **Reading order drag**: Drag figure row above/below text rows → EPUB preview renders image in correct position
12. **Caption link**: Click "Assign caption", click a text block → that block row shows `[figure_caption]` badge
