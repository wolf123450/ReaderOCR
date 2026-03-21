<script setup lang="ts">
import { computed } from "vue";
import { useSessionStore, type ReconcileActions } from "@/stores/session";
import { useCaptureStore } from "@/stores/capture";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const session = useSessionStore();
const capture = useCaptureStore();

const report = computed(() => session.reconcileReport);
const diskCount = computed(
  () => session.lastScanResult?.found.length ?? 0
);
const sessionCount = computed(() => capture.capturedPages.length);

// Action selections — default choices match the most common safe option
const missingAction = ref<"remove" | "mark">("mark");
const extraAction = ref<"adopt" | "ignore">("adopt");

function apply() {
  if (!report.value) return;
  const actions: ReconcileActions = {
    removeFromSession:
      missingAction.value === "remove" ? report.value.missingFromDisk : [],
    markNeedsRecapture:
      missingAction.value === "mark" ? report.value.missingFromDisk : [],
    adoptFromDisk:
      extraAction.value === "adopt" ? report.value.extraOnDisk : [],
  };
  session.applyReconcile(actions);
  emit("close");
}

function cancel() {
  session.clearReconcile();
  emit("close");
}
</script>

<script lang="ts">
import { ref } from "vue";
</script>

<template>
  <Teleport to="body">
    <div v-if="visible && report" class="dialog-backdrop" @click.self="cancel">
      <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="reconcile-title">
        <h2 id="reconcile-title">Session Reconciliation</h2>

        <div class="summary">
          <div>Found on disk: <strong>{{ diskCount }} pages</strong></div>
          <div>In session: <strong>{{ sessionCount }} pages</strong></div>
        </div>

        <!-- Missing from disk -->
        <section v-if="report.missingFromDisk.length > 0" class="conflict-section warning">
          <p>
            ⚠ {{ report.missingFromDisk.length }} page(s) in session are <strong>missing from disk</strong>:
            <span class="page-list">#{{ report.missingFromDisk.join(", #") }}</span>
          </p>
          <div class="action-group">
            <label>
              <input v-model="missingAction" type="radio" value="mark" />
              Mark as needs recapture
            </label>
            <label>
              <input v-model="missingAction" type="radio" value="remove" />
              Remove from session
            </label>
          </div>
        </section>

        <!-- Extra on disk -->
        <section v-if="report.extraOnDisk.length > 0" class="conflict-section info">
          <p>
            ✚ {{ report.extraOnDisk.length }} page(s) found on disk <strong>not in session</strong>:
            <span class="page-list">#{{ report.extraOnDisk.join(", #") }}</span>
          </p>
          <div class="action-group">
            <label>
              <input v-model="extraAction" type="radio" value="adopt" />
              Adopt these pages
            </label>
            <label>
              <input v-model="extraAction" type="radio" value="ignore" />
              Ignore
            </label>
          </div>
        </section>

        <p v-if="report.missingFromDisk.length === 0 && report.extraOnDisk.length === 0" class="all-good">
          ✓ Session and disk are in sync ({{ report.matched.length }} pages matched).
        </p>

        <footer class="dialog-footer">
          <button class="btn-primary" @click="apply">Apply &amp; Continue</button>
          <button class="btn-secondary" @click="cancel">Cancel</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--nav-bg, #1a1a1a);
  border: 1px solid var(--border-color, #444);
  border-radius: 8px;
  padding: 1.5rem;
  min-width: 460px;
  max-width: 600px;
  color: var(--text-primary, #f0f0f0);
}

.dialog h2 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
}

.summary {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: var(--text-muted, #aaa);
}

.conflict-section {
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
}

.conflict-section.warning {
  background: rgba(255, 180, 0, 0.08);
  border-left: 3px solid #ffb400;
}

.conflict-section.info {
  background: rgba(74, 158, 255, 0.08);
  border-left: 3px solid #4a9eff;
}

.conflict-section p {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
}

.page-list {
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--text-muted, #aaa);
}

.action-group {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
}

.action-group label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
}

.all-good {
  color: #4caf50;
  font-size: 0.9rem;
}

.dialog-footer {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color, #444);
}

.btn-primary {
  padding: 0.45rem 1rem;
  background: var(--accent, #4a9eff);
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-primary:hover { background: #3a8eef; }

.btn-secondary {
  padding: 0.45rem 1rem;
  background: transparent;
  border: 1px solid var(--border-color, #444);
  border-radius: 4px;
  color: var(--text-muted, #aaa);
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-secondary:hover { color: var(--text-primary, #f0f0f0); }
</style>
