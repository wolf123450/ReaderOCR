"""EPUB assembly using ebooklib (Step 30).

Assembles a valid EPUB 3.0 file from:
- Book metadata (title, author, language, cover)
- Chapter structure (ChapterSegment[] from step 43)
- Per-page OCR text blocks (with optional edited overrides from step 46)
- Figure regions (from step 47 — optional, used when crop paths are provided)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ebooklib import epub  # type: ignore[import]

from kindleocr.epub.chapter_mapper import ChapterSegment, map_chapters
from kindleocr.epub.html_formatter import blocks_to_html, text_to_html_paragraphs
from kindleocr.ocr.engine import OcrPageResult, TextBlock
from kindleocr.processing.paragraphs import reconstruct_paragraphs

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class EpubMetadata:
    title: str
    author: str
    language: str = "en"
    description: str = ""
    publisher: str = ""
    isbn: str = ""
    cover_image_path: str = ""


@dataclass
class EpubBuildParams:
    metadata: EpubMetadata
    chapters: List[ChapterSegment]
    pages: List[OcrPageResult]
    output_path: str
    edited_blocks: Optional[Dict[int, List[TextBlock]]] = None  # page_index → blocks


@dataclass
class EpubBuildResult:
    output_path: str
    file_size_bytes: int
    chapter_count: int
    page_count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DEFAULT_CSS = """\
body {
  font-family: Georgia, "Times New Roman", Times, serif;
  font-size: 1em;
  line-height: 1.6;
  margin: 1em 2em;
}
h1 {
  font-size: 1.5em;
  font-weight: bold;
  margin-top: 2em;
  margin-bottom: 0.5em;
}
h2 {
  font-size: 1.2em;
  font-weight: bold;
  margin-top: 1.5em;
  margin-bottom: 0.4em;
}
p {
  margin: 0.4em 0;
  text-indent: 1.2em;
}
p:first-child, h1 + p, h2 + p {
  text-indent: 0;
}
aside {
  border-left: 3px solid #888;
  padding-left: 0.8em;
  margin: 1em 0;
  color: #555;
}
figure {
  margin: 1em 0;
  text-align: center;
}
figcaption {
  font-size: 0.85em;
  color: #666;
  margin-top: 0.3em;
}
"""


def _make_chapter_html(title: str, body_html: str, css_href: str = "../Styles/book.css") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <meta charset="UTF-8"/>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="{css_href}"/>
</head>
<body>
<h1>{title}</h1>
{body_html}
</body>
</html>"""


def _blocks_for_page(
    page: OcrPageResult,
    edited_blocks: Optional[Dict[int, List[TextBlock]]],
) -> List[TextBlock]:
    """Return blocks for a page, using edited_blocks override when present."""
    if edited_blocks and page.page_index in edited_blocks:
        return edited_blocks[page.page_index]
    return page.blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_epub(params: EpubBuildParams) -> EpubBuildResult:
    """Build and write an EPUB file.  Returns metadata about the output."""
    book = epub.EpubBook()

    # ── Metadata ──────────────────────────────────────────────────────────
    identifier = params.metadata.isbn if params.metadata.isbn else f"urn:uuid:{uuid.uuid4()}"
    book.set_identifier(identifier)
    book.set_title(params.metadata.title)
    book.set_language(params.metadata.language)
    book.add_author(params.metadata.author)
    if params.metadata.description:
        book.add_metadata("DC", "description", params.metadata.description)
    if params.metadata.publisher:
        book.add_metadata("DC", "publisher", params.metadata.publisher)

    # ── Cover ─────────────────────────────────────────────────────────────
    if params.metadata.cover_image_path:
        cover_path = Path(params.metadata.cover_image_path)
        if cover_path.exists():
            with open(cover_path, "rb") as f:
                cover_data = f.read()
            suffix = cover_path.suffix.lower()
            media_type = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
            book.set_cover(cover_path.name, cover_data, media_type=media_type)

    # ── CSS ───────────────────────────────────────────────────────────────
    css_item = epub.EpubItem(
        uid="style",
        file_name="Styles/book.css",
        media_type="text/css",
        content=_DEFAULT_CSS.encode("utf-8"),
    )
    book.add_item(css_item)

    # ── Chapter content ───────────────────────────────────────────────────
    # Build a page_index → OcrPageResult lookup
    page_lookup: Dict[int, OcrPageResult] = {
        p.page_index: p for p in params.pages
    }

    epub_chapters: List[epub.EpubHtml] = []
    toc_entries: List[epub.Link] = []

    if params.chapters:
        content_entries = map_chapters(params.chapters)

        # Group entries by chapter index
        chapter_groups: Dict[int, list] = {}
        for entry in content_entries:
            chapter_groups.setdefault(entry["chapterIndex"], []).append(entry)

        for ch_idx in sorted(chapter_groups.keys()):
            group = chapter_groups[ch_idx]
            chapter_title = group[0]["title"]

            # Collect pages for this chapter
            chapter_pages = [
                page_lookup[entry["pageIndex"]]
                for entry in group
                if entry["pageIndex"] in page_lookup
            ]

            if not chapter_pages:
                continue  # skip empty chapters

            # Reconstruct paragraphs across pages in this chapter
            reconstructed = reconstruct_paragraphs(
                chapter_pages,
                edited_blocks=params.edited_blocks,
            )

            # Convert to HTML — if we have rich blocks use them, else fall
            # back to the reconstructed plain text
            if any(
                _blocks_for_page(p, params.edited_blocks)
                for p in chapter_pages
            ):
                # Concatenate block HTML from all pages
                all_blocks: List[TextBlock] = []
                for p in chapter_pages:
                    all_blocks.extend(_blocks_for_page(p, params.edited_blocks))
                body_html = blocks_to_html(all_blocks)
            else:
                body_html = text_to_html_paragraphs(reconstructed.text)

            chapter_file = f"Text/chapter_{ch_idx:04d}.xhtml"
            epub_ch = epub.EpubHtml(
                title=chapter_title,
                file_name=chapter_file,
                lang=params.metadata.language,
            )
            epub_ch.content = _make_chapter_html(chapter_title, body_html).encode("utf-8")
            epub_ch.add_item(css_item)
            book.add_item(epub_ch)
            epub_chapters.append(epub_ch)
            toc_entries.append(epub.Link(chapter_file, chapter_title, f"chapter_{ch_idx}"))

    else:
        # No chapters defined → single chapter with all pages
        all_pages = sorted(params.pages, key=lambda p: p.page_index)
        all_blocks: List[TextBlock] = []
        for p in all_pages:
            all_blocks.extend(_blocks_for_page(p, params.edited_blocks))
        body_html = blocks_to_html(all_blocks) if all_blocks else text_to_html_paragraphs(
            reconstruct_paragraphs(all_pages, edited_blocks=params.edited_blocks).text
        )
        chapter_title = params.metadata.title

        epub_ch = epub.EpubHtml(
            title=chapter_title,
            file_name="Text/chapter_0000.xhtml",
            lang=params.metadata.language,
        )
        epub_ch.content = _make_chapter_html(chapter_title, body_html).encode("utf-8")
        epub_ch.add_item(css_item)
        book.add_item(epub_ch)
        epub_chapters.append(epub_ch)
        toc_entries.append(epub.Link("Text/chapter_0000.xhtml", chapter_title, "chapter_0"))

    # ── TOC and spine ─────────────────────────────────────────────────────
    book.toc = tuple(toc_entries)
    book.spine = ["nav"] + epub_chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # ── Write output ──────────────────────────────────────────────────────
    output_path = Path(params.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book, {})

    file_size = output_path.stat().st_size
    return EpubBuildResult(
        output_path=str(output_path),
        file_size_bytes=file_size,
        chapter_count=len(epub_chapters),
        page_count=len(params.pages),
    )
