# Step 13: Duplicate Detection

**Phase**: 2 — Screen Capture Module  
**Layer**: Rust (Tauri backend)  
**Dependencies**: Step 10 (page capture — needs captured images to compare)

## Objective

Detect when consecutive captured pages are identical (book has ended or page didn't turn), and auto-stop the batch capture loop. Uses perceptual image hashing to handle minor rendering differences.

## Inputs

Two image file paths (current page and previous page).

```typescript
interface DuplicateCheckRequest {
  image_path_a: string;
  image_path_b: string;
  threshold: number;     // Hamming distance threshold (0 = exact match, default: 5)
}
```

## Outputs

```typescript
interface DuplicateCheckResult {
  is_duplicate: boolean;
  hamming_distance: number;  // 0 = identical, higher = more different
  hash_a: string;            // Hex-encoded hash for debugging
  hash_b: string;
}
```

## Algorithm

1. Load both images with the `image` crate
2. Compute perceptual hash (pHash) for each using `image_hasher` crate:
   - Resize to 32×32
   - Convert to grayscale
   - Apply DCT (discrete cosine transform)
   - Generate 64-bit hash
3. Compute Hamming distance between the two hashes
4. `is_duplicate = hamming_distance <= threshold`

### Threshold guidance
- `0`: Pixel-perfect identical
- `1–3`: Nearly identical (minor anti-aliasing or rendering differences)
- `5`: Default — tolerates font smoothing variations across captures
- `>10`: Very different pages

## Files to Create/Modify

- `src-tauri/src/capture/duplicate.rs` — duplicate detection implementation
- `src-tauri/src/capture/mod.rs` — export
- `src-tauri/Cargo.toml` — add `image_hasher` crate

## Edge Cases

- One or both images don't exist → return error
- Images have different dimensions → still hash-comparable (resize step normalizes)
- All-white or all-black pages → will hash the same; this is correct behavior (blank page = duplicate)
- Very similar but different pages (e.g., pages with only a few words changed) → threshold tuning needed; default 5 should handle this

## Test Criteria

### Automated (Rust unit tests)
1. **Identical images**: Hash the same PNG twice → hamming_distance = 0, is_duplicate = true
2. **Different images**: Hash two clearly different images (from test fixtures) → hamming_distance > threshold, is_duplicate = false
3. **Near-duplicate**: Take one image, slightly modify a few pixels → hamming_distance should be small (< 5), is_duplicate = true with default threshold
4. **Threshold respected**: With threshold=0, even hamming_distance=1 → is_duplicate = false
5. **Missing file**: Non-existent path → returns error

### Manual verification
6. Capture the same page twice → detected as duplicate
7. Capture two different pages → not flagged as duplicate
