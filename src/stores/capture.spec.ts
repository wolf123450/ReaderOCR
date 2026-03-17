import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useCaptureStore, clampRegion, type WindowInfo } from "@/stores/capture";

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
