<script setup lang="ts">
import { computed, ref } from "vue";
import { convertFileSrc } from "@tauri-apps/api/core";
import { useCaptureStore } from "@/stores/capture";
import { useUiStore } from "@/stores/ui";

const capture = useCaptureStore();
const ui = useUiStore();

const dragIndex = ref<number | null>(null);
const dragOverIndex = ref<number | null>(null);

const pages = computed(() => capture.capturedPages);

function thumbSrc(imagePath: string): string {
  try {
    return convertFileSrc(imagePath);
  } catch {
    return "";
  }
}

function statusIcon(status: string): string {
  if (status === "ok") return "✅";
  if (status === "needs_recapture") return "⚠";
  if (status === "missing") return "❌";
  if (status === "placeholder") return "◻";
  return "";
}

function ocrIcon(status: string): string {
  if (status === "done") return "🔤";
  if (status === "pending" || status === "running") return "⏳";
  return "";
}

function pageTypeBadge(type: string): { icon: string; label: string } | null {
  switch (type) {
    case "cover": return { icon: "📕", label: "cover" };
    case "illustration": return { icon: "🖼", label: "img" };
    case "toc": return { icon: "📋", label: "toc" };
    case "license": return { icon: "⚖", label: "lic" };
    case "blank": return { icon: "◻", label: "blank" };
    case "chapter_start": return { icon: "📖", label: "ch" };
    case "excluded": return { icon: "🚫", label: "skip" };
    default: return null;
  }
}

// --- Drag-and-drop (native HTML5) ---
function onDragStart(index: number, e: DragEvent) {
  dragIndex.value = index;
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = "move";
  }
}

function onDragOver(index: number, e: DragEvent) {
  e.preventDefault();
  if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  dragOverIndex.value = index;
}

function onDrop(index: number) {
  if (dragIndex.value !== null && dragIndex.value !== index) {
    capture.reorderPages(dragIndex.value, index);
    // Keep the same page selected after reorder
    if (ui.selectedPageIndex !== null) {
      ui.selectPage(index);
    }
  }
  dragIndex.value = null;
  dragOverIndex.value = null;
}

function onDragEnd() {
  dragIndex.value = null;
  dragOverIndex.value = null;
}

// --- Context menu ---
const contextMenu = ref<{ x: number; y: number; index: number } | null>(null);

function onRightClick(index: number, e: MouseEvent) {
  e.preventDefault();
  contextMenu.value = { x: e.clientX, y: e.clientY, index };
}

function closeContextMenu() {
  contextMenu.value = null;
}

function ctxMarkRecapture() {
  if (contextMenu.value) {
    capture.setCaptureStatus(contextMenu.value.index, "needs_recapture");
  }
  closeContextMenu();
}

function ctxDelete() {
  if (contextMenu.value) {
    const idx = contextMenu.value.index;
    if (ui.selectedPageIndex === idx) ui.selectedPageIndex = null;
    capture.deletePage(idx);
  }
  closeContextMenu();
}

const emit = defineEmits<{
  (e: "insertBefore", index: number): void;
  (e: "insertAfter", index: number): void;
}>();

function ctxInsertBefore() {
  if (contextMenu.value) emit("insertBefore", contextMenu.value.index);
  closeContextMenu();
}

function ctxInsertAfter() {
  if (contextMenu.value) emit("insertAfter", contextMenu.value.index);
  closeContextMenu();
}
</script>

<template>
  <div class="filmstrip-sidebar" @click="closeContextMenu">
    <div class="filmstrip-list">
      <div
        v-for="(page, idx) in pages"
        :key="page.pageNumber"
        draggable="true"
        :class="[
          'filmstrip-card',
          {
            selected: ui.selectedPageIndex === idx,
            excluded: page.pageType === 'excluded',
            'drag-over': dragOverIndex === idx,
          },
        ]"
        @click.stop="ui.selectPage(idx)"
        @contextmenu="onRightClick(idx, $event)"
        @dragstart="onDragStart(idx, $event)"
        @dragover="onDragOver(idx, $event)"
        @drop="onDrop(idx)"
        @dragend="onDragEnd"
      >
        <!-- Thumbnail -->
        <div class="thumb-img-wrap">
          <img
            v-if="thumbSrc(page.imagePath)"
            :src="thumbSrc(page.imagePath)"
            class="thumb-img"
            :alt="`Page ${page.pageNumber}`"
            loading="lazy"
          />
          <div v-else class="thumb-placeholder" />
        </div>

        <!-- Footer row -->
        <div class="thumb-footer">
          <span class="page-num">{{ page.pageNumber }}</span>
          <span class="status-icon" :title="page.captureStatus">{{ statusIcon(page.captureStatus) }}</span>
          <span class="ocr-icon" :title="page.ocrStatus">{{ ocrIcon(page.ocrStatus) }}</span>
        </div>

        <!-- Type badge -->
        <div
          v-if="pageTypeBadge(page.pageType)"
          class="type-badge"
          :title="page.pageType"
        >
          {{ pageTypeBadge(page.pageType)!.icon }}
        </div>
      </div>

      <!-- Add page button -->
      <button class="add-page-btn" @click="emit('insertAfter', pages.length - 1)">
        + Add
      </button>
    </div>

    <!-- Context menu -->
    <Teleport to="body">
      <div
        v-if="contextMenu"
        class="context-menu"
        :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
        @click.stop
      >
        <button @click="ctxInsertBefore">Insert Before</button>
        <button @click="ctxInsertAfter">Insert After</button>
        <hr />
        <button @click="ctxMarkRecapture">Mark as Needs Recapture</button>
        <hr />
        <button class="danger" @click="ctxDelete">Delete</button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.filmstrip-sidebar {
  width: 96px;
  min-width: 72px;
  border-right: 1px solid var(--border-color, #444);
  overflow-y: auto;
  flex-shrink: 0;
  background: var(--nav-bg, #1a1a1a);
}

.filmstrip-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
}

.filmstrip-card {
  position: relative;
  border-radius: 4px;
  border: 2px solid transparent;
  background: var(--thumb-bg, #2a2a2a);
  cursor: pointer;
  transition: border-color 0.1s;
  user-select: none;
}

.filmstrip-card:hover { border-color: var(--accent-dim, #2a6ab0); }
.filmstrip-card.selected { border-color: var(--accent, #4a9eff); }
.filmstrip-card.excluded { opacity: 0.45; }
.filmstrip-card.drag-over { border-color: #ffb400; border-style: dashed; }

.thumb-img-wrap {
  width: 100%;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  border-radius: 2px 2px 0 0;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  background: #333;
}

.thumb-footer {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 4px;
}

.page-num {
  font-size: 0.62rem;
  color: var(--text-muted, #aaa);
  flex: 1;
}

.status-icon, .ocr-icon {
  font-size: 0.6rem;
  line-height: 1;
}

.type-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  font-size: 0.7rem;
  line-height: 1;
  background: rgba(0,0,0,0.5);
  border-radius: 2px;
  padding: 1px 2px;
}

.add-page-btn {
  width: 100%;
  padding: 4px;
  background: transparent;
  border: 1px dashed var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  font-size: 0.7rem;
  cursor: pointer;
  margin-top: 2px;
}

.add-page-btn:hover { border-color: var(--accent, #4a9eff); color: var(--accent, #4a9eff); }
</style>

<!-- Context menu is teleported to body; use global styles -->
<style>
.context-menu {
  position: fixed;
  z-index: 2000;
  background: #1e1e1e;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 4px 0;
  min-width: 160px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

.context-menu button {
  display: block;
  width: 100%;
  padding: 5px 12px;
  background: transparent;
  border: none;
  color: #ddd;
  font-size: 0.8rem;
  text-align: left;
  cursor: pointer;
}

.context-menu button:hover { background: #333; }
.context-menu button.danger { color: #f44; }
.context-menu hr { border-color: #333; margin: 3px 0; }
</style>
