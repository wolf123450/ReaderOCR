# Step 33: Export & Output

**Phase**: 6 — EPUB Generation  
**Layer**: Tauri + Vue.js frontend  
**Dependencies**: Steps 30–32 (EPUB build, styling, validation)

## Objective

Provide a UI for the user to trigger EPUB generation, see validation results, choose output location, and export the final EPUB file. Show a summary of the book before export.

## Inputs

- Metadata, chapters, pages, cover image (from stores)
- Validation results (from step 32)

## Outputs

- EPUB file saved to user-chosen location
- Export summary displayed

## UI Layout

```
┌──────────────────────────────────────────────┐
│ Export EPUB                                    │
├──────────────────────────────────────────────┤
│ Book Summary:                                  │
│   Title:    "My Book Title"                    │
│   Author:   "Author Name"                      │
│   Chapters: 12                                 │
│   Pages:    342                                │
│   Cover:    ✓ Set                              │
│                                                │
│ Validation:                                    │
│   ✓ Structure valid                            │
│   ✓ Metadata complete                          │
│   ⚠ 2 warnings (click to view)                │
│                                                │
│ Output: [D:\Books\my-book.epub] [Browse...]    │
│                                                │
│         [Build & Export EPUB]                   │
│                                                │
│ ████████████████████ 100% — Complete!          │
│ File size: 1.2 MB                              │
│ [📂 Open Folder] [📖 Open in Reader]           │
└──────────────────────────────────────────────┘
```

## Algorithm

### Pre-export checks
1. Validate all required data is present (metadata, at least 1 chapter, at least 1 page)
2. Show book summary for user review
3. Run validation and display results

### Export flow
1. User selects output path via Tauri file dialog (`dialog.save()`)
2. Default filename: `{title} - {author}.epub` (sanitized)
3. Send EpubBuildParams to Python sidecar via JSON-RPC
4. Show progress bar during EPUB build
5. On success: show file size, offer to open folder or open in default reader
6. On failure: show error details from sidecar response

### Post-export actions
1. **Open folder**: Use Tauri `shell.open()` to open containing directory
2. **Open in reader**: Use Tauri `shell.open()` to open EPUB with default application
3. **Export again**: Allow re-export with different settings or output path

## Files to Create/Modify

- `src/components/ExportPanel.vue` — Export UI with summary and progress
- `src/components/ValidationResults.vue` — Validation error/warning display
- `src/composables/useExport.ts` — Export logic, file dialog, sidecar communication
- `src-tauri/src/commands.rs` — Tauri command for file dialog and shell.open

## Edge Cases

- Output path is read-only or full → show clear error from OS
- Sidecar crashes during build → show error, offer retry
- User cancels file dialog → no-op, return to export panel
- EPUB validation has errors → warn but allow export anyway (user's choice)
- Filename sanitization → replace illegal chars (`<>:"/\|?*`) with underscore
- Very fast build → still show progress briefly so user sees feedback

## Test Criteria

### Automated (vitest)
1. **Summary display**: Correct chapter/page counts from store
2. **Filename sanitization**: `Book: "Title"` → `Book_ _Title_.epub`
3. **Pre-export validation**: Missing title → export button disabled
4. **Export state machine**: idle → building → complete/error transitions
5. **Validation display**: Errors shown in red, warnings in yellow

### Manual
6. **End-to-end export**: Full workflow produces valid EPUB file
7. **File dialog**: Browse dialog opens and returns selected path
8. **Open in reader**: EPUB opens in system default reader
