"""Paragraph reconstruction across page boundaries (Step 21).

Merges OCR text blocks from consecutive pages into coherent paragraphs by:
1. Filtering out non-body block types (header, footer, page_number, excluded, figure_caption)
2. Detecting within-page paragraph breaks (short lines, sentence-ending punctuation)
3. Rejoining hyphenated line-break words across page boundaries
4. Detecting sentence continuations across page boundaries
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from kindleocr.ocr.engine import OcrPageResult, TextBlock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Block types included in body text (everything else is excluded by default)
BODY_TYPES = frozenset({"body", "chapter_title", "section_heading", "sidebar"})

# Block types excluded from paragraph text stream
EXCLUDED_TYPES = frozenset({"header", "footer", "page_number", "excluded", "figure_caption"})

# Characters that end a sentence / paragraph
_SENTENCE_END = re.compile(r'[.!?""\')\]]+$')

# A line ending with an end-of-line hyphen (word continuation)
_TRAILING_HYPHEN = re.compile(r'-$')


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ReconstructedText:
    """Result of paragraph reconstruction across all provided pages."""

    text: str                          # Full text with paragraphs separated by \n\n
    paragraphs: List[str]              # Individual paragraph strings
    paragraph_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _body_blocks(blocks: List[TextBlock]) -> List[TextBlock]:
    """Return blocks that contribute to body text, in reading order."""
    return [b for b in blocks if b.type not in EXCLUDED_TYPES]


def _merge_page_blocks(blocks: List[TextBlock]) -> List[str]:
    """Convert the body blocks of one page into a list of paragraph fragments.

    Within a page, each block is treated as a unit.  Blocks of type
    ``chapter_title`` or ``section_heading`` are emitted as their own
    paragraph fragment (to force surrounding paragraph breaks).
    """
    fragments: List[str] = []
    for block in _body_blocks(blocks):
        text = block.text.strip()
        if not text:
            continue
        if block.type in ("chapter_title", "section_heading"):
            # Force a standalone paragraph for headings
            if fragments:
                fragments.append("\n\n")
            fragments.append(text)
            fragments.append("\n\n")
        else:
            fragments.append(text)
    return fragments


def _is_sentence_end(text: str) -> bool:
    """Return True if *text* ends with sentence-terminating punctuation."""
    return bool(_SENTENCE_END.search(text.rstrip()))


def _is_trailing_hyphen(text: str) -> bool:
    """Return True if *text* ends with a line-break hyphen."""
    return bool(_TRAILING_HYPHEN.search(text.rstrip()))


def _starts_with_lowercase(text: str) -> bool:
    """Return True if the first non-space character of *text* is lowercase."""
    stripped = text.lstrip()
    return bool(stripped) and stripped[0].islower()


def _join_across_boundary(
    last_text: str,
    first_text: str,
) -> tuple[str, bool]:
    """Determine how to join the last line of page N with the first of page N+1.

    Returns ``(joined_text, new_paragraph)`` where:
    - ``joined_text`` is the text to append after *last_text*
    - ``new_paragraph`` is True when a paragraph break \n\n should precede *first_text*

    Rules (applied in order):
    1. Trailing hyphen → remove hyphen, concatenate (hyphen rejoin)
    2. Last text ends with sentence punctuation → paragraph break
    3. Last text does NOT end with punctuation AND first text starts lowercase → space-join
    4. Otherwise → paragraph break (conservative default)
    """
    if _is_trailing_hyphen(last_text):
        # "compre-" + "hensive" → "comprehensive"; no space, no break
        return ("", False)  # caller strips hyphen before joining
    if _is_sentence_end(last_text):
        return ("", True)
    if _starts_with_lowercase(first_text):
        # Continuation — same paragraph, add space
        return (" ", False)
    # Default: start new paragraph
    return ("", True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reconstruct_paragraphs(
    pages: List[OcrPageResult],
    edited_blocks: Optional[Dict[int, List[TextBlock]]] = None,
) -> ReconstructedText:
    """Reconstruct paragraphs from an ordered list of OCR page results.

    Parameters
    ----------
    pages:
        OCR results in page order.  Only body-type blocks are included.
    edited_blocks:
        Optional map of ``page_index → blocks`` that overrides the raw OCR
        blocks for that page.  Keys are 0-based page indices matching
        ``OcrPageResult.page_index``.

    Returns
    -------
    ReconstructedText
        Reconstructed text with ``\\n\\n`` between paragraphs.
    """
    if not pages:
        return ReconstructedText(text="", paragraphs=[], paragraph_count=0)

    # Collect body blocks per page, applying edited_blocks override
    all_page_blocks: List[List[TextBlock]] = []
    for page in pages:
        override = (edited_blocks or {}).get(page.page_index)
        blocks = override if override is not None else page.blocks
        all_page_blocks.append(blocks)

    # Build running text across pages
    running_text = ""

    for page_idx, blocks in enumerate(all_page_blocks):
        page_fragments = _merge_page_blocks(blocks)
        if not page_fragments:
            continue

        page_text = " ".join(
            f for f in page_fragments if f not in ("\n\n",)
        )
        # Restore forced heading breaks (they embed \n\n markers)
        # Re-run with proper break handling:
        page_text_parts: List[str] = []
        current_part: List[str] = []
        for frag in page_fragments:
            if frag == "\n\n":
                if current_part:
                    page_text_parts.append(" ".join(current_part).strip())
                    current_part = []
            else:
                current_part.append(frag)
        if current_part:
            page_text_parts.append(" ".join(current_part).strip())
        page_text = "\n\n".join(p for p in page_text_parts if p)

        if not running_text:
            running_text = page_text
        else:
            # Determine how to join with previous page
            # Get last line of running_text and first line of page_text
            last_line = running_text.rstrip().split("\n")[-1].rstrip()
            first_line = page_text.lstrip().split("\n")[0]

            separator, new_para = _join_across_boundary(last_line, first_line)

            if _is_trailing_hyphen(last_line):
                # Remove trailing hyphen and concatenate directly
                running_text = running_text.rstrip()
                if running_text.endswith("-"):
                    running_text = running_text[:-1]
                running_text += page_text.lstrip()
            elif new_para:
                running_text = running_text.rstrip() + "\n\n" + page_text.lstrip()
            else:
                running_text = running_text.rstrip() + separator + page_text.lstrip()

    # Split into paragraph list
    raw_paragraphs = [p.strip() for p in running_text.split("\n\n") if p.strip()]

    return ReconstructedText(
        text="\n\n".join(raw_paragraphs),
        paragraphs=raw_paragraphs,
        paragraph_count=len(raw_paragraphs),
    )
