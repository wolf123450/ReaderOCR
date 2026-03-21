<script setup lang="ts">
import { computed } from "vue";
import { convertFileSrc } from "@tauri-apps/api/core";
import { useCaptureStore, type PageType } from "@/stores/capture";
import { useUiStore } from "@/stores/ui";
import { useChaptersStore } from "@/stores/chapters";

const capture = useCaptureStore();
const ui = useUiStore();
const chaptersStore = useChaptersStore();

const PAGE_TYPES: { value: PageType; label: string }[] = [
  { value: "text", label: "Text" },
  { value: "cover", label: "Cover" },
  { value: "illustration", label: "Illustration" },
  { value: "toc", label: "TOC" },
  { value: "license", label: "License" },
  { value: "blank", label: "Blank" },
  { value: "chapter_start", label: "Chapter Start" },
  { value: "excluded", label: "Excluded" },
];

const selectedIndex = computed(() => ui.selectedPageIndex);
const page = computed(() =>
  selectedIndex.value !== null ? capture.capturedPages[selectedIndex.value] ?? null : null
);
const total = computed(() => capture.capturedPages.length);

function imageSrc(path: string): string {
  try { return convertFileSrc(path); } catch { return ""; }
}

function onTypeChange(e: Event) {
  if (selectedIndex.value === null) return;
  const val = (e.target as HTMLSelectElement).value as PageType;
  capture.setPageType(selectedIndex.value, val);
}

function markRecapture() {
  if (selectedIndex.value !== null) {
    capture.setCaptureStatus(selectedIndex.value, "needs_recapture");
  }
}

function deletePage() {
  if (selectedIndex.value !== null) {
    const idx = selectedIndex.value;
    capture.deletePage(idx);
    ui.selectedPageIndex = idx > 0 ? idx - 1 : null;
  }
}

const emit = defineEmits<{
  (e: "insertBefore"): void;
  (e: "insertAfter"): void;
}>();

function statusLabel(s: string): string {
  if (s === "ok") return "✅ ok";
  if (s === "needs_recapture") return "⚠ needs recapture";
  if (s === "missing") return "❌ missing";
  if (s === "placeholder") return "◻ placeholder";
  return s;
}

// ── Chapter assignment ───────────────────────────────────────

/** 0-based page index for the selected page (same key used in chapter sources). */
const pageIndex = computed(() => selectedIndex.value);

/** ID of the chapter currently containing this page, or empty string. */
const pageChapterId = computed(() => {
  if (pageIndex.value === null) return "";
  return chaptersStore.getChapterForPage(pageIndex.value)?.id ?? "";
});

function onChapterChange(e: Event) {
  if (pageIndex.value === null) return;
  const chapterId = (e.target as HTMLSelectElement).value;
  if (chapterId === "") {
    const current = chaptersStore.getChapterForPage(pageIndex.value);
    if (current) chaptersStore.removePageFromChapter(current.id, pageIndex.value);
  } else {
    chaptersStore.assignPageToChapter(chapterId, pageIndex.value);
  }
}
</script>

<template>
  <div class="page-detail-pane">
    <div v-if="page" class="detail-body">
      <!-- Header -->
      <div class="detail-header">
        <span class="page-counter">Page {{ page.pageNumber }} of {{ total }}</span>
        <div class="action-row">
          <button class="action-btn" title="Recapture this page" @click="markRecapture">🔄 Recapture</button>
          <button class="action-btn" @click="emit('insertBefore')">➕ Before</button>
          <button class="action-btn" @click="emit('insertAfter')">➕ After</button>
          <button class="action-btn danger" title="Remove from session" @click="deletePage">🗑</button>
        </div>
      </div>

      <!-- Thumbnail -->
      <div class="thumb-preview">
        <img
          v-if="imageSrc(page.imagePath)"
          :src="imageSrc(page.imagePath)"
          class="preview-img"
          :alt="`Page ${page.pageNumber}`"
        />
        <div v-else class="preview-placeholder">No preview</div>
      </div>

      <!-- Metadata -->
      <div class="meta-row">
        <label class="meta-label">
          Type:
          <select :value="page.pageType" @change="onTypeChange" class="type-select">
            <option v-for="t in PAGE_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </label>
        <span class="meta-status">Status: {{ statusLabel(page.captureStatus) }}</span>
        <span class="meta-ocr">OCR: {{ page.ocrStatus }}</span>
      </div>

      <!-- Chapter assignment (only shown when chapters exist) -->
      <div v-if="chaptersStore.chapters.length > 0" class="meta-row">
        <label class="meta-label">
          Chapter:
          <select :value="pageChapterId" @change="onChapterChange" class="type-select">
            <option value="">— Not assigned —</option>
            <option v-for="ch in chaptersStore.sortedChapters" :key="ch.id" :value="ch.id">
              {{ ch.title }}
            </option>
          </select>
        </label>
      </div>
    </div>

    <div v-else class="no-selection">
      <p>Select a page to view details.</p>
    </div>
  </div>
</template>

<style scoped>
.page-detail-pane {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  height: 100%;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.page-counter {
  font-size: 0.875rem;
  color: var(--text-muted, #aaa);
}

.action-row {
  display: flex;
  gap: 0.35rem;
}

.action-btn {
  padding: 0.3rem 0.55rem;
  background: transparent;
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  font-size: 0.75rem;
  cursor: pointer;
}

.action-btn:hover { color: var(--text-primary, #f0f0f0); border-color: var(--accent, #4a9eff); }
.action-btn.danger:hover { border-color: #f44; color: #f44; }

.thumb-preview {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--thumb-bg, #2a2a2a);
  border-radius: 4px;
  overflow: hidden;
}

.preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.preview-placeholder {
  color: var(--text-muted, #aaa);
  font-size: 0.8rem;
  font-style: italic;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding-bottom: 0.5rem;
}

.meta-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: var(--text-muted, #aaa);
}

.type-select {
  background: var(--nav-bg, #1a1a1a);
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-primary, #f0f0f0);
  font-size: 0.8rem;
  padding: 2px 4px;
}

.meta-status, .meta-ocr {
  font-size: 0.8rem;
  color: var(--text-muted, #aaa);
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted, #aaa);
  font-style: italic;
  font-size: 0.875rem;
}
</style>
