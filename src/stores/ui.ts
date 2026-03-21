import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useCaptureStore } from "@/stores/capture";

export type TopTab = "capture" | "review" | "export";
export type ReviewSubtab = "pages" | "ocr" | "review" | "edit";

export const useUiStore = defineStore("ui", () => {
  const activeTab = ref<TopTab>("capture");
  const activeReviewSubtab = ref<ReviewSubtab>("pages");
  const selectedPageIndex = ref<number | null>(null);

  // Tracks pages with OCR results; wired up by step 44 OCR workflow
  const ocrPageCount = ref(0);

  const captureStore = useCaptureStore();

  function isTabEnabled(tab: TopTab): boolean {
    if (tab === "capture") return true;
    const pageCount = captureStore.capturedPages.length;
    if (tab === "review") return pageCount > 0;
    if (tab === "export") return ocrPageCount.value > 0;
    return false;
  }

  function isSubtabEnabled(sub: ReviewSubtab): boolean {
    const pageCount = captureStore.capturedPages.length;
    if (sub === "pages") return pageCount > 0;
    if (sub === "ocr") return pageCount > 0;
    if (sub === "review") return ocrPageCount.value > 0;
    if (sub === "edit") return ocrPageCount.value > 0;
    return false;
  }

  /** Switch to tab if enabled. Returns false if the tab is gated. */
  function setTab(tab: TopTab): boolean {
    if (!isTabEnabled(tab)) return false;
    activeTab.value = tab;
    return true;
  }

  function setSubtab(sub: ReviewSubtab): void {
    activeReviewSubtab.value = sub;
  }

  /** Select a page by index; silently ignores out-of-range values. */
  function selectPage(index: number): void {
    const count = captureStore.capturedPages.length;
    if (index < 0 || index >= count) return;
    selectedPageIndex.value = index;
  }

  /** Called by OCR workflow (step 44) to update the OCR page count. */
  function setOcrPageCount(count: number): void {
    ocrPageCount.value = count;
  }

  return {
    activeTab,
    activeReviewSubtab,
    selectedPageIndex,
    ocrPageCount,
    isTabEnabled,
    isSubtabEnabled,
    setTab,
    setSubtab,
    selectPage,
    setOcrPageCount,
  };
});
