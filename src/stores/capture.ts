import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface WindowInfo {
  handle: number;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  process_name: string;
}

export interface CaptureRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

const MIN_REGION_SIZE = 50;

/**
 * Clamp a region to stay within window bounds, enforcing minimum size.
 */
export function clampRegion(
  region: CaptureRegion,
  window: { x: number; y: number; width: number; height: number }
): CaptureRegion {
  let { x, y, width, height } = region;

  // Enforce minimum size
  width = Math.max(width, MIN_REGION_SIZE);
  height = Math.max(height, MIN_REGION_SIZE);

  // Clamp dimensions to window size
  width = Math.min(width, window.width);
  height = Math.min(height, window.height);

  // Clamp position to window bounds
  x = Math.max(x, window.x);
  y = Math.max(y, window.y);

  // Ensure the region doesn't extend past the window's right/bottom edge
  x = Math.min(x, window.x + window.width - width);
  y = Math.min(y, window.y + window.height - height);

  return { x, y, width, height };
}

export const useCaptureStore = defineStore("capture", () => {
  const windows = ref<WindowInfo[]>([]);
  const selectedWindow = ref<WindowInfo | null>(null);
  const region = ref<CaptureRegion | null>(null);

  const hasSelection = computed(
    () => selectedWindow.value !== null && region.value !== null
  );

  function setWindows(list: WindowInfo[]) {
    windows.value = list;
  }

  function selectWindow(w: WindowInfo) {
    selectedWindow.value = w;
    region.value = null; // Reset region when window changes
  }

  function setRegion(r: CaptureRegion) {
    if (!selectedWindow.value) return;
    region.value = clampRegion(r, selectedWindow.value);
  }

  function clearSelection() {
    selectedWindow.value = null;
    region.value = null;
  }

  return {
    windows,
    selectedWindow,
    region,
    hasSelection,
    setWindows,
    selectWindow,
    setRegion,
    clearSelection,
  };
});
