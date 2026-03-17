# Plan: KindleOCR — Book Image to EPUB Converter

## TL;DR
Build a desktop app that captures book pages from any windowed reader application, runs OCR to extract text, and assembles the result into a well-structured EPUB. The app uses **Tauri + Vue.js** for the GUI, a **Python sidecar** for OCR (PaddleOCR) and EPUB generation (ebooklib), with optional **Ollama integration** for post-processing. This architecture puts OS-level concerns (window capture, keyboard simulation) in Rust and ML/document processing in Python.

## Key Technical Decisions

### OCR Engine: PaddleOCR (not Ollama VL)
- **PaddleOCR PP-OCRv5**: ~100MB model, 0.1–0.3s/page on GPU, 93%+ accuracy on clean text, Apache 2.0
- **PaddleOCR-VL-1.5**: 0.9B params, 94.5% precision on document benchmarks, handles tables/complex layouts, Apache 2.0
- **Why not Ollama VL**: 10–50x slower (5–40s/page), 4–50GB model size, hallucination risk on text. Specialized OCR is dramatically better for this task.
- **Ollama's role**: Optional post-processing only — paragraph reconstruction, chapter detection, OCR error correction. LLMs are good at understanding context, not pixel-level text extraction.

### Architecture: Tauri + Vue.js + Python Sidecar
- **Rust/Tauri**: Window enumeration, screen capture, keyboard simulation (page turns), file I/O, app shell
- **Vue.js**: Region selector, capture controls, OCR review/editor, chapter editor, EPUB metadata form, progress dashboard
- **Python sidecar**: PaddleOCR inference, text post-processing, EPUB generation via ebooklib
- **Communication**: Tauri ↔ Python via Tauri's sidecar API (stdin/stdout JSON-RPC) for development; bundled via PyInstaller for distribution
- **Ollama**: HTTP calls to local Ollama server when enabled (optional)

### Why not alternatives?
- **Tesseract**: Poor accuracy (~45% on diverse docs) and terrible layout analysis. Not viable for mixed content.
- **Surya**: Excellent accuracy but GPL-3.0 license restricts distribution.
- **GOT-OCR**: Strong contender (580M params, Apache 2.0, handles formulas/tables/charts), but PaddleOCR has better ecosystem, speed, and language support. Could be offered as an alternative engine.
- **Full Rust OCR (no Python)**: No mature Rust OCR libraries for complex layouts. Tesseract Rust bindings exist but accuracy is insufficient.
- **Python-only (no Tauri)**: User needs interactive region selection, page-by-page capture control, and visual OCR review — a native GUI is warranted.

---

## Development Process Rules

1. **Git-first**: Initialize a git repository before any code is written. Commit at the end of each step. Use conventional commits. Each phase should end with a stable, passing-tests commit.
2. **Test-driven steps**: Every step that involves complex logic, algorithms, or data transformation must include automated tests. Tests serve as executable specs and assist AI-driven development by providing clear correctness signals.
3. **Spec-first workflow**: After scaffolding (Phase 1), save the plan into the repo and generate a detailed spec file for each subsequent step *before* implementing it. Specs live in `docs/specs/` and describe inputs, outputs, edge cases, and test criteria.

### Testing Strategy

- **Rust (Tauri backend)**: `cargo test` — unit tests inline in modules, integration tests in `src-tauri/tests/`
- **Python (sidecar)**: `pytest` — unit tests in `src-python/tests/`, fixtures with sample images and expected OCR output
- **Vue.js (frontend)**: `vitest` — component and store tests in `src/__tests__/`
- **E2E**: Manual verification checklists per phase (captured in spec files). Automated E2E deferred to Phase 7.
- **Test fixtures**: `test-fixtures/` directory at repo root for sample page images, expected OCR text, and expected EPUB output

---

## Steps

### Phase 1: Project Scaffolding & Spec Generation
1. **Git init** — Initialize git repository, create `.gitignore` (Rust, Node, Python, OS artifacts), initial commit
2. **Tauri + Vue.js init** — `create-tauri-app` with Vue + TypeScript + Vite. Verify `cargo tauri dev` runs a blank window
3. **Python sidecar init** — Create `src-python/` with `pyproject.toml`, virtual env, pytest configured. Verify `pytest` runs (even with 0 tests)
4. **JSON-RPC protocol schema** — Define TypeScript + Python types for Tauri ↔ Python messages (request/response). Shared schema file.
5. **Monorepo dev scripts** — `package.json` scripts for concurrent dev (`tauri dev` + Python sidecar). Document in README.
6. **Save plan & generate specs** — Commit `docs/plan.md` (this plan) to repo. Generate a spec file (`docs/specs/step-NN-slug.md`) for each step in Phases 2–7. Each spec includes: objective, inputs, outputs, algorithm description (if applicable), edge cases, test criteria, and dependencies on prior steps. **All subsequent implementation follows the spec for that step.**
7. **Test infrastructure commit** — Create `test-fixtures/` with 2–3 sample page images (public domain book pages). Verify Rust, Python, and Vue test harnesses all pass. Commit.

### Phase 2: Screen Capture Module (Rust + Vue)
8. **Window enumeration** — Rust command to list open windows with titles and handles (win32 API via `windows` crate). **Tests**: unit test that enumeration returns at least 1 window and filters out invisible/zero-size windows.
9. **Region selection UI** — Vue overlay component: user selects a window, then draws a rectangle over the content area. Draggable/resizable selection box. **Tests**: Vitest component test for region data model (coordinates, resize logic, bounds clamping).
10. **Page capture** — Rust command to capture screenshot of selected region (`xcap` crate). Save as PNG. **Tests**: integration test that captures a known region and verifies PNG output (file exists, non-zero size, valid image dimensions).
11. **Page turn automation** — Configurable key press simulation (default: Right Arrow). Configurable delay. Rust `SendInput`. **Tests**: unit test for key config parsing; manual verification of key delivery.
12. **Batch capture loop** — Vue controls: Start/Stop/Pause. Configurable delay, page count. Numbered PNGs. Live preview. **Tests**: Vitest store test for batch state machine (idle→capturing→paused→stopped transitions).
13. **Duplicate detection** — Compare consecutive captures via perceptual image hash (`image_hasher` crate or similar). Auto-stop when same page detected. **Tests**: Rust unit test — hash two identical images → match; hash two different images → no match; hash near-duplicate (minor rendering diff) → configurable threshold.

### Phase 3: OCR Pipeline (Python Sidecar)
14. **Sidecar setup** — Tauri sidecar configuration to spawn Python process. JSON-RPC over stdin/stdout. **Tests**: integration test — Tauri sends a ping request, Python responds with pong. Python-side test — feed JSON-RPC messages to server, verify responses.
15. **Image preprocessing** — Auto-crop, deskew, contrast normalization via Pillow. **Tests**: pytest with fixture images — verify cropped output dimensions, verify deskew on a deliberately rotated image, verify contrast-normalized histogram.
16. **OCR execution** — PaddleOCR PP-OCRv5 for standard pages. PaddleOCR-VL-1.5 for complex pages. **Tests**: pytest with fixture page image → verify extracted text matches expected output with >90% character accuracy (Levenshtein distance check).
17. **Layout analysis** — PP-StructureV3: identify headers, footers, page numbers, body, tables. **Tests**: fixture image with known header/footer → verify classified correctly. Fixture with body-only → verify no false positives.
18. **Text extraction** — Extract in reading order, return structured blocks `{ type, text, confidence, bbox }`. **Tests**: multi-column fixture → verify reading order. Single-column fixture → verify sequential output.

### Phase 4: Text Post-Processing (Python)
19. **Page number removal** — Regex removal of standalone numbers, "Page N", "- N -" at page boundaries. **Tests**: parameterized pytest — input texts with various page number formats → verify clean output. Edge case: text containing legitimate standalone numbers (e.g., "There were 3 apples") not removed.
20. **Header/footer filtering** — Detect repeated text at same position across pages. **Tests**: provide 5 pages where 3 share the same header → verify header detected and removed. Pages with no repeats → verify no content lost.
21. **Paragraph reconstruction** — Merge across page breaks, rejoin hyphens, detect continuations. **Tests**: page ending "The quick brown-" + next page "fox jumped" → "The quick brown-fox jumped" (hyphen rejoin). Page ending without period + next starting lowercase → merged. Page ending with period + next starting uppercase → not merged.
22. **Chapter detection** — Heuristic: "Chapter N", centered headings, large font blocks, whitespace gaps. **Tests**: fixture data with 3 chapter titles in various formats → all detected. Body text with the word "chapter" mid-sentence → not falsely detected.
23. **Optional: Ollama post-processing** — HTTP client to local Ollama. Send OCR text for error correction, paragraph refinement, chapter title extraction. **Tests**: mock Ollama HTTP responses → verify correctly parsed. Test graceful fallback when Ollama unavailable.

### Phase 5: Review & Editing UI (Vue)
24. **Side-by-side viewer** — Left: source image. Right: editable text (Tiptap editor). Page navigation. **Tests**: Vitest — component renders with mock page data, navigation updates current page index.
25. **Confidence highlighting** — Low-confidence words highlighted yellow/red. **Tests**: Vitest — provide word list with confidence scores, verify correct CSS classes applied above/below threshold.
26. **Chapter boundary editor** — Visual markers, add/remove/move chapter breaks, drag-and-drop reorder. **Tests**: Vitest store test — add chapter at page N, remove chapter, move chapter, verify resulting chapter list.
27. **Batch operations** — Accept all, find/replace, regex support. **Tests**: Vitest — find/replace across mock multi-page data, verify all occurrences replaced. Regex test with capture groups.
28. **Page management** — Delete, reorder, re-run OCR on single page. **Tests**: Vitest store test — delete page at index, verify page list updated and indices renumbered.

### Phase 6: EPUB Generation (Python)
29. **Metadata form** — Vue form: title, author(s), language, cover, description, ISBN. **Tests**: Vitest — form validation (required fields, ISBN format).
30. **EPUB assembly** — ebooklib: create book, set metadata, chapters from processed text, TOC, default CSS, cover. **Tests**: pytest — generate EPUB from fixture data, verify: ZIP structure valid, `content.opf` contains correct metadata, chapter XHTML files present, TOC entries match chapters.
31. **CSS styling** — Default book stylesheet (typography, margins, spacing). Presets. **Tests**: verify CSS file included in generated EPUB.
32. **EPUB validation** — Structural validation in Python (check required files, valid XHTML). **Tests**: generate a valid EPUB → passes. Generate a deliberately broken EPUB → fails validation.
33. **Output** — Save to user-selected path. Option to preview in default reader. **Tests**: integration — verify file written to specified path.

### Phase 7: Distribution & Polish
34. **PyInstaller bundling** — Bundle Python sidecar as standalone exe with PaddleOCR models. **Tests**: run bundled exe, send JSON-RPC ping → verify pong response.
35. **Tauri installer** — MSI/NSIS for Windows, include sidecar binary. **Tests**: install on clean VM/sandbox, verify app launches and sidecar communicates.
36. **Error handling** — Graceful: OCR unavailable, window closed during capture, Ollama offline, invalid images. **Tests**: Python — send invalid image path → verify error response (not crash). Rust — attempt capture on closed window → verify error returned to UI.
37. **Logging** — Structured logging (Rust `tracing`, Python `structlog`). Log file accessible from UI. **Tests**: trigger logged events → verify log file contains expected entries.
38. **Settings persistence** — Save/load preferences: capture delay, OCR engine, Ollama endpoint, output dir. **Tests**: Vitest — save settings, reload, verify round-trip. Rust — verify settings file written as valid JSON.

---

## Decisions
- **OCR engine**: PaddleOCR over Ollama VL (10–50x faster, no hallucination risk, better accuracy for printed text). Ollama reserved for optional post-processing only.
- **Architecture**: Tauri + Python sidecar over pure Rust (Python has the mature OCR ecosystem) or pure Python (user wants native GUI with Tauri + Vue)
- **Sidecar communication**: JSON-RPC over stdin/stdout (Tauri-native, no port conflicts, no network exposure)
- **EPUB generation**: Python ebooklib (mature, well-maintained, already in the sidecar process) over Rust epub-builder (immature ecosystem)
- **Development process**: Git-first, test-driven, spec-first. Each step gets a spec before implementation. Tests at every step to assist AI-driven development.
- **Scope included**: Window-agnostic capture, OCR, text cleanup, chapter detection, EPUB export, review UI
- **Scope excluded**: DRM removal/bypass, PDF extraction (this tool is for image-based capture only), cloud storage integration, batch processing of multiple books simultaneously

## Further Considerations
1. **PaddleOCR vs GOT-OCR for complex pages**: GOT-OCR (580M params, Apache 2.0) outputs structured Markdown/LaTeX and handles formulas/tables natively. Could be offered as an alternative engine alongside PaddleOCR. **Recommendation**: Start with PaddleOCR, add GOT-OCR as a second engine if complex content proves challenging.
2. **Project data format**: Should we save in-progress work (captured images, OCR results, chapter edits) as a "project file" so users can resume? **Recommendation**: Yes — use a project directory with a JSON manifest file. This is important for usability since OCR is time-consuming.
3. **Capture method**: `BitBlt`/`PrintWindow` via win32 are fast but some readers use GPU rendering that `BitBlt` can't capture. The `xcap` Rust crate handles this more robustly. **Recommendation**: Use `xcap` crate as primary, fall back to win32 API if needed.
