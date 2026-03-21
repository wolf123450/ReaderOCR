"""Tests for EPUB assembly (Step 30)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from kindleocr.epub.builder import EpubBuildParams, EpubBuildResult, EpubMetadata, build_epub
from kindleocr.epub.html_formatter import blocks_to_html, text_to_html_paragraphs
from kindleocr.ocr.engine import BoundingBox, OcrPageResult, TextBlock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _block(text: str, btype: str = "body") -> TextBlock:
    return TextBlock(
        type=btype,
        text=text,
        confidence=0.95,
        bbox=BoundingBox(x=10, y=10, width=200, height=20),
    )


def _page(page_index: int, texts: list[str], btype: str = "body") -> OcrPageResult:
    blocks = [_block(t, btype) for t in texts]
    return OcrPageResult(
        page_index=page_index,
        blocks=blocks,
        raw_text=" ".join(texts),
        avg_confidence=0.95,
    )


def _simple_meta(**kwargs) -> EpubMetadata:
    return EpubMetadata(
        title=kwargs.get("title", "Test Book"),
        author=kwargs.get("author", "Test Author"),
        language=kwargs.get("language", "en"),
    )


def _is_valid_epub(path: Path) -> bool:
    """Return True if path is a ZIP file with mimetype file."""
    if not zipfile.is_zipfile(path):
        return False
    with zipfile.ZipFile(path) as zf:
        return "mimetype" in zf.namelist()


# ---------------------------------------------------------------------------
# html_formatter tests
# ---------------------------------------------------------------------------

class TestHtmlFormatter:

    def test_body_block_to_p(self):
        html = blocks_to_html([_block("Hello world.")])
        assert "<p>Hello world.</p>" in html

    def test_chapter_title_to_h1(self):
        html = blocks_to_html([_block("Chapter One", "chapter_title")])
        assert "<h1>Chapter One</h1>" in html

    def test_section_heading_to_h2(self):
        html = blocks_to_html([_block("Section A", "section_heading")])
        assert "<h2>Section A</h2>" in html

    def test_sidebar_to_aside(self):
        html = blocks_to_html([_block("Side note", "sidebar")])
        assert "<aside>" in html

    def test_excluded_omitted(self):
        html = blocks_to_html([
            _block("Visible", "body"),
            _block("Hidden", "excluded"),
        ])
        assert "Visible" in html
        assert "Hidden" not in html

    def test_header_omitted(self):
        html = blocks_to_html([
            _block("Header Text", "header"),
            _block("Body Text", "body"),
        ])
        assert "Header Text" not in html
        assert "Body Text" in html

    def test_footer_omitted(self):
        html = blocks_to_html([_block("Footer", "footer")])
        assert "Footer" not in html

    def test_page_number_omitted(self):
        html = blocks_to_html([_block("42", "page_number")])
        assert html.strip() == ""

    def test_figure_caption_omitted_from_blocks_to_html(self):
        html = blocks_to_html([_block("Fig. 1: A diagram", "figure_caption")])
        assert "Fig. 1" not in html

    def test_html_escaping(self):
        html = blocks_to_html([_block('<b>bold</b> & "quotes"')])
        assert "&lt;b&gt;" in html
        assert "&amp;" in html
        assert "&quot;" in html

    def test_text_to_html_paragraphs(self):
        html = text_to_html_paragraphs("First paragraph.\n\nSecond paragraph.")
        assert html.count("<p>") == 2
        assert "First paragraph." in html
        assert "Second paragraph." in html


# ---------------------------------------------------------------------------
# EPUB builder tests
# ---------------------------------------------------------------------------

class TestEpubBuilder:

    def test_minimal_epub_created(self, tmp_path):
        """Single chapter, no cover → valid EPUB produced."""
        out = tmp_path / "test.epub"
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=[_page(0, ["Hello world."])],
            output_path=str(out),
        )
        result = build_epub(params)
        assert out.exists()
        assert result.file_size_bytes > 0
        assert _is_valid_epub(out)

    def test_returns_epub_build_result(self, tmp_path):
        out = tmp_path / "test.epub"
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=[_page(0, ["Some text."])],
            output_path=str(out),
        )
        result = build_epub(params)
        assert isinstance(result, EpubBuildResult)
        assert result.output_path == str(out)
        assert result.page_count == 1

    def test_multi_chapter(self, tmp_path):
        """3 chapters → 3 chapter XHTML files in EPUB spine."""
        from kindleocr.epub.chapter_mapper import ChapterSegment
        out = tmp_path / "multi.epub"
        chapters: list[ChapterSegment] = [
            {"id": "c0", "title": "Introduction", "chapterIndex": 0, "sources": [{"pageIndex": 0, "start": 0.0, "end": 1.0}], "chapterType": "chapter"},
            {"id": "c1", "title": "Chapter One", "chapterIndex": 1, "sources": [{"pageIndex": 1, "start": 0.0, "end": 1.0}], "chapterType": "chapter"},
            {"id": "c2", "title": "Chapter Two", "chapterIndex": 2, "sources": [{"pageIndex": 2, "start": 0.0, "end": 1.0}], "chapterType": "chapter"},
        ]
        pages = [
            _page(0, ["Intro text."]),
            _page(1, ["Chapter one body."]),
            _page(2, ["Chapter two body."]),
        ]
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=chapters,
            pages=pages,
            output_path=str(out),
        )
        result = build_epub(params)
        assert result.chapter_count == 3
        # Verify 3 chapter XHTML files exist in the ZIP
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        xhtml_chapters = [n for n in names if n.startswith("EPUB/Text/chapter_")]
        assert len(xhtml_chapters) == 3

    def test_metadata_in_opf(self, tmp_path):
        """Title and author should appear in content.opf."""
        out = tmp_path / "meta.epub"
        params = EpubBuildParams(
            metadata=EpubMetadata(
                title="My Great Novel",
                author="Jane Doe",
                language="fr",
            ),
            chapters=[],
            pages=[_page(0, ["Text."])],
            output_path=str(out),
        )
        build_epub(params)
        with zipfile.ZipFile(out) as zf:
            opf_names = [n for n in zf.namelist() if n.endswith(".opf")]
            assert opf_names, "No OPF file found in EPUB"
            opf_content = zf.read(opf_names[0]).decode("utf-8")
        assert "My Great Novel" in opf_content
        assert "Jane Doe" in opf_content

    def test_css_included(self, tmp_path):
        """CSS file should be present in the EPUB archive."""
        out = tmp_path / "css.epub"
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=[_page(0, ["Text."])],
            output_path=str(out),
        )
        build_epub(params)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert any(n.endswith("book.css") for n in names)

    def test_excluded_blocks_not_in_epub(self, tmp_path):
        """Blocks of type 'excluded' should not appear in chapter HTML."""
        out = tmp_path / "excl.epub"
        pages = [
            OcrPageResult(
                page_index=0,
                blocks=[
                    _block("Visible text.", "body"),
                    _block("Secret text.", "excluded"),
                ],
                raw_text="Visible text. Secret text.",
                avg_confidence=0.95,
            )
        ]
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=pages,
            output_path=str(out),
        )
        build_epub(params)
        with zipfile.ZipFile(out) as zf:
            ch_names = [n for n in zf.namelist() if n.startswith("EPUB/Text/chapter_")]
            content = zf.read(ch_names[0]).decode("utf-8")
        assert "Visible text." in content
        assert "Secret text." not in content

    def test_header_footer_not_in_epub(self, tmp_path):
        """Header and footer blocks should be omitted from chapter HTML."""
        out = tmp_path / "hf.epub"
        pages = [
            OcrPageResult(
                page_index=0,
                blocks=[
                    _block("Running Header", "header"),
                    _block("Main content here.", "body"),
                    _block("Page 5", "footer"),
                ],
                raw_text="Running Header Main content here. Page 5",
                avg_confidence=0.95,
            )
        ]
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=pages,
            output_path=str(out),
        )
        build_epub(params)
        with zipfile.ZipFile(out) as zf:
            ch_names = [n for n in zf.namelist() if n.startswith("EPUB/Text/chapter_")]
            content = zf.read(ch_names[0]).decode("utf-8")
        assert "Running Header" not in content
        assert "Page 5" not in content
        assert "Main content here." in content

    def test_section_heading_h2(self, tmp_path):
        """section_heading block type → <h2> in output."""
        out = tmp_path / "h2.epub"
        pages = [
            OcrPageResult(
                page_index=0,
                blocks=[
                    _block("Section Title", "section_heading"),
                    _block("Section body text.", "body"),
                ],
                raw_text="Section Title Section body text.",
                avg_confidence=0.95,
            )
        ]
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=pages,
            output_path=str(out),
        )
        build_epub(params)
        with zipfile.ZipFile(out) as zf:
            ch_names = [n for n in zf.namelist() if n.startswith("EPUB/Text/chapter_")]
            content = zf.read(ch_names[0]).decode("utf-8")
        assert "<h2>Section Title</h2>" in content

    def test_empty_chapter_skipped(self, tmp_path):
        """Chapter with no matching pages is not included."""
        from kindleocr.epub.chapter_mapper import ChapterSegment
        out = tmp_path / "empty_ch.epub"
        chapters: list[ChapterSegment] = [
            {"id": "c0", "title": "Chapter A", "chapterIndex": 0, "sources": [{"pageIndex": 0, "start": 0.0, "end": 1.0}], "chapterType": "chapter"},
            {"id": "c1", "title": "Chapter B (no pages)", "chapterIndex": 1, "sources": [{"pageIndex": 99, "start": 0.0, "end": 1.0}], "chapterType": "chapter"},
        ]
        pages = [_page(0, ["Chapter A content."])]
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=chapters,
            pages=pages,
            output_path=str(out),
        )
        result = build_epub(params)
        assert result.chapter_count == 1

    def test_edited_blocks_used_in_epub(self, tmp_path):
        """edited_blocks override replaces raw OCR blocks in chapter HTML."""
        out = tmp_path / "edited.epub"
        pages = [_page(0, ["Original text."])]
        edited = {
            0: [_block("Edited text.")]
        }
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=pages,
            output_path=str(out),
            edited_blocks=edited,
        )
        build_epub(params)
        with zipfile.ZipFile(out) as zf:
            ch_names = [n for n in zf.namelist() if n.startswith("EPUB/Text/chapter_")]
            content = zf.read(ch_names[0]).decode("utf-8")
        assert "Edited text." in content
        assert "Original text." not in content

    def test_missing_edited_blocks_fallback(self, tmp_path):
        """Pages without edited_blocks entry fall back to raw OCR blocks."""
        out = tmp_path / "fallback.epub"
        pages = [_page(0, ["Raw text."])]
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=pages,
            output_path=str(out),
            edited_blocks={},  # empty — no override for page 0
        )
        build_epub(params)
        with zipfile.ZipFile(out) as zf:
            ch_names = [n for n in zf.namelist() if n.startswith("EPUB/Text/chapter_")]
            content = zf.read(ch_names[0]).decode("utf-8")
        assert "Raw text." in content

    def test_file_size_positive(self, tmp_path):
        out = tmp_path / "size.epub"
        params = EpubBuildParams(
            metadata=_simple_meta(),
            chapters=[],
            pages=[_page(0, ["Some content."])],
            output_path=str(out),
        )
        result = build_epub(params)
        assert result.file_size_bytes > 0
