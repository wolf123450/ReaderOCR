import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useSessionStore, buildReport, type DiskPageEntry } from "@/stores/session";
import { useCaptureStore, type CapturedPage } from "@/stores/capture";

// Mock Tauri invoke so we can control the scan result
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

function makeDiskEntry(n: number): DiskPageEntry {
  return {
    pageNumber: n,
    filePath: `book/page-${String(n).padStart(3, "0")}.png`,
    fileSizeBytes: 50000,
    modifiedAt: 1700000000,
  };
}

describe("buildReport (pure reconciliation logic)", () => {
  it("1. perfect match → all fields empty except matched", () => {
    const pages = [1, 2, 3].map(makePage);
    const disk = [1, 2, 3].map(makeDiskEntry);
    const report = buildReport(pages, disk);
    expect(report.missingFromDisk).toHaveLength(0);
    expect(report.extraOnDisk).toHaveLength(0);
    expect(report.matched).toEqual([1, 2, 3]);
  });

  it("2. JSON has 5 pages, disk only has 1-3 → missingFromDisk = [4, 5]", () => {
    const pages = [1, 2, 3, 4, 5].map(makePage);
    const disk = [1, 2, 3].map(makeDiskEntry);
    const report = buildReport(pages, disk);
    expect(report.missingFromDisk.sort()).toEqual([4, 5]);
    expect(report.extraOnDisk).toHaveLength(0);
  });

  it("3. JSON has pages 1-3, disk has pages 1-5 → extraOnDisk = [4, 5]", () => {
    const pages = [1, 2, 3].map(makePage);
    const disk = [1, 2, 3, 4, 5].map(makeDiskEntry);
    const report = buildReport(pages, disk);
    expect(report.extraOnDisk.sort()).toEqual([4, 5]);
    expect(report.missingFromDisk).toHaveLength(0);
  });
});

describe("useSessionStore — applyReconcile", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("4. removeFromSession removes those page numbers", () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3, 4, 5].map(makePage));

    const session = useSessionStore();
    session.lastScanResult = { found: [1, 2, 3].map(makeDiskEntry) };
    session.applyReconcile({ removeFromSession: [4, 5], markNeedsRecapture: [], adoptFromDisk: [] });
    expect(capture.capturedPages.map((p) => p.pageNumber)).toEqual([1, 2, 3]);
  });

  it("5. adoptFromDisk adds 2 new pages with status ok", () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3].map(makePage));

    const session = useSessionStore();
    session.lastScanResult = { found: [1, 2, 3, 4, 5].map(makeDiskEntry) };
    session.applyReconcile({ removeFromSession: [], markNeedsRecapture: [], adoptFromDisk: [4, 5] });
    expect(capture.capturedPages).toHaveLength(5);
    const p4 = capture.capturedPages.find((p) => p.pageNumber === 4);
    expect(p4?.captureStatus).toBe("ok");
  });

  it("6. cancel (clearReconcile) leaves session unchanged", () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3].map(makePage));

    const session = useSessionStore();
    session.reconcileReport = { missingFromDisk: [3], extraOnDisk: [], matched: [1, 2] };
    session.clearReconcile();
    expect(session.reconcileReport).toBeNull();
    expect(capture.capturedPages).toHaveLength(3);
  });

  it("applyReconcile — markNeedsRecapture sets captureStatus", () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3].map(makePage));

    const session = useSessionStore();
    session.lastScanResult = { found: [1, 2].map(makeDiskEntry) };
    session.applyReconcile({ removeFromSession: [], markNeedsRecapture: [3], adoptFromDisk: [] });
    const p3 = capture.capturedPages.find((p) => p.pageNumber === 3);
    expect(p3?.captureStatus).toBe("needs_recapture");
  });
});

describe("useSessionStore — reconcileWithDisk (mocked invoke)", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("invokes scan_session_dir and returns reconcile report", async () => {
    const capture = useCaptureStore();
    capture.capturedPages.push(...[1, 2, 3, 4, 5].map(makePage));
    vi.mocked(invoke).mockResolvedValue({ found: [1, 2, 3].map(makeDiskEntry) });

    const session = useSessionStore();
    const report = await session.reconcileWithDisk("C:\\Books\\MyBook", "page");
    expect(report.missingFromDisk.sort()).toEqual([4, 5]);
    expect(report.extraOnDisk).toHaveLength(0);
  });
});
