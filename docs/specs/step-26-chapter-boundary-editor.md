# Step 26: Chapter Boundary Editor

**Phase**: 5 — Review & Editing UI  
**Layer**: Vue.js frontend  
**Dependencies**: Step 22 (auto-detected chapters), Step 24 (viewer)

## Objective

Provide a UI for the user to review, add, remove, and rename auto-detected chapter boundaries. The chapter list determines how the EPUB will be split.

## Inputs

- ChapterBoundary[] from auto-detection (step 22)
- Full page list with text

## Outputs

- User-confirmed ChapterBoundary[] stored in application state
- Visual chapter markers in the page navigation

## UI Layout

```
┌─────────────────────────────────────┐
│ Chapter Structure                    │
├─────────────────────────────────────┤
│ ☐ Chapter 1: "Introduction" (p.1)   │  [✎] [✕]
│ ☐ Chapter 2: "The Beginning" (p.15) │  [✎] [✕]
│ ☐ Chapter 3: "Rising Action" (p.42) │  [✎] [✕]
│                                      │
│ [+ Add Chapter at Current Page]      │
│ [Auto-Detect Again]                  │
├─────────────────────────────────────┤
│ Drag to reorder │ Click page to jump │
└─────────────────────────────────────┘
```

## Algorithm

### Chapter management
1. Display sortable list of chapters with title and start page
2. **Add**: Insert chapter boundary at current page position, prompt for title
3. **Remove**: Remove chapter boundary (merge into previous chapter)
4. **Rename**: Inline edit chapter title
5. **Reorder**: Drag-and-drop reordering (updates page assignments)

### Page-chapter mapping
1. Each page belongs to the chapter whose start page is ≤ page number
2. Pages before first chapter → "Front Matter" (auto-created, can be renamed)
3. Display chapter indicator in page navigation bar

### Validation
1. No two chapters can start on the same page
2. Chapter titles cannot be empty (use "Untitled Chapter" as fallback)
3. At least one chapter must exist

## Files to Create/Modify

- `src/components/ChapterEditor.vue` — Chapter list with CRUD operations
- `src/components/ChapterItem.vue` — Individual chapter row (editable title, page number)
- `src/stores/chapters.ts` — Pinia store for chapter state
- `src/stores/pages.ts` — Add chapter indicator to page store

## Edge Cases

- No auto-detected chapters → show empty list with prompt to add manually
- Single-chapter book → valid, entire book is one chapter
- User adds chapter at same page as existing → show validation error
- Very long chapter titles → truncate in list view, show full on hover

## Test Criteria

### Automated (vitest)
1. **Add chapter**: Adding chapter at page 15 → chapters sorted by page, new entry present
2. **Remove chapter**: Removing middle chapter → pages reassigned to previous chapter
3. **Rename chapter**: Title update persists in store
4. **Duplicate page validation**: Adding chapter at existing chapter's page → rejected
5. **Empty title fallback**: Empty title → "Untitled Chapter"
6. **Sort invariant**: Chapters always sorted by start page regardless of insert order

### Manual
7. **Drag reorder**: Reordering updates page assignments visually
8. **Click to navigate**: Clicking chapter jumps to that page in viewer
