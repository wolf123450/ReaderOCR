<script setup lang="ts">
import { ref, computed, onUnmounted } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { convertFileSrc } from "@tauri-apps/api/core";
import { open as openDialog, save as saveDialog } from "@tauri-apps/plugin-dialog";
import MetadataForm from "@/components/MetadataForm.vue";
import { useMetadataStore } from "@/stores/metadata";
import { useOcrStore } from "@/stores/ocr";
import { useChaptersStore } from "@/stores/chapters";
import { useCaptureStore } from "@/stores/capture";

const meta = useMetadataStore();
const ocr = useOcrStore();
const chaptersStore = useChaptersStore();
const captureStore = useCaptureStore();

const buildState = ref<"idle" | "building" | "done" | "error">("idle");
const buildMessage = ref("");
const outputPath = ref("");

// ── Cover crop modal ──────────────────────────────────────────────────────────

const cropModalOpen = ref(false);
const cropImageUrl = ref("");
const cropImageNaturalW = ref(0);
const cropImageNaturalH = ref(0);
const cropDisplayW = ref(0);
const cropDisplayH = ref(0);
const cropX = ref(0);
const cropY = ref(0);
const cropW = ref(0);
const cropH = ref(0);
const isDragging = ref(false);
const dragStartX = ref(0);
const dragStartY = ref(0);
const cropContainerRef = ref<HTMLDivElement | null>(null);
const cropImageRef = ref<HTMLImageElement | null>(null);

function coverPreviewUrl(): string {
  if (!meta.coverImagePath) return "";
  try { return convertFileSrc(meta.coverImagePath); } catch { return ""; }
}

async function openCropModal() {
  if (!meta.coverImagePath) return;
  cropImageUrl.value = coverPreviewUrl();
  cropModalOpen.value = true;
}

function onCropImageLoad(e: Event) {
  const img = e.target as HTMLImageElement;
  cropImageNaturalW.value = img.naturalWidth;
  cropImageNaturalH.value = img.naturalHeight;
  cropDisplayW.value = img.clientWidth;
  cropDisplayH.value = img.clientHeight;
  // Default: full image selected
  cropX.value = 0;
  cropY.value = 0;
  cropW.value = img.clientWidth;
  cropH.value = img.clientHeight;
}

function pixelRatio(): { scaleX: number; scaleY: number } {
  return {
    scaleX: cropDisplayW.value > 0 ? cropImageNaturalW.value / cropDisplayW.value : 1,
    scaleY: cropDisplayH.value > 0 ? cropImageNaturalH.value / cropDisplayH.value : 1,
  };
}

function onMouseDown(e: MouseEvent) {
  if (!cropImageRef.value) return;
  const rect = cropImageRef.value.getBoundingClientRect();
  const x = Math.max(0, e.clientX - rect.left);
  const y = Math.max(0, e.clientY - rect.top);
  dragStartX.value = x;
  dragStartY.value = y;
  cropX.value = x;
  cropY.value = y;
  cropW.value = 0;
  cropH.value = 0;
  isDragging.value = true;
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value || !cropImageRef.value) return;
  const rect = cropImageRef.value.getBoundingClientRect();
  const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
  const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height));
  cropX.value = Math.min(x, dragStartX.value);
  cropY.value = Math.min(y, dragStartY.value);
  cropW.value = Math.abs(x - dragStartX.value);
  cropH.value = Math.abs(y - dragStartY.value);
}

function onMouseUp() {
  isDragging.value = false;
}

function closeCropModal() {
  cropModalOpen.value = false;
  isDragging.value = false;
}

async function applyCrop() {
  if (!meta.coverImagePath || cropW.value < 4 || cropH.value < 4) return;
  const { scaleX, scaleY } = pixelRatio();
  const px = Math.round(cropX.value * scaleX);
  const py = Math.round(cropY.value * scaleY);
  const pw = Math.round(cropW.value * scaleX);
  const ph = Math.round(cropH.value * scaleY);

  // Derive output path: same directory, suffix -cover-crop.jpg
  const src = meta.coverImagePath;
  const dot = src.lastIndexOf(".");
  const outputPath = (dot > 0 ? src.slice(0, dot) : src) + "-cover-crop.jpg";

  try {
    const saved = await invoke<string>("crop_cover_image", {
      sourcePath: src,
      x: px,
      y: py,
      w: pw,
      h: ph,
      outputPath,
    });
    meta.setCoverImagePath(saved);
    closeCropModal();
  } catch (err) {
    alert(`Crop failed: ${String(err)}`);
  }
}

// Clean up drag listeners on unmount
function globalMouseUp() { isDragging.value = false; }
window.addEventListener("mouseup", globalMouseUp);
onUnmounted(() => window.removeEventListener("mouseup", globalMouseUp));

// ── EPUB build ────────────────────────────────────────────────────────────────

const canBuild = computed(() => {
  return (
    meta.title.trim().length > 0 &&
    meta.author.trim().length > 0 &&
    ocr.pageResults.size > 0
  );
});

/** Convert pageResults Map into the JSON-RPC page array format. */
function collectPages() {
  return Array.from(ocr.pageResults.values())
    .sort((a, b) => a.pageNumber - b.pageNumber)
    .map((r) => ({
      page_index: r.pageNumber - 1,
      blocks: (r.blocks ?? []).map((b) => ({
        type: b.type,
        text: b.text,
        confidence: b.confidence,
        bbox: b.bbox,
        col_index: b.col_index,
      })),
      raw_text: r.text,
      avg_confidence: r.confidence / 100,
    }));
}

async function pickCoverImage() {
  const selected = await openDialog({
    filters: [{ name: "Images", extensions: ["jpg", "jpeg", "png"] }],
    multiple: false,
    title: "Select Cover Image",
  });
  if (typeof selected === "string") {
    meta.setCoverImagePath(selected);
  }
}

async function buildEpub() {
  buildState.value = "building";
  buildMessage.value = "";

  try {
    const savePath = await saveDialog({
      filters: [{ name: "EPUB", extensions: ["epub"] }],
      defaultPath: meta.title
        ? `${meta.title.replace(/[^a-zA-Z0-9 _-]/g, "")}.epub`
        : "output.epub",
      title: "Save EPUB as",
    });

    if (!savePath) {
      buildState.value = "idle";
      return;
    }

    const pages = collectPages();
    const chapters = chaptersStore.chapters.map((c) => ({
      id: c.id,
      title: c.title,
      chapterIndex: c.chapterIndex,
      sources: c.sources,
      chapterType: c.chapterType,
    }));

    const result = await invoke<{
      output_path: string;
      file_size_bytes: number;
      chapter_count: number;
      page_count: number;
    }>("build_epub", {
      metadata: {
        title: meta.title,
        author: meta.author,
        language: meta.language || "en",
        description: meta.description,
        publisher: meta.publisher,
        isbn: meta.isbn,
        coverImagePath: meta.coverImagePath,
      },
      chapters,
      pages,
      outputPath: savePath,
      editedBlocks: ocr.editedBlocks.size > 0
        ? Object.fromEntries(
            Array.from(ocr.editedBlocks.entries()).map(([pn, blocks]) => [
              String(pn - 1), // convert pageNumber (1-based) → page_index (0-based)
              blocks.map((b) => ({
                type: b.type,
                text: b.text,
                confidence: b.confidence,
                bbox: b.bbox,
                col_index: b.col_index,
              })),
            ])
          )
        : null,
    });

    outputPath.value = result.output_path;
    buildMessage.value =
      `EPUB saved: ${result.chapter_count} chapter(s), ` +
      `${result.page_count} page(s), ` +
      `${(result.file_size_bytes / 1024).toFixed(1)} KB`;
    buildState.value = "done";
  } catch (e: unknown) {
    buildMessage.value = String(e);
    buildState.value = "error";
  }
}
</script>

<template>
  <div class="export-view">
    <div class="export-layout">
      <!-- Left column: metadata + chapter editor -->
      <div class="left-pane">
        <MetadataForm />

        <div class="cover-row">
          <label class="cover-label">Cover Image</label>
          <div class="cover-picker">
            <span class="cover-path">{{ meta.coverImagePath || "None selected" }}</span>
            <button class="pick-btn" @click="pickCoverImage">Browse…</button>
          </div>
          <div v-if="meta.coverImagePath" class="cover-preview-area">
            <img
              :src="coverPreviewUrl()"
              class="cover-thumb"
              alt="Cover preview"
            />
            <button class="crop-btn" @click="openCropModal" title="Crop cover image">
              ✂ Crop
            </button>
          </div>
        </div>

        <div class="divider" />

        <!-- Chapter summary — managed in Pages/Review → Edit -->
        <div class="chapter-summary">
          <div class="chapter-summary-header">
            <span>Chapter Structure</span>
            <span class="summary-count">{{ chaptersStore.chapters.length }} chapter(s)</span>
          </div>
          <p v-if="chaptersStore.chapters.length === 0" class="summary-hint">
            No chapters defined. Use <strong>Pages/Review → Edit</strong> to assign pages to chapters.
            Without chapters, all OCR'd pages will be exported as a single chapter.
          </p>
          <ul v-else class="summary-list">
            <li v-for="ch in chaptersStore.sortedChapters" :key="ch.id">
              <span class="summary-title">{{ ch.title }}</span>
              <span class="summary-pages">{{ ch.sources.length }} page(s)</span>
            </li>
          </ul>
          <p class="summary-edit-hint">Edit chapters in <strong>Pages/Review → Edit</strong>.</p>
        </div>
      </div>

      <!-- Right column: build action -->
      <div class="right-pane">
        <div class="build-card">
          <h3>Build EPUB</h3>
          <p class="build-info">
            <strong>{{ ocr.pageResults.size }}</strong> page(s) ready &mdash;
            <strong>{{ chaptersStore.chapters.length }}</strong> chapter(s) defined
          </p>

          <div v-if="!canBuild" class="build-hint">
            <template v-if="!meta.title.trim()">Enter a book title to continue.</template>
            <template v-else-if="!meta.author.trim()">Enter an author name to continue.</template>
            <template v-else>Run OCR on at least one page first.</template>
          </div>

          <button
            class="build-btn"
            :disabled="!canBuild || buildState === 'building'"
            @click="buildEpub"
          >
            <span v-if="buildState === 'building'">Building…</span>
            <span v-else>⬇ Build EPUB</span>
          </button>

          <div v-if="buildState === 'done'" class="result success">
            ✓ {{ buildMessage }}
          </div>
          <div v-else-if="buildState === 'error'" class="result error">
            ✗ {{ buildMessage }}
          </div>
        </div>
      </div>
    </div>

    <!-- Crop Modal -->
    <Teleport to="body">
      <div v-if="cropModalOpen" class="crop-overlay" @mouseup="onMouseUp">
        <div class="crop-modal">
          <div class="crop-modal-header">
            <span>Crop Cover Image</span>
            <button class="crop-close" @click="closeCropModal">✕</button>
          </div>
          <p class="crop-hint">Drag a rectangle to select the crop area, then click Apply.</p>
          <div
            ref="cropContainerRef"
            class="crop-image-container"
            @mousedown.prevent="onMouseDown"
            @mousemove="onMouseMove"
          >
            <img
              ref="cropImageRef"
              :src="cropImageUrl"
              class="crop-source-image"
              draggable="false"
              @load="onCropImageLoad"
            />
            <div
              v-if="cropW > 0 && cropH > 0"
              class="crop-selection"
              :style="{
                left: cropX + 'px',
                top: cropY + 'px',
                width: cropW + 'px',
                height: cropH + 'px',
              }"
            />
          </div>
          <div class="crop-modal-footer">
            <span class="crop-coords" v-if="cropW > 0">
              {{ Math.round(cropW * pixelRatio().scaleX) }} × {{ Math.round(cropH * pixelRatio().scaleY) }} px
            </span>
            <div class="crop-actions">
              <button class="pick-btn" @click="closeCropModal">Cancel</button>
              <button
                class="build-btn crop-apply-btn"
                :disabled="cropW < 4 || cropH < 4"
                @click="applyCrop"
              >
                Apply Crop
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.export-view {
  padding: 1.5rem;
  height: 100%;
  overflow: auto;
}

.export-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 1.5rem;
  align-items: start;
}

.left-pane {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.cover-label {
  font-size: 0.8rem;
  color: var(--color-text-muted, #aaa);
  display: block;
  margin-bottom: 0.25rem;
}

.cover-picker {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.cover-path {
  flex: 1;
  font-size: 0.8rem;
  color: var(--color-text, #eee);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pick-btn {
  padding: 0.25rem 0.6rem;
  font-size: 0.8rem;
  background: var(--color-background-soft, #1e1e1e);
  border: 1px solid var(--color-border, #444);
  border-radius: 4px;
  color: var(--color-text, #eee);
  cursor: pointer;
  white-space: nowrap;
}

.pick-btn:hover {
  border-color: var(--color-brand, #4f8cff);
}

.cover-preview-area {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.cover-thumb {
  max-height: 120px;
  max-width: 100px;
  object-fit: contain;
  border: 1px solid var(--color-border, #444);
  border-radius: 4px;
}

.crop-btn {
  padding: 0.25rem 0.6rem;
  font-size: 0.8rem;
  background: var(--color-background-soft, #1e1e1e);
  border: 1px solid var(--color-border, #444);
  border-radius: 4px;
  color: var(--color-text, #eee);
  cursor: pointer;
  align-self: flex-start;
}

.crop-btn:hover {
  border-color: var(--color-brand, #4f8cff);
}

.divider {
  border-top: 1px solid var(--color-border, #333);
}

/* Chapter summary */
.chapter-summary {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.chapter-summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-heading, #ccc);
}

.summary-count {
  font-size: 0.78rem;
  font-weight: normal;
  color: var(--color-text-muted, #888);
}

.summary-hint {
  font-size: 0.78rem;
  color: var(--color-text-muted, #999);
  margin: 0;
  line-height: 1.5;
}

.summary-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8rem;
  padding: 2px 0;
}

.summary-title {
  color: var(--color-text, #eee);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-pages {
  font-size: 0.72rem;
  color: var(--color-text-muted, #888);
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.summary-edit-hint {
  font-size: 0.72rem;
  color: var(--color-text-muted, #666);
  margin: 0;
  font-style: italic;
}

/* Right pane */
.right-pane {
  position: sticky;
  top: 0;
}

.build-card {
  background: var(--color-background-soft, #1a1a1a);
  border: 1px solid var(--color-border, #333);
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.build-card h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.build-info {
  font-size: 0.82rem;
  color: var(--color-text-muted, #aaa);
  margin: 0;
}

.build-hint {
  font-size: 0.8rem;
  color: #f59e0b;
}

.build-btn {
  padding: 0.6rem 1rem;
  background: var(--color-brand, #4f8cff);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.build-btn:hover:not(:disabled) {
  background: #6aa0ff;
}

.build-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.result {
  font-size: 0.8rem;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
}

.result.success {
  background: rgba(52, 211, 153, 0.1);
  color: #34d399;
}

.result.error {
  background: rgba(248, 113, 113, 0.1);
  color: #f87171;
}

/* Crop modal */
.crop-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.crop-modal {
  background: var(--color-background, #1e1e1e);
  border: 1px solid var(--color-border, #444);
  border-radius: 8px;
  padding: 1rem;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow: hidden;
}

.crop-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
  font-weight: 600;
}

.crop-close {
  background: none;
  border: none;
  color: var(--color-text-muted, #aaa);
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
  line-height: 1;
}

.crop-close:hover {
  color: var(--color-text, #eee);
}

.crop-hint {
  font-size: 0.78rem;
  color: var(--color-text-muted, #aaa);
  margin: 0;
}

.crop-image-container {
  position: relative;
  overflow: auto;
  max-height: 60vh;
  cursor: crosshair;
  user-select: none;
  border: 1px solid var(--color-border, #333);
}

.crop-source-image {
  display: block;
  max-width: 100%;
  pointer-events: none;
}

.crop-selection {
  position: absolute;
  border: 2px solid #4f8cff;
  background: rgba(79, 140, 255, 0.18);
  box-sizing: border-box;
  pointer-events: none;
}

.crop-modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.crop-coords {
  font-size: 0.75rem;
  color: var(--color-text-muted, #888);
}

.crop-actions {
  display: flex;
  gap: 0.5rem;
}

.crop-apply-btn {
  padding: 0.35rem 0.8rem;
  font-size: 0.85rem;
}
</style>
