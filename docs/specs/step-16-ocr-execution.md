# Step 16: OCR Execution

**Phase**: 3 — OCR Pipeline  
**Layer**: Python sidecar  
**Dependencies**: Step 15 (preprocessed images)

## Objective

Run PaddleOCR on preprocessed page images and return structured text results with bounding boxes and confidence scores.

## Inputs

```python
OcrProcessPageParams:
    image_path: str                           # Path to (preprocessed) page image
    engine: Literal["ppocr", "ppocr_vl"] = "ppocr"  # OCR engine variant
```

## Outputs

```python
OcrPageResult:
    page_index: int
    blocks: List[TextBlock]     # Each detected text region
    raw_text: str               # All text concatenated in reading order
    avg_confidence: float       # Mean confidence across all blocks

TextBlock:
    type: BlockType             # "body" for now; layout analysis refines later
    text: str
    confidence: float           # 0.0 to 1.0
    bbox: BoundingBox           # x, y, width, height
```

## Algorithm

1. Initialize PaddleOCR engine (lazy singleton — first call loads model, subsequent calls reuse):
   - `ppocr`: `PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)`
   - `ppocr_vl`: PaddleOCR-VL model (if available)
2. Run OCR: `result = ocr.ocr(image_path, cls=True)`
3. Parse PaddleOCR output format:
   - Each result is `[bbox_points, (text, confidence)]`
   - `bbox_points` is 4 corner points `[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]`
   - Convert to axis-aligned bounding box: `BoundingBox(min_x, min_y, max_x-min_x, max_y-min_y)`
4. Sort blocks by reading order (top-to-bottom, left-to-right)
5. Concatenate text with newlines for `raw_text`
6. Compute `avg_confidence`

## Files to Create/Modify

- `src-python/kindleocr/ocr/engine.py` — OCR engine abstraction (protocol/interface)
- `src-python/kindleocr/ocr/paddle_ocr.py` — PaddleOCR implementation
- `src-python/tests/test_ocr.py` — OCR accuracy tests

## Edge Cases

- PaddleOCR not installed → clear error message ("Install with pip install paddleocr")
- No GPU available → fall back to CPU mode automatically
- Image with no text → return empty blocks list, avg_confidence=0
- Very small text → PaddleOCR may miss; preprocessing (step 15) should help with contrast
- Non-English text → Currently English-only; lang parameter configurable for future
- Model download on first run → may take time; handle gracefully with progress indication

## Test Criteria

### Automated (pytest)
1. **Basic OCR accuracy**: Run OCR on fixture page image with known text → compute character-level Levenshtein similarity → assert > 90%
2. **Structured output**: Result has correct fields (blocks, raw_text, avg_confidence)
3. **Confidence range**: All confidence values in [0.0, 1.0]
4. **Bounding boxes valid**: All bbox values are positive, within image dimensions
5. **Empty image**: All-white image → returns empty blocks list
6. **Engine singleton**: Multiple calls don't re-initialize the model (check via timing or mock)

### Manual verification
7. Run OCR on a real book page capture → visually inspect extracted text for accuracy
