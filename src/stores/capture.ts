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

export type BatchState = "idle" | "capturing" | "paused" | "stopped" | "completed";

export interface BatchCaptureConfig {
  outputDir: string;
  delayBetweenMs: number;
  maxPages: number | null;
  filePrefix: string;
  pageTurnKey: string;
}

export interface CaptureProgress {
  pageNumber: number;
  totalPages: number | null;
  imagePath: string;
  status: "captured" | "error";
  errorMessage?: string;
}

const MIN_REGION_SIZE = 50;
const MIN_DELAY_MS = 200;

/**
 * Clamp a region to stay within window bounds, enforcing minimum size.
 */
export function clampRegion(
  region: CaptureRegion,
  window: { x: number; y: number; width: number; height: number }
): CaptureRegion {
  let { x, y, width, height } = region;

  width = Math.max(width, MIN_REGION_SIZE);
  height = Math.max(height, MIN_REGION_SIZE);
  width = Math.min(width, window.width);
  height = Math.min(height, window.height);
  x = Math.max(x, window.x);
  y = Math.max(y, window.y);
  x = Math.min(x, window.x + window.width - width);
  y = Math.min(y, window.y + window.height - height);

  return { x, y, width, height };
}

/** Format page number as zero-padded 3-digit string. */
export function formatPageFilename(prefix: string, pageNumber: number): string {
  return `${prefix}-${String(pageNumber).padStart(3, "0")}.png`;
}

/** Valid state transitions for the batch capture state machine. */
const VALID_TRANSITIONS: Record<BatchState, BatchState[]> = {
  idle: ["capturing"],
  capturing: ["paused", "stopped", "completed"],
  paused: ["capturing", "stopped"],
  stopped: ["idle"],
  completed: ["idle"],
};

/** Check if a state transition is valid. */
export function isValidTransition(from: BatchState, to: BatchState): boolean {
  return VALID_TRANSITIONS[from]?.includes(to) ?? false;
}

export const useCaptureStore = defineStore("capture", () => {
  // Window selection state
  const windows = ref<WindowInfo[]>([]);
  const selectedWindow = ref<WindowInfo | null>(null);
  const region = ref<CaptureRegion | null>(null);

  // Batch capture state
  const batchState = ref<BatchState>("idle");
  const batchConfig = ref<BatchCaptureConfig>({
    outputDir: "",
    delayBetweenMs: 1500,
    maxPages: null,
    filePrefix: "page",
    pageTurnKey: "Right",
  });
  const pagesCaptured = ref(0);
  const captureHistory = ref<CaptureProgress[]>([]);

  const hasSelection = computed(
    () => selectedWindow.value !== null && region.value !== null
  );

  const isCapturing = computed(() => batchState.value === "capturing");
  const isPaused = computed(() => batchState.value === "paused");

  function setWindows(list: WindowInfo[]) {
    windows.value = list;
  }

  function selectWindow(w: WindowInfo) {
    selectedWindow.value = w;
    region.value = null;
  }

  function setRegion(r: CaptureRegion) {
    if (!selectedWindow.value) return;
    region.value = clampRegion(r, selectedWindow.value);
  }

  function clearSelection() {
    selectedWindow.value = null;
    region.value = null;
  }

  function setBatchConfig(config: Partial<BatchCaptureConfig>) {
    Object.assign(batchConfig.value, config);
    // Enforce minimum delay
    batchConfig.value.delayBetweenMs = Math.max(
      batchConfig.value.delayBetweenMs,
      MIN_DELAY_MS
    );
  }

  function transitionTo(newState: BatchState): boolean {
    if (!isValidTransition(batchState.value, newState)) {
      return false;
    }
    batchState.value = newState;
    if (newState === "idle") {
      pagesCaptured.value = 0;
      captureHistory.value = [];
    }
    return true;
  }

  function recordCapture(progress: CaptureProgress) {
    captureHistory.value.push(progress);
    if (progress.status === "captured") {
      pagesCaptured.value = progress.pageNumber;
    }
  }

  return {
    // Window selection
    windows,
    selectedWindow,
    region,
    hasSelection,
    setWindows,
    selectWindow,
    setRegion,
    clearSelection,
    // Batch capture
    batchState,
    batchConfig,
    pagesCaptured,
    captureHistory,
    isCapturing,
    isPaused,
    setBatchConfig,
    transitionTo,
    recordCapture,
  };
});
