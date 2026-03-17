# Step 28: Page Management

**Phase**: 5 — Review & Editing UI  
**Layer**: Vue.js frontend  
**Dependencies**: Step 24 (viewer), Step 27 (batch operations)

## Objective

Allow users to reorder, delete, and insert pages in the project. Support drag-and-drop page reordering, inserting blank pages, and handling cover/front matter separately.

## Inputs

- Ordered list of pages with images and OCR text
- User interactions (drag, delete, insert)

## Outputs

- Updated page ordering persisted in application state
- EPUB generation respects the final page order

## UI Layout

```
┌──────────────────────────────────────┐
│ Page Manager                   [Grid │ List]
├──────────────────────────────────────┤
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐   │
│ │  1  │ │  2  │ │  3  │ │  4  │   │
│ │     │ │     │ │     │ │     │   │
│ │ 📄  │ │ 📄  │ │ 📄  │ │ 📄  │   │
│ └─────┘ └─────┘ └─────┘ └─────┘   │
│ Cover    Ch.1     Ch.1    Ch.1     │
│                                     │
│ [+ Insert Blank] [📷 Add Capture]  │
│ [🗑 Delete Selected]               │
└──────────────────────────────────────┘
```

## Algorithm

### Page operations
1. **Reorder**: Drag-and-drop pages in grid/list view, update internal ordering
2. **Delete**: Remove page (image + text) from project, confirm dialog for multi-delete
3. **Insert blank**: Add a blank page (title page, separator) with user-provided text
4. **Mark as cover**: Designate one page as the book cover (used for EPUB cover image)

### Page types
1. **Cover**: Single page, used as EPUB cover image
2. **Front matter**: Pages before first chapter (title page, copyright, etc.)
3. **Content**: Regular content pages belonging to chapters
4. **Blank/separator**: User-inserted pages with custom text

### Thumbnail generation
1. Generate small thumbnails (200px wide) from page images for the grid view
2. Cache thumbnails to avoid regeneration
3. Show page number, chapter assignment, and review status on each thumbnail

## Files to Create/Modify

- `src/components/PageManager.vue` — Main page management grid/list view
- `src/components/PageThumbnail.vue` — Individual page thumbnail card
- `src/components/InsertPageDialog.vue` — Dialog for inserting blank/text pages
- `src/stores/pages.ts` — Add reorder, delete, insert methods
- `src/stores/chapters.ts` — Update chapter boundaries when pages change

## Edge Cases

- Delete page that starts a chapter → chapter moves to next page or is removed
- Reorder across chapter boundaries → chapter assignments update automatically
- Delete all pages → show empty state with re-capture prompt
- Insert blank page between chapters → properly handles chapter boundary shift
- Very many pages (500+) → virtualize grid to maintain performance

## Test Criteria

### Automated (vitest)
1. **Reorder**: Moving page 3 to position 1 → order is [3, 1, 2, 4, ...]
2. **Delete**: Removing page updates total count and shifts subsequent pages
3. **Delete chapter start**: Deleting first page of chapter → chapter moves to next page
4. **Insert blank**: Inserting at position 5 → shifts pages 5+ by one
5. **Cover designation**: Only one page can be cover at a time
6. **Chapter boundary update**: Reordering pages updates chapter start pages correctly

### Manual
7. **Drag-drop**: Visually reorder pages and verify new numbering
8. **Grid/list toggle**: Both views show same data in different layouts
