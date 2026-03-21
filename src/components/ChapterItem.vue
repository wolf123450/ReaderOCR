<script setup lang="ts">
import { ref, computed } from "vue";
import { useChaptersStore, type ChapterSegment, type ChapterType } from "@/stores/chapters";
import { useCaptureStore } from "@/stores/capture";

const props = defineProps<{ chapter: ChapterSegment }>();

const chapters = useChaptersStore();
const capture = useCaptureStore();

const editing = ref(false);
const expanded = ref(false);
const editTitle = ref(props.chapter.title);

const chapterTypeOptions: { value: ChapterType; label: string }[] = [
  { value: "front_matter", label: "Front Matter" },
  { value: "chapter", label: "Chapter" },
  { value: "back_matter", label: "Back Matter" },
  { value: "part", label: "Part Divider" },
  { value: "appendix", label: "Appendix" },
];

/** Human-readable page range, e.g. "p.3–14" */
const pageRangeLabel = computed(() => {
  const indices = props.chapter.sources.map((s) => s.pageIndex);
  if (indices.length === 0) return "—";
  const min = Math.min(...indices);
  const max = Math.max(...indices);
  return min === max ? `p.${min + 1}` : `p.${min + 1}–${max + 1}`;
});

function startEdit() {
  editTitle.value = props.chapter.title;
  editing.value = true;
}

function commitEdit() {
  chapters.updateChapter(props.chapter.id, { title: editTitle.value.trim() || "Untitled" });
  editing.value = false;
}

function cancelEdit() {
  editing.value = false;
}

function deleteChapter() {
  chapters.removeChapter(props.chapter.id);
}

function onTypeChange(e: Event) {
  chapters.updateChapter(props.chapter.id, {
    chapterType: (e.target as HTMLSelectElement).value as ChapterType,
  });
}
</script>

<template>
  <div class="chapter-item">
    <div class="chapter-row">
      <span class="drag-handle" title="Drag to reorder">≡</span>

      <!-- Inline title edit -->
      <span v-if="!editing" class="chapter-title" @dblclick="startEdit" :title="'Double-click to rename'">
        {{ chapter.title }}
      </span>
      <input
        v-else
        class="title-input"
        v-model="editTitle"
        @keydown.enter="commitEdit"
        @keydown.escape="cancelEdit"
        @blur="commitEdit"
        autofocus
      />

      <span class="page-range">{{ pageRangeLabel }}</span>

      <select class="type-select" :value="chapter.chapterType" @change="onTypeChange" title="Chapter type">
        <option v-for="opt in chapterTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>

      <button class="action-btn" @click="startEdit" title="Rename">✎</button>
      <button class="action-btn expand-btn" @click="expanded = !expanded" :title="expanded ? 'Collapse' : 'Expand'">
        {{ expanded ? '▲' : '▼' }}
      </button>
      <button class="action-btn delete-btn" @click="deleteChapter" title="Delete chapter">✕</button>
    </div>

    <div v-if="expanded" class="chapter-detail">
      <p class="detail-hint">Pages in this chapter (drag from filmstrip to add/remove):</p>
      <ul class="source-list">
        <li v-for="(src, i) in chapter.sources" :key="i">
          Page {{ src.pageIndex + 1 }}
          <span v-if="src.start !== 0 || src.end !== 1.0" class="fraction">
            [{{ (src.start * 100).toFixed(0) }}%–{{ (src.end * 100).toFixed(0) }}%]
          </span>
        </li>
        <li v-if="chapter.sources.length === 0" class="empty-sources">No pages assigned yet.</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.chapter-item {
  background: #1a1a2e;
  border: 1px solid var(--border-color, #333);
  border-radius: 4px;
}

.chapter-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
}

.drag-handle {
  color: var(--text-muted, #666);
  user-select: none;
  cursor: grab;
  font-size: 1rem;
  flex-shrink: 0;
}

.chapter-title {
  flex: 1;
  font-size: 0.875rem;
  color: var(--text-primary, #f0f0f0);
  cursor: text;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title-input {
  flex: 1;
  background: #16213e;
  border: 1px solid var(--accent, #4a9eff);
  border-radius: 3px;
  color: #eee;
  font-size: 0.875rem;
  padding: 0.15rem 0.4rem;
}

.page-range {
  font-size: 0.75rem;
  color: var(--text-muted, #aaa);
  white-space: nowrap;
  flex-shrink: 0;
}

.type-select {
  background: #16213e;
  border: 1px solid var(--border-color, #444);
  border-radius: 3px;
  color: var(--text-muted, #aaa);
  font-size: 0.75rem;
  padding: 1px 3px;
  flex-shrink: 0;
}

.action-btn {
  padding: 0.15rem 0.35rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  color: var(--text-muted, #888);
  cursor: pointer;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.action-btn:hover { color: var(--text-primary, #f0f0f0); border-color: var(--border-color, #444); }
.delete-btn:hover { color: #f77; }

/* Detail panel */
.chapter-detail {
  border-top: 1px solid var(--border-color, #333);
  padding: 0.5rem 0.8rem;
}

.detail-hint {
  font-size: 0.75rem;
  color: var(--text-muted, #aaa);
  margin: 0 0 0.35rem 0;
  font-style: italic;
}

.source-list {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.8rem;
  color: #ccc;
}

.fraction { color: #ffb400; margin-left: 0.3rem; }
.empty-sources { color: #666; font-style: italic; }
</style>
