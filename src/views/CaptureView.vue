<script setup lang="ts">
import { computed } from "vue";
import WindowPicker from "@/components/WindowPicker.vue";
import RegionSelector from "@/components/RegionSelector.vue";
import { useCaptureStore } from "@/stores/capture";

const store = useCaptureStore();

const selectionSummary = computed(() => {
  if (!store.region || !store.selectedWindow) return null;
  return {
    window: store.selectedWindow.title,
    region: `${store.region.width}×${store.region.height} at (${store.region.x}, ${store.region.y})`,
  };
});
</script>

<template>
  <div class="capture-view">
    <h2>Screen Capture Setup</h2>

    <WindowPicker />

    <RegionSelector />

    <div v-if="selectionSummary" class="selection-summary">
      <p><strong>Window:</strong> {{ selectionSummary.window }}</p>
      <p><strong>Region:</strong> {{ selectionSummary.region }}</p>
      <button class="confirm-btn">Start Capture</button>
    </div>
  </div>
</template>

<style scoped>
.capture-view {
  padding: 1rem;
}

.selection-summary {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #1a1a2e;
  border-radius: 6px;
}

.confirm-btn {
  margin-top: 0.5rem;
  padding: 0.5rem 1.5rem;
  background: #4a9eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.confirm-btn:hover {
  background: #3a8eee;
}
</style>
