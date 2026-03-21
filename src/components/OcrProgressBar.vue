<script setup lang="ts">
import { computed } from "vue";
import { useOcrStore } from "@/stores/ocr";

const ocr = useOcrStore();

const percent = computed(() => {
  const { current, total } = ocr.batchProgress;
  if (total === 0) return 0;
  return Math.round((current / total) * 100);
});

const pages = computed(() => {
  // Show last 20 processed pages
  return [...ocr.pageResults.entries()]
    .slice(-20)
    .reverse()
    .map(([num, result]) => ({
      num,
      confidence: result.confidence,
      error: result.errorMessage,
    }));
});
</script>

<template>
  <div class="ocr-progress-bar">
    <div class="progress-header">
      <span class="progress-label">
        Progress: {{ ocr.batchProgress.current }} / {{ ocr.batchProgress.total }}
        <span v-if="ocr.batchProgress.errors > 0" class="error-count">
          · {{ ocr.batchProgress.errors }} error(s)
        </span>
      </span>
      <span class="progress-pct">{{ percent }}%</span>
    </div>

    <div class="progress-track">
      <div class="progress-fill" :style="{ width: `${percent}%` }" />
    </div>

    <div class="results-list">
      <div
        v-for="entry in pages"
        :key="entry.num"
        :class="['result-row', { error: !!entry.error, low: !entry.error && entry.confidence < 80 }]"
      >
        <span class="result-icon">{{ entry.error ? "⚠" : "☑" }}</span>
        <span class="result-page">p.{{ entry.num }}</span>
        <span v-if="entry.error" class="result-detail error-text">{{ entry.error }}</span>
        <span v-else class="result-detail">
          {{ entry.confidence.toFixed(1) }}% confidence
          <span v-if="entry.confidence < 80" class="low-warning">(low — review recommended)</span>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ocr-progress-bar {
  margin-top: 0.75rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--text-muted, #aaa);
  margin-bottom: 0.35rem;
}

.error-count { color: #f77; }

.progress-track {
  height: 8px;
  background: #333;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent, #4a9eff);
  border-radius: 4px;
  transition: width 0.2s;
}

.results-list {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 200px;
  overflow-y: auto;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--text-muted, #aaa);
  padding: 1px 0;
}

.result-row.error { color: #f77; }
.result-row.low { color: #ffb400; }

.result-icon { font-size: 0.7rem; width: 14px; }
.result-page { font-weight: 600; min-width: 30px; }
.result-detail { flex: 1; }
.low-warning { margin-left: 0.3rem; opacity: 0.8; }
.error-text { font-style: italic; }
</style>
