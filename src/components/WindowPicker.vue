<script setup lang="ts">
import { ref, onMounted } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { useCaptureStore, type WindowInfo } from "@/stores/capture";

const store = useCaptureStore();
const loading = ref(false);
const error = ref<string | null>(null);

async function fetchWindows() {
  loading.value = true;
  error.value = null;
  try {
    const result = await invoke<WindowInfo[]>("list_windows");
    store.setWindows(result);
  } catch (e) {
    error.value = String(e);
  } finally {
    loading.value = false;
  }
}

function onSelect(event: Event) {
  const target = event.target as HTMLSelectElement;
  const handle = Number(target.value);
  const win = store.windows.find((w) => w.handle === handle);
  if (win) store.selectWindow(win);
}

onMounted(fetchWindows);
</script>

<template>
  <div class="window-picker">
    <label for="window-select">Target Window:</label>
    <select
      id="window-select"
      :value="store.selectedWindow?.handle ?? ''"
      :disabled="loading"
      @change="onSelect"
    >
      <option value="" disabled>Select a window…</option>
      <option
        v-for="w in store.windows"
        :key="w.handle"
        :value="w.handle"
      >
        {{ w.title }} ({{ w.process_name }})
      </option>
    </select>
    <button @click="fetchWindows" :disabled="loading" title="Refresh window list">
      {{ loading ? "…" : "↻" }}
    </button>
    <span v-if="error" class="error">{{ error }}</span>
  </div>
</template>

<style scoped>
.window-picker {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
}

select {
  flex: 1;
  padding: 0.4rem;
}

button {
  padding: 0.4rem 0.8rem;
  cursor: pointer;
}

.error {
  color: #e74c3c;
  font-size: 0.85rem;
}
</style>
