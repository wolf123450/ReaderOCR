"""Smoke test to verify the test harness works."""

from kindleocr import __version__


def test_version():
    assert __version__ == "0.1.0"
