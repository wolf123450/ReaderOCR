use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};
use std::sync::Arc;

use image::DynamicImage;
use super::region::{capture_region, CaptureRequest};
use crate::keyboard::input::{send_page_turn, PageTurnConfig};

/// Batch capture state constants.
const STATE_CAPTURING: u8 = 1;
const STATE_PAUSED: u8 = 2;
const STATE_STOPPED: u8 = 3;

#[derive(Debug, Deserialize)]
pub struct BatchCaptureConfig {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
    pub window_handle: u64,
    pub output_dir: String,
    pub delay_between_ms: u64,
    pub max_pages: Option<u32>,
    pub file_prefix: String,
    pub page_turn_key: String,
    #[serde(default = "default_start_page")]
    pub start_page: u32,
    #[serde(default)]
    pub book_name: String,
}

fn default_start_page() -> u32 {
    1
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CaptureProgress {
    pub page_number: u32,
    pub total_pages: Option<u32>,
    pub image_path: String,
    pub status: String, // "captured" or "error"
    pub error_message: Option<String>,
}

/// Shared state for controlling the batch loop from outside.
#[derive(Clone)]
pub struct BatchControl {
    state: Arc<AtomicU8>,
    pub should_stop: Arc<AtomicBool>,
}

impl BatchControl {
    pub fn new() -> Self {
        Self {
            state: Arc::new(AtomicU8::new(STATE_CAPTURING)),
            should_stop: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn pause(&self) {
        self.state.store(STATE_PAUSED, Ordering::SeqCst);
    }

    pub fn resume(&self) {
        self.state.store(STATE_CAPTURING, Ordering::SeqCst);
    }

    pub fn stop(&self) {
        self.should_stop.store(true, Ordering::SeqCst);
        self.state.store(STATE_STOPPED, Ordering::SeqCst);
    }

    pub fn is_paused(&self) -> bool {
        self.state.load(Ordering::SeqCst) == STATE_PAUSED
    }

    pub fn is_stopped(&self) -> bool {
        self.should_stop.load(Ordering::SeqCst)
    }
}

/// Format a page filename with zero-padded number.
pub fn format_page_path(output_dir: &str, prefix: &str, page_num: u32) -> String {
    let filename = format!("{}-{:03}.png", prefix, page_num);
    let path: PathBuf = [output_dir, &filename].iter().collect();
    path.to_string_lossy().to_string()
}

/// Run a single capture iteration and return both the progress event and the
/// captured image data (for in-memory duplicate hashing).
pub fn capture_single_page(
    config: &BatchCaptureConfig,
    page_number: u32,
) -> (CaptureProgress, Option<DynamicImage>) {
    let output_path = format_page_path(&config.output_dir, &config.file_prefix, page_number);

    let req = CaptureRequest {
        x: config.x,
        y: config.y,
        width: config.width,
        height: config.height,
        output_path: output_path.clone(),
    };

    match capture_region(&req) {
        Ok((_result, img)) => (
            CaptureProgress {
                page_number,
                total_pages: config.max_pages,
                image_path: output_path,
                status: "captured".to_string(),
                error_message: None,
            },
            Some(img),
        ),
        Err(e) => (
            CaptureProgress {
                page_number,
                total_pages: config.max_pages,
                image_path: output_path,
                status: "error".to_string(),
                error_message: Some(e),
            },
            None,
        ),
    }
}

/// Send a page turn to the target window.
pub fn turn_page(config: &BatchCaptureConfig) -> Result<(), String> {
    let page_turn_config = PageTurnConfig {
        window_handle: config.window_handle,
        key: config.page_turn_key.clone(),
        delay_before_ms: None,
    };
    send_page_turn(&page_turn_config)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn format_page_path_zero_pads() {
        let path = format_page_path("output", "page", 1);
        assert!(path.ends_with("page-001.png"));
        let path = format_page_path("output", "page", 42);
        assert!(path.ends_with("page-042.png"));
        let path = format_page_path("output", "book", 999);
        assert!(path.ends_with("book-999.png"));
    }

    #[test]
    fn batch_control_state_transitions() {
        let ctrl = BatchControl::new();
        assert!(!ctrl.is_paused());
        assert!(!ctrl.is_stopped());

        ctrl.pause();
        assert!(ctrl.is_paused());
        assert!(!ctrl.is_stopped());

        ctrl.resume();
        assert!(!ctrl.is_paused());

        ctrl.stop();
        assert!(ctrl.is_stopped());
    }

    #[test]
    fn capture_single_page_produces_file() {
        let output_dir = std::env::temp_dir()
            .join("kindleocr_batch_test")
            .to_string_lossy()
            .to_string();

        let config = BatchCaptureConfig {
            x: 0,
            y: 0,
            width: 50,
            height: 50,
            window_handle: 0,
            output_dir: output_dir.clone(),
            delay_between_ms: 0,
            max_pages: Some(1),
            file_prefix: "test".to_string(),
            page_turn_key: "Right".to_string(),
            start_page: 1,
            book_name: String::new(),
        };

        let (progress, _img) = capture_single_page(&config, 1);
        assert_eq!(progress.status, "captured");
        assert_eq!(progress.page_number, 1);
        assert!(std::path::Path::new(&progress.image_path).exists());

        // Cleanup
        let _ = std::fs::remove_dir_all(&output_dir);
    }

    /// Profiling test: captures a 1280×800 region 5 times and prints per-phase
    /// timings so we can see where the per-page time is being spent.
    /// Run with: cargo test profile_capture_cycle -- --nocapture --ignored
    #[test]
    #[ignore]
    fn profile_capture_cycle() {

        let output_dir = std::env::temp_dir()
            .join("kindleocr_profile_test")
            .to_string_lossy()
            .to_string();

        let config = BatchCaptureConfig {
            x: 0,
            y: 0,
            width: 1280,
            height: 800,
            window_handle: 0,
            output_dir: output_dir.clone(),
            delay_between_ms: 0,
            max_pages: Some(5),
            file_prefix: "prof".to_string(),
            page_turn_key: "Right".to_string(),
            start_page: 1,
            book_name: String::new(),
        };

        println!("\n=== KindleOCR capture profiling (5 pages, 1280×800) ===");

        let mut prev_hash: Option<image_hasher::ImageHash> = None;

        for page in 1u32..=5 {
            let t_cycle = std::time::Instant::now();

            // --- capture ---
            let t_cap = std::time::Instant::now();
            let (progress, img) = capture_single_page(&config, page);
            let cap_ms = t_cap.elapsed().as_millis();
            assert_eq!(progress.status, "captured", "Capture failed on page {page}");
            let img = img.unwrap();

            // --- in-memory duplicate check (page 2 onwards) ---
            let dup_ms = if let Some(ph) = &prev_hash {
                use crate::capture::duplicate::{hash_image, compare_hashes};
                let t_dup = std::time::Instant::now();
                let curr_hash = hash_image(&img);
                let _result = compare_hashes(ph, &curr_hash, 5);
                let ms = t_dup.elapsed().as_millis();
                prev_hash = Some(curr_hash);
                ms
            } else {
                use crate::capture::duplicate::hash_image;
                prev_hash = Some(hash_image(&img));
                0
            };

            let cycle_ms = t_cycle.elapsed().as_millis();
            println!(
                "  page {page}: capture={cap_ms}ms  dup_check={dup_ms}ms  cycle_total={cycle_ms}ms"
            );
        }

        println!("=== done ===\n");
        let _ = std::fs::remove_dir_all(&output_dir);
    }
}
