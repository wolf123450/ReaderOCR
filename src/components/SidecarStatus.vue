<script setup lang="ts">
import { onMounted } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { useCaptureStore } from "@/stores/capture";

const store = useCaptureStore();

async function checkSidecar() {
  store.setSidecarStatus("connecting");
  try {
    const result = await invoke<{ status: string; version: string }>("sidecar_ping");
    if (result.status === "ok") {
      store.setSidecarStatus("connected");
    } else {
      store.setSidecarStatus("error", "Unexpected ping response");
    }
  } catch (e) {
    store.setSidecarStatus("error", String(e));
  }
}

onMounted(() => {
  checkSidecar();
});
</script>

<template>
  <div class="sidecar-status">
    <span class="dot" :class="store.sidecarStatus" />
    <span class="label">
      <template v-if="store.sidecarStatus === 'connected'">OCR Engine Connected</template>
      <template v-else-if="store.sidecarStatus === 'connecting'">Connecting…</template>
      <template v-else-if="store.sidecarStatus === 'error'">
        OCR Engine Error
        <button class="retry-btn" @click="checkSidecar">Retry</button>
      </template>
      <template v-else>OCR Engine Offline</template>
    </span>
  </div>
</template>

<style scoped>
.sidecar-status {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: #aaa;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot.connected {
  background: #4caf50;
}

.dot.connecting {
  background: #ff9800;
  animation: pulse 1s ease-in-out infinite;
}

.dot.error {
  background: #f44336;
}

.dot.disconnected {
  background: #666;
}

.retry-btn {
  margin-left: 0.4rem;
  padding: 0.1rem 0.4rem;
  font-size: 0.75rem;
  background: #333;
  color: #ddd;
  border: 1px solid #555;
  border-radius: 3px;
  cursor: pointer;
}

.retry-btn:hover {
  background: #444;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
