# Step 45: Capture Tab Collapse

**Phase**: 8 — UI Workflow Redesign  
**Layer**: Vue.js frontend  
**Dependencies**: Step 39 (tab shell), Step 9 (region selector), Step 8 (window picker)

## Objective

Once the user has selected a window and region and started capture, the window picker and region selector collapse into a compact summary bar. The full controls remain accessible but are hidden by default to reduce visual noise during a long capture session.

## Collapsed State (shown during/after capture)

```
┌────────────────────────────────────────────────────────────────────┐
│ 📷  Capturing from: Kindle for PC — 800 × 600 px region    [✎ Edit]│
└────────────────────────────────────────────────────────────────────┘
```

- Shows app window title and region dimensions
- **[✎ Edit]** expands back to full picker + region selector
- If capture is currently running, clicking Edit pauses it first (with a "Pause to edit?" confirmation)

## Expanded State (default on first launch; also shown after clicking Edit)

Normal full layout:
```
┌────────────────────────────────────────────────────────────────────┐
│  Step 1: Select window                                   [▲ Collapse]│
│  [Window Picker component]                                         │
│                                                                    │
│  Step 2: Select capture region                                      │
│  [Region Selector component]                                        │
│                                                                    │
│  Step 3: Configure & capture                                        │
│  [Capture controls + progress]                                      │
└────────────────────────────────────────────────────────────────────┘
```

## Collapse Trigger Rules

| Event | Result |
|---|---|
| First successful capture of page 1 | Auto-collapse after 2s delay |
| User clicks [✎ Edit] | Expand |
| Capture completes (all pages done) | Stay collapsed; show summary "Done: 47 pages" |
| Session loaded with existing pages | Start collapsed (window/region from session) |
| No window/region selected yet | Cannot collapse (button disabled) |

## State Stored

```typescript
// in ui.ts store (step 39)
captureConfigCollapsed: boolean   // default false; auto-set to true after first capture
```

Persisted in the UI preferences (not session JSON, since it's a display preference).

## Animation

Collapse/expand uses a CSS height transition (`max-height` animation, `overflow: hidden`):
- Collapse: 300ms ease-out
- Expand: 200ms ease-in

## Files to Create/Modify

- `src/views/CaptureView.vue` — wrap window picker + region selector in a collapsible `<CaptureConfigPanel>` 
- `src/components/CaptureConfigPanel.vue` — NEW: collapsible wrapper with summary bar and expand/collapse logic
- `src/stores/ui.ts` — add `captureConfigCollapsed` state (step 39 dependency)

## Test Criteria

### Vitest — `src/__tests__/ui.store.spec.ts` additions

1. Initial state: `captureConfigCollapsed` = false
2. `setCaptureConfigCollapsed(true)` → state changes
3. After `onPageCaptured` event with page 1 → `captureConfigCollapsed` set to true
4. Loading session with existing pages → `captureConfigCollapsed` defaults to true

### Vitest — component tests (`CaptureConfigPanel.spec.ts`)

5. Renders in expanded state when `captureConfigCollapsed` = false
6. Renders collapsed summary bar when `captureConfigCollapsed` = true
7. Summary bar shows correct window title and region dimensions from store
8. Clicking Edit emits `expand` event (and if capturing, emits `pause-and-expand`)
9. [▲ Collapse] button visible in expanded state; clicking it collapses
10. Cannot collapse when no window is selected (button disabled, tooltip present)
