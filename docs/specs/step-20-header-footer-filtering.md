# Step 20: Header/Footer Filtering

**Phase**: 4 — Text Post-Processing  
**Layer**: Python sidecar  
**Dependencies**: Step 18 (extracted text), Step 17 (layout-classified blocks)

## Objective

Detect and remove repeated headers and footers across pages. If the same (or very similar) text appears at the same vertical position across multiple pages, it's a running header/footer and should be removed.

## Inputs

```python
pages: List[OcrPageResult]  # All pages with classified blocks
```

## Outputs

```python
CleanupResult:
    pages: List[OcrPageResult]  # Pages with repeated headers/footers removed
    removed_headers: List[str]  # Text strings identified as headers
    removed_footers: List[str]  # Text strings identified as footers
```

## Algorithm

### Detection
1. Collect all blocks from the top 10% of each page (candidate headers)
2. Collect all blocks from the bottom 10% of each page (candidate footers)
3. For each candidate text:
   a. Normalize: strip whitespace, lowercase
   b. Count how many pages it appears on
   c. If it appears on ≥ 50% of pages (minimum 3 pages), classify as repeated header/footer
4. Also check for near-matches using fuzzy string matching (Levenshtein ratio > 0.85) to handle OCR variations ("Chapter Five" vs "chapter five" vs "Chapter  Five")

### Removal
1. For each identified repeated text:
   a. Remove matching blocks from all pages
   b. Add to `removed_headers` or `removed_footers` list
2. Rebuild `raw_text` for affected pages

## Files to Create/Modify

- `src-python/kindleocr/processing/cleanup.py` — add header/footer filtering (extends step 19)
- `src-python/tests/test_cleanup.py` — add header/footer tests

## Edge Cases

- Book with different chapter headers on each page → not repeated, should NOT be removed
- Header appears on only 2 of 50 pages → below threshold, kept
- OCR errors cause slight variations ("Chapter" vs "Chaptcr") → fuzzy matching handles this
- Header changes mid-book (Part 1 vs Part 2 headers) → each variant counted separately; may fall below threshold
- Page with no header/footer zone blocks → skip gracefully
- Very short book (< 5 pages) → lower threshold to 2 repetitions

## Test Criteria

### Automated (pytest)
1. **Repeated header detected**: 5 pages, 3 have "The Great Gatsby" at top → detected and removed
2. **Non-repeated preserved**: 5 pages, each with unique text at top → nothing removed
3. **Fuzzy matching**: "Chapter Five" on 3 pages, "chapter five" on 1 page → all 4 count toward the same header
4. **Threshold respected**: Text appears on 2 of 10 pages → NOT removed (below 50%)
5. **Short book handling**: 4 pages, text appears on 3 → removed (≥ 50% and ≥ 3 occurrences)
6. **No content lost**: Body text in the middle of pages → unchanged
7. **Removal reported**: removed_headers list contains the detected header text
