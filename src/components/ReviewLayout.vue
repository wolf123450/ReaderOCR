<script setup lang="ts">
import { computed } from "vue";
import { useUiStore, type ReviewSubtab } from "@/stores/ui";
import { useCaptureStore } from "@/stores/capture";

const ui = useUiStore();
const capture = useCaptureStore();

const subtabs: { id: ReviewSubtab; label: string }[] = [
  { id: "pages", label: "Pages" },
  { id: "ocr", label: "OCR" },
  { id: "review", label: "Review" },
  { id: "edit", label: "Edit" },
];

function subtabTitle(id: ReviewSubtab): string {
  if (id === "review" && !ui.isSubtabEnabled("review")) return "Run OCR on at least one page to unlock";
  if (id === "edit" && !ui.isSubtabEnabled("edit")) return "Run OCR on at least one page to unlock";
  return "";
}
</script>

<template>
  <div class="review-layout">
    <!-- Subtab bar -->
    <nav class="subtab-nav" role="tablist">
      <button
        v-for="sub in subtabs"
        :key="sub.id"
        role="tab"
        :aria-selected="ui.activeReviewSubtab === sub.id"
        :aria-disabled="!ui.isSubtabEnabled(sub.id)"
        :class="['subtab-btn', { active: ui.activeReviewSubtab === sub.id, disabled: !ui.isSubtabEnabled(sub.id) }]"
        :title="subtabTitle(sub.id)"
        @click="ui.setSubtab(sub.id)"
      >
        {{ sub.label }}
      </button>
    </nav>

    <!-- Main area: filmstrip + content -->
    <div class="review-body">
      <!-- Filmstrip sidebar -->
      <aside class="filmstrip-sidebar">
        <div class="filmstrip-list">
          <div
            v-for="(page, idx) in capture.capturedPages"
            :key="page.pageNumber"
            :class="['filmstrip-thumb', { selected: ui.selectedPageIndex === idx }]"
            @click="ui.selectPage(idx)"
          >
            <div class="thumb-number">{{ page.pageNumber }}</div>
          </div>
        </div>
      </aside>

      <!-- Content area driven by active subtab -->
      <main class="subtab-content">
        <slot :subtab="ui.activeReviewSubtab" />
      </main>
    </div>
  </div>
</template>

<style scoped>
.review-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.subtab-nav {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-color, #444);
  flex-shrink: 0;
  padding: 0 0.5rem;
}

.subtab-btn {
  padding: 0.35rem 0.75rem;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-muted, #aaa);
  font-size: 0.8rem;
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}

.subtab-btn:hover:not(.disabled) {
  color: var(--text-primary, #f0f0f0);
}

.subtab-btn.active {
  color: var(--text-primary, #f0f0f0);
  border-bottom-color: var(--accent, #4a9eff);
}

.subtab-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.review-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.filmstrip-sidebar {
  width: 90px;
  min-width: 60px;
  border-right: 1px solid var(--border-color, #444);
  overflow-y: auto;
  flex-shrink: 0;
}

.filmstrip-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
}

.filmstrip-thumb {
  height: 60px;
  border-radius: 3px;
  border: 2px solid transparent;
  background: var(--thumb-bg, #2a2a2a);
  cursor: pointer;
  display: flex;
  align-items: flex-end;
  padding: 2px;
  transition: border-color 0.1s;
}

.filmstrip-thumb:hover {
  border-color: var(--accent-dim, #2a6ab0);
}

.filmstrip-thumb.selected {
  border-color: var(--accent, #4a9eff);
}

.thumb-number {
  font-size: 0.65rem;
  color: var(--text-muted, #aaa);
}

.subtab-content {
  flex: 1;
  overflow: auto;
  padding: 1rem;
}
</style>
