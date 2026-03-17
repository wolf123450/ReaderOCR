# Step 19: Page Number Removal

**Phase**: 4 — Text Post-Processing  
**Layer**: Python sidecar  
**Dependencies**: Step 18 (extracted text with blocks)

## Objective

Remove page numbers that may have survived layout filtering. Uses regex patterns to identify and strip standalone page numbers from the text while preserving legitimate in-text numbers.

## Inputs

```python
pages: List[OcrPageResult]  # Extracted text pages
```

## Outputs

Same pages with page number text removed from blocks and raw_text.

## Algorithm

### Page number patterns (regex)
```python
PATTERNS = [
    r'^\s*\d{1,4}\s*$',           # Standalone number: "42"
    r'^\s*-\s*\d{1,4}\s*-\s*$',   # Dashed: "- 42 -"
    r'^\s*Page\s+\d{1,4}\s*$',    # "Page 42"
    r'^\s*p\.\s*\d{1,4}\s*$',     # "p. 42"
    r'^\s*\[\d{1,4}\]\s*$',       # "[42]"
]
```

### Removal strategy
1. For each page, check each text block:
   - If block type is "page_number" (from layout analysis) → remove
   - If block text matches any page number pattern AND block is at the top/bottom 15% of the page → remove
2. **Critical safety rule**: Only remove if the block is short (< 15 characters) AND at page edges. Never remove a standalone number from the middle of a paragraph.
3. Rebuild `raw_text` from remaining blocks

### Sequential validation
- If the removed numbers form a roughly sequential series (e.g., 1, 2, 3, ... or 42, 43, 44, ...), confidence is high
- If removed numbers are scattered/non-sequential, flag for manual review

## Files to Create/Modify

- `src-python/kindleocr/processing/cleanup.py` — page number removal
- `src-python/tests/test_cleanup.py` — parameterized tests

## Edge Cases

- Text body contains legitimate standalone numbers ("There were 3 apples") → NOT removed (not at page edge, part of longer text)
- Roman numeral page numbers ("xii", "XIV") → add patterns for common Roman numeral forms
- Page numbers at top of page (some books) → check both top and bottom zones
- No page numbers present → return pages unchanged
- Page number is part of a header ("Chapter 3 - Page 42") → header already filtered; if not, regex only matches standalone patterns

## Test Criteria

### Automated (pytest — parameterized)
1. **Standalone digit removed**: Block at bottom with text "42" → removed
2. **Dashed format removed**: "- 42 -" → removed
3. **"Page N" format removed**: "Page 42" → removed
4. **In-text number preserved**: Block in middle with "There were 3 apples" → NOT removed
5. **Long text preserved**: Block at bottom with "This is a long sentence ending with 42" → NOT removed
6. **Empty page after removal**: Page with only a page number → body_text is empty
7. **Sequential validation**: Remove "1", "2", "3" from 3 pages → sequential, high confidence
8. **Non-matching text preserved**: "Hello World" at bottom → NOT removed
