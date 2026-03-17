# Step 22: Chapter Detection

**Phase**: 4 — Text Post-Processing  
**Layer**: Python sidecar  
**Dependencies**: Steps 16–18 (OCR results with bboxes and text)

## Objective

Automatically detect chapter boundaries from the OCR output. Uses heuristics based on text patterns, typography (bounding box size), and page structure.

## Inputs

```python
pages: List[OcrPageResult]  # OCR pages with blocks and bboxes
```

## Outputs

```python
DetectChaptersResult:
    chapters: List[ChapterBoundary]

ChapterBoundary:
    page_index: int       # Page where chapter starts
    title: str            # Detected chapter title
    confidence: float     # 0.0–1.0, how confident the detection is
```

## Algorithm

### Pattern matching (highest priority)
Check each block's text against chapter title patterns:
```python
CHAPTER_PATTERNS = [
    r'^Chapter\s+\d+',              # "Chapter 1", "Chapter 12"
    r'^Chapter\s+[IVXLC]+',         # "Chapter IV", "Chapter XII"
    r'^CHAPTER\s+\d+',              # "CHAPTER 1"
    r'^CHAPTER\s+[IVXLC]+',         # "CHAPTER IV"
    r'^Part\s+\d+',                 # "Part 1"
    r'^Part\s+[IVXLC]+',           # "Part II"
    r'^PART\s+\d+',                 # "PART 1"
    r'^Prologue\s*$',              # "Prologue"
    r'^Epilogue\s*$',              # "Epilogue"
    r'^Introduction\s*$',          # "Introduction"
    r'^Preface\s*$',               # "Preface"
    r'^Foreword\s*$',              # "Foreword"
    r'^Afterword\s*$',             # "Afterword"
    r'^Appendix(\s+[A-Z])?\s*$',   # "Appendix", "Appendix A"
]
```

### Typography heuristics
1. **Large text**: Block's bounding box height is significantly larger (> 1.5×) than the average body text block height → likely a heading
2. **Centered**: Block is horizontally centered on the page (x center within 15% of page center)
3. **Isolated**: Block is preceded or followed by significant vertical whitespace (> 3× average line spacing)
4. **Short**: Block text is short (< 50 characters) — titles are concise

### Scoring
For each candidate block, assign a score:
- Pattern match: +0.5
- Large text: +0.2
- Centered: +0.15
- Isolated (whitespace): +0.1
- Short text: +0.05
- Total score = confidence (capped at 1.0)

Blocks with confidence ≥ 0.4 are reported as chapter boundaries.

### Deduplication
- If multiple candidates exist on the same page, keep the one with highest confidence
- Merge "Chapter 5" and "The Journey Begins" if they're on the same page (combine into title)

## Files to Create/Modify

- `src-python/kindleocr/processing/chapters.py` — chapter detection
- `src-python/tests/test_chapters.py` — chapter detection tests

## Edge Cases

- "Chapter" appears in body text ("In this chapter, we discuss...") → NOT at start of block, lower confidence, no typography match → filtered out
- Numbered chapters without "Chapter" prefix ("1. The Beginning") → add simple numeric heading pattern with typography requirement
- Books without chapter markings → return empty, let user manually define
- Sub-headings within chapters → may be detected as chapters; user can remove in editor (step 26)
- Title page → "The Great Gatsby" at top may trigger; acceptable, user can remove
- Very short book with no chapters → return single chapter covering entire book

## Test Criteria

### Automated (pytest)
1. **Pattern match**: Block with "Chapter 5" → detected, confidence ≥ 0.5
2. **Pattern + typography**: Block with "CHAPTER 5", large bbox, centered → confidence ≥ 0.8
3. **Body text not matched**: Block with "In this chapter, we discuss the..." → NOT detected as chapter
4. **Roman numerals**: "Chapter XII" → detected
5. **Standard names**: "Prologue", "Epilogue", "Appendix A" → all detected
6. **Multiple on same page**: "Chapter 5" and "The Journey" → merged into single chapter with title "Chapter 5 — The Journey"
7. **No chapters found**: Pages with only body text → empty chapters list
8. **Confidence ordering**: Results sorted by page_index
