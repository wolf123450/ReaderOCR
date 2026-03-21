<script setup lang="ts">
import { ref } from "vue";
import { useUiStore } from "@/stores/ui";
import ReviewLayout from "@/components/ReviewLayout.vue";
import PageDetailPane from "@/components/PageDetailPane.vue";
import InsertPageDialog from "@/components/InsertPageDialog.vue";
import OcrSubtab from "@/views/OcrSubtab.vue";

const ui = useUiStore();

const insertDialog = ref<{ visible: boolean; insertIndex: number }>({
  visible: false,
  insertIndex: 0,
});

function openInsertBefore(index: number) {
  insertDialog.value = { visible: true, insertIndex: index };
}

function openInsertAfter(index: number) {
  insertDialog.value = { visible: true, insertIndex: index + 1 };
}
</script>

<template>
  <ReviewLayout
    @insert-before="openInsertBefore"
    @insert-after="openInsertAfter"
  >
    <template #default="{ subtab }">
      <PageDetailPane
        v-if="subtab === 'pages'"
        @insert-before="ui.selectedPageIndex !== null && openInsertBefore(ui.selectedPageIndex)"
        @insert-after="ui.selectedPageIndex !== null && openInsertAfter(ui.selectedPageIndex)"
      />
      <OcrSubtab v-else-if="subtab === 'ocr'" />
      <div v-else-if="subtab === 'review'" class="subtab-stub">
        <p>Side-by-side review (step 24/25)</p>
      </div>
      <div v-else-if="subtab === 'edit'" class="subtab-stub">
        <p>Batch text editing (step 27)</p>
      </div>
    </template>
  </ReviewLayout>

  <InsertPageDialog
    :visible="insertDialog.visible"
    :insert-index="insertDialog.insertIndex"
    @close="insertDialog.visible = false"
  />
</template>

<style scoped>
.subtab-stub {
  color: var(--text-muted, #aaa);
  font-style: italic;
}
</style>
