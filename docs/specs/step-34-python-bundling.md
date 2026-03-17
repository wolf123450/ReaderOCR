# Step 34: Python Bundling

**Phase**: 7 — Distribution & Polish  
**Layer**: Build/deployment  
**Dependencies**: All Python sidecar code (Phases 3–4, 6)

## Objective

Bundle the Python sidecar into a standalone executable using PyInstaller so end users don't need Python installed. The bundled executable is shipped alongside the Tauri app.

## Inputs

- Python sidecar package (`src-python/kindleocr/`)
- PaddleOCR models and dependencies
- PyInstaller configuration

## Outputs

- Single executable `kindleocr-sidecar.exe` (Windows)
- Bundled in `src-tauri/binaries/` for Tauri sidecar integration

## Algorithm

### PyInstaller configuration
1. Create `kindleocr.spec` or use CLI flags
2. Entry point: `src-python/kindleocr/server.py` (JSON-RPC server)
3. Include data files: PaddleOCR models, any config files
4. Hidden imports: paddleocr, paddle, numpy, Pillow (PyInstaller misses some)
5. Exclude unnecessary modules to reduce size (tkinter, matplotlib test suites)

### Tauri sidecar integration
1. Name the binary `kindleocr-sidecar-{target_triple}` per Tauri convention
   - `kindleocr-sidecar-x86_64-pc-windows-msvc.exe` for Windows x64
2. Place in `src-tauri/binaries/`
3. Configure `tauri.conf.json` → `bundle.externalBin` to include the sidecar

### Build script
1. Create `scripts/build-sidecar.ps1` (Windows) that:
   a. Activates the Python venv
   b. Runs PyInstaller with correct options
   c. Copies output to `src-tauri/binaries/` with correct naming
2. Integrate into npm scripts: `npm run build:sidecar`

### Size optimization
1. Use `--onefile` for single executable
2. Use UPX compression if available
3. Exclude test code and dev dependencies
4. Expected size: ~100–200 MB (due to PaddleOCR/PaddlePaddle)

## Files to Create/Modify

- `src-python/kindleocr.spec` — PyInstaller spec file
- `scripts/build-sidecar.ps1` — Build script for Windows
- `src-tauri/tauri.conf.json` — Add externalBin configuration
- `package.json` — Add `build:sidecar` script

## Edge Cases

- PaddleOCR models not found at runtime → bundle models or download on first run
- Large binary size → document expected size, consider download-on-demand for models
- Antivirus false positive → sign the executable (addressed in step 35)
- Missing DLLs on target machine → ensure all Visual C++ redistributables are bundled
- Different CPU architectures → build for x64 only initially, document limitation

## Test Criteria

### Automated (CI/manual script)
1. **Build succeeds**: PyInstaller produces `kindleocr-sidecar.exe` without errors
2. **Executable runs**: `./kindleocr-sidecar.exe` starts and responds to JSON-RPC ping
3. **No missing imports**: All hidden imports resolved (no `ModuleNotFoundError` at runtime)
4. **Correct binary name**: Output follows Tauri target-triple naming convention
5. **Sidecar integration**: Tauri app can launch the bundled sidecar

### Manual
6. **Clean machine test**: Run on a machine without Python installed → sidecar works
