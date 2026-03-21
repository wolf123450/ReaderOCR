<script setup lang="ts">
import { computed, ref } from "vue";
import { convertFileSrc } from "@tauri-apps/api/core";
import { useCaptureStore } from "@/stores/capture";
import { useUiStore } from "@/stores/ui";
import { useSettingsStore } from "@/stores/settings";
import { useOcrStore } from "@/stores/ocr";
import OcrProgressBar from "@/components/OcrProgressBar.vue";

const capture = useCaptureStore();
const ui = useUiStore();
const settings = useSettingsStore();
const ocr = useOcrStore();

const selectedPage = computed(() =>
  ui.selectedPageIndex !== null ? capture.capturedPages[ui.selectedPageIndex] ?? null : null
);

const ocrEngines = [
  { value: "paddleocr-pp-ocrv5", label: "PaddleOCR PP-OCRv5" },
  // Tesseract is not yet implemented — add back once the sidecar engine is wired up
];

const languages = [
  { value: "en", label: "English" },
  { value: "zh", label: "Chinese" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "de", label: "German" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
];

function runTestOcr() {
  if (ui.selectedPageIndex !== null) {
    ocr.runTestOcr(ui.selectedPageIndex);
  }
}

// --- Debug overlay ---
const showDebug = ref(false);
const debugImgSize = ref({ w: 0, h: 0 });

function onDebugImgLoad(e: Event) {
  const img = e.target as HTMLImageElement;
  debugImgSize.value = { w: img.naturalWidth, h: img.naturalHeight };
}

// Distinct colours for up to 6 columns; wraps after that.
const COL_COLOURS = ["#ff4444", "#4488ff", "#33cc55", "#ff8800", "#cc44ff", "#00cccc"];
function colColour(colIndex: number): string {
  return COL_COLOURS[colIndex % COL_COLOURS.length];
}

// --- Block editor (Step 46) ---

const BLOCK_TYPES = [
  "body",
  "chapter_title",
  "section_heading",
  "header",
  "footer",
  "page_number",
  "sidebar",
  "figure_caption",
  "excluded",
];

const editPageNumber = computed(() => selectedPage.value?.pageNumber ?? null);

const activeBlocks = computed(() => {
  const pn = editPageNumber.value;
  if (pn === null) return null;
  if (ocr.editedBlocks.has(pn)) return ocr.editedBlocks.get(pn)!;
  const result = ocr.pageResults.get(pn);
  return result?.blocks ?? null;
});

const isEditing = computed(() => {
  const pn = editPageNumber.value;
  return pn !== null && ocr.editedBlocks.has(pn);
});

function startEditing() {
  const pn = editPageNumber.value;
  if (pn === null || !activeBlocks.value) return;
  ocr.setEditedBlocks(pn, activeBlocks.value);
}

function resetEditing() {
  const pn = editPageNumber.value;
  if (pn === null) return;
  ocr.resetEditedBlocks(pn);
}

function onBlockTypeChange(blockIdx: number, newType: string) {
  const pn = editPageNumber.value;
  if (pn === null) return;
  ocr.setBlockType(pn, blockIdx, newType);
}

function onBlockTextChange(blockIdx: number, newText: string) {
  const pn = editPageNumber.value;
  if (pn === null) return;
  ocr.setBlockText(pn, blockIdx, newText);
}

function moveBlockUp(blockIdx: number) {
  const pn = editPageNumber.value;
  if (pn === null || blockIdx === 0) return;
  ocr.moveBlock(pn, blockIdx, blockIdx - 1);
}

function moveBlockDown(blockIdx: number) {
  const pn = editPageNumber.value;
  const blocks = activeBlocks.value;
  if (pn === null || !blocks || blockIdx >= blocks.length - 1) return;
  ocr.moveBlock(pn, blockIdx, blockIdx + 1);
}
</script>

<template>
  <div class="ocr-subtab">
    <!-- Settings section -->
    <section class="ocr-section">
      <h3>OCR Settings</h3>
      <label class="setting-row">
        <input
          type="checkbox"
          :checked="settings.autoOcrAfterCapture"
          @change="settings.setAutoOcr(($event.target as HTMLInputElement).checked)"
        />
        Auto-OCR new pages after capture
      </label>
      <div class="setting-row">
        <label>
          Engine:
          <select :value="settings.ocrEngine" @change="settings.setOcrEngine(($event.target as HTMLSelectElement).value)" class="setting-select">
            <option v-for="e in ocrEngines" :key="e.value" :value="e.value">{{ e.label }}</option>
          </select>
        </label>
        <label>
          Language:
          <select :value="settings.ocrLanguage" @change="settings.setOcrLanguage(($event.target as HTMLSelectElement).value)" class="setting-select">
            <option v-for="l in languages" :key="l.value" :value="l.value">{{ l.label }}</option>
          </select>
        </label>
        <label>
          Max columns:
          <input
            type="number"
            :value="settings.ocrMaxColumns"
            min="1"
            max="20"
            class="setting-input-num"
            @change="settings.setOcrMaxColumns(+($event.target as HTMLInputElement).value)"
          />
        </label>
      </div>
    </section>

    <!-- Test run section -->
    <section class="ocr-section">
      <h3>Test Run</h3>
      <p class="section-desc">Run OCR on the selected page before committing to a full batch.</p>
      <div class="test-run-row">
        <button
          class="btn-primary"
          :disabled="!selectedPage || ocr.testRunning"
          @click="runTestOcr"
        >
          <span v-if="ocr.testRunning">Running…</span>
          <span v-else-if="selectedPage">Test OCR on page {{ selectedPage.pageNumber }}</span>
          <span v-else>Select a page first</span>
        </button>
      </div>
      <div v-if="ocr.testRunResult" class="test-result">
        <div class="test-result-header">
          <span v-if="ocr.testRunResult.errorMessage" class="result-error">
            ✗ Error: {{ ocr.testRunResult.errorMessage }}
          </span>
          <span v-else>
            ✓ Confidence: {{ ocr.testRunResult.confidence.toFixed(1) }}%
            <span v-if="ocr.testRunResult.confidence < 80" class="low-conf">(low)</span>
          </span>
          <label class="debug-toggle" v-if="!ocr.testRunResult.errorMessage">
            <input type="checkbox" v-model="showDebug" />
            Debug view
          </label>
        </div>

        <!-- Debug mode: bounding box overlay + block table -->
        <div v-if="showDebug && ocr.testRunResult.blocks?.length && selectedPage" class="debug-view">
          <!-- Image with SVG overlay -->
          <div class="debug-img-wrap">
            <img
              :src="convertFileSrc(selectedPage.imagePath)"
              class="debug-img"
              @load="onDebugImgLoad"
            />
            <svg
              v-if="debugImgSize.w > 0"
              :viewBox="`0 0 ${debugImgSize.w} ${debugImgSize.h}`"
              class="debug-svg"
              xmlns="http://www.w3.org/2000/svg"
            >
              <g v-for="(block, idx) in ocr.testRunResult.blocks" :key="idx">
                <rect
                  :x="block.bbox.x"
                  :y="block.bbox.y"
                  :width="block.bbox.width"
                  :height="block.bbox.height"
                  :stroke="colColour(block.col_index)"
                  fill="none"
                  stroke-width="3"
                />
                <!-- Reading-order number badge -->
                <rect
                  :x="block.bbox.x"
                  :y="block.bbox.y - 16"
                  :width="String(idx + 1).length * 9 + 4"
                  height="16"
                  :fill="colColour(block.col_index)"
                />
                <text
                  :x="block.bbox.x + 2"
                  :y="block.bbox.y - 3"
                  fill="white"
                  font-size="13"
                  font-family="monospace"
                  font-weight="bold"
                >{{ idx + 1 }}</text>
              </g>
            </svg>
          </div>

          <!-- Column legend -->
          <div class="debug-legend">
            <span
              v-for="col in [...new Set(ocr.testRunResult.blocks.map(b => b.col_index))].sort()"
              :key="col"
              class="legend-chip"
              :style="{ background: colColour(col) }"
            >col {{ col }}</span>
          </div>

          <!-- Block table -->
          <table class="debug-table">
            <thead>
              <tr>
                <th>#</th>
                <th>col</th>
                <th>conf</th>
                <th>bbox (x,y,w,h)</th>
                <th>text</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(block, idx) in ocr.testRunResult.blocks" :key="idx">
                <td :style="{ color: colColour(block.col_index) }">{{ idx + 1 }}</td>
                <td :style="{ color: colColour(block.col_index) }">{{ block.col_index }}</td>
                <td>{{ (block.confidence * 100).toFixed(0) }}%</td>
                <td class="bbox-cell">{{ block.bbox.x }},{{ block.bbox.y }},{{ block.bbox.width }},{{ block.bbox.height }}</td>
                <td class="text-cell">{{ block.text }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Normal text view -->
        <pre v-if="!showDebug && ocr.testRunResult.text" class="result-text">{{ ocr.testRunResult.text }}</pre>
      </div>
    </section>

    <!-- Batch OCR section -->
    <section class="ocr-section">
      <h3>Batch OCR</h3>
      <div class="batch-controls">
        <button
          v-if="ocr.batchState === 'idle' || ocr.batchState === 'stopped' || ocr.batchState === 'completed'"
          class="btn-primary"
          :disabled="capture.capturedPages.length === 0"
          @click="ocr.startBatchOcr()"
        >
          Run OCR — All Pages
        </button>
        <template v-if="ocr.batchState === 'running'">
          <button class="btn-secondary" @click="ocr.pauseBatchOcr()">Pause</button>
          <button class="btn-secondary" @click="ocr.stopBatchOcr()">Stop</button>
        </template>
        <button
          v-if="ocr.batchState === 'paused'"
          class="btn-primary"
          @click="ocr.resumeBatchOcr()"
        >
          Resume
        </button>

        <span class="batch-state-label">{{ ocr.batchState }}</span>
      </div>

      <OcrProgressBar
        v-if="ocr.batchState !== 'idle'"
      />
    </section>

    <!-- Block Editor section (Step 46) -->
    <section v-if="activeBlocks" class="ocr-section">
      <div class="editor-header">
        <h3>Block Editor</h3>
        <span class="editor-status">
          <template v-if="isEditing">
            <span class="badge-editing">✎ Editing overrides active</span>
            <button class="btn-reset" @click="resetEditing">Reset to OCR</button>
          </template>
          <template v-else>
            <span class="badge-readonly">Read-only (original OCR)</span>
            <button class="btn-secondary" @click="startEditing">Edit Blocks</button>
          </template>
        </span>
      </div>
      <p class="section-desc">
        Adjust block types and reading order before exporting.
        Changes apply only to this page's OCR output during EPUB assembly.
      </p>

      <table class="editor-table">
        <thead>
          <tr>
            <th class="col-order">↕</th>
            <th class="col-num">#</th>
            <th class="col-type">Type</th>
            <th class="col-text">Text</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(block, idx) in activeBlocks"
            :key="idx"
            :class="['editor-row', { 'row-excluded': block.type === 'excluded' || block.type === 'header' || block.type === 'footer' || block.type === 'page_number' }]"
          >
            <td class="col-order">
              <div v-if="isEditing" class="order-btns">
                <button
                  class="order-btn"
                  :disabled="idx === 0"
                  title="Move up"
                  @click="moveBlockUp(idx)"
                >▲</button>
                <button
                  class="order-btn"
                  :disabled="idx === activeBlocks.length - 1"
                  title="Move down"
                  @click="moveBlockDown(idx)"
                >▼</button>
              </div>
              <span v-else class="order-static">—</span>
            </td>
            <td class="col-num">{{ idx + 1 }}</td>
            <td class="col-type">
              <select
                v-if="isEditing"
                :value="block.type"
                class="type-select"
                @change="onBlockTypeChange(idx, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="t in BLOCK_TYPES" :key="t" :value="t">{{ t }}</option>
              </select>
              <span v-else class="type-badge" :class="`type-${block.type}`">{{ block.type }}</span>
            </td>
            <td class="col-text">
              <textarea
                v-if="isEditing"
                class="text-edit"
                :value="block.text"
                rows="2"
                @input="onBlockTextChange(idx, ($event.target as HTMLTextAreaElement).value)"
              />
              <span v-else class="text-static">{{ block.text }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.ocr-subtab {
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
  overflow-y: auto;
}

.ocr-section {
  padding: 1rem;
  border-bottom: 1px solid var(--border-color, #444);
}

.ocr-section h3 {
  margin: 0 0 0.65rem 0;
  font-size: 0.9rem;
  color: var(--text-primary, #f0f0f0);
}

.section-desc {
  font-size: 0.8rem;
  color: var(--text-muted, #aaa);
  margin: 0 0 0.5rem 0;
}

.setting-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-muted, #aaa);
}

.setting-row input[type="checkbox"] { cursor: pointer; }

.setting-select {
  background: var(--nav-bg, #1a1a1a);
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-primary, #f0f0f0);
  font-size: 0.8rem;
  padding: 2px 4px;
  margin-left: 0.4rem;
}

.setting-input-num {
  background: var(--nav-bg, #1a1a1a);
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-primary, #f0f0f0);
  font-size: 0.8rem;
  padding: 2px 4px;
  margin-left: 0.4rem;
  width: 3.5rem;
  text-align: center;
}

.test-run-row { margin-bottom: 0.5rem; }

.test-result {
  margin-top: 0.5rem;
  padding: 0.6rem;
  background: #222;
  border-radius: 4px;
  font-size: 0.8rem;
}

.test-result-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.4rem;
  color: var(--text-primary, #f0f0f0);
}
.result-error { color: #f77; }
.low-conf { color: #ffb400; margin-left: 0.3rem; }

.debug-toggle {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  color: var(--text-muted, #aaa);
  cursor: pointer;
  margin-left: auto;
}
.debug-toggle input { cursor: pointer; }

.debug-view {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.debug-img-wrap {
  position: relative;
  line-height: 0;
}

.debug-img {
  width: 100%;
  display: block;
  border-radius: 2px;
}

.debug-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.debug-legend {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.legend-chip {
  padding: 2px 7px;
  border-radius: 3px;
  font-size: 0.7rem;
  color: white;
  font-weight: bold;
}

.debug-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.72rem;
  font-family: monospace;
  table-layout: fixed;
}

.debug-table th {
  text-align: left;
  padding: 2px 4px;
  border-bottom: 1px solid #444;
  color: var(--text-muted, #aaa);
  font-weight: normal;
}

.debug-table td {
  padding: 2px 4px;
  border-bottom: 1px solid #333;
  color: var(--text-primary, #f0f0f0);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.debug-table th:nth-child(1),
.debug-table td:nth-child(1) { width: 2.5rem; }
.debug-table th:nth-child(2),
.debug-table td:nth-child(2) { width: 2.5rem; }
.debug-table th:nth-child(3),
.debug-table td:nth-child(3) { width: 3rem; }
.debug-table th:nth-child(4),
.debug-table td:nth-child(4) { width: 9rem; }
.debug-table th:nth-child(5),
.debug-table td:nth-child(5) { width: auto; }

.bbox-cell { color: var(--text-muted, #aaa) !important; font-size: 0.68rem; }
.text-cell { white-space: nowrap; }

.result-text {
  margin: 0;
  color: var(--text-muted, #aaa);
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 0.75rem;
  max-height: 120px;
  overflow-y: auto;
}

.batch-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.btn-primary {
  padding: 0.4rem 0.85rem;
  background: var(--accent, #4a9eff);
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { background: #3a8eef; }

.btn-secondary {
  padding: 0.4rem 0.85rem;
  background: transparent;
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-secondary:hover { color: var(--text-primary, #f0f0f0); }

.batch-state-label {
  font-size: 0.78rem;
  color: var(--text-muted, #aaa);
  font-style: italic;
}

/* ── Block editor (Step 46) ───────────────────────────────────────────── */

.editor-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.editor-header h3 { margin: 0; }

.editor-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.badge-editing {
  font-size: 0.75rem;
  background: rgba(79, 140, 255, 0.15);
  color: #4f8cff;
  border-radius: 3px;
  padding: 1px 6px;
}

.badge-readonly {
  font-size: 0.75rem;
  color: var(--text-muted, #888);
}

.btn-reset {
  padding: 0.25rem 0.55rem;
  font-size: 0.75rem;
  background: rgba(248, 113, 113, 0.15);
  border: 1px solid rgba(248, 113, 113, 0.4);
  border-radius: 4px;
  color: #f87171;
  cursor: pointer;
}

.btn-reset:hover { background: rgba(248, 113, 113, 0.25); }

.editor-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
  table-layout: fixed;
}

.editor-table th {
  text-align: left;
  padding: 3px 5px;
  border-bottom: 1px solid #444;
  color: var(--text-muted, #aaa);
  font-weight: normal;
}

.editor-table td {
  padding: 3px 5px;
  border-bottom: 1px solid #2a2a2a;
  vertical-align: top;
}

.col-order { width: 3.5rem; }
.col-num   { width: 2rem; color: var(--text-muted, #888); }
.col-type  { width: 9rem; }
.col-text  { width: auto; }

.order-btns {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.order-btn {
  background: none;
  border: 1px solid #444;
  border-radius: 3px;
  color: var(--text-muted, #aaa);
  cursor: pointer;
  font-size: 0.65rem;
  padding: 0 4px;
  line-height: 1.4;
}

.order-btn:disabled { opacity: 0.25; cursor: not-allowed; }
.order-btn:not(:disabled):hover { border-color: #4f8cff; color: #4f8cff; }

.order-static { color: #444; }

.type-select {
  width: 100%;
  background: var(--nav-bg, #1a1a1a);
  border: 1px solid #444;
  border-radius: 3px;
  color: var(--text-primary, #eee);
  font-size: 0.75rem;
  padding: 1px 3px;
}

.type-badge {
  font-size: 0.7rem;
  padding: 1px 5px;
  border-radius: 3px;
  background: #2a2a2a;
  color: var(--text-muted, #aaa);
  display: inline-block;
}

.type-badge.type-chapter_title  { color: #a78bfa; background: rgba(167,139,250,0.1); }
.type-badge.type-section_heading { color: #60a5fa; background: rgba(96,165,250,0.1); }
.type-badge.type-body            { color: var(--text-primary, #eee); background: transparent; }
.type-badge.type-excluded,
.type-badge.type-header,
.type-badge.type-footer,
.type-badge.type-page_number     { color: #666; background: transparent; }

.row-excluded td { opacity: 0.45; }

.text-edit {
  width: 100%;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 3px;
  color: var(--text-primary, #eee);
  font-size: 0.75rem;
  font-family: monospace;
  padding: 2px 4px;
  resize: vertical;
  box-sizing: border-box;
}

.text-edit:focus { border-color: #4f8cff; outline: none; }

.text-static {
  color: var(--text-primary, #eee);
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
