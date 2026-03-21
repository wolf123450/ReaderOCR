# Step 42: Per-Page Metadata Model

**Phase**: 8 — UI Workflow Redesign  
**Layer**: Vue.js store + Rust session persistence  
**Dependencies**: Step 41 (page management UI), Step 40 (session reconciliation)

## Objective

Extend the `CapturedPage` model with a richer `pageType` enum and a capture status field. Persist this metadata in the session JSON and expose it in the filmstrip and detail pane.

## Page Type Enum

```typescript
export type PageType =
  | 'text'           // regular book content page (default)
  | 'cover'          // book cover image
  | 'illustration'   // full-page image/diagram (no OCR, or OCR optional)
  | 'toc'            // table of contents page
  | 'license'        // copyright/license page (common book artifact)
  | 'blank'          // intentionally blank or near-blank
  | 'chapter_start'  // decorative chapter opener (image-heavy, with chapter title)
  | 'excluded'       // user wants this page skipped in EPUB output
```

**Default**: `'text'` when a page is first captured.

## Capture Status Enum

```typescript
export type CaptureStatus =
  | 'ok'               // normally captured, file exists
  | 'needs_recapture'  // user or auto-detection flagged for redo
  | 'missing'          // session references this page but file not found on disk
  | 'placeholder'      // user inserted a logical slot not yet captured
```

## Updated `CapturedPage` Interface

```typescript
export interface CapturedPage {
  // existing fields
  pageNumber: number
  imagePath: string
  timestamp: number

  // refined status (replaces old status: "ok" | "error")
  captureStatus: CaptureStatus
  errorMessage?: string

  // new metadata
  pageType: PageType
  userNotes?: string        // free-text annotation
  ocrStatus: OcrStatus      // see step 44
}

export type OcrStatus = 'pending' | 'running' | 'done' | 'error' | 'skipped'
```

## Session JSON Schema (Rust side)

In `src-tauri/src/session/session.rs`, extend the `SessionPage` struct:

```rust
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct SessionPage {
    pub page_number: u32,
    pub image_path: String,
    pub timestamp: i64,
    pub capture_status: String,    // "ok" | "needs_recapture" | "missing" | "placeholder"
    pub page_type: String,         // matches PageType enum values
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_notes: Option<String>,
    pub ocr_status: String,        // "pending" | "running" | "done" | "error" | "skipped"
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_message: Option<String>,
}
```

Use string serialisation (not numeric enums) for maximal forward compatibility.

## Default Values on Migration

When loading an old session JSON that lacks new fields:
- `capture_status` missing → default `"ok"`
- `page_type` missing → default `"text"`
- `ocr_status` missing → default `"pending"`

Implement via `#[serde(default = "default_...")]` attributes on the Rust struct.

## UI: Type Selector

In `PageDetailPane.vue` (step 41), render a `<select>` or segmented button:

```
Type: [text ▼]
      ─────────
      text
      cover
      illustration
      TOC
      license
      blank
      chapter start
      excluded
```

Selecting a type immediately dispatches `setPageType(index, type)` in the store and queues a session auto-save.

## UI: Filmstrip Badge

Each filmstrip card shows a small coloured badge:
- `text` → no badge (default, no visual noise)
- `cover` → 📕 gold
- `illustration` → 🖼 purple
- `toc` → 📋 blue
- `license` → ⚖ grey
- `blank` → ◻ light grey
- `chapter_start` → 📖 teal
- `excluded` → 🚫 red, dimmed thumbnail

## Auto-Detection Hints (informational, not enforced)

The following detections feed *suggestions* (shown as a badge saying "Detected: blank?") but do not auto-set the type without user confirmation:
- Near-blank page (>95% white pixels after preprocessing) → suggested `blank`
- Very short OCR output (<10 words) → suggested `blank` or `illustration`
- First captured page → suggested `cover` (just a hint)

Auto-detection is implemented in the Python preprocessing pipeline (step 15 extension) and surfaced as a `detectedType?: PageType` field on `OcrPageResult`.

## Files to Create/Modify

- `src/stores/capture.ts` — extend `CapturedPage`, add `setPageType`, `setCaptureStatus` actions; migrate old `status` field
- `src-tauri/src/session/session.rs` — extend `SessionPage` struct with new fields and serde defaults
- `src/components/PageDetailPane.vue` — add type selector (step 41 dependency)
- `src/components/FilmstripSidebar.vue` — add type badge rendering (step 41 dependency)

## Test Criteria

### Vitest — store

1. New page defaults to `pageType: 'text'`, `captureStatus: 'ok'`, `ocrStatus: 'pending'`
2. `setPageType(0, 'cover')` → page 0 has `pageType: 'cover'`; other pages unchanged
3. Session serialise/deserialise round-trip preserves all new fields
4. Loading old JSON without new fields → missing fields receive correct defaults

### Rust — serde tests

5. `SessionPage` with only legacy fields deserialises without panic
6. `capture_status` defaults to `"ok"` when absent
7. `page_type` defaults to `"text"` when absent
8. Round-trip: serialise → deserialise → identical struct
