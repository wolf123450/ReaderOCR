<script setup lang="ts">
import { ref } from "vue";
import { open } from "@tauri-apps/plugin-dialog";
import { useCaptureStore, type CapturedPage } from "@/stores/capture";

const props = defineProps<{
  visible: boolean;
  insertIndex: number; // 0-based; page will be inserted AT this position
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const capture = useCaptureStore();

type InsertMode = "capture" | "file";
const mode = ref<InsertMode>("capture");
const selectedFilePath = ref<string | null>(null);

async function browseFile() {
  const result = await open({
    filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "webp"] }],
    multiple: false,
  });
  if (typeof result === "string") {
    selectedFilePath.value = result;
  }
}

function insert() {
  if (mode.value === "file" && selectedFilePath.value) {
    const newPage: CapturedPage = {
      pageNumber: props.insertIndex + 1, // will be renumbered
      imagePath: selectedFilePath.value,
      captureType: "page",
      timestamp: Date.now(),
      captureStatus: "ok",
      pageType: "text",
      ocrStatus: "pending",
    };
    capture.insertPageAt(props.insertIndex, newPage);
  }
  // "capture" mode: just close — the caller (ReviewView) handles switching to Capture tab
  emit("close");
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-backdrop" @click.self="emit('close')">
      <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="insert-title">
        <h2 id="insert-title">Insert page at position {{ insertIndex + 1 }}</h2>

        <div class="option-list">
          <label class="option">
            <input v-model="mode" type="radio" value="capture" />
            <div>
              <strong>Capture a new page now</strong>
              <p>Switches to the Capture tab with the slot pre-queued.</p>
            </div>
          </label>
          <label class="option">
            <input v-model="mode" type="radio" value="file" />
            <div>
              <strong>Import image from file</strong>
              <p>Choose a PNG or JPEG from your computer.</p>
              <button
                v-if="mode === 'file'"
                class="browse-btn"
                @click.prevent="browseFile"
              >
                {{ selectedFilePath ? selectedFilePath.split(/[\\/]/).pop() : "Browse…" }}
              </button>
            </div>
          </label>
        </div>

        <footer class="dialog-footer">
          <button
            class="btn-primary"
            :disabled="mode === 'file' && !selectedFilePath"
            @click="insert"
          >
            Insert
          </button>
          <button class="btn-secondary" @click="emit('close')">Cancel</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--nav-bg, #1a1a1a);
  border: 1px solid var(--border-color, #444);
  border-radius: 8px;
  padding: 1.5rem;
  width: 380px;
  color: var(--text-primary, #f0f0f0);
}

.dialog h2 { margin: 0 0 1rem 0; font-size: 1rem; }

.option-list { display: flex; flex-direction: column; gap: 0.75rem; }

.option {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  border: 1px solid transparent;
}

.option:hover { border-color: var(--border-color, #444); }

.option input[type="radio"] { margin-top: 3px; flex-shrink: 0; }

.option strong { font-size: 0.875rem; }

.option p {
  margin: 0.15rem 0 0;
  font-size: 0.78rem;
  color: var(--text-muted, #aaa);
}

.browse-btn {
  margin-top: 0.4rem;
  padding: 0.3rem 0.6rem;
  background: transparent;
  border: 1px solid var(--border-color, #555);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  font-size: 0.78rem;
  cursor: pointer;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog-footer {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color, #444);
}

.btn-primary {
  padding: 0.4rem 1rem;
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
  padding: 0.4rem 1rem;
  background: transparent;
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  cursor: pointer;
  font-size: 0.875rem;
}
</style>
