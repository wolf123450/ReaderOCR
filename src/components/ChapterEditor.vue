<script setup lang="ts">
import { ref } from "vue";
import { useChaptersStore, type ChapterSegment } from "@/stores/chapters";
import { useCaptureStore } from "@/stores/capture";
import ChapterItem from "@/components/ChapterItem.vue";

const chapters = useChaptersStore();
const capture = useCaptureStore();

const draggingIndex = ref<number | null>(null);

function addChapter() {
  // Start new chapter from selected pages or at end
  chapters.addChapter();
}

function onDragStart(chapterIndex: number) {
  draggingIndex.value = chapterIndex;
}

function onDrop(targetIndex: number) {
  if (draggingIndex.value !== null && draggingIndex.value !== targetIndex) {
    chapters.reorderChapters(draggingIndex.value, targetIndex);
  }
  draggingIndex.value = null;
}

function onDragOver(e: DragEvent) {
  e.preventDefault();
}
</script>

<template>
  <div class="chapter-editor">
    <div class="editor-header">
      <h3>Chapter Structure</h3>
      <div class="header-actions">
        <button class="btn-secondary" @click="addChapter">+ Add Chapter</button>
        <button class="btn-ghost" title="Re-run chapter auto-detection (step 22)">Auto ↺</button>
      </div>
    </div>

    <div v-if="chapters.sortedChapters.length === 0" class="empty-hint">
      <p>No chapters yet. Click <strong>+ Add Chapter</strong> to get started.</p>
    </div>

    <ul class="chapter-list" v-else>
      <li
        v-for="ch in chapters.sortedChapters"
        :key="ch.id"
        class="chapter-row-wrapper"
        draggable="true"
        @dragstart="onDragStart(ch.chapterIndex)"
        @dragover="onDragOver"
        @drop="onDrop(ch.chapterIndex)"
        :class="{ dragging: draggingIndex === ch.chapterIndex }"
      >
        <ChapterItem :chapter="ch" />
      </li>
    </ul>

    <div v-if="!chapters.isValid()" class="validation-errors">
      <h4>⚠ Validation errors</h4>
      <ul>
        <li v-for="(err, i) in chapters.getValidationErrors()" :key="i">{{ err }}</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.chapter-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor-header h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--text-primary, #f0f0f0);
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-secondary {
  padding: 0.35rem 0.7rem;
  background: transparent;
  border: 1px solid var(--accent, #4a9eff);
  border-radius: 4px;
  color: var(--accent, #4a9eff);
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-ghost {
  padding: 0.35rem 0.7rem;
  background: transparent;
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-ghost:hover, .btn-secondary:hover {
  opacity: 0.8;
}

.chapter-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chapter-row-wrapper {
  cursor: grab;
  border-radius: 4px;
  transition: opacity 150ms;
}

.chapter-row-wrapper.dragging { opacity: 0.4; }
.chapter-row-wrapper:active { cursor: grabbing; }

.empty-hint {
  color: var(--text-muted, #aaa);
  font-style: italic;
  font-size: 0.875rem;
}

.validation-errors {
  padding: 0.6rem;
  background: #3a1a1a;
  border: 1px solid #b71c1c;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #ef9a9a;
}

.validation-errors h4 { margin: 0 0 0.4rem 0; }
.validation-errors ul { margin: 0; padding-left: 1rem; }
</style>
