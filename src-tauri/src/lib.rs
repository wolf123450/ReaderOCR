mod capture;
mod keyboard;

use std::sync::Mutex;
use tauri::Emitter;
use capture::windows_api::WindowInfo;
use capture::region::{CaptureRequest, CaptureResult};
use capture::batch::{BatchCaptureConfig, BatchControl, CaptureProgress, capture_single_page, turn_page};
use keyboard::input::{PageTurnConfig, PageTurnResult};

#[tauri::command]
fn list_windows() -> Result<Vec<WindowInfo>, String> {
    capture::windows_api::list_windows()
}

#[tauri::command]
fn capture_region(request: CaptureRequest) -> Result<CaptureResult, String> {
    capture::region::capture_region(&request)
}

#[tauri::command]
fn send_page_turn(config: PageTurnConfig) -> Result<PageTurnResult, String> {
    keyboard::input::send_page_turn(&config)
}

#[tauri::command]
async fn start_batch_capture(
    config: BatchCaptureConfig,
    control: tauri::State<'_, Mutex<BatchControl>>,
    app: tauri::AppHandle,
) -> Result<Vec<CaptureProgress>, String> {
    // Reset control for new session
    let ctrl = {
        let mut guard = control.lock().map_err(|e| format!("Lock error: {e}"))?;
        *guard = BatchControl::new();
        guard.clone()
    };

    // Create output directory
    std::fs::create_dir_all(&config.output_dir)
        .map_err(|e| format!("Failed to create output dir: {e}"))?;

    let delay = std::cmp::max(config.delay_between_ms, 200);
    let mut results: Vec<CaptureProgress> = Vec::new();
    let mut page_num: u32 = 1;

    loop {
        if ctrl.is_stopped() {
            break;
        }

        // Pause loop
        while ctrl.is_paused() {
            if ctrl.is_stopped() {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        if ctrl.is_stopped() {
            break;
        }

        // Capture
        let progress = capture_single_page(&config, page_num);
        let _ = app.emit("capture-progress", &progress);
        let had_error = progress.status == "error";
        results.push(progress);

        if had_error {
            break;
        }

        // Check max pages
        if let Some(max) = config.max_pages {
            if page_num >= max {
                break;
            }
        }

        // Page turn
        if let Err(e) = turn_page(&config) {
            let err_progress = CaptureProgress {
                page_number: page_num,
                total_pages: config.max_pages,
                image_path: String::new(),
                status: "error".to_string(),
                error_message: Some(format!("Page turn failed: {e}")),
            };
            let _ = app.emit("capture-progress", &err_progress);
            results.push(err_progress);
            break;
        }

        // Delay
        std::thread::sleep(std::time::Duration::from_millis(delay));

        page_num += 1;
    }

    Ok(results)
}

#[tauri::command]
fn pause_batch_capture(control: tauri::State<'_, Mutex<BatchControl>>) -> Result<(), String> {
    let guard = control.lock().map_err(|e| format!("Lock error: {e}"))?;
    guard.pause();
    Ok(())
}

#[tauri::command]
fn resume_batch_capture(control: tauri::State<'_, Mutex<BatchControl>>) -> Result<(), String> {
    let guard = control.lock().map_err(|e| format!("Lock error: {e}"))?;
    guard.resume();
    Ok(())
}

#[tauri::command]
fn stop_batch_capture(control: tauri::State<'_, Mutex<BatchControl>>) -> Result<(), String> {
    let guard = control.lock().map_err(|e| format!("Lock error: {e}"))?;
    guard.stop();
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .manage(Mutex::new(BatchControl::new()))
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      list_windows,
      capture_region,
      send_page_turn,
      start_batch_capture,
      pause_batch_capture,
      resume_batch_capture,
      stop_batch_capture
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
