import { defineStore } from "pinia";
import { ref } from "vue";

export const useSettingsStore = defineStore("settings", () => {
  const autoOcrAfterCapture = ref(false);
  const ocrEngine = ref("paddleocr-pp-ocrv5");
  const ocrLanguage = ref("en");

  function setAutoOcr(value: boolean) {
    autoOcrAfterCapture.value = value;
  }

  function setOcrEngine(engine: string) {
    ocrEngine.value = engine;
  }

  function setOcrLanguage(language: string) {
    ocrLanguage.value = language;
  }

  return {
    autoOcrAfterCapture,
    ocrEngine,
    ocrLanguage,
    setAutoOcr,
    setOcrEngine,
    setOcrLanguage,
  };
});
