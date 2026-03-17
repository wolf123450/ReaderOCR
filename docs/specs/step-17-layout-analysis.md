# Step 17: Layout Analysis

**Phase**: 3 — OCR Pipeline  
**Layer**: Python sidecar  
**Dependencies**: Step 16 (OCR execution — needs text blocks with bboxes)

## Objective

Classify OCR text blocks as body, header, footer, page number, table, or figure. This allows post-processing to filter out non-body content.

## Inputs

```python
OcrPageResult  # from step 16, with blocks containing bboxes
image_width: int
image_height: int
```

## Outputs

Same `OcrPageResult` with each block's `type` field updated from the default "body" to the appropriate classification.

## Algorithm

### Heuristic-based classification (no additional ML model needed)

1. **Page numbers**: Block at bottom 10% of page, containing only digits or "Page N" pattern, short text (< 10 chars)
2. **Headers**: Block at top 8% of page, short text (< 100 chars), not starting with lowercase
3. **Footers**: Block at bottom 10% of page (but not a page number), short text
4. **Body**: Everything else in the middle 80% of the page, or long text blocks regardless of position
5. **Tables**: Blocks with multiple aligned columns detected (if PaddleOCR structure mode is used) — defer to PP-StructureV3 if available
6. **Figures**: Large bounding boxes with very little text (low text density) — rare in OCR output

### Position zones
```
Top 8%:    headers
8%–90%:    body
90–100%:   footers / page numbers
```

### Refinement rules
- If a "header" block is long (> 100 chars), reclassify as body
- If a "footer" block matches page number regex, classify as page_number
- Blocks spanning > 50% of page width and in body zone → body

## Files to Create/Modify

- `src-python/kindleocr/ocr/layout.py` — layout classification functions
- `src-python/tests/test_layout.py` — layout classification tests

## Edge Cases

- Page with no header/footer → all blocks should remain "body"
- Header/footer text is unusually long (e.g., running header with full chapter title) → length threshold prevents misclassification
- Page number at top of page (some book formats) → check both top and bottom zones
- Two-column layout → blocks may interleave; classification should still work (based on Y-position)
- Image-heavy page with captions → caption text near images may be misclassified

## Test Criteria

### Automated (pytest)
1. **Page number detection**: Block at y=95% of page, text="42" → classified as "page_number"
2. **Header detection**: Block at y=3% of page, text="Chapter 5" → classified as "header"
3. **Body text preserved**: Block at y=50% of page, long text → classified as "body"
4. **No false positives on body-only page**: Page with all blocks in middle zone → no headers/footers detected
5. **Page number regex**: "Page 42", "- 42 -", "42" all match; "There are 42 reasons" does not
6. **Long header reclassification**: Block at top with 150 chars → reclassified as body
