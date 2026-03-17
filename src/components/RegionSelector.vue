<script setup lang="ts">
import { ref, computed, onUnmounted } from "vue";
import { useCaptureStore, type CaptureRegion } from "@/stores/capture";

const store = useCaptureStore();

const isDragging = ref(false);
const dragStart = ref({ x: 0, y: 0 });
const dragCurrent = ref({ x: 0, y: 0 });

const overlayRef = ref<HTMLElement | null>(null);

const drawingRegion = computed<CaptureRegion | null>(() => {
  if (!isDragging.value) return null;
  const x = Math.min(dragStart.value.x, dragCurrent.value.x);
  const y = Math.min(dragStart.value.y, dragCurrent.value.y);
  const width = Math.abs(dragCurrent.value.x - dragStart.value.x);
  const height = Math.abs(dragCurrent.value.y - dragStart.value.y);
  return { x, y, width, height };
});

const displayRegion = computed(() => store.region ?? drawingRegion.value);

const regionStyle = computed(() => {
  const r = displayRegion.value;
  if (!r || !store.selectedWindow) return null;
  // Convert absolute coords to relative to the overlay
  const win = store.selectedWindow;
  return {
    left: `${r.x - win.x}px`,
    top: `${r.y - win.y}px`,
    width: `${r.width}px`,
    height: `${r.height}px`,
  };
});

const dimensionLabel = computed(() => {
  const r = displayRegion.value;
  if (!r) return "";
  return `${r.width} × ${r.height}`;
});

function onMouseDown(e: MouseEvent) {
  if (!store.selectedWindow || !overlayRef.value) return;
  const rect = overlayRef.value.getBoundingClientRect();
  const win = store.selectedWindow;
  const x = win.x + (e.clientX - rect.left);
  const y = win.y + (e.clientY - rect.top);
  dragStart.value = { x, y };
  dragCurrent.value = { x, y };
  isDragging.value = true;
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value || !overlayRef.value || !store.selectedWindow) return;
  const rect = overlayRef.value.getBoundingClientRect();
  const win = store.selectedWindow;
  const x = win.x + (e.clientX - rect.left);
  const y = win.y + (e.clientY - rect.top);
  dragCurrent.value = { x, y };
}

function onMouseUp() {
  if (!isDragging.value) return;
  isDragging.value = false;
  const region = drawingRegion.value;
  if (region && region.width > 10 && region.height > 10) {
    store.setRegion(region);
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    isDragging.value = false;
    store.clearSelection();
  }
}

document.addEventListener("keydown", onKeyDown);
onUnmounted(() => document.removeEventListener("keydown", onKeyDown));
</script>

<template>
  <div
    v-if="store.selectedWindow"
    ref="overlayRef"
    class="region-overlay"
    :style="{
      width: store.selectedWindow.width + 'px',
      height: store.selectedWindow.height + 'px',
    }"
    @mousedown.prevent="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseUp"
  >
    <div class="overlay-bg" />

    <div v-if="displayRegion && regionStyle" class="selection-box" :style="regionStyle">
      <span class="dimension-label">{{ dimensionLabel }}</span>
    </div>

    <p v-if="!displayRegion" class="instruction">
      Click and drag to select the capture region
    </p>
  </div>
</template>

<style scoped>
.region-overlay {
  position: relative;
  cursor: crosshair;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #555;
  user-select: none;
}

.overlay-bg {
  position: absolute;
  inset: 0;
}

.selection-box {
  position: absolute;
  border: 2px solid #4a9eff;
  background: rgba(74, 158, 255, 0.15);
  pointer-events: none;
}

.dimension-label {
  position: absolute;
  bottom: -22px;
  left: 50%;
  transform: translateX(-50%);
  background: #4a9eff;
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.75rem;
  white-space: nowrap;
}

.instruction {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: rgba(255, 255, 255, 0.8);
  font-size: 1rem;
  pointer-events: none;
}
</style>
