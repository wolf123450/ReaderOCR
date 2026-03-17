# Step 18: Text Extraction

**Phase**: 3 — OCR Pipeline  
**Layer**: Python sidecar  
**Dependencies**: Step 17 (layout analysis — blocks classified by type)

## Objective

Extract body text from classified OCR blocks in correct reading order, filtering out headers, footers, and page numbers. Return clean structured output ready for post-processing.

## Inputs

```python
OcrPageResult  # with blocks classified by layout analysis (step 17)
```

## Outputs

```python
ExtractedText:
    page_index: int
    body_text: str              # Body blocks concatenated in reading order
    body_blocks: List[TextBlock]  # Only body-type blocks, sorted
    filtered_blocks: List[TextBlock]  # Blocks that were filtered out (for review)
```

## Algorithm

### Reading order sort
1. Divide page into vertical zones (columns) using X-position clustering:
   - Group blocks by X center within a tolerance band (e.g., 100px)
   - Each cluster = one column
2. Within each column, sort blocks top-to-bottom by Y coordinate
3. Sort columns left-to-right
4. Flatten: column1 blocks (top→bottom), then column2 blocks, etc.

### Extraction
1. Filter: keep only blocks where `type == "body"`
2. Sort in reading order (above algorithm)
3. Concatenate with newlines between blocks
4. Return both the concatenated text and the individual blocks

## Files to Create/Modify

- `src-python/kindleocr/ocr/extraction.py` — text extraction and reading order
- `src-python/tests/test_extraction.py` — extraction tests

## Edge Cases

- Single column page → simple top-to-bottom sort
- Two-column page → must detect columns and read each fully before moving to next
- Block spanning full width (chapter title) → should be its own "column" or handled as a row separator
- Empty page (all blocks filtered out) → return empty body_text
- Very short blocks (single word) → still include in body if classified as body

## Test Criteria

### Automated (pytest)
1. **Single column order**: 5 body blocks at y=100,200,300,400,500 → output in that order
2. **Two column order**: Blocks at (x=100,y=100), (x=500,y=100), (x=100,y=200), (x=500,y=200) → output order: (100,100), (100,200), (500,100), (500,200)
3. **Filtering**: Mix of body, header, page_number blocks → only body blocks in output; filtered_blocks contains the rest
4. **Empty after filtering**: All blocks are headers → body_text is empty string
5. **Concatenation**: Three body blocks with text "Hello", "World", "Test" → body_text == "Hello\nWorld\nTest"
