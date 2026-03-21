import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useOcrStore } from "@/stores/ocr";
import { useCaptureStore, type CapturedPage } from "@/stores/capture";
import { useSettingsStore } from "@/stores/settings";
import { useUiStore } from "@/stores/ui";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

import { invoke } from "@tauri-apps/api/core";

function makePage(n: number, extra?: Partial<CapturedPage>): CapturedPage {
  return {
    pageNumber: n,
    imagePath: `book/page-${String(n).padStart(3, "0")}.png`,
    captureType: "page",
    timestamp: Date.now(),
    captureStatus: "ok",
    pageType: "text",
    ocrStatus: "pending",
    ...extra,
  };
}

function mockOcrSuccess(text = "Hello", confidence = 95) {
  vi.mocked(invoke).mockImplementation(async (_cmd, args: any) => ({
    pageNumber: 1,
    text,
    confidence,
    imagePath: args?.imagePath ?? "",
  }));
}

function mockOcrError(msg = "sidecar crashed") {
  vi.mocked(invoke).mockRejectedValue(new Error(msg));
}

describe("useOcrStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("1. startBatchOcr — queues all non-skipped pages, sets state=running", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3, 4, 5].map(makePage));

    mockOcrSuccess();
    const ocr = useOcrStore();
    ocr.startBatchOcr();

    // Immediately after call, state is running and total is 5
    expect(ocr.batchState).toBe("running");
    expect(ocr.batchProgress.total).toBe(5);
  });

  it("2. successful OCR page — increments current, sets ocrStatus=done", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    mockOcrSuccess("Sample text", 92);

    const ocr = useOcrStore();
    ocr.startBatchOcr();

    // Wait for async processing to complete
    await vi.waitUntil(() => ocr.batchState === "completed", { timeout: 1000 });

    expect(ocr.batchProgress.current).toBe(1);
    expect(capture.capturedPages[0].ocrStatus).toBe("done");
    expect(ocr.pageResults.get(1)?.text).toBe("Sample text");
    expect(ocr.pageResults.get(1)?.confidence).toBe(92);
  });

  it("3. failed OCR page — increments errors, sets ocrStatus=error, batch continues", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1), makePage(2));
    // First call fails, second succeeds
    vi.mocked(invoke)
      .mockRejectedValueOnce(new Error("timeout"))
      .mockResolvedValueOnce({ pageNumber: 2, text: "page 2", confidence: 88 });

    const ocr = useOcrStore();
    ocr.startBatchOcr();

    await vi.waitUntil(() => ocr.batchState === "completed", { timeout: 1000 });

    expect(ocr.batchProgress.errors).toBe(1);
    expect(ocr.batchProgress.current).toBe(2);
    expect(capture.capturedPages[0].ocrStatus).toBe("error");
    expect(capture.capturedPages[1].ocrStatus).toBe("done");
  });

  it("4. pauseBatchOcr — sets state=paused", () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3].map(makePage));
    // Hang invoke so the batch doesn't drain
    vi.mocked(invoke).mockReturnValue(new Promise(() => {}));

    const ocr = useOcrStore();
    ocr.startBatchOcr();
    expect(ocr.batchState).toBe("running");

    ocr.pauseBatchOcr();
    expect(ocr.batchState).toBe("paused");
  });

  it("5. resumeBatchOcr — transitions paused→running, continues processing", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1), makePage(2));
    // Hang first call to allow pause, then succeed on resume
    let resolveFirst!: (v: any) => void;
    vi.mocked(invoke)
      .mockReturnValueOnce(new Promise((res) => { resolveFirst = res; }))
      .mockResolvedValue({ pageNumber: 2, text: "p2", confidence: 90 });

    const ocr = useOcrStore();
    ocr.startBatchOcr();
    ocr.pauseBatchOcr();
    expect(ocr.batchState).toBe("paused");

    // Resolve the first page and resume
    resolveFirst({ pageNumber: 1, text: "p1", confidence: 90 });
    ocr.resumeBatchOcr();

    // Give the async loop a tick to detect paused state during _processNext
    await vi.waitUntil(() => ocr.batchState === "running" || ocr.batchState === "completed", { timeout: 1000 });
    expect(["running", "completed"]).toContain(ocr.batchState);
  });

  it("6. stopBatchOcr — remaining pages stay pending, state=stopped", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3].map(makePage));
    // Hang invoke permanently
    vi.mocked(invoke).mockReturnValue(new Promise(() => {}));

    const ocr = useOcrStore();
    ocr.startBatchOcr();
    ocr.stopBatchOcr();

    expect(ocr.batchState).toBe("stopped");
    // Queue is cleared on stop
    expect(ocr.ocrQueue.length).toBe(0);
    // Pages that weren't processed remain pending
    const pendingPages = capture.capturedPages.filter((p) => p.ocrStatus === "pending");
    expect(pendingPages.length).toBeGreaterThan(0);
  });

  it("7. blank and excluded pages are auto-skipped with ocrStatus=skipped", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(
      makePage(1, { pageType: "text" }),
      makePage(2, { pageType: "blank" }),
      makePage(3, { pageType: "illustration" }),
      makePage(4, { pageType: "excluded" }),
      makePage(5, { pageType: "text" }),
    );
    mockOcrSuccess();

    const ocr = useOcrStore();
    ocr.startBatchOcr();

    // Only pages 1 and 5 should be in the queue (blank/illustration/excluded skipped)
    expect(ocr.batchProgress.total).toBe(2);
    expect(capture.capturedPages[1].ocrStatus).toBe("skipped");
    expect(capture.capturedPages[2].ocrStatus).toBe("skipped");
    expect(capture.capturedPages[3].ocrStatus).toBe("skipped");

    await vi.waitUntil(() => ocr.batchState === "completed", { timeout: 1000 });
    expect(capture.capturedPages[0].ocrStatus).toBe("done");
    expect(capture.capturedPages[4].ocrStatus).toBe("done");
  });

  it("8. autoOcrAfterCapture=false — onPageCaptured does nothing", () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    const settings = useSettingsStore();
    settings.setAutoOcr(false);

    const ocr = useOcrStore();
    ocr.onPageCaptured(0);

    expect(ocr.batchState).toBe("idle");
    expect(ocr.ocrQueue.length).toBe(0);
  });

  it("9. autoOcrAfterCapture=true — onPageCaptured queues and starts OCR", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    const settings = useSettingsStore();
    settings.setAutoOcr(true);
    mockOcrSuccess();

    const ocr = useOcrStore();
    ocr.onPageCaptured(0);

    expect(["running", "completed"]).toContain(ocr.batchState);
    await vi.waitUntil(() => ocr.batchState === "completed", { timeout: 1000 });
    expect(capture.capturedPages[0].ocrStatus).toBe("done");
  });
});
