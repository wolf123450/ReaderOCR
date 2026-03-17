# Step 38: Settings Persistence

**Phase**: 7 — Distribution & Polish  
**Layer**: Tauri + Vue.js frontend  
**Dependencies**: Steps 29, 36, 37

## Objective

Persist user preferences and application settings across sessions. Store settings in a local JSON file in the app data directory. Settings include OCR options, Ollama configuration, UI preferences, and last-used paths.

## Inputs

- User interactions with settings UI
- Default values for all settings

## Outputs

- Settings file: `%APPDATA%\com.kindleocr.app\settings.json`
- Settings loaded on app startup, saved on change

## Settings Schema

```json
{
  "version": 1,
  "ocr": {
    "engine": "paddleocr",
    "language": "en",
    "gpuEnabled": true,
    "preprocessDeskew": true,
    "preprocessDenoise": true
  },
  "ollama": {
    "enabled": false,
    "endpoint": "http://localhost:11434",
    "model": "llama3",
    "timeout": 30
  },
  "capture": {
    "defaultDelay": 500,
    "pageTurnKey": "Right",
    "duplicateThreshold": 0.98
  },
  "epub": {
    "defaultOutputDir": "",
    "fontFamily": "Georgia, serif",
    "fontSize": "1.0em",
    "lineHeight": 1.6,
    "textAlign": "justify",
    "includePageBreaks": false
  },
  "ui": {
    "theme": "system",
    "sidebarWidth": 250,
    "zoomLevel": 100,
    "showConfidenceHighlight": true,
    "confidenceThreshold": 0.8
  },
  "recent": {
    "lastOutputPath": "",
    "lastCaptureWindow": "",
    "recentProjects": []
  }
}
```

## Algorithm

### Settings management
1. On app launch: read settings file, merge with defaults (handles new fields in updates)
2. On settings change: debounced write to file (500ms after last change)
3. Deep merge: user settings override defaults, new default fields are added

### Settings UI
1. Settings panel accessible from menu bar or gear icon
2. Organized in tabs matching schema sections (OCR, Ollama, Capture, EPUB, UI)
3. Changes applied immediately (no explicit save button)
4. Reset to defaults button per section

### File operations
1. Read/write via Tauri `fs` plugin (not Node.js fs)
2. Settings directory: Tauri `appDataDir()` 
3. Handle missing file gracefully → use all defaults on first run
4. Handle corrupt JSON → log warning, use defaults, back up corrupt file

### Migration
1. Include `version` field in settings
2. On load, check version and apply any necessary migrations
3. Future versions can add migration functions

## Files to Create/Modify

- `src/stores/settings.ts` — Pinia store for settings with persistence
- `src/components/SettingsPanel.vue` — Settings UI with tabbed sections
- `src-tauri/src/commands.rs` — Tauri commands for settings file read/write
- `src/utils/settingsMigration.ts` — Version migration logic

## Edge Cases

- Settings file doesn't exist → create with defaults on first run
- Settings file is corrupt JSON → back up as `.bak`, start fresh with defaults
- New setting added in app update → deep merge adds new field with default value
- Settings file is read-only → warn user, operate with in-memory settings only
- Concurrent writes → debounce prevents rapid consecutive writes
- Very large recent projects list → cap at 10 entries, FIFO

## Test Criteria

### Automated (vitest)
1. **Default initialization**: No settings file → store has all default values
2. **Deep merge**: Partial settings file → missing fields filled from defaults
3. **Persistence round-trip**: Set value → save → reload → value preserved
4. **Corrupt file handling**: Invalid JSON → defaults loaded, no crash
5. **Version migration**: v0 settings → v1 migration applied, new fields added
6. **Debounced save**: Rapid changes → only one write operation
7. **Recent projects cap**: Adding 11th project → oldest removed, list has 10

### Manual
8. **Settings UI**: All tabs render correctly, changes reflected immediately
9. **Cross-session**: Change setting, close app, reopen → setting persisted
