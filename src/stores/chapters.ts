import { defineStore } from "pinia";
import { ref, computed } from "vue";

export type ChapterType =
  | "front_matter"
  | "chapter"
  | "back_matter"
  | "part"
  | "appendix";

/** A fractional region of a source page (0.0 = top, 1.0 = bottom). */
export interface PageFraction {
  pageIndex: number; // 0-based index into CapturedPage[]
  start: number;     // 0.0 = top
  end: number;       // 1.0 = bottom
}

export interface ChapterSegment {
  id: string;
  title: string;
  chapterIndex: number; // 0-based output ordering in EPUB
  sources: PageFraction[];
  chapterType: ChapterType;
}

export const useChaptersStore = defineStore("chapters", () => {
  const chapters = ref<ChapterSegment[]>([]);

  // ── CRUD ──────────────────────────────────────────────────────────

  function addChapter(
    partial?: Partial<Omit<ChapterSegment, "id" | "chapterIndex">>
  ): ChapterSegment {
    const chapter: ChapterSegment = {
      id: crypto.randomUUID(),
      title: partial?.title ?? "New Chapter",
      chapterIndex: chapters.value.length,
      sources: partial?.sources ?? [],
      chapterType: partial?.chapterType ?? "chapter",
    };
    chapters.value.push(chapter);
    return chapter;
  }

  function removeChapter(id: string): void {
    const idx = chapters.value.findIndex((c) => c.id === id);
    if (idx === -1) return;
    chapters.value.splice(idx, 1);
    _renumber();
  }

  function updateChapter(
    id: string,
    patch: Partial<Omit<ChapterSegment, "id" | "chapterIndex">>
  ): void {
    const ch = chapters.value.find((c) => c.id === id);
    if (!ch) return;
    if (patch.title !== undefined) ch.title = patch.title;
    if (patch.chapterType !== undefined) ch.chapterType = patch.chapterType;
    if (patch.sources !== undefined) ch.sources = patch.sources;
  }

  /** Reorder by chapterIndex positions; renumbers after. */
  function reorderChapters(fromIndex: number, toIndex: number): void {
    if (fromIndex === toIndex) return;
    const len = chapters.value.length;
    if (fromIndex < 0 || toIndex < 0 || fromIndex >= len || toIndex >= len) return;
    const items = [...chapters.value];
    const [moved] = items.splice(fromIndex, 1);
    items.splice(toIndex, 0, moved);
    items.forEach((ch, i) => (ch.chapterIndex = i));
    chapters.value = items;
  }

  function _renumber(): void {
    chapters.value.forEach((ch, i) => (ch.chapterIndex = i));
  }

  // ── Validation ────────────────────────────────────────────────────

  function getValidationErrors(): string[] {
    const errors: string[] = [];

    // Group fractions by pageIndex across all chapters
    const byPage = new Map<number, Array<{ start: number; end: number; title: string }>>();
    for (const ch of chapters.value) {
      for (const src of ch.sources) {
        if (!byPage.has(src.pageIndex)) byPage.set(src.pageIndex, []);
        byPage.get(src.pageIndex)!.push({ start: src.start, end: src.end, title: ch.title });
      }
    }

    for (const [pageIndex, fracs] of byPage) {
      // Check overlaps: O(n²) — chapter counts are small
      for (let i = 0; i < fracs.length; i++) {
        for (let j = i + 1; j < fracs.length; j++) {
          const a = fracs[i];
          const b = fracs[j];
          if (a.start < b.end && b.start < a.end) {
            errors.push(
              `overlap on page ${pageIndex + 1}: "${a.title}" [${a.start}–${a.end}] and "${b.title}" [${b.start}–${b.end}]`
            );
          }
        }
      }
      // Check fraction sum
      const sum = fracs.reduce((acc, f) => acc + (f.end - f.start), 0);
      if (sum > 1.0 + 1e-9) {
        errors.push(
          `page ${pageIndex + 1} fractions sum to ${sum.toFixed(3)}, exceeding 1.0`
        );
      }
    }

    return errors;
  }

  function isValid(): boolean {
    return getValidationErrors().length === 0;
  }

  // ── Serialisation ─────────────────────────────────────────────────

  function serialize(): string {
    return JSON.stringify(chapters.value);
  }

  function deserialize(json: string): void {
    const parsed: ChapterSegment[] = JSON.parse(json);
    chapters.value = parsed;
  }

  // ── Computed ──────────────────────────────────────────────────────

  /** Chapters sorted by chapterIndex for display. */
  const sortedChapters = computed(() =>
    [...chapters.value].sort((a, b) => a.chapterIndex - b.chapterIndex)
  );

  return {
    chapters,
    sortedChapters,
    addChapter,
    removeChapter,
    updateChapter,
    reorderChapters,
    getValidationErrors,
    isValid,
    serialize,
    deserialize,
  };
});
