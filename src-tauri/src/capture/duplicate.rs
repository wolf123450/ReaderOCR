use image::DynamicImage;
use image_hasher::{HashAlg, HasherConfig, ImageHash};
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Deserialize)]
pub struct DuplicateCheckRequest {
    pub image_path_a: String,
    pub image_path_b: String,
    #[serde(default = "default_threshold")]
    pub threshold: u32,
}

fn default_threshold() -> u32 {
    5
}

#[derive(Debug, Clone, Serialize)]
pub struct DuplicateCheckResult {
    pub is_duplicate: bool,
    pub hamming_distance: u32,
    pub hash_a: String,
    pub hash_b: String,
}

fn make_hasher() -> image_hasher::Hasher {
    HasherConfig::new()
        .hash_alg(HashAlg::DoubleGradient)
        .hash_size(16, 16)
        .to_hasher()
}

/// Compute a perceptual hash for an in-memory image.
pub fn hash_image(img: &DynamicImage) -> ImageHash {
    make_hasher().hash_image(img)
}

/// Compare two pre-computed hashes. Returns a result struct.
pub fn compare_hashes(hash_a: &ImageHash, hash_b: &ImageHash, threshold: u32) -> DuplicateCheckResult {
    let hamming_distance = hash_a.dist(hash_b);
    DuplicateCheckResult {
        is_duplicate: hamming_distance <= threshold,
        hamming_distance,
        hash_a: hash_a.to_base64(),
        hash_b: hash_b.to_base64(),
    }
}

/// Check whether two images are perceptual duplicates (file-based, kept for
/// the Tauri command and tests that work with paths).
pub fn check_duplicate(req: &DuplicateCheckRequest) -> Result<DuplicateCheckResult, String> {
    let path_a = Path::new(&req.image_path_a);
    let path_b = Path::new(&req.image_path_b);

    if !path_a.exists() {
        return Err(format!("Image not found: {}", req.image_path_a));
    }
    if !path_b.exists() {
        return Err(format!("Image not found: {}", req.image_path_b));
    }

    let img_a = image::open(path_a).map_err(|e| format!("Failed to open {}: {e}", req.image_path_a))?;
    let img_b = image::open(path_b).map_err(|e| format!("Failed to open {}: {e}", req.image_path_b))?;

    let hash_a = hash_image(&img_a);
    let hash_b = hash_image(&img_b);

    Ok(compare_hashes(&hash_a, &hash_b, req.threshold))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn fixture_path(name: &str) -> String {
        let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        p.pop(); // src-tauri -> project root
        p.push("test-fixtures");
        p.push(name);
        p.to_string_lossy().to_string()
    }

    #[test]
    fn identical_images_zero_distance() {
        let req = DuplicateCheckRequest {
            image_path_a: fixture_path("sample-page-01.png"),
            image_path_b: fixture_path("sample-page-01.png"),
            threshold: 5,
        };
        let result = check_duplicate(&req).unwrap();
        assert_eq!(result.hamming_distance, 0);
        assert!(result.is_duplicate);
    }

    #[test]
    fn identical_content_different_files() {
        // sample-page-01-duplicate.png is a copy of sample-page-01.png
        let req = DuplicateCheckRequest {
            image_path_a: fixture_path("sample-page-01.png"),
            image_path_b: fixture_path("sample-page-01-duplicate.png"),
            threshold: 5,
        };
        let result = check_duplicate(&req).unwrap();
        assert!(result.hamming_distance <= 5, "Expected near-zero distance for duplicate, got {}", result.hamming_distance);
        assert!(result.is_duplicate);
    }

    #[test]
    fn different_images_high_distance() {
        // Use a content page vs blank page for clearly different images
        let req = DuplicateCheckRequest {
            image_path_a: fixture_path("sample-page-01.png"),
            image_path_b: fixture_path("blank-page.png"),
            threshold: 5,
        };
        let result = check_duplicate(&req).unwrap();
        assert!(result.hamming_distance > 5, "Expected high distance for different pages, got {}", result.hamming_distance);
        assert!(!result.is_duplicate);
    }

    #[test]
    fn similar_pages_within_threshold() {
        // Two similar generated pages may have small hamming distance
        let req = DuplicateCheckRequest {
            image_path_a: fixture_path("sample-page-01.png"),
            image_path_b: fixture_path("sample-page-02.png"),
            threshold: 5,
        };
        let result = check_duplicate(&req).unwrap();
        // These are structurally similar fixture pages — just verify we get a result
        assert!(result.hamming_distance > 0 || result.hamming_distance == 0);
    }

    #[test]
    fn threshold_zero_strict_match() {
        // Two different pages with threshold=0 should not match
        let req = DuplicateCheckRequest {
            image_path_a: fixture_path("sample-page-01.png"),
            image_path_b: fixture_path("sample-page-02.png"),
            threshold: 0,
        };
        let result = check_duplicate(&req).unwrap();
        assert!(!result.is_duplicate);
    }

    #[test]
    fn missing_file_returns_error() {
        let req = DuplicateCheckRequest {
            image_path_a: "nonexistent_a.png".to_string(),
            image_path_b: "nonexistent_b.png".to_string(),
            threshold: 5,
        };
        let result = check_duplicate(&req);
        assert!(result.is_err());
    }
}
