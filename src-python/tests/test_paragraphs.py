"""Tests for paragraph reconstruction (Step 21)."""
from __future__ import annotations

import pytest

from kindleocr.ocr.engine import BoundingBox, OcrPageResult, TextBlock
from kindleocr.processing.paragraphs import reconstruct_paragraphs, ReconstructedText


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _page(page_index: int, blocks: list[tuple[str, str]]) -> OcrPageResult:
    """Build an OcrPageResult from (type, text) tuples."""
    blks = [
        TextBlock(
            type=t,
            text=txt,
            confidence=0.95,
            bbox=BoundingBox(x=10, y=i * 30, width=200, height=20),
        )
        for i, (t, txt) in enumerate(blocks)
    ]
    raw = " ".join(b.text for b in blks if b.type not in {"header", "footer", "page_number", "excluded"})
    return OcrPageResult(
        page_index=page_index,
        blocks=blks,
        raw_text=raw,
        avg_confidence=0.95,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReconstructParagraphs:

    def test_single_page_single_block(self):
        pages = [_page(0, [("body", "Hello world.")])]
        result = reconstruct_paragraphs(pages)
        assert "Hello world." in result.text
        assert result.paragraph_count >= 1

    def test_empty_pages_returns_empty(self):
        result = reconstruct_paragraphs([])
        assert result.text == ""
        assert result.paragraphs == []
        assert result.paragraph_count == 0

    def test_header_footer_excluded(self):
        pages = [_page(0, [
            ("header", "My Book Title"),
            ("body", "First paragraph text."),
            ("footer", "Page 1"),
        ])]
        result = reconstruct_paragraphs(pages)
        assert "My Book Title" not in result.text
        assert "Page 1" not in result.text
        assert "First paragraph text." in result.text

    def test_page_number_excluded(self):
        pages = [_page(0, [
            ("page_number", "42"),
            ("body", "The quick brown fox."),
        ])]
        result = reconstruct_paragraphs(pages)
        # standalone "42" from page_number block should not be in output
        assert "42" not in result.text
        assert "quick brown fox" in result.text

    def test_hyphen_rejoin_across_pages(self):
        """'compre-' ending page N + 'hensive' starting page N+1 → 'comprehensive'."""
        pages = [
            _page(0, [("body", "This is compre-")]),
            _page(1, [("body", "hensive text.")]),
        ]
        result = reconstruct_paragraphs(pages)
        assert "comprehensive" in result.text
        # The hyphen should be gone
        assert "compre-" not in result.text

    def test_continuation_lowercase_start(self):
        """Page N ends without punctuation, page N+1 starts lowercase → merge."""
        pages = [
            _page(0, [("body", "The quick brown fox")]),
            _page(1, [("body", "jumped over the fence.")]),
        ]
        result = reconstruct_paragraphs(pages)
        # Should be in one paragraph, tokens adjacent
        assert "fox" in result.text and "jumped" in result.text
        # No paragraph break between them
        assert "fox\n\njumped" not in result.text

    def test_paragraph_break_after_sentence_end(self):
        """Page N ends with period, page N+1 starts uppercase → new paragraph."""
        pages = [
            _page(0, [("body", "End of paragraph.")]),
            _page(1, [("body", "Start of new paragraph.")]),
        ]
        result = reconstruct_paragraphs(pages)
        assert result.paragraph_count >= 2
        assert "End of paragraph." in result.paragraphs[0]
        assert "Start of new paragraph." in result.paragraphs[1]

    def test_chapter_title_forces_paragraph_break(self):
        """chapter_title block gets emitted as its own paragraph."""
        pages = [_page(0, [
            ("body", "End of previous chapter."),
            ("chapter_title", "Chapter Two"),
            ("body", "Start of chapter two."),
        ])]
        result = reconstruct_paragraphs(pages)
        assert "Chapter Two" in result.text
        assert result.paragraph_count >= 3

    def test_multiple_pages_all_body(self):
        pages = [
            _page(0, [("body", "Page one text.")]),
            _page(1, [("body", "Page two text.")]),
            _page(2, [("body", "Page three text.")]),
        ]
        result = reconstruct_paragraphs(pages)
        assert "Page one" in result.text
        assert "Page two" in result.text
        assert "Page three" in result.text

    def test_edited_blocks_override(self):
        """edited_blocks for a page replaces raw OCR blocks."""
        from kindleocr.ocr.engine import TextBlock, BoundingBox
        pages = [_page(0, [("body", "Original text.")])]
        edited = {
            0: [
                TextBlock(
                    type="body",
                    text="Edited text.",
                    confidence=0.99,
                    bbox=BoundingBox(x=0, y=0, width=100, height=20),
                )
            ]
        }
        result = reconstruct_paragraphs(pages, edited_blocks=edited)
        assert "Edited text." in result.text
        assert "Original text." not in result.text

    def test_excluded_block_type_omitted(self):
        pages = [_page(0, [
            ("body", "Visible text."),
            ("excluded", "Should not appear."),
        ])]
        result = reconstruct_paragraphs(pages)
        assert "Should not appear." not in result.text
        assert "Visible text." in result.text

    def test_result_fields(self):
        pages = [_page(0, [
            ("body", "First paragraph."),
            ("body", "Also first paragraph."),
        ])]
        result = reconstruct_paragraphs(pages)
        assert isinstance(result, ReconstructedText)
        assert isinstance(result.text, str)
        assert isinstance(result.paragraphs, list)
        assert isinstance(result.paragraph_count, int)
        assert result.paragraph_count == len(result.paragraphs)

    def test_question_mark_sentence_end(self):
        """Question mark is treated as sentence end."""
        pages = [
            _page(0, [("body", "Is this a question?")]),
            _page(1, [("body", "Yes, it is.")]),
        ]
        result = reconstruct_paragraphs(pages)
        assert result.paragraph_count >= 2

    def test_exclamation_sentence_end(self):
        """Exclamation mark is treated as sentence end."""
        pages = [
            _page(0, [("body", "Incredible!")]),
            _page(1, [("body", "It truly is.")]),
        ]
        result = reconstruct_paragraphs(pages)
        assert result.paragraph_count >= 2
