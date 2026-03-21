# Step 43: Chapter Structure Model & Editor

**Phase**: 8 — UI Workflow Redesign  
**Layer**: Vue.js store + Python EPUB pipeline  
**Dependencies**: Step 42 (page metadata), Step 22 (chapter auto-detection), Step 26 (chapter boundary editor — supersedes)

## Objective

Replace the simple "chapter starts at page N" model with a flexible `ChapterSegment` that can express any mapping between source pages and EPUB chapters, including:

- Many source pages → one chapter
- One source page → one chapter
- One source page → multiple chapters (page is split between two or more chapters)
- Entire capture (possibly one giant image) → multiple chapters
- Arbitrary re-ordering within final EPUB (independent of capture order)

This step supersedes the original step 26 (Chapter Boundary Editor) for the data model. The editor UI described here replaces the old spec.

## Data Model

```typescript
// A fraction of a source page, 0.0–1.0 from top.
// start < end. (0.0, 1.0) = whole page.
export interface PageFraction {
  pageIndex: number    // 0-based index into CapturedPage[]
  start: number        // 0.0 = top of page
  end: number          // 1.0 = bottom of page
}

export interface ChapterSegment {
  id: string                   // uuid
  title: string
  chapterIndex: number         // 0-based output ordering in EPUB
  sources: PageFraction[]      // ordered list of page regions that form this chapter
  chapterType: ChapterType
}

export type ChapterType =
  | 'front_matter'    // before first chapter (title page, TOC, etc.)
  | 'chapter'         // regular chapter
  | 'back_matter'     // after last chapter (index, bibliography, etc.)
  | 'part'            // a "Part I" divider (no content, just a heading)
  | 'appendix'
```

### Constraints

1. Every `PageFraction` must cover a contiguous, non-overlapping region (no two segments can claim the same pixels of the same page).
2. Fractions for the same `pageIndex` must together sum to ≤ 1.0 (a page may be partially excluded).
3. A `PageFraction` with `(0.0, 1.0)` covers the whole page.
4. `chapterIndex` values must be unique and gapless (0, 1, 2, …) — reorder by dragging.

### Special Cases

**Entire-book capture (single image)**  
If the user has one `CapturedPage` that contains the whole book (a very long scroll capture, or a PDF-rendered single file), they can create multiple `ChapterSegment`s all pointing to `pageIndex: 0` with different `start/end` fractions. The fractions act as scroll-position markers, and the EPUB builder will crop the image to extract each chapter's portion.

**Single-page chapter**  
`sources: [{ pageIndex: 5, start: 0.0, end: 1.0 }]`

**Multi-page chapter**  
`sources: [{ pageIndex: 5, start: 0.0, end: 1.0 }, { pageIndex: 6, start: 0.0, end: 1.0 }, ...]`

**Page split between two chapters**  
Chapter A: `sources: [..., { pageIndex: 10, start: 0.0, end: 0.45 }]`  
Chapter B: `sources: [{ pageIndex: 10, start: 0.45, end: 1.0 }, ...]`

## UI Layout

The chapter editor lives in the Export tab (and optionally as a panel in the Pages subtab for quick annotation).

```
┌──────────────────────────────────────────────────────────────────────┐
│  Chapter Structure                          [+ Add Chapter] [Auto ↺] │
├──────────────────────────────────────────────────────────────────────┤
│  ≡ Front Matter         p.1–2       [edit] [delete]                  │
│  ≡ Chapter 1: "Intro"   p.3–14      [edit] [delete]                  │
│  ≡ Chapter 2: "Part I"  p.15–41     [edit] [delete] ← drag to reorder│
│  ≡ Chapter 3: "Part II" p.42–60     [edit] [delete]                  │
│  ≡ Back Matter          p.61–62     [edit] [delete]                  │
│                                                                      │
│  ─── Page Split View (when editing a chapter boundary) ───────────   │
│  Drag the split line on the thumbnail to adjust where ch.2 ends      │
│  and ch.3 begins on page 41.                                         │
│                                                                      │
│  [Page 41 thumbnail — draggable horizontal split line at 45%]        │
└──────────────────────────────────────────────────────────────────────┘
```

### Interactions

- **Drag chapter row** → reorder chapters in EPUB output (does not affect source page order)
- **Click title** → inline rename
- **[edit] Edit** → expand detail pane for this chapter; shows its page list; drag pages in/out
- **[+ Add Chapter]** → creates a new chapter from the currently selected page range in the filmstrip, or at the end
- **[Auto ↺]** → re-run chapter auto-detection (step 22); merge with existing manual boundaries (user confirms each suggestion)
- **Page split handle** → drag to adjust `start`/`end` fraction for pages shared between chapters; preview shows split point overlay on thumbnail

### Page Coverage Indicator

Below the filmstrip (step 41), each page thumbnail shows a colour-coded strip indicating which chapter(s) it belongs to:

```
[=====1=====][==2==][========3========][4]
```

Clicking a chapter's colour segment in the strip navigates to that chapter in the editor.

## Python Side: EPUB Builder Input

The EPUB builder (step 30) receives a list of `ChapterSegment`s. For segments with `PageFraction` containing non-whole-page fractions, the builder:
1. Opens the source image
2. Crops vertically to `(height * start, height * end)`
3. Uses the cropped image as the "page" for OCR re-processing or as a figure if the page type is `illustration`

## Files to Create/Modify

- `src/stores/chapters.ts` — NEW: `ChapterSegment[]`, CRUD actions, validation, serialisation
- `src/components/ChapterEditor.vue` — REPLACE step-26 spec; new drag-to-reorder list
- `src/components/ChapterItem.vue` — chapter row with expand/collapse
- `src/components/PageSplitHandle.vue` — NEW: draggable fraction editor on a thumbnail
- `src/components/PageCoverageBar.vue` — NEW: colour strip showing chapter assignments per page
- `src-tauri/src/session/session.rs` — add `chapters: Vec<SessionChapter>` to session struct
- `src-python/kindleocr/epub/chapter_mapper.py` — NEW: given chapters + pages → ordered content list for EPUB builder

## Test Criteria

### Vitest — `src/__tests__/chapters.store.spec.ts`

1. Empty store → `chapters` = `[]`; `isValid()` = true (no chapters is valid before export)
2. Add chapter → `chapters.length` = 1; `chapterIndex` = 0
3. `addChapter` auto-assigns gapless indices
4. Reorder chapters → `chapterIndex` values renumbered; `sources` unchanged
5. **Overlap validation**: two segments claiming `pageIndex: 5, start: 0.0, end: 0.7` and `start: 0.5, end: 1.0` → `isValid()` = false, error message contains "overlap"
6. **Fraction sum**: three segments on page 5 with fractions 0.3, 0.4, 0.3 → sum = 1.0, valid
7. **Fraction sum over 1.0**: 0.6 + 0.6 → `isValid()` = false
8. Serialise complex mapping → deserialise → identical `ChapterSegment[]`

### Python — `src-python/tests/test_chapter_mapper.py`

9. Single whole-page chapter → one content entry, no cropping
10. Page split 50/50 → two content entries, each references cropped image region
11. Multi-page chapter → entries in source order
12. Re-ordered chapters (ch index 2, 0, 1) → output list follows `chapterIndex` order
