# Step 40: Session Disk Reconciliation

**Phase**: 8 — UI Workflow Redesign  
**Layer**: Rust (Tauri command) + Vue.js frontend  
**Dependencies**: Step 12 (batch capture), Step 13 (session JSON)

## Objective

When a session is loaded (or the app starts with a previously used output directory), scan the actual PNG files on disk and reconcile with what is recorded in the session JSON. Surface a dialog so the user can resolve any conflicts.

## Problem Cases

| Scenario | Cause | Resolution options |
|---|---|---|
| PNG on disk, missing from JSON | App crashed mid-capture; file copied in manually | Adopt file into session (with auto-assigned page number) |
| JSON entry, PNG missing | File deleted externally; moved; wrong output dir | Remove from session, or re-capture |
| Page number gap in JSON (e.g. 1,2,4,5) | Prior deletion or partial capture | Renumber sequentially or preserve gaps with placeholders |
| Page count mismatch (different total) | JSON says 42 pages, disk has 38 PNGs | Show diff, let user decide |
| Extra PNGs beyond session range (e.g. `book-050.png` when JSON only goes to 42) | Manual copy or aborted extension | Offer to adopt extras |
| Filename prefix mismatch | Session renamed or moved | Show warning; offer to re-link |

## Algorithm

### Rust side — `scan_session_dir` Tauri command

```
Input: output_dir: String, file_prefix: String
Output: DiskScanResult
```

1. List all files in `output_dir` matching `{prefix}-NNN.png` (glob `{prefix}-*.png`)
2. Parse page numbers from filenames
3. Return sorted list of `{ page_number, file_path, file_size_bytes, modified_at }`

### Vue/store side — reconciliation logic

```typescript
interface DiskScanResult {
  found: Array<{ pageNumber: number; filePath: string; fileSizeBytes: number; modifiedAt: number }>
}

interface ReconcileReport {
  missingFromDisk: number[]        // in JSON but PNG gone
  extraOnDisk: number[]            // PNG exists, not in JSON
  gaps: number[]                   // page numbers absent from both
  matched: number[]                // all good
}
```

1. Call `scan_session_dir` with current session prefix
2. Build `ReconcileReport`
3. If report has no conflicts → silent success, continue
4. If conflicts found → show `ReconcileDialog.vue`

### Reconcile Dialog

```
┌──────────────────────────────────────────────────────┐
│  Session Reconciliation                               │
├──────────────────────────────────────────────────────┤
│  Found on disk:  38 pages                            │
│  In session:     42 pages                            │
│                                                      │
│  ⚠  4 pages in session are missing from disk:       │
│     #15, #16, #17, #18                               │
│     [Remove from session] [Mark as needs recapture]  │
│                                                      │
│  ✚  2 pages found on disk not in session:            │
│     #43, #44                                         │
│     [Adopt these pages] [Ignore]                     │
│                                                      │
│  [Apply & Continue]  [Cancel]                        │
└──────────────────────────────────────────────────────┘
```

## Trigger Points

- On `load_session` (open existing project)
- On first app launch when output dir is pre-populated
- On user clicking "Sync with disk" button in Pages tab

## Files to Create/Modify

### Rust
- `src-tauri/src/session/reconcile.rs` — NEW: `scan_session_dir` logic, `DiskScanResult` type
- `src-tauri/src/lib.rs` — register `scan_session_dir` Tauri command

### Vue
- `src/stores/session.ts` — NEW (or extend `capture.ts`): `reconcileWithDisk()` action, `ReconcileReport` type
- `src/components/ReconcileDialog.vue` — NEW: conflict resolution dialog

## Test Criteria

### Rust — `src-tauri/src/session/reconcile.rs`

1. Directory with no PNGs → returns empty `found` list, no panic
2. Directory with `book-001.png`, `book-002.png`, `book-005.png` → returns `[1, 2, 5]`; gaps `[3, 4]` not reported (gap detection is client-side)
3. Non-matching filenames (`cover.png`, `notes.txt`) are ignored
4. File with malformed number (`book-abc.png`) is skipped without panic

### Vitest — `src/__tests__/session.store.spec.ts`

1. Reconcile with perfect match → `ReconcileReport` has empty `missingFromDisk`, `extraOnDisk`, `gaps`
2. JSON has 5 pages, disk has pages 1-3 only → `missingFromDisk` = [4, 5]
3. JSON has pages 1-3, disk has pages 1-5 → `extraOnDisk` = [4, 5]
4. `applyReconcile({ removeFromSession: [4,5], adoptFromDisk: [] })` → session page list updated
5. `applyReconcile({ adoptFromDisk: [4,5] })` → 2 new pages added with status `"ok"`
6. Cancel reconcile → session unchanged

## Edge Cases

- Output directory does not exist → treat as 0 PNGs found (not an error)
- Two sessions share a prefix in the same directory → warn user (files may intermix)
- Very large directories (1000+ files) → scan is async, show spinner
