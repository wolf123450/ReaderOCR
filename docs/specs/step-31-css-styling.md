# Step 31: CSS Styling

**Phase**: 6 — EPUB Generation  
**Layer**: Python sidecar  
**Dependencies**: Step 30 (EPUB assembly)

## Objective

Add a clean, readable CSS stylesheet to the EPUB that ensures consistent typography across e-readers. Support customizable font sizes, margins, and basic formatting.

## Inputs

- Style configuration from user preferences (optional)
- Default stylesheet

## Outputs

- CSS file embedded in EPUB
- All chapter HTML documents reference the stylesheet

## Default Stylesheet

```css
/* Base typography */
body {
    font-family: Georgia, "Times New Roman", serif;
    line-height: 1.6;
    margin: 1em;
    text-align: justify;
}

/* Chapter headings */
h1 {
    font-size: 1.8em;
    text-align: center;
    margin: 2em 0 1em 0;
    page-break-before: always;
}

h2 { font-size: 1.4em; margin-top: 1.5em; }
h3 { font-size: 1.2em; margin-top: 1.2em; }

/* Paragraphs */
p {
    text-indent: 1.5em;
    margin: 0.3em 0;
}

/* First paragraph after heading — no indent */
h1 + p, h2 + p, h3 + p {
    text-indent: 0;
}

/* Page separator (optional) */
.page-break {
    page-break-after: always;
}

/* Cover image */
.cover-image {
    width: 100%;
    height: auto;
    max-width: 100%;
}
```

## Algorithm

1. Define default CSS as a Python string constant
2. Allow user overrides via style configuration dict (font-family, font-size, line-height, margin, text-align)
3. Merge defaults with overrides
4. Create `epub.EpubItem` with CSS content, media_type "text/css"
5. Add stylesheet item to book
6. Reference stylesheet in each chapter's HTML document

## Files to Create/Modify

- `src-python/kindleocr/epub/styles.py` — Default CSS and style configuration
- `src-python/kindleocr/epub/builder.py` — Integrate stylesheet into EPUB build
- `src-python/tests/test_epub_styles.py` — Test CSS generation and overrides

## Edge Cases

- E-reader ignores CSS → use inline styles as fallback for critical formatting
- User provides invalid CSS property → ignore invalid properties, use defaults
- Very custom fonts → don't embed fonts (licensing issues), stick to generic families
- RTL languages → add `direction: rtl` when language is Arabic/Hebrew

## Test Criteria

### Automated (pytest)
1. **Default CSS**: Generated CSS contains expected selectors (body, h1, p)
2. **Override merge**: Custom font-family replaces default, other properties preserved
3. **CSS in EPUB**: Built EPUB contains stylesheet item in manifest
4. **Chapter references CSS**: Each chapter HTML includes `<link>` to stylesheet
5. **RTL support**: Language "ar" → CSS includes `direction: rtl`
