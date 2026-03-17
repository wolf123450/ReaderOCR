# Step 35: Tauri Installer

**Phase**: 7 — Distribution & Polish  
**Layer**: Build/deployment  
**Dependencies**: Step 34 (bundled sidecar)

## Objective

Configure Tauri's built-in bundler to produce a Windows installer (MSI/NSIS) that bundles the Tauri app, the Python sidecar executable, and all necessary resources.

## Inputs

- Tauri application (compiled Rust + Vue.js frontend)
- Bundled Python sidecar from step 34
- App icon, license file

## Outputs

- Windows installer: `KindleOCR_x.y.z_x64-setup.exe` (NSIS) or `.msi`
- Portable ZIP option

## Algorithm

### Tauri bundle configuration
1. Update `tauri.conf.json` → `bundle` section:
   - `active: true`
   - `targets: ["nsis", "msi"]`
   - `icon`: App icons in multiple sizes (32x32, 128x128, 256x256 PNG + .ico)
   - `externalBin`: Reference to sidecar binary
   - `resources`: Any additional data files (models, default configs)
2. Set app metadata: name, version, description, copyright, license

### NSIS installer
1. Configure install directory (default: `%LOCALAPPDATA%\KindleOCR`)
2. Add Start Menu shortcut
3. Add desktop shortcut (optional, user-selectable)
4. Register file association for `.epub` (optional)
5. Add uninstaller entry in Add/Remove Programs

### Build process
1. Run `npm run build:sidecar` first (step 34)
2. Run `npm run tauri build` → produces installer
3. Sign the installer if code signing certificate is available

### App icon
1. Create or source an icon representing book/OCR
2. Generate all required sizes: 32x32, 128x128, 256x256 PNG + `.ico`
3. Place in `src-tauri/icons/`

## Files to Create/Modify

- `src-tauri/tauri.conf.json` — Bundle configuration
- `src-tauri/icons/` — App icons in required sizes
- `scripts/build-installer.ps1` — Full build script (sidecar + Tauri)
- `package.json` — Add `build:installer` script

## Edge Cases

- Missing sidecar binary → build script checks for sidecar before running Tauri build
- Code signing not available → unsigned installer works but shows SmartScreen warning
- Large installer size (200+ MB) → document, consider optional model download
- Upgrade installation → NSIS handles in-place upgrade, preserves user settings
- Uninstall → clean removal of all installed files, optionally keep user data

## Test Criteria

### Manual
1. **Installer produced**: `tauri build` completes with installer output
2. **Clean install**: Install on fresh Windows → app launches, sidecar starts
3. **Uninstall clean**: Uninstall removes program files, Start Menu entry
4. **Upgrade path**: Install v1, then install v2 over it → works correctly
5. **Icon displays**: App icon visible in taskbar, Start Menu, Add/Remove Programs
