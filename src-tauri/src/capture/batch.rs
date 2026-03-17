use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};
use std::sync::Arc;

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
}

#[derive(Debug, Clone, Serialize)]
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

/// Run a single capture iteration: capture + page turn.
pub fn capture_single_page(
    config: &BatchCaptureConfig,
    page_number: u32,
) -> CaptureProgress {
    let output_path = format_page_path(&config.output_dir, &config.file_prefix, page_number);

    let req = CaptureRequest {
        x: config.x,
        y: config.y,
        width: config.width,
        height: config.height,
        output_path: output_path.clone(),
    };

    match capture_region(&req) {
        Ok(_result) => CaptureProgress {
            page_number,
            total_pages: config.max_pages,
            image_path: output_path,
            status: "captured".to_string(),
            error_message: None,
        },
        Err(e) => CaptureProgress {
            page_number,
            total_pages: config.max_pages,
            image_path: output_path,
            status: "error".to_string(),
            error_message: Some(e),
        },
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
        };

        let progress = capture_single_page(&config, 1);
        assert_eq!(progress.status, "captured");
        assert_eq!(progress.page_number, 1);
        assert!(std::path::Path::new(&progress.image_path).exists());

        // Cleanup
        let _ = std::fs::remove_dir_all(&output_dir);
    }
}
