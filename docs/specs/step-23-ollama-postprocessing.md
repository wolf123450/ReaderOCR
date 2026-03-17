# Step 23: Ollama Post-Processing (Optional)

**Phase**: 4 — Text Post-Processing  
**Layer**: Python sidecar  
**Dependencies**: Steps 19–22 (cleaned/structured text)

## Objective

Optionally send OCR text to a local Ollama instance for error correction, paragraph refinement, or chapter title extraction. This leverages LLM contextual understanding to fix OCR artifacts.

## Inputs

```python
OllamaPostprocessParams:
    text: str           # OCR text to process
    task: Literal["fix_errors", "detect_paragraphs", "detect_chapters"]
    model: str = "llama3"
    endpoint: str = "http://localhost:11434"
```

## Outputs

```python
OllamaPostprocessResult:
    corrected_text: str
    changes_made: int
```

## Algorithm

### HTTP client
1. Use `httpx` to call the Ollama `/api/generate` endpoint
2. Stream response tokens for progress feedback

### Task-specific prompts

**fix_errors**: 
```
Fix OCR errors in the following text. Only correct obvious scanning/recognition 
errors (e.g., "rn" misread as "m", "l" misread as "1"). Do not change meaning, 
style, or add content. Return only the corrected text.
```

**detect_paragraphs**:
```
The following text was extracted via OCR and paragraph breaks may be incorrect. 
Add paragraph breaks (blank lines) where they naturally belong. Do not change 
any words. Return only the reformatted text.
```

**detect_chapters**:
```
Identify chapter titles in the following text. Return a JSON array of objects 
with "title" and "line_number" fields. Only identify clear chapter/section 
headings, not subheadings or paragraph starts.
```

### Response processing
1. Parse Ollama response
2. For fix_errors: diff original vs corrected to count changes
3. For detect_chapters: parse JSON array from response
4. Validate: if response is empty or drastically different (>30% edit distance), reject and return original

## Files to Create/Modify

- `src-python/kindleocr/ollama/postprocess.py` — Ollama HTTP client and prompt templates
- `src-python/tests/test_ollama.py` — tests with mocked HTTP responses

## Edge Cases

- Ollama not running → return error with code OLLAMA_UNAVAILABLE (-32004), do not crash
- Ollama returns empty response → return original text unchanged
- LLM hallucinates extra content → validate output length is within 10% of input; reject if too different
- Network timeout → configurable timeout (default 30s per request), return error
- Very long text → chunk into ~2000-word segments to avoid context limits
- Model not available → clear error message suggesting `ollama pull llama3`

## Test Criteria

### Automated (pytest — mocked HTTP)
1. **fix_errors response parsed**: Mock Ollama returning corrected text → verify changes_made count
2. **detect_chapters response parsed**: Mock returning JSON → verify ChapterBoundary list
3. **Ollama unavailable**: Mock connection refused → verify OLLAMA_UNAVAILABLE error returned
4. **Empty response handling**: Mock empty response → original text returned, changes_made=0
5. **Hallucination guard**: Mock response 50% longer than input → rejected, original returned
6. **Timeout handling**: Mock slow response → verify timeout error after configured duration
