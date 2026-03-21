# Step 39: App Shell Tab Layout

**Phase**: 8 — UI Workflow Redesign  
**Layer**: Vue.js frontend  
**Dependencies**: Step 12 (batch capture loop), Step 24 (side-by-side viewer)

## Objective

Replace the current single-view layout with a three-tab shell that guides the user through the book-capture workflow. The tabs are not strictly gated — most are accessible as soon as relevant data exists — but the UI surfaces clear "next step" cues.

## Tab Structure

```
┌────────────────────────────────────────────────────────────────────┐
│  KindleOCR   [📷 Capture]  [📄 Pages / Review]  [📦 Export]       │
├────────────────────────────────────────────────────────────────────┤
│  (active tab content)                                              │
└────────────────────────────────────────────────────────────────────┘
```

### Tab 1 — Capture
- Window picker + region selector (collapsible once capture starts — see step 45)
- Capture controls (start / pause / stop)
- Progress tracker
- "Next: Review pages →" call-to-action once any pages are captured

### Tab 2 — Pages / Review / OCR / Edit
Four **subtabs** rendered as a secondary nav bar inside this tab:

| Subtab | Purpose |
|--------|---------|
| **Pages** | Filmstrip sidebar + page detail pane. Drag-drop reorder, page types, chapter markers. (step 41, 42, 43) |
| **OCR** | Trigger OCR (auto/manual). Per-page progress. Re-run single page. (step 44) |
| **Review** | Side-by-side viewer: image left, OCR text right, editable. (step 24, 25) |
| **Edit** | Batch operations (find/replace, regex), global text transforms. (step 27) |

### Tab 3 — Export
- Metadata form (title, author, language, cover, ISBN)
- Chapter structure editor (step 43)
- EPUB generation + validation
- Output path selector

## Gating Rules

| Tab / Subtab | Accessible when |
|---|---|
| Capture | Always |
| Pages subtab | ≥ 1 page captured or on disk |
| OCR subtab | ≥ 1 page captured |
| Review subtab | ≥ 1 page has OCR result |
| Edit subtab | ≥ 1 page has OCR result |
| Export tab | ≥ 1 page has OCR result |

Disabled tabs show a tooltip explaining what is needed to unlock them.

## Layout — Middle Tab (Pages / Review)

```
┌──────────────────────────────────────────────────────────────────┐
│  [Pages]  [OCR]  [Review]  [Edit]                                │
├──────────┬───────────────────────────────────────────────────────┤
│          │                                                        │
│ Filmstrip│  Main content area (varies by subtab)                 │
│ sidebar  │                                                        │
│ (thumbs) │  [subtab-specific controls and data]                  │
│          │                                                        │
│ ───────  │                                                        │
│ + add    │                                                        │
└──────────┴───────────────────────────────────────────────────────┘
```

The filmstrip sidebar is **shared across all four subtabs** — selecting a page in the filmstrip drives the main content area regardless of the active subtab.

## State Model

```typescript
// src/stores/ui.ts (NEW)
export type TopTab = 'capture' | 'review' | 'export'
export type ReviewSubtab = 'pages' | 'ocr' | 'review' | 'edit'

interface UiState {
  activeTab: TopTab
  activeReviewSubtab: ReviewSubtab
  selectedPageIndex: number | null   // drives filmstrip + main content
}
```

The store exposes:
- `setTab(tab: TopTab)` — validates gating, sets `activeTab`
- `setSubtab(sub: ReviewSubtab)` — sets `activeReviewSubtab`
- `selectPage(index: number)` — validates index, sets `selectedPageIndex`
- `isTabEnabled(tab: TopTab): boolean` — computed from page/OCR counts
- `isSubtabEnabled(sub: ReviewSubtab): boolean`

## Files to Create/Modify

- `src/stores/ui.ts` — NEW: UiState store
- `src/App.vue` — replace current layout with `<TabShell>` + router-style tab switching
- `src/components/TabShell.vue` — NEW: top-level tab bar + tab content switcher
- `src/components/ReviewLayout.vue` — NEW: filmstrip sidebar + subtab bar + main content area
- `src/views/CaptureView.vue` — becomes the content for the Capture tab (no layout changes yet)
- `src/views/ReviewView.vue` — NEW: wrapper that renders `<ReviewLayout>` with correct subtab content
- `src/views/ExportView.vue` — NEW: stub for the Export tab

## Test Criteria

### Vitest — `src/__tests__/ui.store.spec.ts`

1. **Initial state**: `activeTab` = `'capture'`, `selectedPageIndex` = null
2. **Tab gating — no pages**: `isTabEnabled('review')` = false; `isTabEnabled('capture')` = true
3. **Tab gating — pages exist**: add mock page to capture store → `isTabEnabled('review')` = true
4. **Tab gating — OCR required**: Review and Edit subtabs disabled when no OCR results
5. **setTab blocked**: calling `setTab('review')` when 0 pages → tab does not change, returns false
6. **selectPage out of range**: index -1 or > page count → no change, no throw
7. **Subtab persistence**: switch top tab away and back → `activeReviewSubtab` unchanged

## Edge Cases

- User opens app with an existing session on disk (step 40 handles reconciliation) — after reconcile, if pages exist, default to Review tab rather than Capture tab
- Resize: filmstrip sidebar should be collapsible on narrow screens or by user drag
- Keyboard navigation: `Ctrl+1/2/3` to switch top tabs; `Alt+1/2/3/4` for subtabs
