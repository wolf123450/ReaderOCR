use serde::{Deserialize, Serialize};
use std::thread;
use std::time::Duration;
use windows::Win32::Foundation::HWND;
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP,
    VIRTUAL_KEY, VK_LEFT, VK_NEXT, VK_PRIOR, VK_RIGHT, VK_SPACE,
};
use windows::Win32::UI::WindowsAndMessaging::SetForegroundWindow;

#[derive(Debug, Deserialize)]
pub struct PageTurnConfig {
    pub window_handle: u64,
    pub key: String,
    #[serde(default)]
    pub delay_before_ms: Option<u64>,
}

#[derive(Debug, Serialize)]
pub struct PageTurnResult {
    pub success: bool,
    pub key_sent: String,
}

/// Parse a key name string into a Win32 virtual key code.
pub fn parse_key(name: &str) -> Result<VIRTUAL_KEY, String> {
    match name {
        "Right" => Ok(VK_RIGHT),
        "Left" => Ok(VK_LEFT),
        "PageDown" => Ok(VK_NEXT),
        "PageUp" => Ok(VK_PRIOR),
        "Space" => Ok(VK_SPACE),
        _ => Err(format!(
            "Unknown key '{}'. Valid keys: Right, Left, PageDown, PageUp, Space",
            name
        )),
    }
}

/// Simulate a page turn by sending a keypress to the target window.
pub fn send_page_turn(config: &PageTurnConfig) -> Result<PageTurnResult, String> {
    let vk = parse_key(&config.key)?;

    // Bring target window to foreground
    let hwnd = HWND(config.window_handle as *mut std::ffi::c_void);
    unsafe {
        // SetForegroundWindow can fail but we try anyway
        let _ = SetForegroundWindow(hwnd);
    }

    // Optional delay
    if let Some(delay) = config.delay_before_ms {
        if delay > 0 {
            thread::sleep(Duration::from_millis(delay));
        }
    }

    // Send key down + key up
    let inputs = [
        INPUT {
            r#type: INPUT_KEYBOARD,
            Anonymous: INPUT_0 {
                ki: KEYBDINPUT {
                    wVk: vk,
                    wScan: 0,
                    dwFlags: Default::default(),
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        },
        INPUT {
            r#type: INPUT_KEYBOARD,
            Anonymous: INPUT_0 {
                ki: KEYBDINPUT {
                    wVk: vk,
                    wScan: 0,
                    dwFlags: KEYEVENTF_KEYUP,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        },
    ];

    let sent = unsafe { SendInput(&inputs, std::mem::size_of::<INPUT>() as i32) };
    if sent == 0 {
        return Err("SendInput failed: no events were sent".to_string());
    }

    Ok(PageTurnResult {
        success: true,
        key_sent: config.key.clone(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_valid_keys() {
        assert_eq!(parse_key("Right").unwrap(), VK_RIGHT);
        assert_eq!(parse_key("Left").unwrap(), VK_LEFT);
        assert_eq!(parse_key("PageDown").unwrap(), VK_NEXT);
        assert_eq!(parse_key("PageUp").unwrap(), VK_PRIOR);
        assert_eq!(parse_key("Space").unwrap(), VK_SPACE);
    }

    #[test]
    fn parse_invalid_key_returns_error() {
        let result = parse_key("InvalidKey");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("Unknown key"));
        assert!(err.contains("Valid keys"));
    }
}
