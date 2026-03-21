use serde::{Deserialize, Serialize};
use std::path::Path;

/// Metadata for a single PNG found on disk.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct DiskPageEntry {
    pub page_number: u32,
    pub file_path: String,
    pub file_size_bytes: u64,
    /// UNIX timestamp (seconds) of last modification.
    pub modified_at: i64,
}

/// Result of scanning the output directory for page PNGs.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DiskScanResult {
    pub found: Vec<DiskPageEntry>,
}

/// Scan `output_dir` for files matching `{file_prefix}-NNN.png`.
///
/// - Non-existent directories return an empty result (not an error).
/// - Files with non-numeric suffixes are silently skipped.
/// - Results are sorted by page number ascending.
pub fn scan_session_dir(output_dir: &str, file_prefix: &str) -> DiskScanResult {
    let dir = Path::new(output_dir);
    if !dir.exists() {
        return DiskScanResult { found: vec![] };
    }

    let read_dir = match std::fs::read_dir(dir) {
        Ok(d) => d,
        Err(_) => return DiskScanResult { found: vec![] },
    };

    let prefix_dash = format!("{}-", file_prefix);
    let mut found: Vec<DiskPageEntry> = Vec::new();

    for entry in read_dir.flatten() {
        let fname = entry.file_name();
        let fname_str = fname.to_string_lossy();

        if !fname_str.ends_with(".png") {
            continue;
        }
        if !fname_str.starts_with(prefix_dash.as_str()) {
            continue;
        }

        // Extract the number between prefix- and .png
        let stem = fname_str.trim_end_matches(".png");
        let num_str = &stem[prefix_dash.len()..];
        let page_number = match num_str.parse::<u32>() {
            Ok(n) => n,
            Err(_) => continue, // malformed number → skip silently
        };

        let meta = entry.metadata().ok();
        let file_size_bytes = meta.as_ref().map(|m| m.len()).unwrap_or(0);
        let modified_at = meta
            .and_then(|m| m.modified().ok())
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0);

        found.push(DiskPageEntry {
            page_number,
            file_path: entry.path().to_string_lossy().to_string(),
            file_size_bytes,
            modified_at,
        });
    }

    found.sort_by_key(|e| e.page_number);
    DiskScanResult { found }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn write_png(dir: &TempDir, name: &str) {
        fs::write(dir.path().join(name), b"fake-png").unwrap();
    }

    #[test]
    fn empty_directory_returns_no_entries() {
        let dir = TempDir::new().unwrap();
        let result = scan_session_dir(dir.path().to_str().unwrap(), "book");
        assert!(result.found.is_empty());
    }

    #[test]
    fn nonexistent_directory_returns_no_entries() {
        let result = scan_session_dir("C:\\does\\not\\exist\\surely", "book");
        assert!(result.found.is_empty());
    }

    #[test]
    fn finds_matching_pngs_and_parses_page_numbers() {
        let dir = TempDir::new().unwrap();
        write_png(&dir, "book-001.png");
        write_png(&dir, "book-002.png");
        write_png(&dir, "book-005.png");
        let result = scan_session_dir(dir.path().to_str().unwrap(), "book");
        let nums: Vec<u32> = result.found.iter().map(|e| e.page_number).collect();
        assert_eq!(nums, vec![1, 2, 5]);
    }

    #[test]
    fn ignores_non_matching_files() {
        let dir = TempDir::new().unwrap();
        write_png(&dir, "cover.png");
        fs::write(dir.path().join("notes.txt"), b"hello").unwrap();
        write_png(&dir, "book-003.png");
        let result = scan_session_dir(dir.path().to_str().unwrap(), "book");
        assert_eq!(result.found.len(), 1);
        assert_eq!(result.found[0].page_number, 3);
    }

    #[test]
    fn skips_malformed_page_numbers_without_panic() {
        let dir = TempDir::new().unwrap();
        write_png(&dir, "book-abc.png");
        write_png(&dir, "book-001.png");
        let result = scan_session_dir(dir.path().to_str().unwrap(), "book");
        assert_eq!(result.found.len(), 1);
        assert_eq!(result.found[0].page_number, 1);
    }

    #[test]
    fn result_is_sorted_by_page_number() {
        let dir = TempDir::new().unwrap();
        write_png(&dir, "page-010.png");
        write_png(&dir, "page-003.png");
        write_png(&dir, "page-007.png");
        let result = scan_session_dir(dir.path().to_str().unwrap(), "page");
        let nums: Vec<u32> = result.found.iter().map(|e| e.page_number).collect();
        assert_eq!(nums, vec![3, 7, 10]);
    }
}
