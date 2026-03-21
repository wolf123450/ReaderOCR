import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { useCaptureStore } from "@/stores/capture";
import { useUiStore } from "@/stores/ui";
import { useSettingsStore } from "@/stores/settings";

export type OcrBatchState = "idle" | "running" | "paused" | "stopped" | "completed";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TextBlock {
  type: string;
  text: string;
  confidence: number;
  bbox: BoundingBox;
  col_index: number;
}

export interface OcrPageResult {
  pageNumber: number;
  text: string;
  confidence: number;
  blocks?: TextBlock[];
  errorMessage?: string;
}

export interface OcrBatchProgress {
  current: number;
  total: number;
  errors: number;
}

/** Page types that should be skipped during OCR (no text content expected). */
const SKIP_PAGE_TYPES = new Set(["illustration", "blank", "excluded"]);

export const useOcrStore = defineStore("ocr", () => {
  const batchState = ref<OcrBatchState>("idle");
  const batchProgress = ref<OcrBatchProgress>({ current: 0, total: 0, errors: 0 });
  const ocrQueue = ref<number[]>([]); // indices into capturedPages
  const pageResults = ref<Map<number, OcrPageResult>>(new Map());
  const testRunResult = ref<OcrPageResult | null>(null);
  const testRunning = ref(false);
  const isProcessing = ref(false);

  const captureStore = useCaptureStore();
  const uiStore = useUiStore();

  const isRunning = computed(() => batchState.value === "running");
  const isPaused = computed(() => batchState.value === "paused");

  // --- Batch OCR ---

  function startBatchOcr(): void {
    const pages = captureStore.capturedPages;
    const indices: number[] = [];
    for (let i = 0; i < pages.length; i++) {
      const p = pages[i];
      if (SKIP_PAGE_TYPES.has(p.pageType)) {
        captureStore.capturedPages[i].ocrStatus = "skipped";
      } else if (p.ocrStatus !== "done") {
        indices.push(i);
      }
    }
    ocrQueue.value = indices;
    batchProgress.value = { current: 0, total: indices.length, errors: 0 };
    batchState.value = "running";
    _processNext();
  }

  function pauseBatchOcr(): void {
    if (batchState.value === "running") batchState.value = "paused";
  }

  function resumeBatchOcr(): void {
    if (batchState.value === "paused") {
      batchState.value = "running";
      _processNext();
    }
  }

  function stopBatchOcr(): void {
    batchState.value = "stopped";
    ocrQueue.value = [];
  }

  async function _processNext(): Promise<void> {
    if (batchState.value !== "running") return;
    if (ocrQueue.value.length === 0) {
      batchState.value = "completed";
      return;
    }
    if (isProcessing.value) return; // guard against re-entrancy

    isProcessing.value = true;
    const idx = ocrQueue.value.shift()!;
    const page = captureStore.capturedPages[idx];
    if (!page) {
      isProcessing.value = false;
      _processNext();
      return;
    }

    captureStore.capturedPages[idx].ocrStatus = "running";
    try {
      const result: OcrPageResult = await invoke("ocr_page", {
        imagePath: page.imagePath,
        pageNumber: page.pageNumber,
        engine: useSettingsStore().ocrEngine,
        language: useSettingsStore().ocrLanguage,
        maxCols: useSettingsStore().ocrMaxColumns,
      });
      captureStore.capturedPages[idx].ocrStatus = "done";
      pageResults.value.set(page.pageNumber, result);
      batchProgress.value.current += 1;
      _updateOcrCount();
    } catch (e: unknown) {
      captureStore.capturedPages[idx].ocrStatus = "error";
      pageResults.value.set(page.pageNumber, {
        pageNumber: page.pageNumber,
        text: "",
        confidence: 0,
        errorMessage: String(e),
      });
      batchProgress.value.current += 1;
      batchProgress.value.errors += 1;
    } finally {
      isProcessing.value = false;
    }

    // Continue to next page (even after error)
    _processNext();
  }

  function _updateOcrCount(): void {
    const done = captureStore.capturedPages.filter((p) => p.ocrStatus === "done").length;
    uiStore.setOcrPageCount(done);
  }

  // --- Single-page test run ---

  async function runTestOcr(pageIndex: number): Promise<void> {
    const page = captureStore.capturedPages[pageIndex];
    if (!page) return;
    testRunning.value = true;
    testRunResult.value = null;
    try {
      const result: OcrPageResult = await invoke("ocr_page", {
        imagePath: page.imagePath,
        pageNumber: page.pageNumber,
        engine: useSettingsStore().ocrEngine,
        language: useSettingsStore().ocrLanguage,
        maxCols: useSettingsStore().ocrMaxColumns,
      });
      testRunResult.value = result;
    } catch (e: unknown) {
      testRunResult.value = {
        pageNumber: page.pageNumber,
        text: "",
        confidence: 0,
        errorMessage: String(e),
      };
    } finally {
      testRunning.value = false;
    }
  }

  // --- Single-page re-run (from filmstrip context menu) ---

  async function rerunPageOcr(pageIndex: number): Promise<void> {
    const page = captureStore.capturedPages[pageIndex];
    if (!page || SKIP_PAGE_TYPES.has(page.pageType)) return;
    captureStore.capturedPages[pageIndex].ocrStatus = "running";
    try {
      const result: OcrPageResult = await invoke("ocr_page", {
        imagePath: page.imagePath,
        pageNumber: page.pageNumber,
        engine: useSettingsStore().ocrEngine,
        language: useSettingsStore().ocrLanguage,
        maxCols: useSettingsStore().ocrMaxColumns,
      });
      captureStore.capturedPages[pageIndex].ocrStatus = "done";
      pageResults.value.set(page.pageNumber, result);
      _updateOcrCount();
    } catch (e: unknown) {
      captureStore.capturedPages[pageIndex].ocrStatus = "error";
    }
  }

  // --- Auto-OCR hook (called by capture listener in CaptureView) ---

  function onPageCaptured(pageIndex: number): void {
    if (!useSettingsStore().autoOcrAfterCapture) return;
    const page = captureStore.capturedPages[pageIndex];
    if (!page || SKIP_PAGE_TYPES.has(page.pageType)) return;
    if (!ocrQueue.value.includes(pageIndex)) {
      ocrQueue.value.push(pageIndex);
    }
    if (batchState.value === "idle" || batchState.value === "completed") {
      batchProgress.value.total = ocrQueue.value.length;
      batchState.value = "running";
      _processNext();
    }
  }

  return {
    batchState,
    batchProgress,
    ocrQueue,
    pageResults,
    testRunResult,
    testRunning,
    isProcessing,
    isRunning,
    isPaused,
    startBatchOcr,
    pauseBatchOcr,
    resumeBatchOcr,
    stopBatchOcr,
    runTestOcr,
    rerunPageOcr,
    onPageCaptured,
  };
});
