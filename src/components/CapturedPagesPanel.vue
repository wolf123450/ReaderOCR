<script setup lang="ts">
import { computed } from "vue";
import { useCaptureStore } from "@/stores/capture";

const store = useCaptureStore();

const pages = computed(() => [...store.capturedPages].reverse());

const stats = computed(() => {
  const total = store.capturedPages.length;
  const ok = store.capturedPages.filter((p) => p.captureStatus === "ok").length;
  const errors = total - ok;
  const covers = store.capturedPages.filter((p) => p.captureType === "cover").length;
  const illustrations = store.capturedPages.filter((p) => p.captureType === "illustration").length;
  return { total, ok, errors, covers, illustrations };
});

function typeLabel(type: string): string {
  switch (type) {
    case "cover": return "📕 Cover";
    case "illustration": return "🖼 Image";
    default: return "📄 Page";
  }
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}
</script>

<template>
  <div class="captured-pages-panel">
    <h3>
      Captured Pages
      <span class="stats">
        {{ stats.ok }} captured
        <template v-if="stats.errors"> · {{ stats.errors }} errors</template>
        <template v-if="stats.covers"> · {{ stats.covers }} cover(s)</template>
        <template v-if="stats.illustrations"> · {{ stats.illustrations }} illustration(s)</template>
      </span>
    </h3>

    <div class="pages-list">
      <div
        v-for="page in pages"
        :key="page.pageNumber"
        class="page-item"
        :class="{ error: page.captureStatus === 'needs_recapture' }"
      >
        <span class="page-num">#{{ page.pageNumber }}</span>
        <span class="page-type">{{ typeLabel(page.captureType) }}</span>
        <span class="page-file" :title="page.imagePath">{{ fileName(page.imagePath) }}</span>
        <span v-if="page.captureStatus === 'needs_recapture'" class="page-err" :title="page.errorMessage">
          ✗ {{ page.errorMessage }}
        </span>
        <span v-else class="page-ok">✓</span>
      </div>

      <p v-if="pages.length === 0" class="empty">No pages captured yet.</p>
    </div>
  </div>
</template>

<style scoped>
.captured-pages-panel {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-radius: 6px;
}

.captured-pages-panel h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.95rem;
  color: #ccc;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.stats {
  font-size: 0.75rem;
  color: #888;
  font-weight: normal;
}

.pages-list {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.page-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.5rem;
  background: #16213e;
  border-radius: 4px;
  font-size: 0.8rem;
}

.page-item.error {
  background: #2a1515;
  border-left: 3px solid #e57373;
}

.page-num {
  color: #4a9eff;
  font-weight: 600;
  min-width: 2.5em;
}

.page-type {
  color: #aaa;
  min-width: 5em;
}

.page-file {
  color: #ccc;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-ok {
  color: #81c784;
}

.page-err {
  color: #e57373;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty {
  color: #666;
  font-size: 0.85rem;
  text-align: center;
  margin: 0.5rem 0;
}
</style>
