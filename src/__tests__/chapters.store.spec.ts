import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useChaptersStore, type PageFraction } from "@/stores/chapters";

function makeFraction(pageIndex: number, start = 0.0, end = 1.0): PageFraction {
  return { pageIndex, start, end };
}

describe("useChaptersStore — Step 43 chapter structure", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("1. empty store: chapters = []; isValid() = true (no chapters is valid)", () => {
    const store = useChaptersStore();
    expect(store.chapters).toHaveLength(0);
    expect(store.isValid()).toBe(true);
  });

  it("2. addChapter → chapters.length = 1; chapterIndex = 0", () => {
    const store = useChaptersStore();
    const ch = store.addChapter({ title: "Introduction" });
    expect(store.chapters).toHaveLength(1);
    expect(ch.chapterIndex).toBe(0);
    expect(ch.title).toBe("Introduction");
  });

  it("3. addChapter auto-assigns gapless indices", () => {
    const store = useChaptersStore();
    store.addChapter({ title: "Front" });
    store.addChapter({ title: "Chapter 1" });
    store.addChapter({ title: "Chapter 2" });
    const indices = store.sortedChapters.map((c) => c.chapterIndex);
    expect(indices).toEqual([0, 1, 2]);
  });

  it("4. reorderChapters → chapterIndex values renumbered; sources unchanged", () => {
    const store = useChaptersStore();
    store.addChapter({ title: "A", sources: [makeFraction(0)] });
    store.addChapter({ title: "B", sources: [makeFraction(1)] });
    store.addChapter({ title: "C", sources: [makeFraction(2)] });

    // Move C (index 2) to front (index 0)
    store.reorderChapters(2, 0);

    const titles = store.sortedChapters.map((c) => c.title);
    expect(titles).toEqual(["C", "A", "B"]);
    // Renumbered 0,1,2
    expect(store.sortedChapters.map((c) => c.chapterIndex)).toEqual([0, 1, 2]);
    // Sources are preserved on the "C" chapter
    expect(store.sortedChapters[0].sources[0].pageIndex).toBe(2);
  });

  it("5. overlap validation: two segments overlapping on same page → isValid() = false, error contains 'overlap'", () => {
    const store = useChaptersStore();
    store.addChapter({
      title: "Ch A",
      sources: [makeFraction(5, 0.0, 0.7)],
    });
    store.addChapter({
      title: "Ch B",
      sources: [makeFraction(5, 0.5, 1.0)],
    });

    expect(store.isValid()).toBe(false);
    const errors = store.getValidationErrors();
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0].toLowerCase()).toContain("overlap");
  });

  it("6. fraction sum exactly 1.0 (0.3+0.4+0.3) across three chapters → valid", () => {
    const store = useChaptersStore();
    store.addChapter({ title: "Top", sources: [makeFraction(5, 0.0, 0.3)] });
    store.addChapter({ title: "Mid", sources: [makeFraction(5, 0.3, 0.7)] });
    store.addChapter({ title: "Bot", sources: [makeFraction(5, 0.7, 1.0)] });

    expect(store.isValid()).toBe(true);
    expect(store.getValidationErrors()).toHaveLength(0);
  });

  it("7. fraction sum over 1.0 (0.6+0.6) → isValid() = false", () => {
    const store = useChaptersStore();
    store.addChapter({ title: "Ch A", sources: [makeFraction(3, 0.0, 0.6)] });
    store.addChapter({ title: "Ch B", sources: [makeFraction(3, 0.4, 1.0)] });

    expect(store.isValid()).toBe(false);
    // The sum is 1.2, which triggers an error; overlap also triggers
    expect(store.getValidationErrors().length).toBeGreaterThan(0);
  });

  it("8. serialise → deserialise → identical ChapterSegment[]", () => {
    const store = useChaptersStore();
    store.addChapter({ title: "Front Matter", chapterType: "front_matter" });
    store.addChapter({
      title: "Chapter 1",
      sources: [makeFraction(2, 0.0, 0.5), makeFraction(3)],
    });

    const json = store.serialize();
    store.deserialize(json);

    const chapters = store.sortedChapters;
    expect(chapters).toHaveLength(2);
    expect(chapters[0].title).toBe("Front Matter");
    expect(chapters[0].chapterType).toBe("front_matter");
    expect(chapters[1].sources).toHaveLength(2);
    expect(chapters[1].sources[0]).toMatchObject({ pageIndex: 2, start: 0.0, end: 0.5 });
    expect(chapters[1].sources[1]).toMatchObject({ pageIndex: 3, start: 0.0, end: 1.0 });
  });
});
