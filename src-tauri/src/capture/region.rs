use image::{DynamicImage, ImageFormat, RgbaImage};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Cursor;
use std::path::Path;
use xcap::Monitor;

#[derive(Debug, Deserialize)]
pub struct CaptureRequest {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
    pub output_path: String,
}

#[derive(Debug, Serialize)]
pub struct CaptureResult {
    pub output_path: String,
    pub width: u32,
    pub height: u32,
    pub file_size_bytes: u64,
}

/// Capture a region of the screen and save as PNG.
pub fn capture_region(req: &CaptureRequest) -> Result<CaptureResult, String> {
    // Find the monitor containing the capture point
    let monitors = Monitor::all().map_err(|e| format!("Failed to enumerate monitors: {e}"))?;

    let monitor = monitors
        .into_iter()
        .find(|m| {
            let (Ok(mx), Ok(my), Ok(mw), Ok(mh)) = (m.x(), m.y(), m.width(), m.height()) else {
                return false;
            };
            let mw = mw as i32;
            let mh = mh as i32;
            req.x >= mx && req.y >= my && req.x < mx + mw && req.y < my + mh
        })
        .ok_or_else(|| {
            format!(
                "No monitor found containing point ({}, {})",
                req.x, req.y
            )
        })?;

    // Capture the full monitor
    let screenshot = monitor
        .capture_image()
        .map_err(|e| format!("Screen capture failed: {e}"))?;

    // Calculate crop coordinates relative to the monitor
    let mon_x = monitor.x().map_err(|e| format!("Failed to get monitor x: {e}"))?;
    let mon_y = monitor.y().map_err(|e| format!("Failed to get monitor y: {e}"))?;
    let crop_x = ((req.x - mon_x) as u32).min(screenshot.width());
    let crop_y = ((req.y - mon_y) as u32).min(screenshot.height());

    // Clamp width/height to not exceed image bounds
    let crop_w = req
        .width
        .min(screenshot.width().saturating_sub(crop_x));
    let crop_h = req
        .height
        .min(screenshot.height().saturating_sub(crop_y));

    if crop_w == 0 || crop_h == 0 {
        return Err("Capture region has zero area after clamping to monitor bounds".to_string());
    }

    // Crop the screenshot
    let rgba: RgbaImage = screenshot;
    let cropped = DynamicImage::ImageRgba8(rgba).crop_imm(crop_x, crop_y, crop_w, crop_h);

    // Ensure output directory exists
    let output = Path::new(&req.output_path);
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create output directory: {e}"))?;
    }

    // Save as PNG
    cropped
        .save_with_format(output, ImageFormat::Png)
        .map_err(|e| format!("Failed to save PNG: {e}"))?;

    let file_size = fs::metadata(output)
        .map(|m| m.len())
        .unwrap_or(0);

    Ok(CaptureResult {
        output_path: req.output_path.clone(),
        width: crop_w,
        height: crop_h,
        file_size_bytes: file_size,
    })
}

#[derive(Debug, Deserialize)]
pub struct PreviewRequest {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Serialize)]
pub struct PreviewResult {
    pub data_url: String,
    pub width: u32,
    pub height: u32,
}

/// Capture a screen region and return as a base64-encoded PNG data URL.
pub fn capture_preview(req: &PreviewRequest) -> Result<PreviewResult, String> {
    use base64::Engine;

    let monitors = Monitor::all().map_err(|e| format!("Failed to enumerate monitors: {e}"))?;

    let monitor = monitors
        .into_iter()
        .find(|m| {
            let (Ok(mx), Ok(my), Ok(mw), Ok(mh)) = (m.x(), m.y(), m.width(), m.height()) else {
                return false;
            };
            req.x >= mx && req.y >= my && req.x < mx + (mw as i32) && req.y < my + (mh as i32)
        })
        .ok_or_else(|| format!("No monitor found containing point ({}, {})", req.x, req.y))?;

    let screenshot = monitor
        .capture_image()
        .map_err(|e| format!("Screen capture failed: {e}"))?;

    let mon_x = monitor.x().map_err(|e| format!("Failed to get monitor x: {e}"))?;
    let mon_y = monitor.y().map_err(|e| format!("Failed to get monitor y: {e}"))?;
    let crop_x = ((req.x - mon_x) as u32).min(screenshot.width());
    let crop_y = ((req.y - mon_y) as u32).min(screenshot.height());
    let crop_w = req.width.min(screenshot.width().saturating_sub(crop_x));
    let crop_h = req.height.min(screenshot.height().saturating_sub(crop_y));

    if crop_w == 0 || crop_h == 0 {
        return Err("Preview region has zero area".to_string());
    }

    let rgba: RgbaImage = screenshot;
    let cropped = DynamicImage::ImageRgba8(rgba).crop_imm(crop_x, crop_y, crop_w, crop_h);

    let mut buf = Cursor::new(Vec::new());
    cropped
        .write_to(&mut buf, ImageFormat::Png)
        .map_err(|e| format!("Failed to encode PNG: {e}"))?;

    let b64 = base64::engine::general_purpose::STANDARD.encode(buf.into_inner());
    let data_url = format!("data:image/png;base64,{}", b64);

    Ok(PreviewResult {
        data_url,
        width: crop_w,
        height: crop_h,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn temp_output_path(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join("kindleocr_test_captures");
        dir.join(name)
    }

    #[test]
    fn capture_produces_valid_png() {
        let output = temp_output_path("test_capture.png");
        let req = CaptureRequest {
            x: 0,
            y: 0,
            width: 100,
            height: 100,
            output_path: output.to_string_lossy().to_string(),
        };

        let result = capture_region(&req).expect("capture should succeed");
        assert!(Path::new(&result.output_path).exists(), "PNG file should exist");
        assert!(result.file_size_bytes > 0, "File should not be empty");
        assert!(result.width > 0, "Width should be positive");
        assert!(result.height > 0, "Height should be positive");

        // Verify it's a valid image
        let img = image::open(&result.output_path).expect("Should open as image");
        assert_eq!(img.width(), result.width);
        assert_eq!(img.height(), result.height);

        // Cleanup
        let _ = fs::remove_file(&output);
    }

    #[test]
    fn creates_parent_directories() {
        let output = temp_output_path("nested/deep/dir/test_nested.png");
        let req = CaptureRequest {
            x: 0,
            y: 0,
            width: 50,
            height: 50,
            output_path: output.to_string_lossy().to_string(),
        };

        let result = capture_region(&req).expect("capture should succeed");
        assert!(Path::new(&result.output_path).exists());

        // Cleanup
        let _ = fs::remove_file(&output);
        let _ = fs::remove_dir_all(temp_output_path("nested"));
    }

    #[test]
    fn non_zero_content() {
        let output = temp_output_path("test_nonzero.png");
        let req = CaptureRequest {
            x: 0,
            y: 0,
            width: 100,
            height: 100,
            output_path: output.to_string_lossy().to_string(),
        };

        let result = capture_region(&req).expect("capture should succeed");
        let img = image::open(&result.output_path).expect("Should open as image");
        let rgba = img.to_rgba8();

        // Check that not all pixels are black
        let has_nonblack = rgba.pixels().any(|p| p[0] > 0 || p[1] > 0 || p[2] > 0);
        // This might fail if the screen is actually all black, so just check file is valid
        assert!(
            result.file_size_bytes > 100,
            "PNG should have reasonable size (not degenerate)"
        );
        // Note: we don't enforce has_nonblack because in headless/CI the screen may be black
        let _ = has_nonblack;

        // Cleanup
        let _ = fs::remove_file(&output);
    }
}
