"""Tests for file_metrics.py summarization strategy tool.

Tests: Category detection, text/binary classification, metrics computation,
excerpt extraction, strategy selection, JSON output, CLI argument parsing,
and edge cases (empty files, permissions, symlinks).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import file_metrics


class TestDetectCategory:
    """Test file category detection from extension."""

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("main.py", "code"),
            ("app.tsx", "code"),
            ("build.rs", "code"),
            ("script.sh", "code"),
            ("config.yaml", "config"),
            ("settings.toml", "config"),
            ("data.csv", "data"),
            ("README.md", "documentation"),
            ("notes.txt", "documentation"),
            ("page.html", "markup"),
            ("icon.svg", "markup"),
            ("photo.jpg", "image"),
            ("logo.png", "image"),
            ("archive.zip", "binary"),
            ("app.exe", "binary"),
            ("database.sqlite", "binary"),
            ("Makefile", "unknown"),
            ("LICENSE", "unknown"),
            (".gitignore", "unknown"),
        ],
    )
    def test_extension_categories(self, filename: str, expected: str, tmp_path: Path) -> None:
        result = file_metrics.detect_category(tmp_path / filename)
        assert result == expected

    def test_case_insensitive(self, tmp_path: Path) -> None:
        assert file_metrics.detect_category(tmp_path / "FILE.PY") == "code"
        assert file_metrics.detect_category(tmp_path / "README.MD") == "documentation"

    def test_no_extension(self, tmp_path: Path) -> None:
        assert file_metrics.detect_category(tmp_path / "Makefile") == "unknown"


class TestIsTextFile:
    """Test text vs binary file detection."""

    def test_text_file(self, text_file: Path) -> None:
        assert file_metrics.is_text_file(text_file) is True

    def test_binary_file(self, binary_file: Path) -> None:
        assert file_metrics.is_text_file(binary_file) is False

    def test_empty_file(self, empty_file: Path) -> None:
        assert file_metrics.is_text_file(empty_file) is True

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        assert file_metrics.is_text_file(tmp_path / "nonexistent") is False

    def test_utf8_with_accents(self, tmp_path: Path) -> None:
        f = tmp_path / "accents.txt"
        f.write_text("cafe\u0301 re\u0301sume\u0301 nai\u0308ve", encoding="utf-8")
        assert file_metrics.is_text_file(f) is True

    def test_latin1_detected_as_binary(self, tmp_path: Path) -> None:
        f = tmp_path / "latin1.txt"
        # Latin-1 bytes that are not valid UTF-8
        f.write_bytes(b"Hello \xe9\xe8\xf1 world")
        assert file_metrics.is_text_file(f) is False


class TestExtractExcerpt:
    """Test extract_excerpt function for head/tail line extraction."""

    def test_basic_excerpt(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.txt"
        f.write_text("hello world\nfoo bar baz\n")
        result = file_metrics.extract_excerpt(f, head_lines=5, tail_lines=3)
        assert result["total_lines"] == 2
        assert "hello" in result["head"]
        assert result["tail"] is None

    def test_empty_content(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = file_metrics.extract_excerpt(f, head_lines=5, tail_lines=3)
        assert result["total_lines"] == 0
        assert result["head"] == ""
        assert result["tail"] is None

    def test_excerpt_head_only_small_file(self, tmp_path: Path) -> None:
        f = tmp_path / "small.txt"
        f.write_text("line1\nline2\nline3\n")
        result = file_metrics.extract_excerpt(f, head_lines=20, tail_lines=10)
        assert result["tail"] is None
        assert "line1" in result["head"]

    def test_excerpt_with_tail(self, tmp_path: Path) -> None:
        lines = [f"line{i}" for i in range(50)]
        f = tmp_path / "fifty.txt"
        f.write_text("\n".join(lines) + "\n")
        result = file_metrics.extract_excerpt(f, head_lines=5, tail_lines=3)
        assert result["tail"] is not None
        assert "line49" in result["tail"]
        assert "line0" in result["head"]
        assert result["total_lines"] == 50

    def test_excerpt_middle_range(self, tmp_path: Path) -> None:
        lines = [f"line{i}" for i in range(25)]
        f = tmp_path / "twentyfive.txt"
        f.write_text("\n".join(lines))
        result = file_metrics.extract_excerpt(f, head_lines=20, tail_lines=10)
        assert result["tail"] is not None
        assert "line20" in result["tail"]
        assert "line24" in result["tail"]


class TestSummarizationStrategy:
    """Test strategy recommendation based on word count."""

    @pytest.mark.parametrize(
        ("word_count", "expected"),
        [
            (None, "unknown"),
            (0, "small"),
            (1999, "small"),
            (2000, "medium"),
            (5000, "medium"),
            (9999, "medium"),
            (10000, "large"),
            (100000, "large"),
        ],
    )
    def test_strategy_thresholds(self, word_count: int | None, expected: str) -> None:
        assert file_metrics.summarization_strategy(word_count) == expected


class TestGetFileMetrics:
    """Test the main get_file_metrics function."""

    def test_text_file_metrics(self, text_file: Path) -> None:
        result = file_metrics.get_file_metrics(text_file)
        assert isinstance(result, dict)
        assert result.get("is_text") is True
        assert result.get("word_count") is not None
        assert result["word_count"] > 0
        assert result.get("line_count") is not None
        assert result["line_count"] > 0
        assert result["strategy"] == "small"
        assert "error" not in result

    def test_binary_file_metrics(self, binary_file: Path) -> None:
        result = file_metrics.get_file_metrics(binary_file)
        assert isinstance(result, dict)
        assert result.get("is_text") is False
        assert result.get("word_count") is None
        assert result["strategy"] == "binary"
        assert result.get("note") is not None

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = file_metrics.get_file_metrics(tmp_path / "gone.txt")
        assert isinstance(result, dict)
        assert "error" in result
        assert "File not found" in result["error"]

    def test_directory_not_file(self, tmp_path: Path) -> None:
        result = file_metrics.get_file_metrics(tmp_path)
        assert isinstance(result, dict)
        assert "error" in result
        assert "Not a file" in result["error"]

    def test_empty_file_metrics(self, empty_file: Path) -> None:
        result = file_metrics.get_file_metrics(empty_file)
        assert isinstance(result, dict)
        assert result.get("is_text") is True
        assert result["word_count"] == 0
        assert result["line_count"] == 0
        assert result["char_count"] == 0
        assert result["strategy"] == "small"

    def test_python_file_category(self, python_file: Path) -> None:
        result = file_metrics.get_file_metrics(python_file)
        assert isinstance(result, dict)
        assert result["category"] == "code"
        assert result["extension"] == ".py"

    def test_no_excerpt_when_zero(self, text_file: Path) -> None:
        result = file_metrics.get_file_metrics(text_file, excerpt_lines=0)
        assert isinstance(result, dict)
        assert result.get("excerpt") is None

    def test_large_file_strategy(self, large_text_file: Path) -> None:
        result = file_metrics.get_file_metrics(large_text_file)
        assert isinstance(result, dict)
        assert result["strategy"] == "large"

    def test_medium_file_strategy(self, medium_text_file: Path) -> None:
        result = file_metrics.get_file_metrics(medium_text_file)
        assert isinstance(result, dict)
        assert result["strategy"] == "medium"

    def test_symlink_to_valid_file(self, text_file: Path, tmp_path: Path) -> None:
        link = tmp_path / "link.txt"
        link.symlink_to(text_file)
        result = file_metrics.get_file_metrics(link)
        assert isinstance(result, dict)
        assert result.get("is_text") is True

    def test_dangling_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "target.txt"
        target.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        target.unlink()
        result = file_metrics.get_file_metrics(link)
        assert isinstance(result, dict)
        assert "error" in result
        assert "File not found" in result["error"]

    def test_tail_lines_parameter(self, multiline_file: Path) -> None:
        result = file_metrics.get_file_metrics(multiline_file, excerpt_lines=5, tail_lines=3)
        assert isinstance(result, dict)
        assert result.get("excerpt") is not None
        excerpt = result["excerpt"]
        assert excerpt.get("tail") is not None
        assert "line 50" in excerpt["tail"]


class TestFormatHumanReadable:
    """Test human-readable formatting."""

    def test_text_file_format(self, text_file: Path) -> None:
        metrics = file_metrics.get_file_metrics(text_file)
        output = file_metrics.format_human_readable(metrics)
        assert "File:" in output
        assert "Words:" in output
        assert "Strategy:" in output

    def test_binary_file_format(self, binary_file: Path) -> None:
        metrics = file_metrics.get_file_metrics(binary_file)
        output = file_metrics.format_human_readable(metrics)
        assert "Note:" in output
        assert "Binary" in output

    def test_error_format(self, tmp_path: Path) -> None:
        metrics = file_metrics.get_file_metrics(tmp_path / "missing.txt")
        output = file_metrics.format_human_readable(metrics)
        assert output.startswith("Error:")


class TestSerialization:
    """Test JSON serialization of results."""

    def test_serialize_file_metrics(self, text_file: Path) -> None:
        metrics = file_metrics.get_file_metrics(text_file)
        assert isinstance(metrics, dict)
        assert "path" in metrics
        assert "word_count" in metrics
        assert "strategy" in metrics
        # Roundtrip through JSON
        json_str = json.dumps(metrics, default=str)
        parsed = json.loads(json_str)
        assert parsed["path"] == str(text_file.resolve())
        assert parsed["strategy"] == "small"

    def test_serialize_error_result(self, tmp_path: Path) -> None:
        metrics = file_metrics.get_file_metrics(tmp_path / "gone.txt")
        assert isinstance(metrics, dict)
        assert "error" in metrics
        assert metrics["error"] is not None
        json_str = json.dumps(metrics)
        parsed = json.loads(json_str)
        assert "File not found" in parsed["error"]

    def test_success_result_has_expected_keys(self, text_file: Path) -> None:
        metrics = file_metrics.get_file_metrics(text_file)
        expected = {"path", "name", "extension", "category", "word_count", "strategy"}
        assert expected.issubset(set(metrics.keys()))


class TestCLIIntegration:
    """Test the CLI via subprocess for integration coverage."""

    SCRIPT = str(Path(__file__).parent.parent / "scripts" / "file_metrics.py")

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args], check=False, capture_output=True, text=True, timeout=10
        )

    def test_json_output_parses(self, text_file: Path) -> None:
        result = self._run(str(text_file), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["is_text"] is True
        assert "path" in data
        assert "strategy" in data

    def test_human_readable_default(self, text_file: Path) -> None:
        result = self._run(str(text_file))
        assert result.returncode == 0
        assert "File:" in result.stdout
        assert "Words:" in result.stdout

    def test_nonexistent_file_exit_code(self, tmp_path: Path) -> None:
        result = self._run(str(tmp_path / "nope.txt"), "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["error"] is not None

    def test_directory_exit_code(self, tmp_path: Path) -> None:
        result = self._run(str(tmp_path), "--json")
        assert result.returncode == 1

    def test_negative_excerpt_lines_rejected(self, text_file: Path) -> None:
        result = self._run(str(text_file), "--excerpt-lines", "-1")
        assert result.returncode == 2

    def test_negative_tail_lines_rejected(self, text_file: Path) -> None:
        result = self._run(str(text_file), "--tail-lines", "-1")
        assert result.returncode == 2

    def test_no_excerpt_flag(self, text_file: Path) -> None:
        result = self._run(str(text_file), "--json", "--no-excerpt")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("excerpt") is None

    def test_error_json_parses(self, tmp_path: Path) -> None:
        result = self._run(str(tmp_path / "missing"), "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert "error" in data
        assert data["error"] is not None

    def test_error_json_has_consistent_schema(self, tmp_path: Path, text_file: Path) -> None:
        success_result = self._run(str(text_file), "--json")
        error_result = self._run(str(tmp_path / "missing"), "--json")
        success_data = json.loads(success_result.stdout)
        error_data = json.loads(error_result.stdout)
        assert "error" in error_data
        assert "path" in success_data

    def test_custom_tail_lines(self, text_file: Path) -> None:
        result = self._run(str(text_file), "--json", "--tail-lines", "5")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["is_text"] is True

    def test_binary_file_json(self, binary_file: Path) -> None:
        result = self._run(str(binary_file), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["is_text"] is False
        assert data["strategy"] == "binary"
        assert data["word_count"] is None
