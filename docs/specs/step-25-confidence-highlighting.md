# Step 25: Confidence Highlighting

**Phase**: 5 — Review & Editing UI  
**Layer**: Vue.js frontend  
**Dependencies**: Step 24 (side-by-side viewer), Step 18 (text blocks with confidence)

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

### Rendering
1. Parse OcrPageResult into annotated spans: `<span class="conf-low" data-bbox="x,y,w,h">word</span>`
2. On click/hover of a highlighted span, draw a rectangle on the image panel at the corresponding bounding box
3. Allow user to toggle highlighting on/off

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

### Manual
5. **Visual**: Colors are distinguishable, readable on both light/dark themes
6. **Click-to-zoom**: Clicking low-confidence word highlights bbox on image
