<script setup lang="ts">
import { ref, computed } from "vue";
import { useChaptersStore, type ChapterSegment, type ChapterType } from "@/stores/chapters";
import { useUiStore } from "@/stores/ui";
import { useCaptureStore } from "@/stores/capture";

const props = defineProps<{ chapter: ChapterSegment }>();

const chapters = useChaptersStore();
const ui = useUiStore();
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

/** Page number label for a source entry, using captured-page data when available. */
function pageLabel(pageIndex: number): string {
  const page = capture.capturedPages[pageIndex];
  return page ? `Page ${page.pageNumber}` : `Page ${pageIndex + 1}`;
}

/** Currently selected page index (from filmstrip selection). */
const selectedIdx = computed(() => ui.selectedPageIndex);

/** True if the selected page is already in THIS chapter. */
const selectedInThisChapter = computed(() =>
  selectedIdx.value !== null &&
  props.chapter.sources.some((s) => s.pageIndex === selectedIdx.value)
);

/** The chapter that currently owns the selected page (may be a different chapter). */
const selectedPageChapter = computed(() => {
  if (selectedIdx.value === null) return null;
  return chapters.getChapterForPage(selectedIdx.value);
});

/** True if the selected page is assigned to a different chapter (will be moved). */
const willMoveFromOtherChapter = computed(() =>
  selectedPageChapter.value !== null &&
  selectedPageChapter.value.id !== props.chapter.id
);

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

function addSelectedPage() {
  if (selectedIdx.value === null) return;
  chapters.assignPageToChapter(props.chapter.id, selectedIdx.value);
}

function removePage(pageIndex: number) {
  chapters.removePageFromChapter(props.chapter.id, pageIndex);
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
      <!-- Assigned pages list -->
      <ul class="source-list">
        <li
          v-for="(src, i) in chapter.sources"
          :key="i"
          class="source-entry"
        >
          <span>{{ pageLabel(src.pageIndex) }}</span>
          <span v-if="src.start !== 0 || src.end !== 1.0" class="fraction">
            [{{ (src.start * 100).toFixed(0) }}%–{{ (src.end * 100).toFixed(0) }}%]
          </span>
          <button class="remove-page-btn" title="Remove from chapter" @click="removePage(src.pageIndex)">✕</button>
        </li>
        <li v-if="chapter.sources.length === 0" class="empty-sources">No pages assigned yet.</li>
      </ul>

      <!-- Add currently selected filmstrip page -->
      <div class="add-page-row">
        <button
          class="add-page-btn"
          :disabled="selectedIdx === null || selectedInThisChapter"
          :title="selectedIdx === null ? 'Select a page in the filmstrip first' : selectedInThisChapter ? 'This page is already in this chapter' : 'Add selected page'"
          @click="addSelectedPage"
        >
          + Add {{ selectedIdx !== null ? pageLabel(selectedIdx) : 'selected page' }}
        </button>
        <span v-if="willMoveFromOtherChapter" class="move-warn">
          Will move from "{{ selectedPageChapter!.title }}"
        </span>
      </div>
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

.source-entry {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 2px 0;
}

.remove-page-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 0.7rem;
  padding: 0 3px;
  line-height: 1;
}

.remove-page-btn:hover { color: #f87171; }

.add-page-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding-top: 0.4rem;
  border-top: 1px solid #2a2a2a;
}

.add-page-btn {
  padding: 0.2rem 0.55rem;
  font-size: 0.75rem;
  background: rgba(74, 158, 255, 0.1);
  border: 1px solid rgba(74, 158, 255, 0.35);
  border-radius: 4px;
  color: #4a9eff;
  cursor: pointer;
}

.add-page-btn:hover:not(:disabled) {
  background: rgba(74, 158, 255, 0.2);
}

.add-page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.move-warn {
  font-size: 0.72rem;
  color: #f59e0b;
}
</style>
