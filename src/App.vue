<script setup lang="ts">
import CaptureView from "@/views/CaptureView.vue";
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>KindleOCR</h1>
    </header>
    <main>
      <CaptureView />
    </main>
  </div>
</template>

<style>
:root {
  font-family: Inter, Avenir, Helvetica, Arial, sans-serif;
  font-size: 16px;
  color: #0f0f0f;
  background-color: #f6f6f6;
}

@media (prefers-color-scheme: dark) {
  :root {
    color: #f6f6f6;
    background-color: #2f2f2f;
  }
}

.app-shell {
  min-height: 100vh;
}

.app-header {
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #444;
}

.app-header h1 {
  margin: 0;
  font-size: 1.2rem;
}

main {
  padding: 0;
}
</style>
