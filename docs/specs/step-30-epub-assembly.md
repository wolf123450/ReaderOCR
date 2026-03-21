# Step 30: EPUB Assembly

**Phase**: 6 — EPUB Generation  
**Layer**: Python sidecar  
**Dependencies**: Step 29 (metadata), Steps 21–22 (paragraphs, chapters)

## Objective

Assemble the final EPUB file from structured text, chapter boundaries, metadata, and cover image using the `ebooklib` library. Produce a valid EPUB 3.0 file.

## Inputs

```python
EpubBuildParams:
    metadata: EpubMetadata           # title, author, language, etc.
    chapters: ChapterBoundary[]      # chapter titles + start pages
    pages: PageText[]                # ordered page text content (blocks in edited reading order)
    figure_regions: dict[int, list[FigureRegion]]  # page_index → figure regions (step 47)
    cover_image_path: str | None
    output_path: str
    session_output_dir: str          # where to write cropped figure images
```

## Outputs

```python
EpubBuildResult:
    output_path: str
    file_size_bytes: int
    chapter_count: int
    page_count: int
```

## Algorithm

### EPUB structure
1. Create `epub.EpubBook()` instance
2. Set metadata: title, author, language, identifier (UUID if no ISBN), publisher, description, date
3. Add cover image if provided (`book.set_cover()`)

### Chapter generation
1. For each chapter boundary:
   a. Collect all pages from chapter start to next chapter start (or end)
   b. Concatenate page text into chapter HTML content
   c. Wrap paragraphs in `<p>` tags
   d. Create `epub.EpubHtml(title=chapter.title, content=html)`
   e. Add chapter to book
2. For front matter pages (before first chapter): create dedicated "Front Matter" section

### Block type handling
Blocks come from `editedBlocks` (step 46) and carry a `blockType` field. Each type maps to an HTML output:

| blockType | HTML output |
|---|---|
| `body` | `<p>text</p>` |
| `chapter_title` | `<h1>text</h1>` (also registered as a chapter boundary if not already in the chapter list) |
| `section_heading` | `<h2>text</h2>` |
| `sidebar` | `<aside><p>text</p></aside>` |
| `figure_caption` | Emitted only inside a `<figcaption>` tag; not emitted as standalone `<p>` |
| `header` | Omitted |
| `footer` | Omitted |
| `page_number` | Omitted |
| `excluded` | Omitted |

Figure regions (step 47) are interleaved in block reading order and emit:
```html
<figure>
  <img src="../images/{figId}.png" alt="{altText}" />
  <figcaption>{captionText if captionBlockId present}</figcaption>
</figure>
```

### HTML formatting
1. Body blocks → `<p>text</p>`
2. Chapter title blocks → `<h1>text</h1>` at start of each chapter
3. Page breaks between original pages → `<div class="page-break"></div>` (optional, configurable)
4. Preserve line breaks within paragraphs only if they appear intentional

### Figure image handling
1. Before assembling HTML, crop all `FigureRegion` bboxes from their respective page images using Pillow (see step 47)
2. Write cropped PNGs to `{session_output_dir}/figures/`
3. Add each cropped image to the EPUB manifest as an image item
4. Reference via relative `../images/` path in chapter HTML

### Table of contents
1. Auto-generate TOC from chapter list
2. Add NCX (EPUB 2 compat) and Navigation Document (EPUB 3)
3. Set spine order matching chapter order

### File output
1. Write EPUB to specified output_path
2. Return file size and counts for confirmation

## Files to Create/Modify

- `src-python/kindleocr/epub/builder.py` — EPUB assembly using ebooklib
- `src-python/kindleocr/epub/html_formatter.py` — Text-to-HTML conversion
- `src-python/tests/test_epub_builder.py` — Integration tests with actual EPUB output

## Edge Cases

- No chapters defined → single chapter with all content titled by book title
- Empty chapter (no pages) → skip, don't create empty EPUB section
- Cover image format → accept JPEG and PNG, convert others if needed
- Very large book (1000+ pages) → no memory issue with ebooklib (streaming write)
- Unicode content → ensure UTF-8 encoding throughout
- Output path not writable → raise clear error before attempting write
- Existing file at output path → overwrite with confirmation (handled by frontend)
- Page has no `editedBlocks` → fall back to raw `OcrPageResult.blocks` with all `blockType` defaulting to `"body"`
- Figure region's page image missing at export time → skip figure, emit `<!-- figure unavailable: {label} -->` HTML comment, log warning
- `chapter_title` block detected mid-chapter (not at chapter boundary) → treat as section heading (`<h2>`) rather than starting a new EPUB chapter, unless it also matches the chapter boundary list

## Test Criteria

### Automated (pytest)
1. **Minimal EPUB**: Single chapter, no cover → valid EPUB file produced, openable by ebooklib reader
2. **Multi-chapter**: 3 chapters → EPUB has 3 content documents in spine
3. **Metadata round-trip**: Set title/author → read back from EPUB, verify match
4. **Cover image**: Provide cover.jpg → EPUB contains cover image in manifest
5. **HTML formatting**: Paragraphs wrapped in `<p>`, chapter title in `<h1>`
6. **TOC generation**: Chapter titles appear in NCX and nav document
7. **Empty chapter skip**: Chapter with no pages → not included in output
8. **File size**: Output EPUB file size > 0 bytes
9. **Excluded blocks omitted**: Block with `blockType: "excluded"` → text not present anywhere in EPUB HTML
10. **Header/footer omitted**: Blocks with `blockType: "header"` or `"footer"` → not in EPUB body
11. **section_heading**: Block with `blockType: "section_heading"` → wrapped in `<h2>`, not `<p>`
12. **Figure embed**: Page with one `FigureRegion` → EPUB contains `<figure><img .../>` in chapter HTML; image file present in EPUB manifest
13. **Figure caption link**: Figure with `captionBlockId` pointing to a `figure_caption` block → `<figcaption>` text matches that block's text; caption block not emitted as standalone `<p>`
14. **Missing editedBlocks fallback**: Page without `editedBlocks` entry → all blocks treated as `blockType: "body"`
