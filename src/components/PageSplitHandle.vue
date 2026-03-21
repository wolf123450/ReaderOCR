<script setup lang="ts">
import { ref, computed } from "vue";
import { convertFileSrc } from "@tauri-apps/api/core";

const props = defineProps<{
  imagePath: string;
  fraction: number;   // 0.0–1.0 from top
  pageIndex: number;
}>();

const emit = defineEmits<{
  "update:fraction": [value: number];
}>();

const containerRef = ref<HTMLDivElement | null>(null);
const isDragging = ref(false);
const localFraction = ref(props.fraction);

const imageUrl = computed(() => convertFileSrc(props.imagePath));

function onMouseDown(e: MouseEvent) {
  e.preventDefault();
  isDragging.value = true;
  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value || !containerRef.value) return;
  const rect = containerRef.value.getBoundingClientRect();
  const relative = (e.clientY - rect.top) / rect.height;
  localFraction.value = Math.max(0.01, Math.min(0.99, relative));
}

function onMouseUp() {
  isDragging.value = false;
  window.removeEventListener("mousemove", onMouseMove);
  window.removeEventListener("mouseup", onMouseUp);
  emit("update:fraction", localFraction.value);
}

const splitPercent = computed(() => `${(localFraction.value * 100).toFixed(1)}%`);
</script>

<template>
  <div class="split-handle-container" ref="containerRef">
    <img :src="imageUrl" class="page-thumb" alt="page thumbnail" />

    <!-- Split line -->
    <div
      class="split-line"
      :style="{ top: splitPercent }"
      @mousedown="onMouseDown"
      title="Drag to adjust chapter split point"
    >
      <span class="split-label">{{ splitPercent }}</span>
    </div>
  </div>
</template>

<style scoped>
.split-handle-container {
  position: relative;
  display: inline-block;
  user-select: none;
  cursor: ns-resize;
}

.page-thumb {
  display: block;
  width: 180px;
  height: auto;
  border: 1px solid var(--border-color, #444);
  border-radius: 3px;
  pointer-events: none;
}

.split-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent, #4a9eff);
  cursor: ns-resize;
  transform: translateY(-50%);
}

.split-line::before,
.split-line::after {
  content: "";
  position: absolute;
  top: -4px;
  width: 100%;
  height: 10px;
  cursor: ns-resize;
}

.split-label {
  position: absolute;
  right: 4px;
  top: -16px;
  background: var(--accent, #4a9eff);
  color: white;
  font-size: 0.65rem;
  padding: 1px 4px;
  border-radius: 2px;
  pointer-events: none;
  white-space: nowrap;
}
</style>
