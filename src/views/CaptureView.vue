<script setup lang="ts">
import { computed, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import WindowPicker from "@/components/WindowPicker.vue";
import RegionSelector from "@/components/RegionSelector.vue";
import ProgressTracker from "@/components/ProgressTracker.vue";
import SidecarStatus from "@/components/SidecarStatus.vue";
import { useCaptureStore, type CaptureProgress } from "@/stores/capture";

const store = useCaptureStore();

const outputDir = ref("");
const delayMs = ref(1500);
const maxPages = ref<number | null>(null);
const filePrefix = ref("page");
const pageTurnKey = ref("Right");

const selectionSummary = computed(() => {
  if (!store.region || !store.selectedWindow) return null;
  return {
    window: store.selectedWindow.title,
    region: `${store.region.width}×${store.region.height} at (${store.region.x}, ${store.region.y})`,
  };
});

const canStart = computed(
  () => store.hasSelection && store.batchState === "idle" && outputDir.value.trim() !== ""
);

async function startCapture() {
  if (!store.region || !store.selectedWindow) return;

  store.setBatchConfig({
    outputDir: outputDir.value,
    delayBetweenMs: delayMs.value,
    maxPages: maxPages.value,
    filePrefix: filePrefix.value,
    pageTurnKey: pageTurnKey.value,
  });
  store.transitionTo("capturing");

  try {
    const results = await invoke<CaptureProgress[]>("start_batch_capture", {
      config: {
        x: store.region.x,
        y: store.region.y,
        width: store.region.width,
        height: store.region.height,
        window_handle: store.selectedWindow.handle,
        output_dir: outputDir.value,
        delay_between_ms: Math.max(delayMs.value, 200),
        max_pages: maxPages.value,
        file_prefix: filePrefix.value,
        page_turn_key: pageTurnKey.value,
      },
    });
    for (const r of results) {
      store.recordCapture(r);
    }
    if (store.batchState === "capturing") {
      store.transitionTo("completed");
    }
  } catch (e) {
    store.transitionTo("stopped");
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
  store.transitionTo("stopped");
}

function resetCapture() {
  store.transitionTo("idle");
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

    <div v-if="selectionSummary" class="selection-summary">
      <p><strong>Window:</strong> {{ selectionSummary.window }}</p>
      <p><strong>Region:</strong> {{ selectionSummary.region }}</p>

      <div class="config-form">
        <label>
          Output directory
          <input v-model="outputDir" type="text" placeholder="C:\captures" />
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
        <button v-if="store.batchState === 'idle'" class="btn start" :disabled="!canStart" @click="startCapture">
          Start Capture
        </button>
        <button v-if="store.isCapturing" class="btn pause" @click="pauseCapture">Pause</button>
        <button v-if="store.isPaused" class="btn resume" @click="resumeCapture">Resume</button>
        <button v-if="store.isCapturing || store.isPaused" class="btn stop" @click="stopCapture">Stop</button>
        <button v-if="store.batchState === 'stopped' || store.batchState === 'completed'" class="btn reset" @click="resetCapture">
          Reset
        </button>
      </div>
    </div>

    <ProgressTracker v-if="store.batchState !== 'idle'" />
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

.selection-summary {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-radius: 6px;
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
</style>
