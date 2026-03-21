<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import TabShell from "@/components/TabShell.vue";
import { startAutoSave } from "@/composables/useSaveSession";

let stopAutoSave: (() => void) | null = null;

onMounted(() => {
  stopAutoSave = startAutoSave();
});

onUnmounted(() => {
  stopAutoSave?.();
});
</script>

<template>
  <TabShell />
</template>

<style>
:root {
  font-family: Inter, Avenir, Helvetica, Arial, sans-serif;
  font-size: 16px;
  color: #0f0f0f;
  background-color: #f6f6f6;

  --border-color: #444;
  --nav-bg: #1a1a1a;
  --text-primary: #f0f0f0;
  --text-muted: #aaa;
  --accent: #4a9eff;
  --accent-dim: #2a6ab0;
  --thumb-bg: #2a2a2a;
}

@media (prefers-color-scheme: dark) {
  :root {
    color: #f6f6f6;
    background-color: #2f2f2f;
  }
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}
</style>
