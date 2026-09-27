"""Shared pytest fixtures for file_metrics tests.

Provides reusable test fixtures for:
- Module loading of the hyphenated script
- Temporary file creation helpers
- Binary and text file samples
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Load the file_metrics module (has hyphen in name, so use importlib)
_METRICS_PATH = Path(__file__).parent.parent / "scripts" / "file_metrics.py"
_spec = importlib.util.spec_from_file_location("file_metrics", _METRICS_PATH)
if _spec and _spec.loader:
    file_metrics = importlib.util.module_from_spec(_spec)
    sys.modules["file_metrics"] = file_metrics
    _spec.loader.exec_module(file_metrics)


def pytest_configure(config: pytest.Config) -> None:
    """Register the markers these tests use; ``run_pytests.py`` reads no parent config.

    Args:
        config: The pytest config object.
    """
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture
def text_file(tmp_path: Path) -> Path:
    """Create a small text file with known content.

    Returns:
        Path to a text file with 5 lines and ~20 words.
    """
    f = tmp_path / "sample.txt"
    f.write_text("line one\nline two\nline three\nline four\nline five\n")
    return f


@pytest.fixture
def large_text_file(tmp_path: Path) -> Path:
    """Create a text file exceeding the medium threshold (>10000 words).

    Returns:
        Path to a text file with >10000 words.
    """
    f = tmp_path / "large.txt"
    # ~4 words per line, 3000 lines = ~12000 words
    f.write_text("\n".join(f"word{i} alpha beta gamma" for i in range(3000)))
    return f


@pytest.fixture
def medium_text_file(tmp_path: Path) -> Path:
    """Create a text file in the medium range (2000-10000 words).

    Returns:
        Path to a text file with ~5000 words.
    """
    f = tmp_path / "medium.txt"
    f.write_text("\n".join(f"word{i} alpha beta gamma delta" for i in range(1000)))
    return f


@pytest.fixture
def binary_file(tmp_path: Path) -> Path:
    """Create a binary file with null bytes.

    Returns:
        Path to a binary file.
    """
    f = tmp_path / "binary.bin"
    f.write_bytes(b"\x00\x01\x02\xff\xfe\xfd" * 100)
    return f


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Create an empty file.

    Returns:
        Path to an empty file.
    """
    f = tmp_path / "empty.txt"
    f.write_text("")
    return f


@pytest.fixture
def python_file(tmp_path: Path) -> Path:
    """Create a sample Python file.

    Returns:
        Path to a .py file.
    """
    f = tmp_path / "example.py"
    f.write_text('#!/usr/bin/env python3\nprint("hello world")\n')
    return f


@pytest.fixture
def unreadable_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a file then remove read permission.

    Yields:
        Path to a file with no read permission.
    """
    f = tmp_path / "noperm.txt"
    f.write_text("secret content")
    f.chmod(0o000)
    yield f
    # Restore permissions for cleanup
    f.chmod(0o644)


@pytest.fixture
def multiline_file(tmp_path: Path) -> Path:
    """Create a file with exactly 50 lines for excerpt testing.

    Returns:
        Path to a 50-line text file.
    """
    f = tmp_path / "fifty_lines.txt"
    f.write_text("\n".join(f"line {i}" for i in range(1, 51)) + "\n")
    return f
