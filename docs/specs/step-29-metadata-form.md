# Step 29: Metadata Form

**Phase**: 6 — EPUB Generation  
**Layer**: Vue.js frontend  
**Dependencies**: Step 22 (auto-detected chapters for suggested title)

## Objective

Provide a form for the user to enter EPUB metadata: title, author, language, publisher, description, ISBN, cover image, and other EPUB-required fields.

## Inputs

- Auto-detected metadata suggestions (title from first page, chapter count)
- Cover image from page manager (step 28)

## Outputs

- EpubMetadata object stored in application state
- Validated metadata ready for EPUB assembly

## UI Layout

```
┌──────────────────────────────────────────┐
│ EPUB Metadata                            │
├──────────────────────────────────────────┤
│ Title*:     [________________________]   │
│ Author*:    [________________________]   │
│ Language:   [English (en)        ▼  ]    │
│ Publisher:  [________________________]   │
│ Description:                             │
│ [                                    ]   │
│ [                                    ]   │
│ ISBN:       [________________________]   │
│ Cover:      [cover.jpg ✓] [Change...]    │
│ Published:  [YYYY-MM-DD]                 │
│                                          │
│           [Save Metadata]                │
└──────────────────────────────────────────┘
```

## Algorithm

### Form fields
1. **Title** (required): Text input, suggested from first page OCR or filename
2. **Author** (required): Text input, no default
3. **Language**: Dropdown with common languages, default "en"
4. **Publisher**: Optional text input
5. **Description**: Optional textarea
6. **ISBN**: Optional, validated with ISBN-10/ISBN-13 checksum
7. **Cover image**: File selector or auto-populated from page marked as cover
8. **Publication date**: Optional date picker

### Validation
1. Title and author are required — form cannot be submitted without them
2. ISBN validation: check digit algorithm for ISBN-10 and ISBN-13
3. Language must be a valid BCP 47 language tag
4. Date must be valid ISO 8601 format if provided

### Auto-suggestions
1. Title: Extract from first content page if it contains large/centered text
2. Cover: Use page marked as cover in page manager, or first page

## Files to Create/Modify

- `src/components/MetadataForm.vue` — EPUB metadata form
- `src/composables/useIsbnValidation.ts` — ISBN checksum validation
- `src/stores/metadata.ts` — Pinia store for metadata state
- `src-python/kindleocr/protocol.py` — Ensure EpubMetadata fields match

## Edge Cases

- User skips metadata → require at minimum title + author before EPUB build
- Invalid ISBN → show inline validation error, don't block save (ISBN is optional)
- Very long title/description → no hard limit, but warn if title > 200 chars
- Cover image missing → EPUB still valid, just won't have cover; show warning
- Non-ASCII characters in metadata → fully supported (EPUB is UTF-8)

## Test Criteria

### Automated (vitest)
1. **Required fields**: Form submit blocked when title or author is empty
2. **ISBN-10 validation**: Valid ISBN-10 ("0306406152") passes; invalid checksum fails
3. **ISBN-13 validation**: Valid ISBN-13 ("9780306406157") passes; invalid fails
4. **Language codes**: "en", "fr", "de" accepted; "xx" rejected
5. **Store update**: Form input updates metadata store reactively
6. **Auto-suggestion**: When cover page is set, metadata.coverImage auto-populates
