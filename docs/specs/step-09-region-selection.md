# Step 09: Region Selection UI

**Phase**: 2 — Screen Capture Module  
**Layer**: Vue.js frontend  
**Dependencies**: Step 8 (window enumeration)

## Objective

Build a Vue component that lets the user: (1) pick a window from the enumerated list, and (2) draw a rectangular selection region over that window's content area. The region defines what portion of the screen to capture for each page.

## Inputs

- `WindowInfo[]` from the `list_windows` Tauri command (step 8)
- User mouse interactions (mousedown, mousemove, mouseup) for drawing the selection rectangle

## Outputs

```typescript
interface CaptureRegion {
  window_handle: number;  // Selected window handle
  x: number;              // Region top-left X (relative to screen)
  y: number;              // Region top-left Y (relative to screen)
  width: number;          // Region width in pixels
  height: number;         // Region height in pixels
}
```

Stored in a Pinia store for use by the capture step.

## UI Design

1. **Window picker dropdown**: Lists available windows by title. "Refresh" button re-fetches. Shows process name in parentheses.
2. **Selection overlay**: After picking a window, show a semi-transparent overlay. User clicks and drags to define the capture rectangle. The rectangle has:
   - Draggable corners and edges for resizing
   - Drag the interior to reposition
   - Dimension readout (WxH in pixels) displayed on the selection box
3. **Preview**: Show a live screenshot of the selected region (capture once to preview).
4. **Confirm button**: Locks in the selection and proceeds to capture settings.

## Algorithm

### Region data model
```typescript
interface RegionState {
  x: number;
  y: number;
  width: number;
  height: number;
}
```

- **Bounds clamping**: Region must stay within the selected window's bounds. On resize/move, clamp: `x >= window.x`, `y >= window.y`, `x + width <= window.x + window.width`, etc.
- **Minimum size**: Enforce minimum 50×50 pixels to prevent accidental zero-area selections.
- **Aspect ratio lock**: Optional (shift-drag to maintain aspect ratio) — nice-to-have, not required.

## Files to Create/Modify

- `src/components/RegionSelector.vue` — the selection overlay component
- `src/components/WindowPicker.vue` — window list dropdown
- `src/stores/capture.ts` — Pinia store for capture state (selected window, region)
- `src/views/CaptureView.vue` — orchestrates the capture workflow

## Edge Cases

- Window moves after selection → warn user and offer to re-select
- Window is minimized → prevent selection, show message
- Very small window → clamp minimum region to window size if window < 50×50
- Multi-monitor with different DPI → coordinates must be in physical pixels
- User closes the target window during selection → handle gracefully

## Test Criteria

### Automated (Vitest)
1. **Region bounds clamping**: Given a window at (100, 100, 800, 600), setting region to (50, 50, 900, 700) should clamp to (100, 100, 800, 600)
2. **Minimum size enforcement**: Setting width=10, height=10 should clamp up to 50×50
3. **Region within window**: Any valid region must satisfy x>=win.x, y>=win.y, x+w<=win.x+win.w, y+h<=win.y+win.h
4. **Store integration**: Setting region in store emits correct reactive values

### Manual verification
5. Select a window, draw region, verify preview screenshot matches selected area
