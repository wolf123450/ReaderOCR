"""Shared test fixtures for KindleOCR tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "test-fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the shared test-fixtures directory."""
    return FIXTURES_DIR
