/**
 * useSaveSession — serializes all Pinia stores into a SessionData payload
 * and calls the `save_session` Tauri command.
 *
 * Import `saveSession()` wherever state changes need to be flushed to disk.
 * Import `startAutoSave()` to wire up debounced watchers in the root component.
 */

import { watch } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { useCaptureStore } from "@/stores/capture";
import { useOcrStore, type TextBlock } from "@/stores/ocr";
import { useChaptersStore } from "@/stores/chapters";
import { useMetadataStore } from "@/stores/metadata";
import { useSettingsStore } from "@/stores/settings";

// Debounce handle shared across composable instances.
let _debounceTimer: ReturnType<typeof setTimeout> | null = null;
const DEBOUNCE_MS = 1500;

/** Build a complete SessionData payload from the current store state. */
function buildPayload() {
  const capture = useCaptureStore();
  const ocr = useOcrStore();
  const chapters = useChaptersStore();
  const meta = useMetadataStore();
  const settings = useSettingsStore();

  const dir = capture.effectiveOutputDir;

  // Build pages array, merging per-page OCR data into each captured page.
  const pages = capture.capturedPages.map((p) => {
    const ocrResult = ocr.pageResults.get(p.pageNumber);
    const editedBlks = ocr.editedBlocks.get(p.pageNumber);

    const base: Record<string, unknown> = {
      pageNumber: p.pageNumber,
      imagePath: p.imagePath,
      timestamp: p.timestamp,
      captureStatus: p.captureStatus,
      pageType: p.pageType,
      ocrStatus: p.ocrStatus,
    };
    if (p.userNotes !== undefined) base.userNotes = p.userNotes;
    if (p.errorMessage !== undefined) base.errorMessage = p.errorMessage;

    if (ocrResult) {
      base.ocrRawText = ocrResult.text;
      base.ocrConfidence = ocrResult.confidence;
      if (ocrResult.blocks && ocrResult.blocks.length > 0) {
        base.ocrBlocks = ocrResult.blocks.map(blockToSession);
      }
    }
    if (editedBlks && editedBlks.length > 0) {
      base.ocrEditedBlocks = editedBlks.map(blockToSession);
    }

    return base;
  });

  const epubMetadata = {
    title: meta.title,
    author: meta.author,
    language: meta.language,
    description: meta.description,
    publisher: meta.publisher,
    isbn: meta.isbn,
    coverImagePath: meta.coverImagePath,
  };

  const ocrSettings = {
    ocrEngine: settings.ocrEngine,
    ocrLanguage: settings.ocrLanguage,
    ocrMaxColumns: settings.ocrMaxColumns,
    autoOcrAfterCapture: settings.autoOcrAfterCapture,
  };

  const sessionData = {
    bookName: capture.bookName,
    outputDir: capture.batchConfig.outputDir,
    filePrefix: capture.batchConfig.filePrefix,
    pageTurnKey: capture.batchConfig.pageTurnKey,
    delayBetweenMs: capture.batchConfig.delayBetweenMs,
    maxPages: capture.batchConfig.maxPages,
    pagesCaptured: capture.pagesCaptured,
    region: capture.region ?? { x: 0, y: 0, width: 0, height: 0 },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    pages,
    chapters: chapters.chapters,
    epubMetadata,
    ocrSettings,
  };

  return { dir, sessionData };
}

function blockToSession(b: TextBlock) {
  return {
    type: b.type,
    text: b.text,
    confidence: b.confidence,
    bbox: { x: b.bbox.x, y: b.bbox.y, width: b.bbox.width, height: b.bbox.height },
    colIndex: b.col_index,
  };
}

/** Persist the current application state immediately. */
export async function saveSession(): Promise<void> {
  try {
    const { dir, sessionData } = buildPayload();
    if (!dir) return;
    await invoke("save_session", { dir, data: sessionData });
  } catch {
    // Non-fatal — silently ignore save errors to avoid disrupting the UI.
  }
}

/** Persist after a debounce delay (cancels any pending save). */
export function debouncedSaveSession(): void {
  if (_debounceTimer !== null) clearTimeout(_debounceTimer);
  _debounceTimer = setTimeout(() => {
    saveSession();
    _debounceTimer = null;
  }, DEBOUNCE_MS);
}

/**
 * Set up reactive watchers.  Call once from App.vue (or a root component)
 * after the stores are initialised.  Returns a cleanup function.
 */
export function startAutoSave(): () => void {
  const capture = useCaptureStore();
  const ocr = useOcrStore();
  const chapters = useChaptersStore();
  const meta = useMetadataStore();
  const settings = useSettingsStore();

  const stoppers: (() => void)[] = [];

  // OCR results (size changes when a page finishes)
  stoppers.push(
    watch(() => ocr.pageResults.size, debouncedSaveSession)
  );
  // Edited blocks
  stoppers.push(
    watch(() => ocr.editedBlocks.size, debouncedSaveSession)
  );
  // Chapter structure
  stoppers.push(
    watch(() => JSON.stringify(chapters.chapters), debouncedSaveSession)
  );
  // Metadata fields
  stoppers.push(
    watch(
      () => [meta.title, meta.author, meta.language, meta.description,
             meta.publisher, meta.isbn, meta.coverImagePath],
      debouncedSaveSession
    )
  );
  // Settings
  stoppers.push(
    watch(
      () => [settings.ocrEngine, settings.ocrLanguage,
             settings.ocrMaxColumns, settings.autoOcrAfterCapture],
      debouncedSaveSession
    )
  );
  // Captured pages (page type changes, notes, etc.)
  stoppers.push(
    watch(
      () => capture.capturedPages.map((p) => `${p.pageNumber}|${p.pageType}|${p.ocrStatus}|${p.captureStatus}`).join(","),
      debouncedSaveSession
    )
  );

  return () => stoppers.forEach((s) => s());
}
