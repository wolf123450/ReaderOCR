<script setup lang="ts">
import { useUiStore, type ReviewSubtab } from "@/stores/ui";
import FilmstripSidebar from "@/components/FilmstripSidebar.vue";

const ui = useUiStore();

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

const emit = defineEmits<{
  (e: "insertBefore", index: number): void;
  (e: "insertAfter", index: number): void;
}>();
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
      <FilmstripSidebar
        @insert-before="(idx) => emit('insertBefore', idx)"
        @insert-after="(idx) => emit('insertAfter', idx)"
      />

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

.subtab-content {
  flex: 1;
  overflow: auto;
  padding: 1rem;
}
</style>
