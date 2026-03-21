<script setup lang="ts">
import { computed } from "vue";
import { useChaptersStore } from "@/stores/chapters";

const props = defineProps<{ pageIndex: number }>();

const chapters = useChaptersStore();

// A fixed palette of colours for up to 12 chapters
const PALETTE = [
  "#4a9eff", "#ff7043", "#66bb6a", "#ab47bc", "#ffb300",
  "#26c6da", "#ef5350", "#26a69a", "#7e57c2", "#d4e157",
  "#ff8a65", "#42a5f5",
];

interface Segment {
  start: number;
  end: number;
  color: string;
  label: string;
  chapterIndex: number;
}

const segments = computed<Segment[]>(() => {
  const result: Segment[] = [];
  for (const ch of chapters.sortedChapters) {
    for (const src of ch.sources) {
      if (src.pageIndex === props.pageIndex) {
        result.push({
          start: src.start,
          end: src.end,
          color: PALETTE[ch.chapterIndex % PALETTE.length],
          label: `Ch ${ch.chapterIndex + 1}`,
          chapterIndex: ch.chapterIndex,
        });
      }
    }
  }
  // Sort by start fraction
  result.sort((a, b) => a.start - b.start);
  return result;
});
</script>

<template>
  <div class="coverage-bar" v-if="segments.length > 0" title="Chapter coverage">
    <div
      v-for="(seg, i) in segments"
      :key="i"
      class="coverage-segment"
      :style="{
        left: `${seg.start * 100}%`,
        width: `${(seg.end - seg.start) * 100}%`,
        background: seg.color,
      }"
      :title="`${seg.label}: ${(seg.start * 100).toFixed(0)}%–${(seg.end * 100).toFixed(0)}%`"
    >
      <span class="seg-label">{{ seg.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.coverage-bar {
  position: relative;
  height: 10px;
  background: #1a1a1a;
  border-radius: 2px;
  overflow: hidden;
  margin-top: 2px;
}

.coverage-segment {
  position: absolute;
  top: 0;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.seg-label {
  font-size: 0.55rem;
  color: rgba(255, 255, 255, 0.85);
  white-space: nowrap;
  pointer-events: none;
}
</style>
