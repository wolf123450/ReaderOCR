<script setup lang="ts">
import { computed } from "vue";
import { useCaptureStore } from "@/stores/capture";

const store = useCaptureStore();

const progressPercent = computed(() => {
  if (!store.batchConfig.maxPages) return null;
  return Math.round((store.pagesCaptured / store.batchConfig.maxPages) * 100);
});

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    idle: "Ready",
    capturing: "Capturing…",
    paused: "Paused",
    stopped: "Stopped",
    completed: "Completed",
  };
  return labels[store.batchState] ?? store.batchState;
});

const lastCapture = computed(() => {
  if (store.captureHistory.length === 0) return null;
  return store.captureHistory[store.captureHistory.length - 1];
});

const errorCount = computed(() =>
  store.captureHistory.filter((c) => c.status === "error").length
);
</script>

<template>
  <div class="progress-tracker">
    <div class="status-row">
      <span class="status-badge" :class="store.batchState">
        {{ statusLabel }}
      </span>
      <span class="page-count">
        {{ store.pagesCaptured }} page{{ store.pagesCaptured === 1 ? "" : "s" }} captured
        <template v-if="store.batchConfig.maxPages">
          / {{ store.batchConfig.maxPages }}
        </template>
        <template v-if="errorCount > 0">
          · <span class="error-count">{{ errorCount }} error{{ errorCount === 1 ? "" : "s" }}</span>
        </template>
      </span>
    </div>

    <div v-if="progressPercent !== null" class="progress-bar">
      <div class="progress-fill" :style="{ width: progressPercent + '%' }" />
      <span class="progress-label">{{ progressPercent }}%</span>
    </div>

    <div v-if="lastCapture" class="last-capture">
      <span class="last-label">Last:</span>
      <span v-if="lastCapture.status === 'captured'" class="capture-ok">
        ✓ Page {{ lastCapture.pageNumber }}
      </span>
      <span v-else class="capture-err">
        ✗ {{ lastCapture.errorMessage }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.progress-tracker {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-radius: 6px;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.status-badge {
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-badge.idle { background: #333; color: #aaa; }
.status-badge.capturing { background: #1b5e20; color: #a5d6a7; }
.status-badge.paused { background: #e65100; color: #ffcc80; }
.status-badge.stopped { background: #b71c1c; color: #ef9a9a; }
.status-badge.completed { background: #1565c0; color: #90caf9; }

.page-count {
  font-variant-numeric: tabular-nums;
  color: #ccc;
}

.progress-bar {
  height: 6px;
  background: #333;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.5rem;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: #4a9eff;
  transition: width 0.3s ease;
}

.progress-label {
  position: absolute;
  right: 0;
  top: -16px;
  font-size: 0.7rem;
  color: #888;
}

.error-count {
  color: #e57373;
}

.last-capture {
  font-size: 0.8rem;
  color: #888;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.last-label {
  color: #666;
}

.capture-ok { color: #81c784; }
.capture-err { color: #e57373; }
</style>
