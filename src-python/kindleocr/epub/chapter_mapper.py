"""Chapter mapper — converts ChapterSegment list into ordered content entries for the EPUB builder."""

from __future__ import annotations

from typing import TypedDict


class PageFraction(TypedDict):
    """A fractional region of a source page (0.0 = top, 1.0 = bottom)."""

    pageIndex: int
    start: float
    end: float


class ChapterSegment(TypedDict):
    """A chapter that maps one or more source page regions to an EPUB chapter."""

    id: str
    title: str
    chapterIndex: int
    sources: list[PageFraction]
    chapterType: str


class ContentEntry(TypedDict):
    """A single content entry for the EPUB builder."""

    chapterIndex: int
    title: str
    chapterType: str
    pageIndex: int
    cropStart: float  # 0.0 = top of image (no crop)
    cropEnd: float    # 1.0 = bottom of image (no crop)


def map_chapters(chapters: list[ChapterSegment]) -> list[ContentEntry]:
    """Given a list of ChapterSegments, produce an ordered flat content list for the EPUB builder.

    Chapters are sorted by ``chapterIndex``; within each chapter the sources
    are emitted in their original order.  Each ``PageFraction`` becomes one
    ``ContentEntry`` with crop coordinates that the EPUB builder uses to crop
    the source image vertically.

    A whole-page fraction ``(start=0.0, end=1.0)`` means no cropping is needed.
    """
    sorted_chapters = sorted(chapters, key=lambda c: c["chapterIndex"])
    entries: list[ContentEntry] = []
    for ch in sorted_chapters:
        for src in ch["sources"]:
            entries.append(
                ContentEntry(
                    chapterIndex=ch["chapterIndex"],
                    title=ch["title"],
                    chapterType=ch["chapterType"],
                    pageIndex=src["pageIndex"],
                    cropStart=src["start"],
                    cropEnd=src["end"],
                )
            )
    return entries
