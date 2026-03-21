use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub const SESSION_FILENAME: &str = "kindleocr-session.json";

/// Serializable capture region stored in the session file.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionRegion {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

/// Bounding box for an OCR block stored in the session.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionBoundingBox {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

/// A single OCR text block stored in the session.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionOcrBlock {
    #[serde(rename = "type")]
    pub block_type: String,
    pub text: String,
    pub confidence: f64,
    pub bbox: SessionBoundingBox,
    #[serde(default)]
    pub col_index: i32,
}

/// EPUB metadata persisted across sessions.
#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionEpubMetadata {
    pub title: String,
    pub author: String,
    pub language: String,
    pub description: String,
    pub publisher: String,
    pub isbn: String,
    pub cover_image_path: String,
}

/// OCR / capture settings persisted across sessions.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionOcrSettings {
    pub ocr_engine: String,
    pub ocr_language: String,
    pub ocr_max_columns: u32,
    pub auto_ocr_after_capture: bool,
}

impl Default for SessionOcrSettings {
    fn default() -> Self {
        SessionOcrSettings {
            ocr_engine: "paddleocr-pp-ocrv5".to_string(),
            ocr_language: "en".to_string(),
            ocr_max_columns: 10,
            auto_ocr_after_capture: false,
        }
    }
}

/// Per-page metadata stored in the session file.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionPage {
    pub page_number: u32,
    pub image_path: String,
    pub timestamp: i64,
    /// "ok" | "needs_recapture" | "missing" | "placeholder"
    #[serde(default = "default_capture_status")]
    pub capture_status: String,
    /// "text" | "cover" | "illustration" | "toc" | "license" | "blank" | "chapter_start" | "excluded"
    #[serde(default = "default_page_type")]
    pub page_type: String,
    /// "pending" | "running" | "done" | "error" | "skipped"
    #[serde(default = "default_ocr_status")]
    pub ocr_status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_notes: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_message: Option<String>,
    /// Raw OCR text for this page (None = not yet OCR'd).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ocr_raw_text: Option<String>,
    /// Average confidence 0–100 (None = not yet OCR'd).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ocr_confidence: Option<f64>,
    /// Structured OCR blocks (None = not yet OCR'd).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ocr_blocks: Option<Vec<SessionOcrBlock>>,
    /// User-edited blocks overriding the OCR output (None = no edits).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ocr_edited_blocks: Option<Vec<SessionOcrBlock>>,
}

fn default_capture_status() -> String { "ok".to_string() }
fn default_page_type() -> String { "text".to_string() }
fn default_ocr_status() -> String { "pending".to_string() }

/// A fractional region of a source page for chapter mapping (0.0 = top, 1.0 = bottom).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionPageFraction {
    pub page_index: u32,
    pub start: f64,
    pub end: f64,
}

/// A chapter segment mapping source pages to an EPUB chapter.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionChapter {
    pub id: String,
    pub title: String,
    pub chapter_index: u32,
    pub sources: Vec<SessionPageFraction>,
    /// "front_matter" | "chapter" | "back_matter" | "part" | "appendix"
    #[serde(default = "default_chapter_type")]
    pub chapter_type: String,
}

fn default_chapter_type() -> String { "chapter".to_string() }

/// Session metadata file written to the capture output directory.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionData {
    /// Human-readable book / project title.
    pub book_name: String,
    /// Base output directory (parent of the book folder).
    pub output_dir: String,
    /// File prefix used for page images.
    pub file_prefix: String,
    /// Page-turn key name.
    pub page_turn_key: String,
    /// Delay between captures in milliseconds.
    pub delay_between_ms: u64,
    /// Maximum pages to capture (null = unlimited).
    pub max_pages: Option<u32>,
    /// Number of pages successfully captured so far.
    pub pages_captured: u32,
    /// Capture region in screen coordinates.
    pub region: SessionRegion,
    /// ISO-8601 timestamp when the session was first created.
    pub created_at: String,
    /// ISO-8601 timestamp when the session was last updated.
    pub updated_at: String,
    /// Per-page metadata; absent in legacy sessions (defaults to empty vec).
    #[serde(default)]
    pub pages: Vec<SessionPage>,
    /// Chapter structure; absent in legacy sessions (defaults to empty vec).
    #[serde(default)]
    pub chapters: Vec<SessionChapter>,
    /// EPUB metadata (title, author, etc.); absent in legacy sessions.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub epub_metadata: Option<SessionEpubMetadata>,
    /// OCR and capture settings; absent in legacy sessions.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ocr_settings: Option<SessionOcrSettings>,
}

/// Return the path to the session file inside `dir`.
pub fn session_path(dir: &str) -> PathBuf {
    Path::new(dir).join(SESSION_FILENAME)
}

/// Write (or overwrite) the session file in `dir`.
pub fn write_session(dir: &str, data: &SessionData) -> Result<(), String> {
    let path = session_path(dir);
    let json = serde_json::to_string_pretty(data)
        .map_err(|e| format!("Failed to serialize session: {e}"))?;
    std::fs::write(&path, json).map_err(|e| format!("Failed to write session file: {e}"))
}

/// Read the session file from `dir`, or return `None` if it doesn't exist / is invalid.
pub fn read_session(dir: &str) -> Option<SessionData> {
    let path = session_path(dir);
    let text = std::fs::read_to_string(&path).ok()?;
    serde_json::from_str(&text).ok()
}

/// Return the current UTC time as an ISO-8601 string without external crate dependencies.
/// Uses a simple, stable format: "2026-01-02T15:04:05Z"
pub fn now_iso8601() -> String {
    // We just use a SystemTime-based approach.
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    // Convert UNIX epoch seconds to a simple ISO date/time string.
    // We implement this without any external crate.
    let s = secs;
    let (y, mo, d, h, mi, sec) = unix_secs_to_datetime(s);
    format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z", y, mo, d, h, mi, sec)
}

/// Minimal UNIX → Gregorian calendar conversion (UTC).
fn unix_secs_to_datetime(secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let sec = secs % 60;
    let min = (secs / 60) % 60;
    let hour = (secs / 3600) % 24;
    let days = secs / 86400; // days since 1970-01-01

    // Gregorian calendar month/day from day count
    let mut year = 1970u64;
    let mut remaining = days;
    loop {
        let in_year = days_in_year(year);
        if remaining < in_year {
            break;
        }
        remaining -= in_year;
        year += 1;
    }
    let mut month = 1u64;
    loop {
        let in_month = days_in_month(year, month);
        if remaining < in_month {
            break;
        }
        remaining -= in_month;
        month += 1;
    }
    let day = remaining + 1;
    (year, month, day, hour, min, sec)
}

fn is_leap(year: u64) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn days_in_year(year: u64) -> u64 {
    if is_leap(year) { 366 } else { 365 }
}

fn days_in_month(year: u64, month: u64) -> u64 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => if is_leap(year) { 29 } else { 28 },
        _ => 30,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn sample_region() -> SessionRegion {
        SessionRegion { x: 100, y: 200, width: 800, height: 600 }
    }

    fn sample_session() -> SessionData {
        SessionData {
            book_name: "My Book".to_string(),
            output_dir: "C:\\Books".to_string(),
            file_prefix: "page".to_string(),
            page_turn_key: "Right".to_string(),
            delay_between_ms: 1500,
            max_pages: None,
            pages_captured: 0,
            region: sample_region(),
            created_at: "2026-01-01T00:00:00Z".to_string(),
            updated_at: "2026-01-01T00:00:00Z".to_string(),
            pages: vec![],
            chapters: vec![],
            epub_metadata: None,
            ocr_settings: None,
        }
    }

    #[test]
    fn write_and_read_session() {
        let dir = TempDir::new().unwrap();
        let dir_str = dir.path().to_str().unwrap();
        let data = sample_session();
        write_session(dir_str, &data).unwrap();
        let loaded = read_session(dir_str).expect("should be readable");
        assert_eq!(loaded.book_name, "My Book");
        assert_eq!(loaded.pages_captured, 0);
        assert_eq!(loaded.region.width, 800);
    }

    #[test]
    fn read_session_missing_file_returns_none() {
        let dir = TempDir::new().unwrap();
        let dir_str = dir.path().to_str().unwrap();
        assert!(read_session(dir_str).is_none());
    }

    #[test]
    fn read_session_corrupt_file_returns_none() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join(SESSION_FILENAME);
        fs::write(&path, b"not valid json {{{").unwrap();
        assert!(read_session(dir.path().to_str().unwrap()).is_none());
    }

    #[test]
    fn now_iso8601_produces_valid_format() {
        let ts = now_iso8601();
        // e.g. "2026-03-20T14:30:00Z"
        assert!(ts.ends_with('Z'));
        assert_eq!(ts.len(), 20);
        assert_eq!(&ts[4..5], "-");
        assert_eq!(&ts[7..8], "-");
    }

    #[test]
    fn session_path_appends_filename() {
        let p = session_path("C:\\Books\\MyBook");
        assert!(p.ends_with(SESSION_FILENAME));
    }

    // --- Step 42: SessionPage serde tests ---

    fn sample_page() -> SessionPage {
        SessionPage {
            page_number: 1,
            image_path: "book/page-001.png".to_string(),
            timestamp: 1700000000,
            capture_status: "ok".to_string(),
            page_type: "text".to_string(),
            ocr_status: "pending".to_string(),
            user_notes: None,
            error_message: None,
            ocr_raw_text: None,
            ocr_confidence: None,
            ocr_blocks: None,
            ocr_edited_blocks: None,
        }
    }

    #[test]
    fn session_page_round_trip() {
        let page = sample_page();
        let json = serde_json::to_string(&page).unwrap();
        let back: SessionPage = serde_json::from_str(&json).unwrap();
        assert_eq!(back, page);
    }

    #[test]
    fn session_page_defaults_when_fields_absent() {
        // Legacy JSON missing capture_status, page_type, ocr_status
        let json = r#"{"pageNumber":1,"imagePath":"book/page-001.png","timestamp":1700000000}"#;
        let page: SessionPage = serde_json::from_str(json).unwrap();
        assert_eq!(page.capture_status, "ok");
        assert_eq!(page.page_type, "text");
        assert_eq!(page.ocr_status, "pending");
    }

    #[test]
    fn session_data_legacy_json_gets_empty_pages() {
        // Old session JSON with no "pages" field → default to empty vec
        let legacy = r#"{
            "bookName": "Old Book",
            "outputDir": "C:\\Old",
            "filePrefix": "page",
            "pageTurnKey": "Right",
            "delayBetweenMs": 1500,
            "maxPages": null,
            "pagesCaptured": 5,
            "region": {"x":0,"y":0,"width":800,"height":600},
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z"
        }"#;
        let data: SessionData = serde_json::from_str(legacy).unwrap();
        assert_eq!(data.book_name, "Old Book");
        assert!(data.pages.is_empty());
    }

    #[test]
    fn session_data_with_pages_round_trip() {
        let mut data = sample_session();
        data.pages.push(sample_page());
        let json = serde_json::to_string_pretty(&data).unwrap();
        let back: SessionData = serde_json::from_str(&json).unwrap();
        assert_eq!(back.pages.len(), 1);
        assert_eq!(back.pages[0].page_type, "text");
    }
}
