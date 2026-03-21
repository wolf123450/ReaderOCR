mod capture;
mod keyboard;
mod sidecar;

use std::sync::Mutex;
use tauri::Emitter;
use tauri::Manager;
use capture::windows_api::WindowInfo;
use capture::region::{CaptureRequest, CaptureResult, PreviewRequest, PreviewResult};
use capture::batch::{BatchCaptureConfig, BatchControl, CaptureProgress, capture_single_page, turn_page, format_page_path};
use capture::duplicate::{DuplicateCheckRequest, DuplicateCheckResult};use capture::session::{SessionData, SessionRegion, read_session, write_session, now_iso8601};
use keyboard::input::{PageTurnConfig, PageTurnResult};
use sidecar::client::SidecarClient;

#[tauri::command]
fn list_windows() -> Result<Vec<WindowInfo>, String> {
    capture::windows_api::list_windows()
}

#[tauri::command]
fn capture_region(request: CaptureRequest) -> Result<CaptureResult, String> {
    capture::region::capture_region(&request).map(|(result, _img)| result)
}

#[tauri::command]
fn capture_preview(request: PreviewRequest) -> Result<PreviewResult, String> {
    capture::region::capture_preview(&request)
}

#[tauri::command]
fn send_page_turn(config: PageTurnConfig) -> Result<PageTurnResult, String> {
    keyboard::input::send_page_turn(&config)
}

#[tauri::command]
fn check_duplicate(request: DuplicateCheckRequest) -> Result<DuplicateCheckResult, String> {
    capture::duplicate::check_duplicate(&request)
}

#[tauri::command]
async fn start_batch_capture(
    config: BatchCaptureConfig,
    control: tauri::State<'_, Mutex<BatchControl>>,
    app: tauri::AppHandle,
) -> Result<(), String> {
    // Reset control for new session and clone the Arc-based handle for the thread.
    let ctrl = {
        let mut guard = control.lock().map_err(|e| format!("Lock error: {e}"))?;
        *guard = BatchControl::new();
        guard.clone()
    };

    // Create output directory before spawning so we can report errors synchronously.
    std::fs::create_dir_all(&config.output_dir)
        .map_err(|e| format!("Failed to create output dir: {e}"))?;

    // Write (or refresh) session file immediately so it exists before capturing.
    let ts = now_iso8601();
    let region = SessionRegion {
        x: config.x,
        y: config.y,
        width: config.width,
        height: config.height,
    };
    // Store the base output dir (without the book-name subfolder) so that
    // reloading sets outputDir = base and bookName = subfolder correctly.
    let base_output_dir = strip_book_name_suffix(&config.output_dir, &config.book_name);
    let existing = read_session(&config.output_dir);
    let session = SessionData {
        book_name: config.book_name.clone(),
        output_dir: base_output_dir.clone(),
        file_prefix: config.file_prefix.clone(),
        page_turn_key: config.page_turn_key.clone(),
        delay_between_ms: config.delay_between_ms,
        max_pages: config.max_pages,
        pages_captured: if config.start_page > 1 { config.start_page - 1 } else { 0 },
        region: region.clone(),
        created_at: existing.as_ref().map(|s| s.created_at.clone()).unwrap_or_else(|| ts.clone()),
        updated_at: ts.clone(),
    };
    let _ = write_session(&config.output_dir, &session);

    // Spawn the blocking capture loop on a dedicated thread so the IPC
    // channel is not blocked and pause/stop commands can be received.
    tauri::async_runtime::spawn_blocking(move || {
        let delay = std::cmp::max(config.delay_between_ms, 200);
        let mut page_num: u32 = config.start_page;
        let mut pages_done: u32 = if config.start_page > 1 { config.start_page - 1 } else { 0 };
        let mut prev_page_hash: Option<image_hasher::ImageHash> = None;

        loop {
            if ctrl.is_stopped() {
                break;
            }

            while ctrl.is_paused() {
                if ctrl.is_stopped() { break; }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
            if ctrl.is_stopped() {
                break;
            }

            let t_page = std::time::Instant::now();
            let (progress, captured_img) = capture_single_page(&config, page_num);
            eprintln!("[PROFILE] --- page {} ---", page_num);
            eprintln!("[PROFILE] capture_single_page: {}ms", t_page.elapsed().as_millis());
            let _ = app.emit("capture-progress", &progress);
            let had_error = progress.status == "error";

            if !had_error {
                pages_done = page_num;
                // Update session file after each successful capture.
                let updated = SessionData {
                    pages_captured: pages_done,
                    updated_at: now_iso8601(),
                    // Preserve original created_at and everything else unchanged.
                    book_name: config.book_name.clone(),
                    output_dir: config.output_dir.clone(),
                    file_prefix: config.file_prefix.clone(),
                    page_turn_key: config.page_turn_key.clone(),
                    delay_between_ms: config.delay_between_ms,
                    max_pages: config.max_pages,
                    region: region.clone(),
                    created_at: session.created_at.clone(),
                };
                let _ = write_session(&config.output_dir, &updated);
            }

            if had_error {
                let _ = app.emit("capture-stopped", serde_json::json!({ "reason": "error" }));
                break;
            }

            // Duplicate detection — compare in-memory hashes, no disk re-read.
            if page_num > 1 {
                if let (Some(prev_hash), Some(img)) = (&prev_page_hash, &captured_img) {
                    let t_dup = std::time::Instant::now();
                    let curr_hash = capture::duplicate::hash_image(img);
                    let dup_result = capture::duplicate::compare_hashes(prev_hash, &curr_hash, 5);
                    eprintln!("[PROFILE] dup_check (mem):     {:>5}ms  (dist={})",
                        t_dup.elapsed().as_millis(), dup_result.hamming_distance);
                    if dup_result.is_duplicate {
                        let _ = app.emit("capture-duplicate-detected", &dup_result);
                        let _ = app.emit("capture-completed", serde_json::json!({ "pages": pages_done }));
                        break;
                    }
                    prev_page_hash = Some(curr_hash);
                }
            } else {
                // Page 1: just store the hash for the next iteration.
                if let Some(img) = &captured_img {
                    prev_page_hash = Some(capture::duplicate::hash_image(img));
                }
            }

            // Check max pages
            if let Some(max) = config.max_pages {
                if page_num >= max {
                    let _ = app.emit("capture-completed", serde_json::json!({ "pages": pages_done }));
                    break;
                }
            }

            // Page turn
            let t_turn = std::time::Instant::now();
            if let Err(e) = turn_page(&config) {
                let err_progress = CaptureProgress {
                    page_number: page_num,
                    total_pages: config.max_pages,
                    image_path: String::new(),
                    status: "error".to_string(),
                    error_message: Some(format!("Page turn failed: {e}")),
                };
                let _ = app.emit("capture-progress", &err_progress);
                let _ = app.emit("capture-stopped", serde_json::json!({ "reason": "page_turn_failed" }));
                break;
            }

            eprintln!("[PROFILE] turn_page:           {:>5}ms", t_turn.elapsed().as_millis());

            let t_sleep = std::time::Instant::now();
            std::thread::sleep(std::time::Duration::from_millis(delay));
            eprintln!("[PROFILE] sleep({}ms):        {:>5}ms", delay, t_sleep.elapsed().as_millis());
            eprintln!("[PROFILE] page {} TOTAL cycle: {}ms", page_num, t_page.elapsed().as_millis());
            page_num += 1;
        }

        // If we exited the loop normally (ctrl.is_stopped()) without breaking via
        // duplicate/max-pages, emit stopped so the frontend can react.
        if ctrl.is_stopped() {
            let _ = app.emit("capture-stopped", serde_json::json!({ "reason": "user_stopped" }));
        }
    });

    Ok(())
}

/// Strip `\book_name` or `/book_name` suffix from `dir` if present.
/// Used to recover the base output directory from the effective dir.
fn strip_book_name_suffix(dir: &str, book_name: &str) -> String {
    if book_name.is_empty() {
        return dir.to_string();
    }
    let suffix_bs = format!("\\{book_name}");
    let suffix_fs = format!("/{book_name}");
    if dir.ends_with(&suffix_bs) {
        dir[..dir.len() - suffix_bs.len()].to_string()
    } else if dir.ends_with(&suffix_fs) {
        dir[..dir.len() - suffix_fs.len()].to_string()
    } else {
        dir.to_string()
    }
}

#[tauri::command]
fn load_session(dir: String) -> Option<SessionData> {
    read_session(&dir)
}

#[tauri::command]
fn save_session(dir: String, data: SessionData) -> Result<(), String> {
    std::fs::create_dir_all(&dir)
        .map_err(|e| format!("Failed to create directory: {e}"))?;
    write_session(&dir, &data)
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

#[tauri::command]
fn sidecar_status(client: tauri::State<'_, Mutex<SidecarClient>>) -> Result<bool, String> {
    let guard = client.lock().map_err(|e| e.to_string())?;
    Ok(guard.is_running())
}

#[tauri::command]
fn sidecar_ping(client: tauri::State<'_, Mutex<SidecarClient>>) -> Result<serde_json::Value, String> {
    let guard = client.lock().map_err(|e| e.to_string())?;
    guard.call::<serde_json::Value, serde_json::Value>("ping", serde_json::json!({}))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .manage(Mutex::new(BatchControl::new()))
    .manage(Mutex::new(SidecarClient::new()))
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Spawn sidecar in background so it doesn't block app startup
      let sidecar_state = app.state::<Mutex<SidecarClient>>();
      let client = sidecar_state.lock().expect("Failed to lock sidecar state");

      // Resolve Python path: prefer venv, fall back to system python
      let resource_dir = app.path().resource_dir().unwrap_or_default();
      let src_python_dir = resource_dir.parent()
          .and_then(|p: &std::path::Path| p.parent())
          .and_then(|p: &std::path::Path| p.parent())
          .map(|p: &std::path::Path| p.join("src-python"))
          .unwrap_or_else(|| std::path::PathBuf::from("src-python"));

      let venv_python = src_python_dir.join(".venv").join("Scripts").join("python.exe");
      let python_path = if venv_python.exists() {
          venv_python.to_string_lossy().to_string()
      } else {
          "python".to_string()
      };

      let project_dir = src_python_dir.to_string_lossy().to_string();

      match client.spawn(&python_path, &project_dir) {
          Ok(()) => log::info!("Sidecar spawned successfully"),
          Err(e) => log::warn!("Failed to spawn sidecar: {e}"),
      }

      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      list_windows,
      capture_region,
      capture_preview,
      send_page_turn,
      check_duplicate,
      start_batch_capture,
      pause_batch_capture,
      resume_batch_capture,
      stop_batch_capture,
      load_session,
      save_session,
      sidecar_status,
      sidecar_ping
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
