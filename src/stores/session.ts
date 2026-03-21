import { defineStore } from "pinia";
import { ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { useCaptureStore, type CapturedPage } from "@/stores/capture";

export interface DiskPageEntry {
  pageNumber: number;
  filePath: string;
  fileSizeBytes: number;
  modifiedAt: number;
}

export interface DiskScanResult {
  found: DiskPageEntry[];
}

export interface ReconcileReport {
  /** Page numbers in session JSON whose PNG is missing on disk. */
  missingFromDisk: number[];
  /** Page numbers found on disk that are absent from the session. */
  extraOnDisk: number[];
  /** Page numbers present in both → all good. */
  matched: number[];
}

export interface ReconcileActions {
  removeFromSession: number[];
  markNeedsRecapture: number[];
  adoptFromDisk: number[];
}

function buildReport(
  sessionPages: CapturedPage[],
  diskEntries: DiskPageEntry[]
): ReconcileReport {
  const sessionNums = new Set(sessionPages.map((p) => p.pageNumber));
  const diskNums = new Set(diskEntries.map((e) => e.pageNumber));

  const missingFromDisk = [...sessionNums].filter((n) => !diskNums.has(n));
  const extraOnDisk = [...diskNums].filter((n) => !sessionNums.has(n));
  const matched = [...sessionNums].filter((n) => diskNums.has(n));

  return { missingFromDisk, extraOnDisk, matched };
}

export const useSessionStore = defineStore("session", () => {
  const reconcileReport = ref<ReconcileReport | null>(null);
  const lastScanResult = ref<DiskScanResult | null>(null);
  const isReconciling = ref(false);

  async function reconcileWithDisk(outputDir: string, filePrefix: string): Promise<ReconcileReport> {
    const captureStore = useCaptureStore();
    isReconciling.value = true;
    try {
      const scan: DiskScanResult = await invoke("scan_session_dir", {
        outputDir,
        filePrefix,
      });
      lastScanResult.value = scan;
      const report = buildReport(captureStore.capturedPages, scan.found);
      reconcileReport.value = report;
      return report;
    } finally {
      isReconciling.value = false;
    }
  }

  /**
   * Apply reconciliation decisions:
   * - removeFromSession: drop these page numbers from capturedPages
   * - markNeedsRecapture: set captureStatus = 'needs_recapture'
   * - adoptFromDisk: insert new pages from disk entries
   */
  function applyReconcile(actions: ReconcileActions): void {
    const captureStore = useCaptureStore();
    const scan = lastScanResult.value;

    // Remove
    if (actions.removeFromSession.length > 0) {
      const removeSet = new Set(actions.removeFromSession);
      captureStore.capturedPages.splice(
        0,
        captureStore.capturedPages.length,
        ...captureStore.capturedPages.filter((p) => !removeSet.has(p.pageNumber))
      );
    }

    // Mark needs_recapture
    for (const num of actions.markNeedsRecapture) {
      const idx = captureStore.capturedPages.findIndex((p) => p.pageNumber === num);
      if (idx >= 0) captureStore.setCaptureStatus(idx, "needs_recapture");
    }

    // Adopt from disk
    if (actions.adoptFromDisk.length > 0 && scan) {
      const adoptSet = new Set(actions.adoptFromDisk);
      for (const entry of scan.found) {
        if (!adoptSet.has(entry.pageNumber)) continue;
        const newPage: CapturedPage = {
          pageNumber: entry.pageNumber,
          imagePath: entry.filePath,
          captureType: "page",
          timestamp: entry.modifiedAt * 1000,
          captureStatus: "ok",
          pageType: "text",
          ocrStatus: "pending",
        };
        captureStore.capturedPages.push(newPage);
      }
      // Re-sort by page number
      captureStore.capturedPages.sort((a, b) => a.pageNumber - b.pageNumber);
    }

    reconcileReport.value = null;
  }

  function clearReconcile(): void {
    reconcileReport.value = null;
    lastScanResult.value = null;
  }

  return {
    reconcileReport,
    lastScanResult,
    isReconciling,
    reconcileWithDisk,
    applyReconcile,
    clearReconcile,
  };
});

/** Pure utility: build a ReconcileReport without store side-effects (used in tests). */
export { buildReport };
