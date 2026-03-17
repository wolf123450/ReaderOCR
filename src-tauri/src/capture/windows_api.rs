use serde::Serialize;
use windows::core::PWSTR;
use windows::Win32::Foundation::{BOOL, HWND, LPARAM, RECT};
use windows::Win32::System::Threading::{
    OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_FORMAT, PROCESS_QUERY_LIMITED_INFORMATION,
};
use windows::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetWindowRect, GetWindowTextLengthW, GetWindowTextW,
    GetWindowThreadProcessId, IsWindowVisible,
};

/// Metadata about a visible top-level window.
#[derive(Debug, Clone, Serialize)]
pub struct WindowInfo {
    pub handle: u64,
    pub title: String,
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
    pub process_name: String,
}

/// Convert a raw u64 handle back to HWND.
fn hwnd_from_raw(raw: u64) -> HWND {
    HWND(raw as *mut std::ffi::c_void)
}

/// Extract the raw pointer value from an HWND as u64.
fn hwnd_to_raw(hwnd: HWND) -> u64 {
    hwnd.0 as u64
}

/// Enumerate all visible top-level windows, excluding self and windows with
/// empty titles or zero dimensions.
pub fn list_windows() -> Result<Vec<WindowInfo>, String> {
    let current_pid = std::process::id();
    let mut windows: Vec<WindowInfo> = Vec::new();

    unsafe {
        EnumWindows(
            Some(enum_window_callback),
            LPARAM(&mut windows as *mut Vec<WindowInfo> as isize),
        )
        .map_err(|e| format!("EnumWindows failed: {e}"))?;
    }

    // Exclude own process
    windows.retain(|w| {
        let mut pid: u32 = 0;
        unsafe {
            GetWindowThreadProcessId(hwnd_from_raw(w.handle), Some(&mut pid));
        }
        pid != current_pid
    });

    windows.sort_by(|a, b| a.title.to_lowercase().cmp(&b.title.to_lowercase()));
    Ok(windows)
}

unsafe extern "system" fn enum_window_callback(hwnd: HWND, lparam: LPARAM) -> BOOL {
    let windows = &mut *(lparam.0 as *mut Vec<WindowInfo>);

    // Skip invisible windows
    if !IsWindowVisible(hwnd).as_bool() {
        return BOOL(1); // continue enumeration
    }

    // Get window title
    let title_len = GetWindowTextLengthW(hwnd);
    if title_len == 0 {
        return BOOL(1);
    }

    let mut title_buf = vec![0u16; (title_len + 1) as usize];
    let copied = GetWindowTextW(hwnd, &mut title_buf);
    if copied == 0 {
        return BOOL(1);
    }
    let title = String::from_utf16_lossy(&title_buf[..copied as usize]);

    if title.is_empty() {
        return BOOL(1);
    }

    // Get window rectangle
    let mut rect = RECT::default();
    if GetWindowRect(hwnd, &mut rect).is_err() {
        return BOOL(1);
    }

    let width = rect.right - rect.left;
    let height = rect.bottom - rect.top;
    if width <= 0 || height <= 0 {
        return BOOL(1);
    }

    // Get process name
    let process_name = get_process_name(hwnd);

    let handle = hwnd_to_raw(hwnd);

    windows.push(WindowInfo {
        handle,
        title,
        x: rect.left,
        y: rect.top,
        width,
        height,
        process_name,
    });

    BOOL(1) // continue enumeration
}

unsafe fn get_process_name(hwnd: HWND) -> String {
    let mut pid: u32 = 0;
    GetWindowThreadProcessId(hwnd, Some(&mut pid));

    if pid == 0 {
        return "Unknown".to_string();
    }

    let Ok(process) = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) else {
        return "Unknown".to_string();
    };

    let mut buf = vec![0u16; 1024];
    let mut size = buf.len() as u32;
    if QueryFullProcessImageNameW(process, PROCESS_NAME_FORMAT(0), PWSTR(buf.as_mut_ptr()), &mut size).is_ok() {
        let full_path = String::from_utf16_lossy(&buf[..size as usize]);
        // Extract just the filename from the full path
        full_path
            .rsplit('\\')
            .next()
            .unwrap_or(&full_path)
            .to_string()
    } else {
        "Unknown".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn returns_at_least_one_window() {
        let windows = list_windows().expect("list_windows should succeed");
        assert!(
            !windows.is_empty(),
            "Should find at least one visible window"
        );
    }

    #[test]
    fn no_empty_titles() {
        let windows = list_windows().expect("list_windows should succeed");
        for w in &windows {
            assert!(!w.title.is_empty(), "Window title should not be empty");
        }
    }

    #[test]
    fn no_zero_area_windows() {
        let windows = list_windows().expect("list_windows should succeed");
        for w in &windows {
            assert!(w.width > 0, "Window width should be positive: {}", w.title);
            assert!(
                w.height > 0,
                "Window height should be positive: {}",
                w.title
            );
        }
    }

    #[test]
    fn excludes_own_process() {
        let current_pid = std::process::id();
        let windows = list_windows().expect("list_windows should succeed");
        for w in &windows {
            let mut pid: u32 = 0;
            unsafe {
                GetWindowThreadProcessId(hwnd_from_raw(w.handle), Some(&mut pid));
            }
            assert_ne!(
                pid, current_pid,
                "Should not include own process window: {}",
                w.title
            );
        }
    }
}
