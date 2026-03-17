# Step 15: Image Preprocessing

**Phase**: 3 — OCR Pipeline  
**Layer**: Python sidecar  
**Dependencies**: Step 14 (sidecar setup)

## Objective

Preprocess captured page images before OCR: auto-crop borders, deskew rotated captures, and normalize contrast. This improves OCR accuracy on imperfect captures.

## Inputs

```python
PreprocessImageParams:
    image_path: str          # Path to source PNG
    output_path: str         # Path to save processed PNG
    auto_crop: bool = True
    deskew: bool = True
    normalize_contrast: bool = True
```

## Outputs

```python
PreprocessImageResult:
    output_path: str
    original_size: tuple[int, int]   # (width, height)
    processed_size: tuple[int, int]
```

## Algorithm

### Auto-crop
1. Convert image to grayscale
2. Apply binary threshold (pixel > 240 = background)
3. Find bounding box of non-background content via `ImageOps.invert()` + `getbbox()`
4. Add small padding (10px) to avoid cutting into text
5. Crop to bounding box

### Deskew
1. Convert to grayscale
2. Apply Canny edge detection or threshold
3. Use Hough line transform (via numpy/scipy) to detect dominant angle
4. If angle is small (< 5°), rotate to correct
5. If angle is large (> 5°), skip (likely not a skew issue)

### Contrast normalization
1. Convert to grayscale
2. Apply histogram equalization (`ImageOps.equalize`) or adaptive CLAHE
3. Alternatively: auto-levels (stretch histogram to full 0-255 range)

### Processing order
Auto-crop → deskew → normalize contrast

## Files to Create/Modify

- `src-python/kindleocr/ocr/preprocessing.py` — preprocessing functions
- `src-python/tests/test_preprocessing.py` — pytest tests

## Edge Cases

- Image is already clean (no borders, no skew) → should pass through unchanged
- Entirely white or black image → auto-crop returns empty bbox → return original image
- Very small crop result (< 50×50) → skip crop, return original
- Deskew angle detection is noisy → only correct if confidence is high (multiple lines agree on angle)
- Non-PNG input (JPEG, BMP) → Pillow handles these transparently

## Test Criteria

### Automated (pytest)
1. **Auto-crop**: Fixture image with 50px white border → cropped output should be ~100px smaller in each dimension
2. **No-op crop**: Image with no padding → output dimensions match input (within padding tolerance)
3. **Deskew**: Fixture image rotated 2° → output should be within 0.5° of horizontal
4. **Contrast normalization**: Dark image (histogram concentrated at low values) → normalized histogram should span wider range
5. **Pipeline preserves content**: After full preprocessing, image should still contain readable text (visual check via test fixture comparison)
6. **Empty image handling**: All-white image → returns original without crashing
