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

export type CaptureType = "page" | "cover" | "illustration";

export type PageType =
  | "text"
  | "cover"
  | "illustration"
  | "toc"
  | "license"
  | "blank"
  | "chapter_start"
  | "excluded";

export type CaptureStatus =
  | "ok"
  | "needs_recapture"
  | "missing"
  | "placeholder";

export type OcrStatus = "pending" | "running" | "done" | "error" | "skipped";

export interface BatchCaptureConfig {
  outputDir: string;
  bookName: string;
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

export interface CapturedPage {
  pageNumber: number;
  imagePath: string;
  captureType: CaptureType;
  timestamp: number;
  captureStatus: CaptureStatus;
  errorMessage?: string;
  pageType: PageType;
  userNotes?: string;
  ocrStatus: OcrStatus;
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
  stopped: ["idle", "capturing"],
  completed: ["idle"],
};

/** Check if a state transition is valid. */
export function isValidTransition(from: BatchState, to: BatchState): boolean {
  return VALID_TRANSITIONS[from]?.includes(to) ?? false;
}

export type SidecarStatus = "disconnected" | "connecting" | "connected" | "error";

export const useCaptureStore = defineStore("capture", () => {
  // Window selection state
  const windows = ref<WindowInfo[]>([]);
  const selectedWindow = ref<WindowInfo | null>(null);
  const region = ref<CaptureRegion | null>(null);
  const previewDataUrl = ref<string | null>(null);

  // Sidecar state
  const sidecarStatus = ref<SidecarStatus>("disconnected");
  const sidecarError = ref<string | null>(null);

  // Project state
  const bookName = ref("");
  const nextCaptureType = ref<CaptureType>("page");

  // Batch capture state
  const batchState = ref<BatchState>("idle");
  const batchConfig = ref<BatchCaptureConfig>({
    outputDir: "",
    bookName: "",
    delayBetweenMs: 1500,
    maxPages: null,
    filePrefix: "page",
    pageTurnKey: "Right",
  });
  const pagesCaptured = ref(0);
  const captureHistory = ref<CaptureProgress[]>([]);
  const capturedPages = ref<CapturedPage[]>([]);

  const hasSelection = computed(
    () => selectedWindow.value !== null && region.value !== null
  );

  const isCapturing = computed(() => batchState.value === "capturing");
  const isPaused = computed(() => batchState.value === "paused");
  const isStopped = computed(() => batchState.value === "stopped");

  /** Effective output directory: outputDir / bookName */
  const effectiveOutputDir = computed(() => {
    const base = batchConfig.value.outputDir;
    const name = bookName.value.trim();
    if (!base) return "";
    if (!name) return base;
    return `${base}\\${name}`;
  });

  function setWindows(list: WindowInfo[]) {
    windows.value = list;
  }

  function selectWindow(w: WindowInfo) {
    selectedWindow.value = w;
    region.value = null;
    previewDataUrl.value = null;
  }

  function setRegion(r: CaptureRegion) {
    if (!selectedWindow.value) return;
    region.value = clampRegion(r, selectedWindow.value);
  }

  function setPreview(dataUrl: string | null) {
    previewDataUrl.value = dataUrl;
  }

  function clearSelection() {
    selectedWindow.value = null;
    region.value = null;
    previewDataUrl.value = null;
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
      capturedPages.value = [];
    }
    return true;
  }

  function recordCapture(progress: CaptureProgress) {
    captureHistory.value.push(progress);
    const inferredPageType: PageType =
      nextCaptureType.value === "cover" ? "cover" :
      nextCaptureType.value === "illustration" ? "illustration" :
      "text";
    if (progress.status === "captured") {
      pagesCaptured.value = progress.pageNumber;
      capturedPages.value.push({
        pageNumber: progress.pageNumber,
        imagePath: progress.imagePath,
        captureType: nextCaptureType.value,
        timestamp: Date.now(),
        captureStatus: "ok",
        pageType: inferredPageType,
        ocrStatus: "pending",
      });
    } else {
      capturedPages.value.push({
        pageNumber: progress.pageNumber,
        imagePath: progress.imagePath,
        captureType: nextCaptureType.value,
        timestamp: Date.now(),
        captureStatus: "needs_recapture",
        errorMessage: progress.errorMessage,
        pageType: inferredPageType,
        ocrStatus: "pending",
      });
    }
  }

  function setSidecarStatus(status: SidecarStatus, error?: string) {
    sidecarStatus.value = status;
    sidecarError.value = error ?? null;
  }

  function setBookName(name: string) {
    bookName.value = name;
  }

  function setNextCaptureType(type: CaptureType) {
    nextCaptureType.value = type;
  }

  /** Restore the pages-captured count from a loaded session (for resume). */
  function restorePagesCaptured(count: number) {
    pagesCaptured.value = count;
  }

  /** Update the page type for a page by index (0-based in capturedPages). */
  function setPageType(index: number, type: PageType): void {
    if (index < 0 || index >= capturedPages.value.length) return;
    capturedPages.value[index].pageType = type;
  }

  /** Update the capture status for a page by index. */
  function setCaptureStatus(index: number, status: CaptureStatus): void {
    if (index < 0 || index >= capturedPages.value.length) return;
    capturedPages.value[index].captureStatus = status;
  }

  return {
    // Window selection
    windows,
    selectedWindow,
    region,
    previewDataUrl,
    hasSelection,
    setWindows,
    selectWindow,
    setRegion,
    setPreview,
    clearSelection,
    // Sidecar
    sidecarStatus,
    sidecarError,
    setSidecarStatus,
    // Project
    bookName,
    nextCaptureType,
    effectiveOutputDir,
    setBookName,
    setNextCaptureType,
    restorePagesCaptured,
    // Batch capture
    batchState,
    batchConfig,
    pagesCaptured,
    captureHistory,
    capturedPages,
    isCapturing,
    isPaused,
    isStopped,
    setBatchConfig,
    transitionTo,
    recordCapture,
    setPageType,
    setCaptureStatus,
  };
});
