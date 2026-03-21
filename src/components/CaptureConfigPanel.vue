<script setup lang="ts">
import { computed } from "vue";
import { useUiStore } from "@/stores/ui";
import { useCaptureStore } from "@/stores/capture";

const emit = defineEmits<{
  "pause-and-expand": [];
}>();

const ui = useUiStore();
const capture = useCaptureStore();

const canCollapse = computed(() => !!capture.selectedWindow && !!capture.region);
const isCollapsed = computed(() => ui.captureConfigCollapsed && canCollapse.value);

const windowTitle = computed(() => capture.selectedWindow?.title ?? "—");
const regionDims = computed(() =>
  capture.region ? `${capture.region.width}×${capture.region.height} px` : ""
);

function collapse() {
  if (canCollapse.value) ui.setCaptureConfigCollapsed(true);
}

function expand() {
  if (capture.isCapturing) {
    emit("pause-and-expand");
  } else {
    ui.setCaptureConfigCollapsed(false);
  }
}
</script>

<template>
  <div class="capture-config-panel">
    <!-- Collapsed summary bar -->
    <div v-if="isCollapsed" class="summary-bar">
      <span class="summary-icon">📷</span>
      <span class="summary-text">
        Capturing from: <strong>{{ windowTitle }}</strong> — {{ regionDims }} region
      </span>
      <button class="edit-btn" @click="expand" title="Edit capture configuration">
        ✎ Edit
      </button>
    </div>

    <!-- Expanded content -->
    <div v-else class="expanded-content">
      <div class="panel-header">
        <button
          class="collapse-btn"
          :disabled="!canCollapse"
          :title="!canCollapse ? 'Select a window and region first' : 'Collapse'"
          @click="collapse"
        >
          ▲ Collapse
        </button>
      </div>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.capture-config-panel {
  width: 100%;
}

/* ── Collapsed summary bar ────────────────────────────────────────── */
.summary-bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.75rem;
  background: #1a2a3a;
  border: 1px solid #1565c0;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.summary-icon { font-size: 1.1rem; }

.summary-text {
  flex: 1;
  color: #ccc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-text strong { color: #e0e0e0; }

.edit-btn {
  padding: 0.3rem 0.75rem;
  background: transparent;
  border: 1px solid #1565c0;
  border-radius: 4px;
  color: #90caf9;
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.edit-btn:hover { background: #1a3a5a; }

/* ── Expanded content ─────────────────────────────────────────────── */
.expanded-content {
  overflow: hidden;
  animation: expand-in 200ms ease-in;
}

@keyframes expand-in {
  from { max-height: 0; opacity: 0.5; }
  to   { max-height: 2000px; opacity: 1; }
}

.panel-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.25rem;
}

.collapse-btn {
  padding: 0.25rem 0.6rem;
  background: transparent;
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  cursor: pointer;
  font-size: 0.78rem;
}

.collapse-btn:not(:disabled):hover { color: var(--text-primary, #f0f0f0); }
.collapse-btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
