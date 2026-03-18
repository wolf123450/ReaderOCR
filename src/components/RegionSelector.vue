<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { useCaptureStore, type CaptureRegion } from "@/stores/capture";

const store = useCaptureStore();

// Zoom / pan state
const zoom = ref(1);
const panX = ref(0);
const panY = ref(0);
const isPanning = ref(false);
const panStart = ref({ x: 0, y: 0 });
const panOrigin = ref({ x: 0, y: 0 });

const MIN_ZOOM = 0.1;
const MAX_ZOOM = 5;

// Container ref for measuring available size
const containerRef = ref<HTMLElement | null>(null);
const overlayRef = ref<HTMLElement | null>(null);

// Region drawing
const isDragging = ref(false);
const dragStart = ref({ x: 0, y: 0 });
const dragCurrent = ref({ x: 0, y: 0 });

// Loading state for preview
const previewLoading = ref(false);

// Auto-fit: calculate scale so the window image fits the container
const fitScale = computed(() => {
  if (!store.selectedWindow || !containerRef.value) return 1;
  const containerW = containerRef.value.clientWidth - 32; // padding
  const containerH = Math.min(window.innerHeight * 0.6, 600);
  const winW = store.selectedWindow.width;
  const winH = store.selectedWindow.height;
  if (winW === 0 || winH === 0) return 1;
  return Math.min(containerW / winW, containerH / winH, 1);
});

// Effective scale = fitScale * user zoom
const effectiveScale = computed(() => fitScale.value * zoom.value);

// Displayed dimensions of the overlay
const displayWidth = computed(() =>
  store.selectedWindow ? store.selectedWindow.width * effectiveScale.value : 0
);
const displayHeight = computed(() =>
  store.selectedWindow ? store.selectedWindow.height * effectiveScale.value : 0
);

// Drawing region in window-local coords
const drawingRegion = computed<CaptureRegion | null>(() => {
  if (!isDragging.value) return null;
  const x = Math.min(dragStart.value.x, dragCurrent.value.x);
  const y = Math.min(dragStart.value.y, dragCurrent.value.y);
  const width = Math.abs(dragCurrent.value.x - dragStart.value.x);
  const height = Math.abs(dragCurrent.value.y - dragStart.value.y);
  return { x, y, width, height };
});

// The region to show (committed or in-progress)
const displayRegion = computed(() => {
  if (drawingRegion.value) return drawingRegion.value;
  if (!store.region || !store.selectedWindow) return null;
  // Convert absolute to window-local
  const win = store.selectedWindow;
  return {
    x: store.region.x - win.x,
    y: store.region.y - win.y,
    width: store.region.width,
    height: store.region.height,
  };
});

// CSS for the selection box, scaled
const regionStyle = computed(() => {
  const r = displayRegion.value;
  if (!r) return null;
  const s = effectiveScale.value;
  return {
    left: `${r.x * s}px`,
    top: `${r.y * s}px`,
    width: `${r.width * s}px`,
    height: `${r.height * s}px`,
  };
});

const dimensionLabel = computed(() => {
  const r = displayRegion.value;
  if (!r) return "";
  return `${Math.round(r.width)} × ${Math.round(r.height)}`;
});

// Fetch preview screenshot when a window is selected
async function refreshPreview() {
  if (!store.selectedWindow) return;
  previewLoading.value = true;
  try {
    const win = store.selectedWindow;
    const result = await invoke<{ data_url: string; width: number; height: number }>(
      "capture_preview",
      {
        request: { x: win.x, y: win.y, width: win.width, height: win.height },
      }
    );
    store.setPreview(result.data_url);
  } catch (e) {
    console.error("Preview capture failed:", e);
    store.setPreview(null);
  } finally {
    previewLoading.value = false;
  }
}

// Refresh when window changes
watch(
  () => store.selectedWindow,
  (w) => {
    if (w) {
      zoom.value = 1;
      panX.value = 0;
      panY.value = 0;
      refreshPreview();
    }
  }
);

// Mouse → window-local coords
function toLocalCoords(e: MouseEvent): { x: number; y: number } | null {
  if (!overlayRef.value) return null;
  const rect = overlayRef.value.getBoundingClientRect();
  const s = effectiveScale.value;
  return {
    x: (e.clientX - rect.left) / s,
    y: (e.clientY - rect.top) / s,
  };
}

function onMouseDown(e: MouseEvent) {
  if (!store.selectedWindow || !overlayRef.value) return;

  // Middle-click or Ctrl+click = pan
  if (e.button === 1 || (e.button === 0 && e.ctrlKey)) {
    isPanning.value = true;
    panStart.value = { x: e.clientX, y: e.clientY };
    panOrigin.value = { x: panX.value, y: panY.value };
    return;
  }

  const local = toLocalCoords(e);
  if (!local) return;
  dragStart.value = local;
  dragCurrent.value = local;
  isDragging.value = true;
}

function onMouseMove(e: MouseEvent) {
  if (isPanning.value) {
    panX.value = panOrigin.value.x + (e.clientX - panStart.value.x);
    panY.value = panOrigin.value.y + (e.clientY - panStart.value.y);
    return;
  }
  if (!isDragging.value) return;
  const local = toLocalCoords(e);
  if (!local) return;
  dragCurrent.value = local;
}

function onMouseUp() {
  if (isPanning.value) {
    isPanning.value = false;
    return;
  }
  if (!isDragging.value) return;
  isDragging.value = false;
  const region = drawingRegion.value;
  if (region && region.width > 10 && region.height > 10 && store.selectedWindow) {
    // Convert window-local to absolute
    const win = store.selectedWindow;
    store.setRegion({
      x: region.x + win.x,
      y: region.y + win.y,
      width: region.width,
      height: region.height,
    });
  }
}

function onWheel(e: WheelEvent) {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  zoom.value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom.value * delta));
}

function zoomIn() {
  zoom.value = Math.min(MAX_ZOOM, zoom.value * 1.25);
}
function zoomOut() {
  zoom.value = Math.max(MIN_ZOOM, zoom.value / 1.25);
}
function zoomFit() {
  zoom.value = 1;
  panX.value = 0;
  panY.value = 0;
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
  <div v-if="store.selectedWindow" ref="containerRef" class="region-container">
    <div class="toolbar">
      <button class="tool-btn" title="Zoom in" @click="zoomIn">+</button>
      <button class="tool-btn" title="Zoom out" @click="zoomOut">−</button>
      <button class="tool-btn" title="Fit to view" @click="zoomFit">⊡</button>
      <span class="zoom-label">{{ Math.round(zoom * fitScale * 100) }}%</span>
      <button class="tool-btn refresh" title="Refresh preview" @click="refreshPreview">↻</button>
      <span class="hint">Drag to select · Ctrl+drag or middle-click to pan · Scroll to zoom</span>
    </div>

    <div class="viewport" @wheel.prevent="onWheel">
      <div
        class="pan-layer"
        :style="{ transform: `translate(${panX}px, ${panY}px)` }"
      >
        <div
          ref="overlayRef"
          class="region-overlay"
          :style="{
            width: displayWidth + 'px',
            height: displayHeight + 'px',
          }"
          @mousedown.prevent="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @mouseleave="onMouseUp"
        >
          <img
            v-if="store.previewDataUrl"
            :src="store.previewDataUrl"
            class="preview-image"
            draggable="false"
          />
          <div v-else-if="previewLoading" class="loading-overlay">
            Capturing preview…
          </div>
          <div v-else class="loading-overlay">
            No preview available
          </div>

          <div v-if="displayRegion && regionStyle" class="selection-box" :style="regionStyle">
            <span class="dimension-label">{{ dimensionLabel }}</span>
          </div>

          <p v-if="!displayRegion && !isDragging" class="instruction">
            Click and drag to select the capture region
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.region-container {
  margin-top: 0.75rem;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.4rem;
}

.tool-btn {
  width: 28px;
  height: 28px;
  background: #333;
  color: #ccc;
  border: 1px solid #555;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tool-btn:hover {
  background: #444;
  color: #fff;
}
.tool-btn.refresh {
  margin-left: 0.25rem;
}

.zoom-label {
  font-size: 0.8rem;
  color: #888;
  min-width: 3em;
  text-align: center;
}

.hint {
  font-size: 0.75rem;
  color: #666;
  margin-left: auto;
}

.viewport {
  overflow: hidden;
  border: 1px solid #555;
  border-radius: 6px;
  background: #111;
  max-height: 65vh;
}

.pan-layer {
  display: inline-block;
}

.region-overlay {
  position: relative;
  cursor: crosshair;
  user-select: none;
  overflow: hidden;
}

.preview-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: fill;
  pointer-events: none;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  background: rgba(0, 0, 0, 0.4);
  font-size: 0.9rem;
}

.selection-box {
  position: absolute;
  border: 2px solid #4a9eff;
  background: rgba(74, 158, 255, 0.15);
  pointer-events: none;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.45);
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
  color: rgba(255, 255, 255, 0.6);
  font-size: 1rem;
  pointer-events: none;
  text-align: center;
}
</style>
