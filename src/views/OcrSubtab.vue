<script setup lang="ts">
import { computed } from "vue";
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
        </div>
        <pre v-if="ocr.testRunResult.text" class="result-text">{{ ocr.testRunResult.text }}</pre>
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

.test-run-row { margin-bottom: 0.5rem; }

.test-result {
  margin-top: 0.5rem;
  padding: 0.6rem;
  background: #222;
  border-radius: 4px;
  font-size: 0.8rem;
}

.test-result-header { margin-bottom: 0.4rem; color: var(--text-primary, #f0f0f0); }
.result-error { color: #f77; }
.low-conf { color: #ffb400; margin-left: 0.3rem; }

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
</style>
