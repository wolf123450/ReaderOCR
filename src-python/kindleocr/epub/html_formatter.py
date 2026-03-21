"""HTML formatting helpers for EPUB chapter content (Step 30)."""
from __future__ import annotations

import re
from typing import List

from kindleocr.ocr.engine import TextBlock

# Block types that map to HTML headings
_H1_TYPES = frozenset({"chapter_title"})
_H2_TYPES = frozenset({"section_heading"})
_ASIDE_TYPES = frozenset({"sidebar"})
_SKIP_TYPES = frozenset({"header", "footer", "page_number", "excluded"})
# figure_caption blocks are handled by the figure embedding code, not here


def blocks_to_html(blocks: List[TextBlock]) -> str:
    """Convert an ordered list of TextBlocks to an HTML fragment.

    Rules:
    - ``chapter_title`` → ``<h1>``
    - ``section_heading`` → ``<h2>``
    - ``sidebar`` → ``<aside><p>…</p></aside>``
    - ``figure_caption`` → skipped (emitted inside ``<figure>`` by the builder)
    - ``header`` / ``footer`` / ``page_number`` / ``excluded`` → omitted
    - Everything else (``body``, unrecognised) → ``<p>``
    """
    parts: List[str] = []
    for block in blocks:
        text = block.text.strip()
        if not text:
            continue
        btype = block.type

        if btype in _SKIP_TYPES or btype == "figure_caption":
            continue
        elif btype in _H1_TYPES:
            parts.append(f"<h1>{_escape(text)}</h1>")
        elif btype in _H2_TYPES:
            parts.append(f"<h2>{_escape(text)}</h2>")
        elif btype in _ASIDE_TYPES:
            parts.append(f"<aside><p>{_escape(text)}</p></aside>")
        else:
            # body or unknown → paragraph
            parts.append(f"<p>{_escape(text)}</p>")

    return "\n".join(parts)


def text_to_html_paragraphs(text: str) -> str:
    """Convert a plain-text string (``\\n\\n``-separated paragraphs) to HTML ``<p>`` tags."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{_escape(p)}</p>" for p in paragraphs)


def _escape(text: str) -> str:
    """Minimal HTML entity escaping."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
