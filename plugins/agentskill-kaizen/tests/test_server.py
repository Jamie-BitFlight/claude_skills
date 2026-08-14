from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
import server as kaizen_server
from process_model import ConformanceDiagnostics, ProcessModel

if TYPE_CHECKING:
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


class TestBuildProcessModel:
    def test_builds_model_from_sequences(self, sample_sequences: dict[str, list[str]]) -> None:
        model = kaizen_server._build_process_model(sample_sequences)

        assert model.session_count == 3
        assert model.event_count == 9
        assert "Read" in model.activity_set
        assert ("Read", "Grep") in model.transition_set

    def test_returns_empty_model_for_empty_sequences(self) -> None:
        model = kaizen_server._build_process_model({})

        assert model.session_count == 0
        assert model.event_count == 0
        assert not model.activity_set
        assert not model.transition_set

    def test_preserves_start_and_end_tools(self) -> None:
        model = kaizen_server._build_process_model({"s1": ["Read", "Write"]})

        assert model.start_set == frozenset({"Read"})
        assert model.end_set == frozenset({"Write"})


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
        """Heuristic miner returns a structured process model."""
        result = await kaizen_server.discover_process_model("", sample_sequences, context=mock_context)

        assert isinstance(result, ProcessModel)
        assert result.event_count > 0

    @pytest.mark.asyncio
    async def test_discovers_model_from_glob(self, multi_session_jsonl: Path, mock_context: AsyncMock) -> None:
        """Tool works when given glob_path instead of sequences."""
        glob_path = str(multi_session_jsonl / "*.jsonl")

        result = await kaizen_server.discover_process_model(glob_path, context=mock_context)

        assert isinstance(result, ProcessModel)
        assert result.event_count > 0

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
            assert isinstance(entry, ConformanceDiagnostics)
            assert entry.session_id
            assert isinstance(entry.trace_is_fit, bool)
            assert isinstance(entry.trace_fitness, float)

    @pytest.mark.asyncio
    async def test_self_conformance_is_fit(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Sessions checked against themselves should be fit."""
        result = await kaizen_server.check_conformance(
            sequences=sample_sequences, reference_sequences=sample_sequences, context=mock_context
        )

        fit_count = sum(1 for entry in result if entry.trace_is_fit)
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
# MCP Tool: cluster_sessions
# ===================================================================


class TestClusterSessions:
    """Tests for the cluster_sessions async MCP tool."""

    @pytest.mark.asyncio
    async def test_clusters_sessions_from_sequences(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        result = await kaizen_server.cluster_sessions(sequences=sample_sequences, n_clusters=2, context=mock_context)

        assert len(result.clusters) == 2
        assert len(result.cluster_profiles) == 2

        # All session IDs should be assigned to exactly one cluster
        all_sessions: set[str] = set()
        for members in result.clusters.values():
            all_sessions.update(members)
        assert all_sessions == set(sample_sequences.keys())

    @pytest.mark.asyncio
    async def test_reduces_n_clusters_when_too_large(
        self, single_sequence: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """n_clusters is capped to number of sessions."""
        result = await kaizen_server.cluster_sessions(sequences=single_sequence, n_clusters=10, context=mock_context)

        # With 1 session, effective clusters = min(10, 1) = 1
        assert len(result.clusters) == 1

    @pytest.mark.asyncio
    async def test_cluster_profiles_contain_top_tools(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Cluster profiles list the most common tools."""
        result = await kaizen_server.cluster_sessions(sequences=sample_sequences, n_clusters=2, context=mock_context)

        for profile in result.cluster_profiles.values():
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

        assert len(result.clusters) == 2

    @pytest.mark.asyncio
    async def test_cluster_keys_are_string_ids(
        self, sample_sequences: dict[str, list[str]], mock_context: AsyncMock
    ) -> None:
        """Cluster keys are string representations of cluster IDs."""
        result = await kaizen_server.cluster_sessions(sequences=sample_sequences, n_clusters=2, context=mock_context)

        for key in result.clusters:
            assert isinstance(key, str)
            assert key.isdigit()
