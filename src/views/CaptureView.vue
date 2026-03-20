<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import WindowPicker from "@/components/WindowPicker.vue";
import RegionSelector from "@/components/RegionSelector.vue";
import ProgressTracker from "@/components/ProgressTracker.vue";
import SidecarStatus from "@/components/SidecarStatus.vue";
import CapturedPagesPanel from "@/components/CapturedPagesPanel.vue";
import { useCaptureStore, type CaptureProgress, type CaptureType } from "@/stores/capture";

const store = useCaptureStore();

const delayMs = ref(1500);
const maxPages = ref<number | null>(null);
const filePrefix = ref("page");
const pageTurnKey = ref("Right");
const captureError = ref<string | null>(null);
const sessionLoaded = ref(false);

interface SessionData {
  bookName: string;
  outputDir: string;
  filePrefix: string;
  pageTurnKey: string;
  delayBetweenMs: number;
  maxPages: number | null;
  pagesCaptured: number;
  region: { x: number; y: number; width: number; height: number };
  createdAt: string;
  updatedAt: string;
}

// Event listeners for real-time progress
let unlistenProgress: UnlistenFn | null = null;
let unlistenDuplicate: UnlistenFn | null = null;
let unlistenCompleted: UnlistenFn | null = null;
let unlistenStopped: UnlistenFn | null = null;

onMounted(async () => {
  unlistenProgress = await listen<CaptureProgress>("capture-progress", (event) => {
    store.recordCapture(event.payload);
  });
  unlistenDuplicate = await listen("capture-duplicate-detected", () => {
    if (store.batchState === "capturing" || store.batchState === "paused") {
      store.transitionTo("completed");
    }
  });
  unlistenCompleted = await listen("capture-completed", () => {
    if (store.batchState === "capturing" || store.batchState === "paused") {
      store.transitionTo("completed");
    }
  });
  unlistenStopped = await listen("capture-stopped", () => {
    if (store.batchState === "capturing" || store.batchState === "paused") {
      store.transitionTo("stopped");
    }
  });
});

onUnmounted(() => {
  unlistenProgress?.();
  unlistenDuplicate?.();
  unlistenCompleted?.();
  unlistenStopped?.();
});

const selectionSummary = computed(() => {
  if (!store.region || !store.selectedWindow) return null;
  return {
    window: store.selectedWindow.title,
    region: `${store.region.width}×${store.region.height} at (${store.region.x}, ${store.region.y})`,
  };
});

const canStart = computed(
  () =>
    store.hasSelection &&
    (store.batchState === "idle" || store.batchState === "stopped") &&
    store.batchConfig.outputDir.trim() !== ""
);

/** Try to load a session from the effective output dir. */
async function tryLoadSession(dir: string) {
  if (!dir) return;
  try {
    const session = await invoke<SessionData | null>("load_session", { dir });
    if (session) {
      store.setBookName(session.bookName);
      store.setBatchConfig({
        outputDir: session.outputDir,
        filePrefix: session.filePrefix,
        pageTurnKey: session.pageTurnKey,
        delayBetweenMs: session.delayBetweenMs,
        maxPages: session.maxPages,
      });
      filePrefix.value = session.filePrefix;
      pageTurnKey.value = session.pageTurnKey;
      delayMs.value = session.delayBetweenMs;
      maxPages.value = session.maxPages;
      // Restore captured page count so resume starts from the right page.
      store.restorePagesCaptured(session.pagesCaptured);
      if (session.pagesCaptured > 0) {
        store.transitionTo("stopped");
      }
      sessionLoaded.value = true;
    } else {
      sessionLoaded.value = false;
    }
  } catch {
    sessionLoaded.value = false;
  }
}

async function browseOutputDir() {
  const selected = await open({
    directory: true,
    multiple: false,
    title: "Select output directory",
  });
  if (selected) {
    const dir = selected as string;
    store.setBatchConfig({ outputDir: dir });
    // After picking a directory, if there's a book name set, check
    // the effective dir; otherwise check the base dir.
    const effectiveDir = store.bookName.trim()
      ? `${dir}\\${store.bookName.trim()}`
      : dir;
    await tryLoadSession(effectiveDir);
  }
}

async function startCapture(resume = false) {
  if (!store.region || !store.selectedWindow) return;

  const outputDir = store.effectiveOutputDir;
  if (!outputDir) return;

  store.setBatchConfig({
    delayBetweenMs: delayMs.value,
    maxPages: maxPages.value,
    filePrefix: filePrefix.value,
    pageTurnKey: pageTurnKey.value,
  });

  const startPage = resume ? store.pagesCaptured + 1 : 1;
  captureError.value = null;
  store.transitionTo("capturing");

  try {
    // start_batch_capture now returns immediately (Ok(()));
    // all progress comes via events.
    await invoke("start_batch_capture", {
      config: {
        x: Math.round(store.region.x),
        y: Math.round(store.region.y),
        width: Math.round(store.region.width),
        height: Math.round(store.region.height),
        window_handle: store.selectedWindow.handle,
        output_dir: outputDir,
        delay_between_ms: Math.max(delayMs.value, 200),
        max_pages: typeof maxPages.value === "number" && !Number.isNaN(maxPages.value) ? maxPages.value : null,
        file_prefix: filePrefix.value,
        page_turn_key: pageTurnKey.value,
        start_page: startPage,
        book_name: store.bookName,
      },
    });
  } catch (e) {
    console.error("Batch capture failed:", e);
    captureError.value = String(e);
    if (store.batchState === "capturing") {
      store.transitionTo("stopped");
    }
  }
}

async function pauseCapture() {
  await invoke("pause_batch_capture");
  store.transitionTo("paused");
}

async function resumeCapture() {
  await invoke("resume_batch_capture");
  store.transitionTo("capturing");
}

async function stopCapture() {
  await invoke("stop_batch_capture");
  // The capture-stopped event will fire and trigger the state transition.
}

function resetCapture() {
  store.transitionTo("idle");
  sessionLoaded.value = false;
}

function continueCapture() {
  startCapture(true);
}
</script>

<template>
  <div class="capture-view">
    <div class="view-header">
      <h2>Screen Capture Setup</h2>
      <SidecarStatus />
    </div>

    <WindowPicker />

    <RegionSelector />

    <!-- Region confirmation banner -->
    <div v-if="store.region && store.selectedWindow && !store.isCapturing" class="region-confirmed">
      <span class="check">✓</span>
      Region selected: {{ store.region.width }}×{{ store.region.height }} px
    </div>

    <!-- Session loaded banner -->
    <div v-if="sessionLoaded" class="session-loaded">
      <span class="check">↩</span>
      Session loaded — {{ store.pagesCaptured }} page{{ store.pagesCaptured === 1 ? '' : 's' }} captured previously. Ready to resume.
    </div>

    <div v-if="selectionSummary" class="selection-summary">
      <h3>Capture Configuration</h3>
      <p><strong>Window:</strong> {{ selectionSummary.window }}</p>
      <p><strong>Region:</strong> {{ selectionSummary.region }}</p>

      <div class="config-form">
        <label>
          Book / Project name
          <input
            :value="store.bookName"
            @input="store.setBookName(($event.target as HTMLInputElement).value)"
            type="text"
            placeholder="My Book Title"
          />
        </label>
        <label>
          Output directory
          <div class="dir-picker">
            <input
              :value="store.batchConfig.outputDir"
              readonly
              type="text"
              placeholder="Choose a folder…"
              @click="browseOutputDir"
            />
            <button class="browse-btn" @click="browseOutputDir" title="Browse…">📁</button>
          </div>
        </label>
        <label v-if="store.effectiveOutputDir">
          <span class="effective-path">→ {{ store.effectiveOutputDir }}</span>
        </label>
        <label>
          Capture type
          <select
            :value="store.nextCaptureType"
            @change="store.setNextCaptureType(($event.target as HTMLSelectElement).value as CaptureType)"
          >
            <option value="page">Page</option>
            <option value="cover">Cover</option>
            <option value="illustration">Illustration / Image</option>
          </select>
        </label>
        <label>
          Delay (ms)
          <input v-model.number="delayMs" type="number" min="200" step="100" />
        </label>
        <label>
          Max pages (blank = unlimited)
          <input v-model.number="maxPages" type="number" min="1" />
        </label>
        <label>
          File prefix
          <input v-model="filePrefix" type="text" />
        </label>
        <label>
          Page turn key
          <select v-model="pageTurnKey">
            <option>Right</option>
            <option>Left</option>
            <option>PageDown</option>
            <option>PageUp</option>
            <option>Space</option>
          </select>
        </label>
      </div>

      <div class="controls">
        <button
          v-if="store.batchState === 'idle'"
          class="btn start"
          :disabled="!canStart"
          @click="startCapture(false)"
        >
          Start Capture
        </button>
        <button v-if="store.isCapturing" class="btn pause" @click="pauseCapture">Pause</button>
        <button v-if="store.isPaused" class="btn resume" @click="resumeCapture">Resume</button>
        <button v-if="store.isCapturing || store.isPaused" class="btn stop" @click="stopCapture">Stop</button>
        <button
          v-if="store.isStopped"
          class="btn resume"
          :disabled="!canStart"
          @click="continueCapture"
        >
          Continue (from page {{ store.pagesCaptured + 1 }})
        </button>
        <button
          v-if="store.isStopped || store.batchState === 'completed'"
          class="btn reset"
          @click="resetCapture"
        >
          Reset
        </button>
      </div>

      <div v-if="captureError" class="capture-error">
        <strong>Error:</strong> {{ captureError }}
      </div>
    </div>

    <ProgressTracker v-if="store.batchState !== 'idle'" />
    <CapturedPagesPanel v-if="store.capturedPages.length > 0" />
  </div>
</template>

<style scoped>
.capture-view {
  padding: 1rem;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.view-header h2 {
  margin: 0;
}

.region-confirmed {
  margin-top: 0.5rem;
  padding: 0.4rem 0.7rem;
  background: #1b3a1b;
  border: 1px solid #2e7d32;
  border-radius: 4px;
  color: #a5d6a7;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.region-confirmed .check {
  font-size: 1rem;
}

.session-loaded {
  margin-top: 0.4rem;
  padding: 0.4rem 0.7rem;
  background: #1a2a3a;
  border: 1px solid #1565c0;
  border-radius: 4px;
  color: #90caf9;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.selection-summary {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-radius: 6px;
}

.selection-summary h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  color: #ccc;
}

.config-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.config-form label {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
  color: #aaa;
}

.config-form input,
.config-form select {
  margin-top: 0.2rem;
  padding: 0.35rem 0.5rem;
  background: #16213e;
  color: #eee;
  border: 1px solid #333;
  border-radius: 4px;
}

.dir-picker {
  display: flex;
  gap: 0.3rem;
  margin-top: 0.2rem;
}

.dir-picker input {
  flex: 1;
  margin-top: 0;
  cursor: pointer;
}

.browse-btn {
  padding: 0.3rem 0.5rem;
  background: #333;
  border: 1px solid #555;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.browse-btn:hover {
  background: #444;
}

.effective-path {
  font-size: 0.75rem;
  color: #666;
  font-style: italic;
}

.controls {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.btn {
  padding: 0.5rem 1.5rem;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.start { background: #4a9eff; }
.btn.start:hover:not(:disabled) { background: #3a8eee; }
.btn.pause { background: #e65100; }
.btn.pause:hover { background: #d84315; }
.btn.resume { background: #1b5e20; }
.btn.resume:hover { background: #2e7d32; }
.btn.stop { background: #b71c1c; }
.btn.stop:hover { background: #c62828; }
.btn.reset { background: #555; }
.btn.reset:hover { background: #666; }

.capture-error {
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #3a1a1a;
  border: 1px solid #b71c1c;
  border-radius: 4px;
  color: #ef9a9a;
  font-size: 0.85rem;
  word-break: break-word;
}
</style>
