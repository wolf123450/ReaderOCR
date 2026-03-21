"""Tests for chapter_mapper.map_chapters()."""

import pytest
from kindleocr.epub.chapter_mapper import map_chapters, ChapterSegment, PageFraction


def _chapter(
    idx: int,
    title: str,
    sources: list[PageFraction],
    chapter_type: str = "chapter",
) -> ChapterSegment:
    return ChapterSegment(
        id=f"id-{idx}",
        title=title,
        chapterIndex=idx,
        sources=sources,
        chapterType=chapter_type,
    )


def _src(page: int, start: float = 0.0, end: float = 1.0) -> PageFraction:
    return PageFraction(pageIndex=page, start=start, end=end)


# ──────────────────────────────────────────────────────────────────
# Test 9: Single whole-page chapter → one content entry, no cropping
# ──────────────────────────────────────────────────────────────────

def test_single_whole_page_chapter():
    chapters = [_chapter(0, "Introduction", [_src(0)])]
    entries = map_chapters(chapters)

    assert len(entries) == 1
    assert entries[0]["chapterIndex"] == 0
    assert entries[0]["title"] == "Introduction"
    assert entries[0]["pageIndex"] == 0
    assert entries[0]["cropStart"] == 0.0
    assert entries[0]["cropEnd"] == 1.0


# ──────────────────────────────────────────────────────────────────
# Test 10: Page split 50/50 → two entries, each references a cropped region
# ──────────────────────────────────────────────────────────────────

def test_page_split_half_half():
    """One page split 50/50 between two chapters."""
    chapters = [
        _chapter(0, "Chapter A", [_src(5, 0.0, 0.5)]),
        _chapter(1, "Chapter B", [_src(5, 0.5, 1.0)]),
    ]
    entries = map_chapters(chapters)

    assert len(entries) == 2

    a = entries[0]
    assert a["chapterIndex"] == 0
    assert a["pageIndex"] == 5
    assert a["cropStart"] == 0.0
    assert a["cropEnd"] == 0.5

    b = entries[1]
    assert b["chapterIndex"] == 1
    assert b["pageIndex"] == 5
    assert b["cropStart"] == 0.5
    assert b["cropEnd"] == 1.0


# ──────────────────────────────────────────────────────────────────
# Test 11: Multi-page chapter → entries in source order
# ──────────────────────────────────────────────────────────────────

def test_multi_page_chapter_source_order():
    """A chapter spanning pages 3, 4, 5 should yield entries in that order."""
    chapters = [
        _chapter(0, "Long Chapter", [_src(3), _src(4), _src(5)]),
    ]
    entries = map_chapters(chapters)

    assert len(entries) == 3
    assert [e["pageIndex"] for e in entries] == [3, 4, 5]
    # All belong to chapter 0
    assert all(e["chapterIndex"] == 0 for e in entries)


# ──────────────────────────────────────────────────────────────────
# Test 12: Re-ordered chapters (chapterIndex 2, 0, 1) → output follows chapterIndex
# ──────────────────────────────────────────────────────────────────

def test_reordered_chapters_use_chapter_index_order():
    """Chapter with index=0 should appear first in output regardless of list order."""
    chapters = [
        _chapter(2, "Back Matter", [_src(10)]),
        _chapter(0, "Front Matter", [_src(0)]),
        _chapter(1, "Chapter 1", [_src(1), _src(2)]),
    ]
    entries = map_chapters(chapters)

    # Should be sorted: Front Matter → Chapter 1 (×2 pages) → Back Matter
    assert len(entries) == 4
    assert entries[0]["title"] == "Front Matter"
    assert entries[1]["title"] == "Chapter 1"
    assert entries[2]["title"] == "Chapter 1"
    assert entries[3]["title"] == "Back Matter"
    # chapterIndex sequence
    assert [e["chapterIndex"] for e in entries] == [0, 1, 1, 2]
