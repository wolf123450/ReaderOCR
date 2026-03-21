<script setup lang="ts">
import { useUiStore } from "@/stores/ui";
import ReviewLayout from "@/components/ReviewLayout.vue";

const ui = useUiStore();
</script>

<template>
  <ReviewLayout>
    <template #default="{ subtab }">
      <div v-if="subtab === 'pages'" class="subtab-stub">
        <p>Pages view — drag-drop management (step 41)</p>
      </div>
      <div v-else-if="subtab === 'ocr'" class="subtab-stub">
        <p>OCR workflow (step 44)</p>
      </div>
      <div v-else-if="subtab === 'review'" class="subtab-stub">
        <p>Side-by-side review (step 24/25)</p>
      </div>
      <div v-else-if="subtab === 'edit'" class="subtab-stub">
        <p>Batch text editing (step 27)</p>
      </div>
    </template>
  </ReviewLayout>
</template>

<style scoped>
.subtab-stub {
  color: var(--text-muted, #aaa);
  font-style: italic;
}
</style>
