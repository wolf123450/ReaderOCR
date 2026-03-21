import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useUiStore } from "@/stores/ui";
import { useCaptureStore, type CapturedPage } from "@/stores/capture";

function makePage(n: number): CapturedPage {
  return {
    pageNumber: n,
    imagePath: `/sessions/book/page-${String(n).padStart(3, "0")}.png`,
    captureType: "page",
    timestamp: Date.now(),
    captureStatus: "ok",
    pageType: "text",
    ocrStatus: "pending",
  };
}

describe("ui store — Step 39", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("1. initial state: activeTab=capture, selectedPageIndex=null", () => {
    const ui = useUiStore();
    expect(ui.activeTab).toBe("capture");
    expect(ui.selectedPageIndex).toBeNull();
  });

  it("2. tab gating with no pages: review disabled, capture enabled", () => {
    const ui = useUiStore();
    expect(ui.isTabEnabled("capture")).toBe(true);
    expect(ui.isTabEnabled("review")).toBe(false);
  });

  it("3. tab gating with pages: review becomes enabled", () => {
    const ui = useUiStore();
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    expect(ui.isTabEnabled("review")).toBe(true);
  });

  it("4. OCR-gated subtabs and export disabled when no OCR results", () => {
    const ui = useUiStore();
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    expect(ui.isSubtabEnabled("review")).toBe(false);
    expect(ui.isSubtabEnabled("edit")).toBe(false);
    expect(ui.isTabEnabled("export")).toBe(false);
  });

  it("4b. Review and Edit subtabs enabled after OCR count set", () => {
    const ui = useUiStore();
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    ui.setOcrPageCount(1);
    expect(ui.isSubtabEnabled("review")).toBe(true);
    expect(ui.isSubtabEnabled("edit")).toBe(true);
    expect(ui.isTabEnabled("export")).toBe(true);
  });

  it("5. setTab blocked: review tab with 0 pages does not change activeTab", () => {
    const ui = useUiStore();
    const result = ui.setTab("review");
    expect(result).toBe(false);
    expect(ui.activeTab).toBe("capture");
  });

  it("6. selectPage out of range: does not change selectedPageIndex", () => {
    const ui = useUiStore();
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    ui.selectPage(-1);
    expect(ui.selectedPageIndex).toBeNull();
    ui.selectPage(5);
    expect(ui.selectedPageIndex).toBeNull();
  });

  it("7. subtab persistence: switching top tab away and back preserves activeReviewSubtab", () => {
    const ui = useUiStore();
    const capture = useCaptureStore();
    capture.capturedPages.push(makePage(1));
    ui.setTab("review");
    ui.setSubtab("ocr");
    expect(ui.activeReviewSubtab).toBe("ocr");
    ui.setTab("capture");
    ui.setTab("review");
    expect(ui.activeReviewSubtab).toBe("ocr");
  });
});
