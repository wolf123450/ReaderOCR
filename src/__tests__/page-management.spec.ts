// Step 41: Page management store action tests
import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useCaptureStore, type CapturedPage } from "@/stores/capture";

function makePages(ids: string[]): CapturedPage[] {
  return ids.map((id, i) => ({
    pageNumber: i + 1,
    imagePath: `book/${id}.png`,
    captureType: "page" as const,
    timestamp: Date.now(),
    captureStatus: "ok" as const,
    pageType: "text" as const,
    ocrStatus: "pending" as const,
  }));
}

describe("capture store — Step 41 page management", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("1. reorderPages(2,0) on [A,B,C,D] moves C to front; pageNumbers = 1,2,3,4", () => {
    const store = useCaptureStore();
    store.capturedPages.push(...makePages(["A", "B", "C", "D"]));
    store.reorderPages(2, 0);
    expect(store.capturedPages.map((p) => p.imagePath.replace("book/", "").replace(".png", ""))).toEqual(
      ["C", "A", "B", "D"]
    );
    expect(store.capturedPages.map((p) => p.pageNumber)).toEqual([1, 2, 3, 4]);
  });

  it("2. deletePage(1) on [A,B,C] → [A,C]; pageNumbers = 1,2", () => {
    const store = useCaptureStore();
    store.capturedPages.push(...makePages(["A", "B", "C"]));
    store.deletePage(1);
    expect(store.capturedPages).toHaveLength(2);
    const labels = store.capturedPages.map(
      (p) => p.imagePath.replace("book/", "").replace(".png", "")
    );
    expect(labels).toEqual(["A", "C"]);
    expect(store.capturedPages.map((p) => p.pageNumber)).toEqual([1, 2]);
  });

  it("3. insertPageAt(1, new) on [A,B,C] → [A,new,B,C]; pageNumbers = 1,2,3,4", () => {
    const store = useCaptureStore();
    store.capturedPages.push(...makePages(["A", "B", "C"]));
    store.insertPageAt(1, makePages(["X"])[0]);
    expect(store.capturedPages).toHaveLength(4);
    const labels = store.capturedPages.map(
      (p) => p.imagePath.replace("book/", "").replace(".png", "")
    );
    expect(labels).toEqual(["A", "X", "B", "C"]);
    expect(store.capturedPages.map((p) => p.pageNumber)).toEqual([1, 2, 3, 4]);
  });

  it("4. reorder + delete + renumber → gapless 1-based numbering", () => {
    const store = useCaptureStore();
    store.capturedPages.push(...makePages(["A", "B", "C", "D", "E"]));
    store.reorderPages(4, 0); // → [E,A,B,C,D]
    store.deletePage(2);       // → [E,A,C,D]
    expect(store.capturedPages.map((p) => p.pageNumber)).toEqual([1, 2, 3, 4]);
  });

  it("5. renumber() is idempotent", () => {
    const store = useCaptureStore();
    store.capturedPages.push(...makePages(["A", "B", "C"]));
    store.renumber();
    const first = store.capturedPages.map((p) => p.pageNumber);
    store.renumber();
    expect(store.capturedPages.map((p) => p.pageNumber)).toEqual(first);
  });

  it("reorderPages out of range: no change", () => {
    const store = useCaptureStore();
    store.capturedPages.push(...makePages(["A", "B"]));
    store.reorderPages(-1, 0);
    store.reorderPages(0, 5);
    const labels = store.capturedPages.map(
      (p) => p.imagePath.replace("book/", "").replace(".png", "")
    );
    expect(labels).toEqual(["A", "B"]);
  });

  it("deletePage out of range: no change, no throw", () => {
    const store = useCaptureStore();
    store.capturedPages.push(...makePages(["A", "B"]));
    expect(() => store.deletePage(-1)).not.toThrow();
    expect(() => store.deletePage(10)).not.toThrow();
    expect(store.capturedPages).toHaveLength(2);
  });
});
