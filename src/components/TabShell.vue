<script setup lang="ts">
import { computed } from "vue";
import { useUiStore, type TopTab } from "@/stores/ui";
import CaptureView from "@/views/CaptureView.vue";
import ReviewView from "@/views/ReviewView.vue";
import ExportView from "@/views/ExportView.vue";

const ui = useUiStore();

const tabs: { id: TopTab; label: string; icon: string }[] = [
  { id: "capture", label: "Capture", icon: "📷" },
  { id: "review", label: "Pages / Review", icon: "📄" },
  { id: "export", label: "Export", icon: "📦" },
];

function tabTitle(id: TopTab): string {
  if (id === "review" && !ui.isTabEnabled("review")) return "Capture at least one page to unlock";
  if (id === "export" && !ui.isTabEnabled("export")) return "Run OCR on at least one page to unlock";
  return "";
}
</script>

<template>
  <div class="tab-shell">
    <nav class="tab-nav" role="tablist">
      <span class="app-name">KindleOCR</span>
      <button
        v-for="tab in tabs"
        :key="tab.id"
        role="tab"
        :aria-selected="ui.activeTab === tab.id"
        :aria-disabled="!ui.isTabEnabled(tab.id)"
        :class="['tab-btn', { active: ui.activeTab === tab.id, disabled: !ui.isTabEnabled(tab.id) }]"
        :title="tabTitle(tab.id)"
        @click="ui.setTab(tab.id)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        {{ tab.label }}
      </button>
    </nav>

    <div class="tab-content">
      <CaptureView v-if="ui.activeTab === 'capture'" />
      <ReviewView v-else-if="ui.activeTab === 'review'" />
      <ExportView v-else-if="ui.activeTab === 'export'" />
    </div>
  </div>
</template>

<style scoped>
.tab-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.tab-nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0 0.75rem;
  border-bottom: 1px solid var(--border-color, #444);
  background: var(--nav-bg, #1a1a1a);
  flex-shrink: 0;
}

.app-name {
  font-weight: 600;
  font-size: 0.9rem;
  margin-right: 1rem;
  color: var(--text-muted, #aaa);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.85rem;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-muted, #aaa);
  font-size: 0.875rem;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;
}

.tab-btn:hover:not(.disabled) {
  color: var(--text-primary, #f0f0f0);
}

.tab-btn.active {
  color: var(--text-primary, #f0f0f0);
  border-bottom-color: var(--accent, #4a9eff);
}

.tab-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tab-icon {
  font-size: 0.8rem;
}

.tab-content {
  flex: 1;
  overflow: auto;
}
</style>
