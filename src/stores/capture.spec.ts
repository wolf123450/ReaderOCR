import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import {
  useCaptureStore,
  clampRegion,
  formatPageFilename,
  isValidTransition,
  type WindowInfo,
} from "@/stores/capture";

const testWindow: WindowInfo = {
  handle: 12345,
  title: "Test Window",
  x: 100,
  y: 100,
  width: 800,
  height: 600,
  process_name: "test.exe",
};

describe("clampRegion", () => {
  it("clamps region that exceeds window bounds", () => {
    const result = clampRegion(
      { x: 50, y: 50, width: 900, height: 700 },
      testWindow
    );
    expect(result.x).toBe(100);
    expect(result.y).toBe(100);
    expect(result.width).toBe(800);
    expect(result.height).toBe(600);
  });

  it("enforces minimum size of 50x50", () => {
    const result = clampRegion(
      { x: 200, y: 200, width: 10, height: 10 },
      testWindow
    );
    expect(result.width).toBe(50);
    expect(result.height).toBe(50);
  });

  it("keeps valid region unchanged", () => {
    const result = clampRegion(
      { x: 200, y: 200, width: 400, height: 300 },
      testWindow
    );
    expect(result).toEqual({ x: 200, y: 200, width: 400, height: 300 });
  });

  it("clamps x+width to not exceed window right edge", () => {
    const result = clampRegion(
      { x: 800, y: 200, width: 200, height: 100 },
      testWindow
    );
    // x should be clamped so x + width <= 100 + 800 = 900
    expect(result.x + result.width).toBeLessThanOrEqual(
      testWindow.x + testWindow.width
    );
  });

  it("clamps y+height to not exceed window bottom edge", () => {
    const result = clampRegion(
      { x: 200, y: 600, width: 100, height: 200 },
      testWindow
    );
    expect(result.y + result.height).toBeLessThanOrEqual(
      testWindow.y + testWindow.height
    );
  });

  it("always produces a region within window bounds", () => {
    // Fuzz: try various extreme inputs
    const extremes = [
      { x: -100, y: -100, width: 2000, height: 2000 },
      { x: 0, y: 0, width: 1, height: 1 },
      { x: 9999, y: 9999, width: 500, height: 500 },
    ];
    for (const input of extremes) {
      const r = clampRegion(input, testWindow);
      expect(r.x).toBeGreaterThanOrEqual(testWindow.x);
      expect(r.y).toBeGreaterThanOrEqual(testWindow.y);
      expect(r.x + r.width).toBeLessThanOrEqual(
        testWindow.x + testWindow.width
      );
      expect(r.y + r.height).toBeLessThanOrEqual(
        testWindow.y + testWindow.height
      );
      expect(r.width).toBeGreaterThanOrEqual(50);
      expect(r.height).toBeGreaterThanOrEqual(50);
    }
  });
});

describe("useCaptureStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("starts with no selection", () => {
    const store = useCaptureStore();
    expect(store.selectedWindow).toBeNull();
    expect(store.region).toBeNull();
    expect(store.hasSelection).toBe(false);
  });

  it("sets windows list", () => {
    const store = useCaptureStore();
    store.setWindows([testWindow]);
    expect(store.windows).toHaveLength(1);
    expect(store.windows[0].title).toBe("Test Window");
  });

  it("selects a window and resets region", () => {
    const store = useCaptureStore();
    store.setWindows([testWindow]);
    store.selectWindow(testWindow);
    expect(store.selectedWindow).toEqual(testWindow);
    expect(store.region).toBeNull();
  });

  it("sets region with clamping", () => {
    const store = useCaptureStore();
    store.selectWindow(testWindow);
    store.setRegion({ x: 50, y: 50, width: 900, height: 700 });
    expect(store.region).not.toBeNull();
    expect(store.region!.x).toBe(100);
    expect(store.region!.width).toBe(800);
    expect(store.hasSelection).toBe(true);
  });

  it("ignores setRegion when no window selected", () => {
    const store = useCaptureStore();
    store.setRegion({ x: 200, y: 200, width: 400, height: 300 });
    expect(store.region).toBeNull();
  });

  it("clears selection", () => {
    const store = useCaptureStore();
    store.selectWindow(testWindow);
    store.setRegion({ x: 200, y: 200, width: 400, height: 300 });
    store.clearSelection();
    expect(store.selectedWindow).toBeNull();
    expect(store.region).toBeNull();
    expect(store.hasSelection).toBe(false);
  });

  it("resets region when selecting a different window", () => {
    const store = useCaptureStore();
    store.selectWindow(testWindow);
    store.setRegion({ x: 200, y: 200, width: 400, height: 300 });
    expect(store.region).not.toBeNull();

    const otherWindow = { ...testWindow, handle: 99999, title: "Other" };
    store.selectWindow(otherWindow);
    expect(store.region).toBeNull();
  });
});

describe("formatPageFilename", () => {
  it("pads page numbers to 3 digits", () => {
    expect(formatPageFilename("page", 1)).toBe("page-001.png");
    expect(formatPageFilename("page", 42)).toBe("page-042.png");
    expect(formatPageFilename("page", 999)).toBe("page-999.png");
  });

  it("handles custom prefixes", () => {
    expect(formatPageFilename("book", 5)).toBe("book-005.png");
  });

  it("handles page numbers beyond 999", () => {
    expect(formatPageFilename("page", 1234)).toBe("page-1234.png");
  });
});

describe("isValidTransition", () => {
  it("allows idle → capturing", () => {
    expect(isValidTransition("idle", "capturing")).toBe(true);
  });

  it("allows capturing → paused", () => {
    expect(isValidTransition("capturing", "paused")).toBe(true);
  });

  it("allows capturing → stopped", () => {
    expect(isValidTransition("capturing", "stopped")).toBe(true);
  });

  it("allows capturing → completed", () => {
    expect(isValidTransition("capturing", "completed")).toBe(true);
  });

  it("allows paused → capturing (resume)", () => {
    expect(isValidTransition("paused", "capturing")).toBe(true);
  });

  it("allows paused → stopped", () => {
    expect(isValidTransition("paused", "stopped")).toBe(true);
  });

  it("rejects idle → paused", () => {
    expect(isValidTransition("idle", "paused")).toBe(false);
  });

  it("allows stopped → capturing (resume)", () => {
    expect(isValidTransition("stopped", "capturing")).toBe(true);
  });

  it("allows stopped → idle (reset)", () => {
    expect(isValidTransition("stopped", "idle")).toBe(true);
  });

  it("allows completed → idle (reset)", () => {
    expect(isValidTransition("completed", "idle")).toBe(true);
  });
});

describe("batch capture state", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("starts in idle state", () => {
    const store = useCaptureStore();
    expect(store.batchState).toBe("idle");
    expect(store.pagesCaptured).toBe(0);
    expect(store.isCapturing).toBe(false);
  });

  it("transitions through capture lifecycle", () => {
    const store = useCaptureStore();
    expect(store.transitionTo("capturing")).toBe(true);
    expect(store.batchState).toBe("capturing");
    expect(store.isCapturing).toBe(true);

    expect(store.transitionTo("paused")).toBe(true);
    expect(store.batchState).toBe("paused");
    expect(store.isPaused).toBe(true);

    expect(store.transitionTo("capturing")).toBe(true);
    expect(store.batchState).toBe("capturing");

    expect(store.transitionTo("stopped")).toBe(true);
    expect(store.batchState).toBe("stopped");
  });

  it("rejects invalid transitions", () => {
    const store = useCaptureStore();
    expect(store.transitionTo("paused")).toBe(false);
    expect(store.batchState).toBe("idle");
  });

  it("tracks captured pages", () => {
    const store = useCaptureStore();
    store.transitionTo("capturing");

    for (let i = 1; i <= 5; i++) {
      store.recordCapture({
        pageNumber: i,
        totalPages: null,
        imagePath: `test/page-${String(i).padStart(3, "0")}.png`,
        status: "captured",
      });
    }

    expect(store.pagesCaptured).toBe(5);
    expect(store.captureHistory).toHaveLength(5);
  });

  it("resets counters when transitioning to idle", () => {
    const store = useCaptureStore();
    store.transitionTo("capturing");
    store.recordCapture({
      pageNumber: 1,
      totalPages: null,
      imagePath: "test/page-001.png",
      status: "captured",
    });
    store.transitionTo("stopped");
    store.transitionTo("idle");

    expect(store.pagesCaptured).toBe(0);
    expect(store.captureHistory).toHaveLength(0);
  });

  it("enforces minimum delay", () => {
    const store = useCaptureStore();
    store.setBatchConfig({ delayBetweenMs: 50 });
    expect(store.batchConfig.delayBetweenMs).toBe(200);
  });

  it("allows resume from stopped (stopped → capturing)", () => {
    const store = useCaptureStore();
    store.transitionTo("capturing");
    store.recordCapture({
      pageNumber: 1,
      totalPages: null,
      imagePath: "test/page-001.png",
      status: "captured",
    });
    store.transitionTo("stopped");
    expect(store.pagesCaptured).toBe(1);
    // Resume should preserve captured pages
    expect(store.transitionTo("capturing")).toBe(true);
    expect(store.batchState).toBe("capturing");
    expect(store.pagesCaptured).toBe(1);
  });

  it("tracks capturedPages with capture type", () => {
    const store = useCaptureStore();
    store.transitionTo("capturing");
    store.setNextCaptureType("cover");
    store.recordCapture({
      pageNumber: 1,
      totalPages: null,
      imagePath: "test/page-001.png",
      status: "captured",
    });
    expect(store.capturedPages).toHaveLength(1);
    expect(store.capturedPages[0].captureType).toBe("cover");
    expect(store.capturedPages[0].status).toBe("ok");

    store.setNextCaptureType("page");
    store.recordCapture({
      pageNumber: 2,
      totalPages: null,
      imagePath: "test/page-002.png",
      status: "captured",
    });
    expect(store.capturedPages).toHaveLength(2);
    expect(store.capturedPages[1].captureType).toBe("page");
  });

  it("records error captures in capturedPages", () => {
    const store = useCaptureStore();
    store.transitionTo("capturing");
    store.recordCapture({
      pageNumber: 1,
      totalPages: null,
      imagePath: "test/page-001.png",
      status: "error",
      errorMessage: "Capture failed",
    });
    expect(store.capturedPages).toHaveLength(1);
    expect(store.capturedPages[0].status).toBe("error");
    expect(store.capturedPages[0].errorMessage).toBe("Capture failed");
  });
});

describe("project settings", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("computes effectiveOutputDir with book name", () => {
    const store = useCaptureStore();
    store.setBatchConfig({ outputDir: "C:\\captures" });
    store.setBookName("My Book");
    expect(store.effectiveOutputDir).toBe("C:\\captures\\My Book");
  });

  it("returns base dir when book name is empty", () => {
    const store = useCaptureStore();
    store.setBatchConfig({ outputDir: "C:\\captures" });
    store.setBookName("");
    expect(store.effectiveOutputDir).toBe("C:\\captures");
  });

  it("returns empty when outputDir is empty", () => {
    const store = useCaptureStore();
    store.setBookName("My Book");
    expect(store.effectiveOutputDir).toBe("");
  });

  it("sets and reads capture type", () => {
    const store = useCaptureStore();
    expect(store.nextCaptureType).toBe("page");
    store.setNextCaptureType("cover");
    expect(store.nextCaptureType).toBe("cover");
    store.setNextCaptureType("illustration");
    expect(store.nextCaptureType).toBe("illustration");
  });

  it("restorePagesCaptured sets the pagesCaptured count", () => {
    const store = useCaptureStore();
    expect(store.pagesCaptured).toBe(0);
    store.restorePagesCaptured(42);
    expect(store.pagesCaptured).toBe(42);
  });

  it("restorePagesCaptured is overwritten on reset", () => {
    const store = useCaptureStore();
    store.restorePagesCaptured(10);
    // Simulate a full session: idle → capturing → idle
    store.transitionTo("capturing");
    store.transitionTo("stopped");
    store.transitionTo("idle");
    expect(store.pagesCaptured).toBe(0);
  });
});
