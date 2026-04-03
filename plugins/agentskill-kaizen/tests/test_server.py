"""Unit and direct-call tests for the kaizen-analysis MCP server module.

Covers helpers and tools invoked on the imported module. MCP protocol coverage
(list_tools, call_tool, read_resource) lives in ``test_server_mcp.py`` using
``Client(mcp)`` in-memory transport.

Tests cover:
- Helper functions: _read_jsonl, _extract_tools_from_records, _resolve_glob,
  _build_event_log, _extract_user_text, _extract_tool_sequences_impl,
  _resolve_sequences
- Session log schema helpers and resource function
- Async MCP tools (direct call): get_transcript_jsonl_schema, extract_tool_sequences,
  discover_process_model, check_conformance, find_frequent_patterns,
  detect_frustration_signals, cluster_sessions
- Edge cases: empty globs, malformed JSONL, zero tool calls,
  n_clusters > sessions, empty sequences
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pandas as pd
import pytest
import server as kaizen_server

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path
    from unittest.mock import AsyncMock

# ===================================================================
# Helper: _read_jsonl
# ===================================================================


class TestReadJsonl:
    """Tests for _read_jsonl helper -- JSONL file parsing."""

    def test_reads_valid_jsonl(self, single_session_jsonl: Path) -> None:
        """Parses valid JSONL and returns list of dicts."""
        jsonl_file = str(single_session_jsonl / "session-abc.jsonl")

        result = kaizen_server._read_jsonl(jsonl_file)

        assert len(result) == 3
        assert all(isinstance(r, dict) for r in result)
        assert result[0]["type"] == "assistant"

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        """Blank lines in JSONL are skipped without error."""
        fpath = tmp_path / "blanks.jsonl"
        fpath.write_text('{"a":1}\n\n\n{"b":2}\n', encoding="utf-8")

        result = kaizen_server._read_jsonl(str(fpath))

        assert len(result) == 2
        assert result[0] == {"a": 1}
        assert result[1] == {"b": 2}

    def test_raises_on_malformed_json(self, malformed_jsonl: Path) -> None:
        """Malformed JSON line raises JSONDecodeError."""
        jsonl_file = str(malformed_jsonl / "malformed-session.jsonl")

        with pytest.raises(json.JSONDecodeError):
            kaizen_server._read_jsonl(jsonl_file)

    def test_returns_empty_for_empty_file(self, tmp_path: Path) -> None:
        """Empty file returns empty list."""
        fpath = tmp_path / "empty.jsonl"
        fpath.write_text("", encoding="utf-8")

        result = kaizen_server._read_jsonl(str(fpath))

        assert result == []

    def test_raises_on_nonexistent_file(self, tmp_path: Path) -> None:
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            kaizen_server._read_jsonl(str(tmp_path / "no-such-file.jsonl"))


# ===================================================================
# Helper: _extract_tools_from_records
# ===================================================================


class TestExtractToolsFromRecords:
    """Tests for _extract_tools_from_records -- tool-call extraction."""

    def test_extracts_tool_names_from_assistant_records(self) -> None:
        """Extracts tool names from assistant message content blocks."""
        records = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {}},
                        {"type": "text", "text": "some text"},
                        {"type": "tool_use", "name": "Write", "input": {}},
                    ]
                },
            }
        ]

        result = kaizen_server._extract_tools_from_records(records)

        assert result == ["Read", "Write"]

    def test_skips_non_assistant_records(self) -> None:
        """Non-assistant records are ignored."""
        records = [{"type": "user", "message": {"content": "hello"}}, {"type": "system", "message": {"content": []}}]

        result = kaizen_server._extract_tools_from_records(records)

        assert result == []

    def test_returns_empty_for_no_tool_calls(self) -> None:
        """Assistant records without tool_use blocks yield empty list."""
        records = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "thinking..."}]}}]

        result = kaizen_server._extract_tools_from_records(records)

        assert result == []

    def test_handles_missing_message_key(self) -> None:
        """Records without message dict are safely skipped."""
        records = [
            {"type": "assistant"},
            {"type": "assistant", "message": "not a dict"},
            {"type": "assistant", "message": {"content": "not a list"}},
        ]

        result = kaizen_server._extract_tools_from_records(records)

        assert result == []

    def test_skips_tool_use_with_non_string_name(self) -> None:
        """Tool-use blocks where name is not a string are skipped."""
        records = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": 123},
                        {"type": "tool_use", "name": None},
                        {"type": "tool_use"},
                    ]
                },
            }
        ]

        result = kaizen_server._extract_tools_from_records(records)

        assert result == []

    def test_preserves_tool_call_order(self) -> None:
        """Tool calls are returned in the order they appear."""
        records = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "A"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "B"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "C"}]}},
        ]

        result = kaizen_server._extract_tools_from_records(records)

        assert result == ["A", "B", "C"]


# ===================================================================
# Helper: _resolve_glob
# ===================================================================


class TestResolveGlob:
    """Tests for _resolve_glob -- glob pattern resolution."""

    def test_resolves_wildcard_pattern(self, single_session_jsonl: Path) -> None:
        """Wildcard glob resolves to matching files."""
        pattern = str(single_session_jsonl / "*.jsonl")

        result = kaizen_server._resolve_glob(pattern)

        assert len(result) == 1
        assert "session-abc.jsonl" in result[0]

    def test_resolves_multiple_files(self, multi_session_jsonl: Path) -> None:
        """Glob pattern returns all matching files sorted."""
        pattern = str(multi_session_jsonl / "*.jsonl")

        result = kaizen_server._resolve_glob(pattern)

        assert len(result) == 3
        # Sorted alphabetically
        assert result == sorted(result)

    def test_returns_empty_for_no_matches(self, empty_jsonl_dir: Path) -> None:
        """Non-matching glob returns empty list."""
        pattern = str(empty_jsonl_dir / "*.jsonl")

        result = kaizen_server._resolve_glob(pattern)

        assert result == []

    def test_resolves_recursive_glob(self, tmp_path: Path) -> None:
        """Recursive ** glob finds files in subdirectories."""
        subdir = tmp_path / "sub" / "deep"
        subdir.mkdir(parents=True)
        (subdir / "nested.jsonl").write_text('{"a":1}\n', encoding="utf-8")

        pattern = str(tmp_path / "**" / "*.jsonl")

        result = kaizen_server._resolve_glob(pattern)

        assert len(result) == 1
        assert "nested.jsonl" in result[0]


# ===================================================================
# Helper: _build_event_log
# ===================================================================


class TestBuildEventLog:
    """Tests for _build_event_log -- PM4Py DataFrame construction."""

    def test_builds_dataframe_from_sequences(self, sample_sequences: dict[str, list[str]]) -> None:
        """Produces DataFrame with expected columns and row count."""
        df = kaizen_server._build_event_log(sample_sequences)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        # Total rows: 3 + 2 + 4 = 9
        assert len(df) == 9
        assert "case:concept:name" in df.columns
        assert "concept:name" in df.columns
        assert "time:timestamp" in df.columns

    def test_returns_empty_dataframe_for_empty_sequences(self) -> None:
        """Empty sequences dict yields empty DataFrame."""
        df = kaizen_server._build_event_log({})

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_preserves_session_ids(self, sample_sequences: dict[str, list[str]]) -> None:
        """Session IDs appear in the case:concept:name column."""
        df = kaizen_server._build_event_log(sample_sequences)

        session_ids = set(df["case:concept:name"].unique())
        assert session_ids == {"session-one", "session-two", "session-three"}

    def test_preserves_tool_names(self) -> None:
        """Tool names appear in the concept:name column."""
        sequences = {"s1": ["Read", "Write"]}

        df = kaizen_server._build_event_log(sequences)

        tool_names = list(df["concept:name"])
        assert tool_names == ["Read", "Write"]

    def test_timestamps_are_monotonically_increasing_within_session(self) -> None:
        """Timestamps within a session increase by 1 second per event."""
        sequences = {"s1": ["A", "B", "C"]}

        df = kaizen_server._build_event_log(sequences)

        timestamps = list(df["time:timestamp"])
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i - 1]


# ===================================================================
# Helper: _extract_user_text
# ===================================================================


class TestExtractUserText:
    """Tests for _extract_user_text -- user message text extraction."""

    def test_extracts_string_content(self) -> None:
        """String content is returned directly."""
        message = {"content": "hello world"}

        result = kaizen_server._extract_user_text(message)

        assert result == "hello world"

    def test_extracts_text_from_block_list(self) -> None:
        """Text blocks in list content are joined with spaces."""
        message = {
            "content": [
                {"type": "text", "text": "hello"},
                {"type": "image", "url": "x"},
                {"type": "text", "text": "world"},
            ]
        }

        result = kaizen_server._extract_user_text(message)

        assert result == "hello world"

    def test_handles_string_items_in_list(self) -> None:
        """Plain strings in the content list are included."""
        message = {"content": ["hello", "world"]}

        result = kaizen_server._extract_user_text(message)

        assert result == "hello world"

    def test_returns_empty_for_missing_content(self) -> None:
        """Missing content key returns empty string."""
        result = kaizen_server._extract_user_text({})

        assert result == ""

    def test_returns_empty_for_non_string_non_list_content(self) -> None:
        """Non-string, non-list content returns empty string."""
        result = kaizen_server._extract_user_text({"content": 42})

        assert result == ""


# ===================================================================
# Helper: _extract_tool_sequences_impl
# ===================================================================


class TestExtractToolSequencesImpl:
    """Tests for _extract_tool_sequences_impl -- glob-based extraction."""

    def test_extracts_sequences_from_single_file(self, single_session_jsonl: Path) -> None:
        """Single JSONL file produces one session entry."""
        glob_path = str(single_session_jsonl / "*.jsonl")

        result = kaizen_server._extract_tool_sequences_impl(glob_path)

        assert len(result) == 1
        assert "session-abc" in result
        assert result["session-abc"] == ["Read", "Grep", "Write"]

    def test_extracts_sequences_from_multiple_files(self, multi_session_jsonl: Path) -> None:
        """Multiple JSONL files produce multiple session entries."""
        glob_path = str(multi_session_jsonl / "*.jsonl")

        result = kaizen_server._extract_tool_sequences_impl(glob_path)

        assert len(result) == 3
        assert result["session-one"] == ["Read", "Grep", "Read"]
        assert result["session-two"] == ["Write", "Edit"]
        assert result["session-three"] == ["Read", "Grep", "Write", "Edit"]

    def test_returns_empty_for_no_matching_files(self, empty_jsonl_dir: Path) -> None:
        """No matching files returns empty dict."""
        glob_path = str(empty_jsonl_dir / "*.jsonl")

        result = kaizen_server._extract_tool_sequences_impl(glob_path)

        assert result == {}

    def test_skips_sessions_with_no_tool_calls(self, tmp_path: Path) -> None:
        """Sessions with only user messages (no tools) are excluded."""
        fpath = tmp_path / "no-tools.jsonl"
        records = [{"type": "user", "message": {"content": "hello"}}]
        fpath.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

        result = kaizen_server._extract_tool_sequences_impl(str(tmp_path / "*.jsonl"))

        assert result == {}


# ===================================================================
# Helper: _resolve_sequences
# ===================================================================


class TestResolveSequences:
    """Tests for _resolve_sequences -- sequence resolution from glob or dict."""

    def test_returns_provided_sequences(self, sample_sequences: dict[str, list[str]]) -> None:
        """Pre-extracted sequences are returned directly."""
        result = kaizen_server._resolve_sequences("", sample_sequences)

        assert result is sample_sequences

    def test_raises_on_empty_provided_sequences(self) -> None:
        """Empty pre-extracted sequences raise ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="No target sequences found"):
            kaizen_server._resolve_sequences("", {})

    def test_raises_when_neither_glob_nor_sequences(self) -> None:
        """Missing both glob and sequences raises ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="Provide either glob_path or sequences"):
            kaizen_server._resolve_sequences("", None)

    def test_resolves_from_glob_path(self, single_session_jsonl: Path) -> None:
        """Resolves sequences from glob when sequences is None."""
        glob_path = str(single_session_jsonl / "*.jsonl")

        result = kaizen_server._resolve_sequences(glob_path, None)

        assert len(result) == 1
        assert "session-abc" in result

    def test_raises_when_glob_finds_no_tool_sequences(self, empty_jsonl_dir: Path) -> None:
        """Glob resolving to no tool sequences raises ToolError."""
        from fastmcp.exceptions import ToolError

        glob_path = str(empty_jsonl_dir / "*.jsonl")

        with pytest.raises(ToolError, match="No target tool sequences found"):
            kaizen_server._resolve_sequences(glob_path, None)

    def test_uses_custom_target_name_in_error(self) -> None:
        """Custom target_name appears in error messages."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="No reference sequences found"):
            kaizen_server._resolve_sequences("", {}, target_name="reference")


# ===================================================================
# MCP Tool: get_transcript_jsonl_schema
# ===================================================================


class TestGetTranscriptJsonlSchema:
    """Tests for get_transcript_jsonl_schema async MCP tool."""

    def test_schema_path_is_readable_file(self) -> None:
        """Bundled schema path resolves to an existing markdown file."""
        path = kaizen_server._session_log_schema_path()
        assert path.name == "session-log-schema.md"
        assert path.is_file()

    @pytest.mark.asyncio
    async def test_returns_full_schema_markdown(self) -> None:
        """Tool returns canonical session log schema markdown."""
        result = await kaizen_server.get_transcript_jsonl_schema()

        assert "Claude Code Session Log Schema Reference" in result
        assert '## `type: "assistant"` Records' in result
        assert len(result) > 2000

    def test_resource_returns_same_schema_body(self) -> None:
        """Resource handler returns the same markdown as the sync reader."""
        body = kaizen_server._read_session_log_schema_text()
        resource_body = kaizen_server.session_log_schema_resource()
        assert resource_body == body
        assert not resource_body.startswith("# Session log schema unavailable")


# ===================================================================
# MCP Tool: extract_tool_sequences
# ===================================================================


class TestExtractToolSequences:
    """Tests for the extract_tool_sequences async MCP tool."""

    @pytest.mark.asyncio
    async def test_extracts_sequences(self, single_session_jsonl: Path) -> None:
        """Async tool returns extracted tool sequences from JSONL files."""
        glob_path = str(single_session_jsonl / "*.jsonl")

        result = await kaizen_server.extract_tool_sequences(glob_path)

        assert isinstance(result, dict)
        assert "session-abc" in result
        assert result["session-abc"] == ["Read", "Grep", "Write"]

    @pytest.mark.asyncio
    async def test_returns_multiple_sessions(self, multi_session_jsonl: Path) -> None:
        """Async tool handles multiple session files."""
        glob_path = str(multi_session_jsonl / "*.jsonl")

        result = await kaizen_server.extract_tool_sequences(glob_path)

        assert len(result) == 3


# ===================================================================
# MCP Tool: discover_process_model
# ===================================================================


class TestDiscoverProcessModel:
    """Tests for the discover_process_model async MCP tool."""

    @pytest.mark.asyncio
    async def test_discovers_model_from_sequences(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Heuristic miner returns a string representation."""
        result = await kaizen_server.discover_process_model("", sample_sequences, context=mock_context)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_discovers_model_from_glob(self, multi_session_jsonl: Path, mock_context: AsyncMock) -> None:
        """Tool works when given glob_path instead of sequences."""
        glob_path = str(multi_session_jsonl / "*.jsonl")

        result = await kaizen_server.discover_process_model(glob_path, context=mock_context)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_raises_on_empty_sequences(self, mock_context: AsyncMock) -> None:
        """Empty sequences raise ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await kaizen_server.discover_process_model("", {}, context=mock_context)

    @pytest.mark.asyncio
    async def test_raises_on_missing_input(self, mock_context: AsyncMock) -> None:
        """Neither glob nor sequences raises ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await kaizen_server.discover_process_model("", None, context=mock_context)


# ===================================================================
# MCP Tool: check_conformance
# ===================================================================


class TestCheckConformance:
    """Tests for the check_conformance async MCP tool."""

    @pytest.mark.asyncio
    async def test_returns_conformance_diagnostics(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Conformance checking returns per-trace diagnostics."""
        result = await kaizen_server.check_conformance(
            sequences=sample_sequences, reference_sequences=sample_sequences, context=mock_context
        )

        assert isinstance(result, list)
        assert len(result) == len(sample_sequences)
        for entry in result:
            assert "session_id" in entry
            assert "trace_is_fit" in entry
            assert "trace_fitness" in entry
            assert "missing_tokens" in entry
            assert "remaining_tokens" in entry
            assert "consumed_tokens" in entry
            assert "produced_tokens" in entry

    @pytest.mark.asyncio
    async def test_self_conformance_is_fit(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Sessions checked against themselves should be fit."""
        result = await kaizen_server.check_conformance(
            sequences=sample_sequences, reference_sequences=sample_sequences, context=mock_context
        )

        fit_count = sum(1 for entry in result if entry["trace_is_fit"])
        # Most traces should be fit when checked against the same model
        assert fit_count > 0

    @pytest.mark.asyncio
    async def test_raises_on_missing_target(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Missing target raises ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await kaizen_server.check_conformance(
                sequences=None, reference_sequences=sample_sequences, context=mock_context
            )

    @pytest.mark.asyncio
    async def test_raises_on_missing_reference(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Missing reference raises ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await kaizen_server.check_conformance(
                sequences=sample_sequences, reference_sequences=None, context=mock_context
            )

    @pytest.mark.asyncio
    async def test_works_with_glob_paths(self, multi_session_jsonl: Path, mock_context: AsyncMock) -> None:
        """Conformance tool works with glob paths for both inputs."""
        glob_path = str(multi_session_jsonl / "*.jsonl")

        result = await kaizen_server.check_conformance(
            glob_path=glob_path, reference_glob_path=glob_path, context=mock_context
        )

        assert isinstance(result, list)
        assert len(result) > 0


# ===================================================================
# MCP Tool: find_frequent_patterns
# ===================================================================


class TestFindFrequentPatterns:
    """Tests for the find_frequent_patterns async MCP tool."""

    @pytest.mark.asyncio
    async def test_finds_patterns_from_sequences(self, sample_sequences: dict[str, list[str]]) -> None:
        """PrefixSpan finds frequent patterns from pre-extracted sequences."""
        result = await kaizen_server.find_frequent_patterns(sequences=sample_sequences, min_support=2)

        assert isinstance(result, list)
        for entry in result:
            assert "support" in entry
            assert "pattern" in entry
            assert isinstance(entry["pattern"], list)
            assert len(entry["pattern"]) >= 2
            assert entry["support"] >= 2

    @pytest.mark.asyncio
    async def test_patterns_sorted_by_support_descending(self, sample_sequences: dict[str, list[str]]) -> None:
        """Results are sorted by support count in descending order."""
        result = await kaizen_server.find_frequent_patterns(sequences=sample_sequences, min_support=2)

        if len(result) > 1:
            supports = [e["support"] for e in result]
            assert supports == sorted(supports, reverse=True)

    @pytest.mark.asyncio
    async def test_min_support_filters_results(self, sample_sequences: dict[str, list[str]]) -> None:
        """Higher min_support reduces the number of frequent patterns."""
        low = await kaizen_server.find_frequent_patterns(sequences=sample_sequences, min_support=1)
        high = await kaizen_server.find_frequent_patterns(sequences=sample_sequences, min_support=3)

        assert len(high) <= len(low)

    @pytest.mark.asyncio
    async def test_raises_on_missing_input(self) -> None:
        """Missing both glob and sequences raises ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await kaizen_server.find_frequent_patterns(glob_path="", sequences=None)

    @pytest.mark.asyncio
    async def test_works_with_glob_path(self, multi_session_jsonl: Path) -> None:
        """Finds patterns from JSONL files via glob path."""
        glob_path = str(multi_session_jsonl / "*.jsonl")

        result = await kaizen_server.find_frequent_patterns(glob_path=glob_path, min_support=2)

        assert isinstance(result, list)


# ===================================================================
# MCP Tool: detect_frustration_signals
# ===================================================================


class TestDetectFrustrationSignals:
    """Tests for the detect_frustration_signals async MCP tool."""

    @pytest.mark.asyncio
    async def test_detects_known_frustration_signals(self, frustration_jsonl: Path) -> None:
        """Known frustration patterns are detected in user messages."""
        glob_path = str(frustration_jsonl / "*.jsonl")

        result = await kaizen_server.detect_frustration_signals(glob_path)

        assert isinstance(result, list)
        # "no, that's wrong" -> correction
        # "wait, hold on a second" -> interrupt
        # "why did you do that again?" -> frustration
        assert len(result) == 3

        signal_types = {s["signal_type"] for s in result}
        assert "correction" in signal_types
        assert "interrupt" in signal_types
        assert "frustration" in signal_types

    @pytest.mark.asyncio
    async def test_skips_tool_use_result_messages(self, frustration_jsonl: Path) -> None:
        """Messages with toolUseResult are not scanned."""
        glob_path = str(frustration_jsonl / "*.jsonl")

        result = await kaizen_server.detect_frustration_signals(glob_path)

        # The toolUseResult message contains "no this is wrong" which matches
        # correction, but should be filtered out
        session_timestamps = [s["timestamp"] for s in result]
        assert "2026-01-01T00:04:00Z" not in session_timestamps

    @pytest.mark.asyncio
    async def test_skips_non_frustration_messages(self, frustration_jsonl: Path) -> None:
        """Neutral messages like 'looks good to me' produce no signal."""
        glob_path = str(frustration_jsonl / "*.jsonl")

        result = await kaizen_server.detect_frustration_signals(glob_path)

        messages = [s["message_text"] for s in result]
        assert not any("looks good" in m for m in messages)

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_files(self, empty_jsonl_dir: Path) -> None:
        """No matching JSONL files returns empty list."""
        glob_path = str(empty_jsonl_dir / "*.jsonl")

        result = await kaizen_server.detect_frustration_signals(glob_path)

        assert result == []

    @pytest.mark.asyncio
    async def test_preserves_full_message_text(self, tmp_path: Path) -> None:
        """Full message text is preserved without truncation."""
        long_text = "no " + "x" * 300
        records = [{"type": "user", "message": {"content": long_text}, "timestamp": "2026-01-01T00:00:00Z"}]
        fpath = tmp_path / "long-msg.jsonl"
        fpath.write_text(json.dumps(records[0]), encoding="utf-8")

        glob_path = str(tmp_path / "*.jsonl")
        result = await kaizen_server.detect_frustration_signals(glob_path)

        assert len(result) == 1
        assert result[0]["message_text"] == long_text

    @pytest.mark.asyncio
    async def test_one_signal_per_message(self, tmp_path: Path) -> None:
        """Only one signal per message even if multiple patterns match."""
        # "no, wait, why did you do that" matches correction, interrupt, frustration
        records = [
            {
                "type": "user",
                "message": {"content": "no, wait, why did you do that"},
                "timestamp": "2026-01-01T00:00:00Z",
            }
        ]
        fpath = tmp_path / "multi-match.jsonl"
        fpath.write_text(json.dumps(records[0]), encoding="utf-8")

        glob_path = str(tmp_path / "*.jsonl")
        result = await kaizen_server.detect_frustration_signals(glob_path)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handles_list_of_blocks_content(self, tmp_path: Path) -> None:
        """User messages with list-of-blocks content are scanned."""
        records = [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "no, that's wrong"}]},
                "timestamp": "2026-01-01T00:00:00Z",
            }
        ]
        fpath = tmp_path / "blocks-content.jsonl"
        fpath.write_text(json.dumps(records[0]), encoding="utf-8")

        glob_path = str(tmp_path / "*.jsonl")
        result = await kaizen_server.detect_frustration_signals(glob_path)

        assert len(result) == 1
        assert result[0]["signal_type"] == "correction"

    @pytest.mark.asyncio
    async def test_result_schema(self, frustration_jsonl: Path) -> None:
        """Each result dict has the expected keys."""
        glob_path = str(frustration_jsonl / "*.jsonl")

        result = await kaizen_server.detect_frustration_signals(glob_path)

        for entry in result:
            assert set(entry.keys()) == {"session_id", "timestamp", "signal_type", "message_text"}


# ===================================================================
# MCP Tool: cluster_sessions
# ===================================================================


class TestClusterSessions:
    """Tests for the cluster_sessions async MCP tool."""

    @pytest.mark.asyncio
    async def test_clusters_sessions_from_sequences(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """KMeans clustering returns clusters and profiles."""
        result = await kaizen_server.cluster_sessions(sequences=sample_sequences, n_clusters=2, context=mock_context)

        assert "clusters" in result
        assert "cluster_profiles" in result
        assert len(result["clusters"]) == 2
        assert len(result["cluster_profiles"]) == 2

        # All session IDs should be assigned to exactly one cluster
        all_sessions: set[str] = set()
        for members in result["clusters"].values():
            all_sessions.update(members)
        assert all_sessions == set(sample_sequences.keys())

    @pytest.mark.asyncio
    async def test_reduces_n_clusters_when_too_large(
        self, single_sequence: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """n_clusters is capped to number of sessions."""
        result = await kaizen_server.cluster_sessions(sequences=single_sequence, n_clusters=10, context=mock_context)

        # With 1 session, effective clusters = min(10, 1) = 1
        assert len(result["clusters"]) == 1

    @pytest.mark.asyncio
    async def test_cluster_profiles_contain_top_tools(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Cluster profiles list the most common tools."""
        result = await kaizen_server.cluster_sessions(sequences=sample_sequences, n_clusters=2, context=mock_context)

        for profile in result["cluster_profiles"].values():
            assert isinstance(profile, list)
            assert len(profile) <= kaizen_server._TOP_TOOLS_PER_CLUSTER

    @pytest.mark.asyncio
    async def test_raises_on_missing_input(self, mock_context: AsyncMock) -> None:
        """Missing both glob and sequences raises ToolError."""
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError):
            await kaizen_server.cluster_sessions(glob_path="", sequences=None, context=mock_context)

    @pytest.mark.asyncio
    async def test_works_with_glob_path(self, multi_session_jsonl: Path, mock_context: AsyncMock) -> None:
        """Clustering works from JSONL files via glob path."""
        glob_path = str(multi_session_jsonl / "*.jsonl")

        result = await kaizen_server.cluster_sessions(glob_path=glob_path, n_clusters=2, context=mock_context)

        assert "clusters" in result
        assert len(result["clusters"]) == 2

    @pytest.mark.asyncio
    async def test_cluster_keys_are_string_ids(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Cluster keys are string representations of cluster IDs."""
        result = await kaizen_server.cluster_sessions(sequences=sample_sequences, n_clusters=2, context=mock_context)

        for key in result["clusters"]:
            assert isinstance(key, str)
            assert key.isdigit()


# ===================================================================
# Frustration patterns unit tests
# ===================================================================


class TestFrustrationPatterns:
    """Direct unit tests for the compiled frustration regex patterns."""

    @pytest.mark.parametrize(
        ("text", "expected_type"),
        [
            ("no, that's not right", "correction"),
            ("don't do that", "correction"),
            ("wrong approach", "correction"),
            ("incorrect result", "correction"),
            ("stop doing that", "correction"),
            ("undo the last change", "correction"),
            ("revert that please", "correction"),
            ("that's not what I wanted", "denial"),
            ("I didn't ask for that", "denial"),
            ("never do that again", "denial"),
            ("absolutely not", "denial"),
            ("wait a moment", "interrupt"),
            ("hold on please", "interrupt"),
            ("cancel that", "interrupt"),
            ("abort the operation", "interrupt"),
            ("forget it", "interrupt"),
            ("nevermind", "interrupt"),
            ("why did you change that", "frustration"),
            ("you keep making errors", "frustration"),
            ("is it broken again?", "frustration"),
            # "still wrong" contains \bwrong\b so correction matches first
            ("still wrong after fixing", "correction"),
        ],
    )
    def test_pattern_matches_expected_type(self, text: str, expected_type: str) -> None:
        """Frustration pattern matches the expected signal type."""
        matched_type = None
        for signal_type, pattern in kaizen_server._FRUSTRATION_PATTERNS:
            if pattern.search(text):
                matched_type = signal_type
                break

        assert matched_type == expected_type, f"Expected '{expected_type}' for text '{text}', got '{matched_type}'"

    @pytest.mark.parametrize(
        "text",
        [
            "looks great, thank you",
            "perfect, exactly what I needed",
            "that works well",
            "please continue with the implementation",
            "yes, proceed",
        ],
    )
    def test_pattern_does_not_match_positive_text(self, text: str) -> None:
        """Positive/neutral text does not trigger frustration patterns."""
        for _, pattern in kaizen_server._FRUSTRATION_PATTERNS:
            assert not pattern.search(text), f"Text '{text}' should not match any frustration pattern"


# ===================================================================
# MCP Tool: open_dashboard
# ===================================================================


class TestOpenDashboard:
    """Tests for the open_dashboard synchronous MCP tool.

    Covers URL-return behavior and not-running error path. Each test
    stubs the deferred ``dashboard.get_dashboard_url`` import.
    """

    @pytest.fixture(autouse=True)
    def _stub_dashboard_module(self) -> Generator[None, None, None]:
        """Insert a stub ``dashboard`` module into sys.modules.

        The open_dashboard tool performs a deferred import:
        ``from dashboard import get_dashboard_url``. The real
        dashboard module pulls in heavy third-party dependencies
        (panel, holoviews, bokeh). This fixture inserts a
        lightweight stub so the import succeeds without those deps.

        The stub's ``get_dashboard_url`` is overwritten per-test
        via ``unittest.mock.patch``.
        """
        import types as _types

        stub = _types.ModuleType("dashboard")
        vars(stub).update({"get_dashboard_url": lambda: None})
        prev = sys.modules.get("dashboard")
        sys.modules["dashboard"] = stub
        yield
        if prev is not None:
            sys.modules["dashboard"] = prev
        else:
            sys.modules.pop("dashboard", None)

    def test_open_dashboard_first_call(self) -> None:
        """Invocation returns the URL with opened_browser=False.

        Tests: open_dashboard MCP tool behavior
        How: Mock get_dashboard_url to return a URL, call open_dashboard,
            verify URL and opened_browser=False in the response.
        Why: The tool returns a URL for the user to copy; it does not
            open a browser (opening during Tornado init causes IOLoop
            exhaustion and a blank page).
        """
        from unittest.mock import patch

        test_url = "http://localhost:49152/"

        with patch("dashboard.get_dashboard_url", return_value=test_url):
            result = kaizen_server.open_dashboard()

        assert result["url"] == test_url
        assert result["opened_browser"] is False
        assert test_url in str(result["message"])

    def test_open_dashboard_when_not_running(self) -> None:
        """Raises ToolError when the dashboard is not running.

        Tests: open_dashboard MCP tool error path
        How: Mock get_dashboard_url to return None (dashboard not started),
            call open_dashboard, verify ToolError is raised with a message
            containing "not running".
        Why: The tool must give a clear error when the dashboard thread
            failed to start, rather than returning a None URL.
        """
        from unittest.mock import patch

        from fastmcp.exceptions import ToolError

        with patch("dashboard.get_dashboard_url", return_value=None), pytest.raises(ToolError, match="not running"):
            kaizen_server.open_dashboard()
