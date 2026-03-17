# KindleOCR

Book image to EPUB converter. Captures book pages from any windowed e-reader, runs OCR to extract text, and assembles the result into a well-structured EPUB.

## Architecture

| Layer | Technology | Role |
|-------|-----------|------|
| Desktop shell | Tauri v2 (Rust) | Window capture, key simulation, sidecar management |
| Frontend | Vue 3 + TypeScript | Region selector, OCR review, chapter editor, export |
| OCR / processing | Python sidecar | PaddleOCR, text cleanup, EPUB generation |
| Post-processing | Ollama (optional) | OCR error correction, chapter detection |

Communication between Tauri and Python uses **JSON-RPC 2.0** over stdin/stdout.

## Prerequisites

- **Rust** ≥ 1.77 (via [rustup](https://rustup.rs))
- **Node.js** ≥ 18 + npm
- **Python** ≥ 3.9

## Setup

```bash
# Install frontend dependencies
npm install

# Set up Python sidecar
cd src-python
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -e ".[dev]"

# Install OCR dependencies (when ready)
# pip install -e ".[ocr]"
```

## Development

```bash
# Run the full Tauri + Vue dev server
npm run tauri:dev

# Run frontend only (no Tauri shell)
npm run dev

# Run all tests (frontend + Python)
npm run test:all

# Run frontend tests only
npm run test

# Run Python tests only
cd src-python && pytest -v
```

## Project Structure

```
KindleOCR/
├── src/                  # Vue.js frontend
│   ├── protocol.ts       # JSON-RPC type definitions
│   ├── App.vue           # Root component
│   └── main.ts           # App entry
├── src-tauri/            # Rust / Tauri backend
│   ├── src/lib.rs        # Tauri app setup
│   └── src/main.rs       # Entry point
├── src-python/           # Python sidecar
│   ├── kindleocr/        # Main package
│   │   ├── protocol.py   # JSON-RPC types (mirrors src/protocol.ts)
│   │   ├── server.py     # stdin/stdout JSON-RPC server
│   │   ├── ocr/          # OCR engines
│   │   ├── processing/   # Text post-processing
│   │   ├── epub/         # EPUB generation
│   │   └── ollama/       # Optional Ollama integration
│   └── tests/            # Python tests
├── test-fixtures/        # Shared test data
├── docs/                 # Plan and step specs
└── package.json          # Monorepo scripts
```

## Testing

Every step includes automated tests for complex logic. Tests serve as executable specs for AI-assisted development.

- **Rust**: `cargo test` (in `src-tauri/`)
- **Python**: `pytest -v` (in `src-python/`)  
- **Vue/TS**: `npm run test` (vitest)

## License

MIT
