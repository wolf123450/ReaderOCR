# Step 25: Confidence Highlighting

**Phase**: 5 — Review & Editing UI  
**Layer**: Vue.js frontend  
**Dependencies**: Step 24 (side-by-side viewer), Step 18 (text blocks with confidence), Step 46 (block editor — SVG overlay already rendered)

## Objective

Highlight low-confidence OCR words/blocks in the text panel so users can quickly spot and correct likely errors. Color-code text by confidence level.

## Inputs

- OcrPageResult with TextBlock[] containing confidence scores per block
- User-configurable confidence thresholds

## Outputs

- Text panel renders with color-coded confidence highlighting
- Clickable low-confidence words zoom to corresponding image region

## Algorithm

### Confidence tiers
1. **High** (≥ 0.95): No highlight (default text color)
2. **Medium** (0.80–0.95): Light yellow background
3. **Low** (0.60–0.80): Orange background
4. **Very Low** (< 0.60): Red background with underline

### Rendering — text panel
1. Parse OcrPageResult into annotated spans: `<span class="conf-low" data-bbox="x,y,w,h">word</span>`
2. On click/hover of a highlighted span, draw a rectangle on the image panel at the corresponding bounding box
3. Allow user to toggle highlighting on/off

### Rendering — SVG overlay (block editor integration)
4. In the block editor (step 46), add a "Colour by confidence" toggle that switches the SVG rect stroke colour from the column-based palette to the confidence-tier palette:
   - High (≥ 0.95): green stroke
   - Medium (0.80–0.95): yellow stroke
   - Low (0.60–0.80): orange stroke
   - Very Low (< 0.60): red stroke
5. A confidence heatmap mode: rect fill opacity proportional to `1 - confidence` (higher opacity = lower confidence = more attention needed)
6. The block order table (step 46) also shows a colour-coded confidence badge per row so the user can sort/filter by confidence without toggling the SVG mode

### Image-text linking
1. When user clicks a highlighted word, scroll image panel to center on that word's bounding box
2. Draw a semi-transparent overlay rectangle on the image at the bbox coordinates
3. Rectangle disappears after 3 seconds or when another word is clicked

## Files to Create/Modify

- `src/components/ConfidenceText.vue` — Renders text with confidence-colored spans
- `src/components/ImagePanel.vue` — Add bbox overlay support
- `src/composables/useConfidenceHighlight.ts` — Logic for tier assignment and bbox mapping
- `src/stores/pages.ts` — Add confidence threshold settings

## Edge Cases

- No confidence data available → render plain text, no highlighting
- Bounding boxes don't match image dimensions → scale bbox proportionally to displayed image size
- All text is low confidence → show warning banner "OCR quality is poor for this page"
- User disables highlighting → render as plain textarea (editable mode)

## Test Criteria

### Automated (vitest)
1. **Tier assignment**: confidence 0.97 → high, 0.85 → medium, 0.70 → low, 0.40 → very-low
2. **Span generation**: TextBlock[] → correct HTML spans with CSS classes
3. **Threshold override**: Custom thresholds apply correctly
4. **No confidence data**: Renders plain text without errors
5. **SVG colour by confidence**: `blockToConfidenceColour(0.70)` → returns orange stroke value; `blockToConfidenceColour(0.97)` → returns green stroke value
6. **Heatmap fill opacity**: Block at confidence 0.40 has higher fill opacity than block at 0.90

### Manual
7. **Visual**: Colors are distinguishable, readable on both light/dark themes
8. **Click-to-zoom**: Clicking low-confidence word highlights bbox on image
9. **SVG toggle**: Switching to "Colour by confidence" mode in the block editor recolours SVG rects correctly
