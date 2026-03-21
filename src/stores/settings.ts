import { defineStore } from "pinia";
import { ref } from "vue";

export const useSettingsStore = defineStore("settings", () => {
  const autoOcrAfterCapture = ref(false);
  const ocrEngine = ref("paddleocr-pp-ocrv5");
  const ocrLanguage = ref("en");
  const ocrMaxColumns = ref(10);

  function setAutoOcr(value: boolean) {
    autoOcrAfterCapture.value = value;
  }

  function setOcrEngine(engine: string) {
    ocrEngine.value = engine;
  }

  function setOcrLanguage(language: string) {
    ocrLanguage.value = language;
  }

  function setOcrMaxColumns(n: number) {
    ocrMaxColumns.value = Math.max(1, Math.min(20, Math.round(n)));
  }

  return {
    autoOcrAfterCapture,
    ocrEngine,
    ocrLanguage,
    ocrMaxColumns,
    setAutoOcr,
    setOcrEngine,
    setOcrLanguage,
    setOcrMaxColumns,
  };
});
