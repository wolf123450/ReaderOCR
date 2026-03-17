# Step 21: Paragraph Reconstruction

**Phase**: 4 — Text Post-Processing  
**Layer**: Python sidecar  
**Dependencies**: Steps 18–20 (clean extracted text)

## Objective

Merge text across page boundaries to reconstruct paragraphs that span multiple pages. Handle hyphenated words, sentence continuations, and paragraph breaks.

## Inputs

```python
pages: List[OcrPageResult]  # Cleaned pages in order
```

## Outputs

```python
ReconstructParagraphsResult:
    text: str                 # Full reconstructed text with paragraph breaks
    paragraph_breaks: List[int]  # Character offsets of paragraph boundaries
```

## Algorithm

### Page boundary merging
For each pair of consecutive pages (page N, page N+1):

1. **Get boundary text**: last line of page N, first line of page N+1
2. **Hyphen rejoin**: If page N ends with `word-` (hyphen at end of line):
   - Remove the hyphen
   - Concatenate with first word of page N+1
   - Example: `"compre-"` + `"hensive"` → `"comprehensive"`
3. **Sentence continuation**: If page N does NOT end with sentence-ending punctuation (`.`, `!`, `?`, `"`, `'`, `)`) AND page N+1 starts with a lowercase letter:
   - Merge with a space (these are the same paragraph)
4. **Paragraph break**: If page N ends with sentence-ending punctuation AND page N+1 starts with an uppercase letter or indentation:
   - Insert paragraph break (`\n\n`)
5. **Ambiguous cases**: If page N ends with punctuation but page N+1 starts with lowercase → merge (likely same paragraph, new sentence)

### Within-page paragraph detection
1. Detect blank lines within a page's text → paragraph boundaries
2. Detect indentation changes → paragraph boundaries
3. Lines that are significantly shorter than average (< 60% of max line width) likely end a paragraph

### Output construction
1. Process all pages sequentially
2. Apply page boundary rules between each pair
3. Apply within-page paragraph detection
4. Build final text with `\n\n` between paragraphs
5. Track character offsets of each `\n\n` in `paragraph_breaks`

## Files to Create/Modify

- `src-python/kindleocr/processing/paragraphs.py` — paragraph reconstruction
- `src-python/tests/test_paragraphs.py` — reconstruction tests

## Edge Cases

- Hyphenated word that's actually hyphenated (e.g., "well-known") → should NOT rejoin; check if result is a valid word? For simplicity, always rejoin at line boundaries (most hyphens at line breaks are word-splits)
- Page ends mid-sentence with no hyphen → still merge if continuation rules match
- Poetry or formatted text with intentional short lines → may be incorrectly merged; accept this limitation
- Dialogue ending with `"` → punctuation check should match
- Ellipsis (`...`) at end of page → treat as sentence-ending, insert paragraph break
- Page N is empty (e.g., illustration page) → skip, connect page N-1 to page N+1
- Single-page book → return text as-is

## Test Criteria

### Automated (pytest)
1. **Hyphen rejoin**: page1 ends "compre-", page2 starts "hensive world" → "comprehensive world"
2. **Sentence continuation**: page1 ends "the quick brown", page2 starts "fox jumped" → merged with space
3. **Paragraph break**: page1 ends "the end.", page2 starts "The next" → separated by `\n\n`
4. **Punctuation + lowercase**: page1 ends "she said.", page2 starts "but he" → merged (same paragraph, new sentence)
5. **Empty page skip**: page1 has text, page2 is empty, page3 has text → page1 and page3 connected correctly
6. **Within-page paragraphs**: text with blank line → two paragraphs detected
7. **No modification for single page**: single page text → returned as-is
