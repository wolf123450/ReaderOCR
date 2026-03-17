# Step 32: EPUB Validation

**Phase**: 6 — EPUB Generation  
**Layer**: Python sidecar  
**Dependencies**: Step 30 (EPUB assembly)

## Objective

Validate the generated EPUB file against EPUB 3.0 standards. Check for structural correctness, required metadata, valid HTML content, and image references. Report errors and warnings.

## Inputs

```python
EpubValidateParams:
    epub_path: str   # Path to generated EPUB file
```

## Outputs

```python
EpubValidateResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
```

## Algorithm

### Structural validation
1. Verify EPUB is a valid ZIP file
2. Check `mimetype` file exists and is first entry (uncompressed)
3. Verify `META-INF/container.xml` exists and is valid XML
4. Verify `content.opf` exists and contains required elements

### Metadata validation
1. `dc:title` present and non-empty
2. `dc:language` present and valid BCP 47
3. `dc:identifier` present
4. `dcterms:modified` present (EPUB 3 requirement)

### Content validation
1. All files referenced in manifest exist in the ZIP
2. All spine items reference valid manifest items
3. HTML content is well-formed XHTML
4. Images referenced in HTML exist in manifest
5. TOC navigation document is valid

### Optional: epubcheck integration
1. If Java is available and epubcheck JAR is present, run `java -jar epubcheck.jar` for full validation
2. Parse epubcheck output for errors/warnings
3. If epubcheck is not available, use built-in validation only

## Files to Create/Modify

- `src-python/kindleocr/epub/validator.py` — EPUB validation logic
- `src-python/tests/test_epub_validator.py` — Tests with valid and intentionally broken EPUBs

## Edge Cases

- EPUB file doesn't exist → clear error "File not found"
- Corrupted ZIP → "Invalid EPUB: not a valid ZIP archive"
- Missing mimetype → error (some readers still work, but mark as warning)
- XHTML parsing errors → report line/column number
- Very large EPUB → stream validation, don't load entire file into memory
- External epubcheck not available → graceful fallback to built-in checks with note

## Test Criteria

### Automated (pytest)
1. **Valid EPUB passes**: Build a correct EPUB → validator returns valid=True, no errors
2. **Missing title detected**: EPUB without dc:title → error reported
3. **Missing manifest item**: Reference non-existent file → error reported
4. **Malformed XHTML**: Invalid HTML in chapter → error with details
5. **Valid ZIP check**: Non-ZIP file → appropriate error message
6. **Warnings separate from errors**: Missing optional metadata → warning, not error
