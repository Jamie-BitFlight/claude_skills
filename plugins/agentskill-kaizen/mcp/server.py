#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "pm4py>=2.7.0",
#     "pandas>=2.0.0",
#     "prefixspan>=0.5.2",
#     "scikit-learn>=1.0",
#     "panel>=1.3.0",
#     "hvplot>=0.9.0",
#     "holoviews>=1.18.0",
#     "bokeh>=3.3.0",
# ]
# ///
"""Kaizen Analysis MCP Server.

Exposes process mining, pattern mining, frustration detection,
and session clustering as MCP tools for the transcript-analyst agent.

Tools:
    get_transcript_jsonl_schema - Full session JSONL schema markdown (same as resource below)
Resources:
    kaizen://session-log/schema - Canonical session log schema (markdown); use resources/read
    extract_tool_sequences - Parse JSONL transcripts into tool-call sequences
    discover_process_model - Heuristic Miner process discovery via PM4Py
    check_conformance - Token-based replay conformance checking
    find_frequent_patterns - PrefixSpan sequential pattern mining
    detect_frustration_signals - Regex-based frustration signal extraction
    cluster_sessions - KMeans clustering on tool-call sequence profiles
"""

from __future__ import annotations

import asyncio
import json
import operator
import pathlib
import re
from collections import Counter
from typing import Any

import pandas as pd
import pm4py
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from prefixspan import PrefixSpan
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MIN_SUPPORT: int = 2
_DEFAULT_N_CLUSTERS: int = 3
_TOP_TOOLS_PER_CLUSTER: int = 5
_KMEANS_RANDOM_STATE: int = 42
_KMEANS_N_INIT: int = 10

_READONLY_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_DASHBOARD_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

# ---------------------------------------------------------------------------
# Frustration signal patterns
# ---------------------------------------------------------------------------

_FRUSTRATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("correction", re.compile(r"\b(?:no[,.]?\s|don'?t|wrong|incorrect|stop|undo|revert)\b", re.IGNORECASE)),
    ("denial", re.compile(r"\b(?:that'?s not|i didn'?t|never|absolutely not)\b", re.IGNORECASE)),
    ("interrupt", re.compile(r"\b(?:wait|hold on|cancel|abort|forget it|nevermind)\b", re.IGNORECASE)),
    ("frustration", re.compile(r"\b(?:why did you|you keep|again\?|still wrong|broken)\b", re.IGNORECASE)),
]

mcp = FastMCP("kaizen-analysis", mask_error_details=False)


def _session_log_schema_path() -> pathlib.Path:
    """Path to the bundled session log schema reference (markdown).

    Content is kept in sync with ``plugins/plugin-creator/.../claude-session-log-schema-reference.md``.

    Returns:
        Absolute path to ``session-log-schema.md`` under this plugin.
    """
    return (
        pathlib.Path(__file__).resolve().parent.parent
        / "skills"
        / "transcript-analysis"
        / "references"
        / "session-log-schema.md"
    )


def _read_session_log_schema_text() -> str:
    """Load session log schema markdown or raise ``ToolError`` if missing.

    Returns:
        Full markdown body of ``session-log-schema.md``.

    Raises:
        ToolError: If the schema file is not present on disk.
    """
    path = _session_log_schema_path()
    if not path.is_file():
        raise ToolError(f"Session log schema reference not found at {path}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_jsonl(file_path: str) -> list[dict[str, Any]]:
    """Read a JSONL file and return a list of parsed records.

    Args:
        file_path: Path to a single JSONL file.

    Returns:
        List of dicts, one per line.
    """
    records: list[dict[str, Any]] = []
    with pathlib.Path(file_path).open(encoding="utf-8") as fh:
        records.extend(json.loads(stripped) for line in fh if (stripped := line.strip()))
    return records


def _extract_tools_from_records(records: list[dict[str, Any]]) -> list[str]:
    """Extract ordered tool names from assistant message content blocks.

    Args:
        records: Parsed JSONL records from a single session file.

    Returns:
        Ordered list of tool names invoked in the session.
    """
    tools: list[str] = []
    for record in records:
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                name = block.get("name")
                if isinstance(name, str):
                    tools.append(name)
    return tools


def _resolve_glob(glob_path: str) -> list[str]:
    """Resolve a glob pattern to a sorted list of file paths.

    Splits the glob pattern into a non-glob base directory and a
    relative pattern, then uses ``pathlib.Path.glob`` for resolution.

    Args:
        glob_path: Glob pattern (e.g. ``/home/user/sessions/**/*.jsonl``).

    Returns:
        Sorted list of matching absolute file path strings.
    """
    parts = pathlib.PurePosixPath(glob_path).parts
    base_parts: list[str] = []
    glob_chars = {"*", "?", "["}
    for part in parts:
        if any(c in part for c in glob_chars):
            break
        base_parts.append(part)

    if base_parts:
        base = pathlib.Path(*base_parts)
        relative = str(pathlib.PurePosixPath(*parts[len(base_parts) :]))
    else:
        base = pathlib.Path()
        relative = glob_path

    return sorted(str(p) for p in base.glob(relative))


def _build_event_log(sequences: dict[str, list[str]]) -> pd.DataFrame:
    """Convert tool sequences into a PM4Py-compatible event log DataFrame.

    Each tool call becomes an event with a synthetic timestamp so that
    the ordering within a session is preserved.

    Args:
        sequences: Mapping of session_id to ordered tool names.

    Returns:
        A pandas DataFrame formatted for PM4Py.
    """
    rows: list[dict[str, Any]] = []
    for session_id, tools in sequences.items():
        for idx, tool_name in enumerate(tools):
            rows.append({
                "case:concept:name": session_id,
                "concept:name": tool_name,
                "time:timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(seconds=idx),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return pm4py.format_dataframe(
        df, case_id="case:concept:name", activity_key="concept:name", timestamp_key="time:timestamp"
    )


def _extract_user_text(message: dict[str, Any]) -> str:
    """Extract plain text from a user message content field.

    Handles both string content and list-of-blocks content formats.

    Args:
        message: The ``message`` dict from a ``user`` record.

    Returns:
        Extracted text, or empty string if no text found.
    """
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if isinstance(text, str):
                        parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return ""


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


def _extract_tool_sequences_impl(glob_path: str) -> dict[str, list[str]]:
    """Core implementation for extracting tool sequences from JSONL files.

    This private helper exists to avoid type-checker FunctionTool errors when
    decorated tools call each other directly.

    Args:
        glob_path: Glob pattern pointing to JSONL files.

    Returns:
        Dict mapping session filename (stem) to list of tool names.
    """
    files = _resolve_glob(glob_path)
    result: dict[str, list[str]] = {}
    for file_path in files:
        session_id = file_path.rsplit("/", maxsplit=1)[-1].removesuffix(".jsonl")
        records = _read_jsonl(file_path)
        tools = _extract_tools_from_records(records)
        if tools:
            result[session_id] = tools
    return result


def _resolve_sequences(
    glob_path: str, sequences: dict[str, list[str]] | None, *, target_name: str = "target"
) -> dict[str, list[str]]:
    """Resolve tool sequences from either a glob path or pre-extracted data.

    Args:
        glob_path: Glob pattern for JSONL files.
        sequences: Pre-extracted tool sequences, or None.
        target_name: Human-readable name for error messages (e.g. "target",
            "reference").

    Returns:
        Dict mapping session ID to tool name list.

    Raises:
        ToolError: If neither glob_path nor sequences is provided, or if
            the resolved sequences are empty.
    """
    if sequences is not None:
        if not sequences:
            raise ToolError(f"No {target_name} sequences found")
        return sequences

    if not glob_path:
        raise ToolError(f"Provide either glob_path or sequences for {target_name}")
    resolved = _extract_tool_sequences_impl(glob_path)
    if not resolved:
        raise ToolError(f"No {target_name} tool sequences found in matched files")
    return resolved


# TODO: Restore Annotated[..., Field(...)] parameter annotations once
# https://github.com/PrefectHQ/fastmcp/issues/3238 is resolved.
@mcp.resource("kaizen://session-log/schema")
def session_log_schema_resource() -> str:
    """Claude Code session JSONL schema (markdown) for MCP ``resources/read``.

    Same markdown as ``get_transcript_jsonl_schema``. Canonical content aligns with
    ``plugin-creator`` ``claude-session-log-schema-reference.md`` (copied into this plugin).

    Returns:
        Schema markdown, or a short error markdown if the file is missing.
    """
    try:
        return _read_session_log_schema_text()
    except ToolError as exc:
        return f"# Session log schema unavailable\n\n{exc}\n"


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_transcript_jsonl_schema() -> str:
    """Return the complete Claude Code session JSONL schema (markdown).

    Same body as MCP resource ``kaizen://session-log/schema`` (prefer ``resources/read``
    when the client supports it). Content matches
    ``plugin-creator/skills/hooks-guide/references/claude-session-log-schema-reference.md``
    (shipped copy: ``session-log-schema.md``).

    Use before writing DuckDB SQL: field paths, record types, and directory layout are here.
    The cookbook in ``duckdb-queries.md`` is examples only — compose any SQL with
    ``json_extract`` / JSON operators using paths from this document.

    Next step: ``kaizen-duckdb`` MCP ``execute_query`` with
    ``read_ndjson_auto('/absolute/path/to/*.jsonl', columns={line: 'JSON'})`` (absolute paths;
    no tilde in SQL). See ``plugins/agentskill-kaizen/docs/cross-platform-notes.md``.

    Returns:
        Full session log schema markdown.

    Raises:
        ToolError: If the schema file is missing from the plugin install.
    """
    return await asyncio.to_thread(_read_session_log_schema_text)


# TODO: Restore Annotated[..., Field(...)] parameter annotations once
# https://github.com/PrefectHQ/fastmcp/issues/3238 is resolved.
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def extract_tool_sequences(glob_path: str) -> dict[str, list[str]]:
    """Extract ordered tool-call sequences from JSONL transcript files.

    Reads each JSONL file matching the glob pattern, extracts tool_use
    blocks from assistant messages, and returns the ordered tool names
    per session.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files,
            e.g. ~/.claude/projects/-my-project/*.jsonl

    Returns:
        Dict mapping session filename (stem) to list of tool names.
    """
    return await asyncio.to_thread(_extract_tool_sequences_impl, glob_path)


# TODO: Restore Annotated[..., Field(...)] parameter annotations once
# https://github.com/PrefectHQ/fastmcp/issues/3238 is resolved.
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def discover_process_model(
    glob_path: str = "", sequences: dict[str, list[str]] | None = None, *, context: Context
) -> str:
    """Discover a process model using PM4Py Heuristic Miner.

    Provide either a glob path to JSONL files or pre-extracted sequences.
    Returns a string representation of the discovered heuristic net.

    Args:
        glob_path: Glob pattern for JSONL transcript files; used when
            sequences is not provided.
        sequences: Pre-extracted tool sequences from extract_tool_sequences;
            pass this to avoid re-reading files.
        context: FastMCP context for progress reporting.

    Returns:
        String representation of the discovered heuristic net showing
        nodes and their connection strengths.

    Raises:
        ToolError: If inputs are missing or the event log is empty.
    """
    await context.info("Resolving tool sequences...")
    resolved = await asyncio.to_thread(_resolve_sequences, glob_path, sequences, target_name="target")

    await context.info("Building event log from sequences...")
    event_log = _build_event_log(resolved)
    if event_log.empty:
        raise ToolError("Event log is empty after building from sequences")

    await context.info("Running Heuristic Miner...")
    heu_net = await asyncio.to_thread(pm4py.discover_heuristics_net, event_log)
    return repr(heu_net)


# TODO: Restore Annotated[..., Field(...)] parameter annotations once
# https://github.com/PrefectHQ/fastmcp/issues/3238 is resolved.
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def check_conformance(
    glob_path: str = "",
    sequences: dict[str, list[str]] | None = None,
    reference_glob_path: str = "",
    reference_sequences: dict[str, list[str]] | None = None,
    *,
    context: Context,
) -> list[dict[str, Any]]:
    """Check conformance of sessions against a reference process model.

    Discovers a Petri net from the reference sequences via Heuristic
    Miner, then runs token-based replay on the target sessions.

    Args:
        glob_path: Glob pattern for target JSONL files to check conformance.
        sequences: Pre-extracted target tool sequences to check.
        reference_glob_path: Glob pattern for reference JSONL files (the
            'golden' model).
        reference_sequences: Pre-extracted reference tool sequences for the
            model.
        context: FastMCP context for progress reporting.

    Returns:
        List of per-trace conformance dicts with keys including
        ``trace_is_fit``, ``trace_fitness``, ``missing_tokens``,
        ``remaining_tokens``, and the ``session_id``.

    Raises:
        ToolError: If required inputs are missing or sequences are empty.
    """
    await context.info("Resolving target sequences...")
    resolved_target = await asyncio.to_thread(_resolve_sequences, glob_path, sequences, target_name="target")

    await context.info("Resolving reference sequences...")
    resolved_ref = await asyncio.to_thread(
        _resolve_sequences, reference_glob_path, reference_sequences, target_name="reference"
    )

    await context.info("Building reference model (Heuristic Miner -> Petri Net)...")

    def _build_reference_model(ref_seqs: dict[str, list[str]]) -> tuple[Any, Any, Any]:
        ref_log = _build_event_log(ref_seqs)
        heu_net = pm4py.discover_heuristics_net(ref_log)
        result: tuple[Any, Any, Any] = pm4py.convert_to_petri_net(heu_net)
        return result

    net, initial_marking, final_marking = await asyncio.to_thread(_build_reference_model, resolved_ref)

    await context.info("Running token-based replay on target sessions...")

    def _run_replay(target_seqs: dict[str, list[str]]) -> list[dict[str, Any]]:
        target_log = _build_event_log(target_seqs)
        result: list[dict[str, Any]] = pm4py.conformance_diagnostics_token_based_replay(
            target_log, net, initial_marking, final_marking
        )
        return result

    replay_results: list[dict[str, Any]] = await asyncio.to_thread(_run_replay, resolved_target)

    session_ids = list(resolved_target.keys())
    output: list[dict[str, Any]] = []
    for idx, diag in enumerate(replay_results):
        entry: dict[str, Any] = {
            "session_id": session_ids[idx] if idx < len(session_ids) else f"trace_{idx}",
            "trace_is_fit": diag.get("trace_is_fit", False),
            "trace_fitness": diag.get("trace_fitness", 0.0),
            "missing_tokens": diag.get("missing_tokens", 0),
            "remaining_tokens": diag.get("remaining_tokens", 0),
            "consumed_tokens": diag.get("consumed_tokens", 0),
            "produced_tokens": diag.get("produced_tokens", 0),
        }
        output.append(entry)
    return output


# TODO: Restore Annotated[..., Field(...)] parameter annotations once
# https://github.com/PrefectHQ/fastmcp/issues/3238 is resolved.
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def find_frequent_patterns(
    glob_path: str = "", sequences: dict[str, list[str]] | None = None, min_support: int = _DEFAULT_MIN_SUPPORT
) -> list[dict[str, Any]]:
    """Find frequent sequential patterns in tool-call sequences using PrefixSpan.

    Args:
        glob_path: Glob pattern for JSONL files; used when sequences is not
            provided.
        sequences: Pre-extracted tool sequences from extract_tool_sequences;
            pass this to avoid re-reading files.
        min_support: Minimum number of sessions a pattern must appear in.

    Returns:
        List of dicts with ``pattern`` (list of tool names) and
        ``support`` (count of sessions containing the pattern),
        sorted by support descending.

    Raises:
        ToolError: If neither glob_path nor sequences is provided.
    """
    resolved = await asyncio.to_thread(_resolve_sequences, glob_path, sequences, target_name="target")

    def _mine_patterns(seqs: dict[str, list[str]], min_sup: int) -> list[dict[str, Any]]:
        db = list(seqs.values())
        ps = PrefixSpan(db)
        ps.minlen = 2
        # PrefixSpan lacks type stubs; ty infers ps.frequent as Unknown | None.
        # The callable guard narrows the type for static analysis.
        frequent_method = ps.frequent
        if not callable(frequent_method):
            msg = "PrefixSpan.frequent is not callable"
            raise TypeError(msg)
        frequent: list[tuple[int, list[str]]] = frequent_method(min_sup)
        results: list[dict[str, Any]] = [{"support": count, "pattern": pattern} for count, pattern in frequent]
        results.sort(key=operator.itemgetter("support"), reverse=True)
        return results

    return await asyncio.to_thread(_mine_patterns, resolved, min_support)


# TODO: Restore Annotated[..., Field(...)] parameter annotations once
# https://github.com/PrefectHQ/fastmcp/issues/3238 is resolved.
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def detect_frustration_signals(glob_path: str) -> list[dict[str, str]]:
    """Detect user frustration signals in JSONL transcripts.

    Scans user-type messages for patterns indicating corrections,
    denials, interrupts, and expressions of frustration. Filters
    out system-generated messages (tool results).

    Args:
        glob_path: Glob pattern for JSONL transcript files to scan for
            frustration signals.

    Returns:
        List of dicts with ``session_id``, ``timestamp``,
        ``signal_type``, and ``message_text``.
    """

    def _scan(glob: str) -> list[dict[str, str]]:
        files = _resolve_glob(glob)
        signals: list[dict[str, str]] = []

        for file_path in files:
            session_id = file_path.rsplit("/", maxsplit=1)[-1].removesuffix(".jsonl")
            records = _read_jsonl(file_path)

            for record in records:
                if record.get("type") != "user":
                    continue
                if record.get("toolUseResult"):
                    continue

                message = record.get("message")
                if not isinstance(message, dict):
                    continue

                text = _extract_user_text(message)
                if not text:
                    continue

                timestamp = record.get("timestamp", "")

                for signal_type, pattern in _FRUSTRATION_PATTERNS:
                    if pattern.search(text):
                        signals.append({
                            "session_id": session_id,
                            "timestamp": str(timestamp),
                            "signal_type": signal_type,
                            "message_text": text,
                        })
                        break  # One signal per message

        return signals

    return await asyncio.to_thread(_scan, glob_path)


# TODO: Restore Annotated[..., Field(...)] parameter annotations once
# https://github.com/PrefectHQ/fastmcp/issues/3238 is resolved.
@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def cluster_sessions(
    glob_path: str = "",
    sequences: dict[str, list[str]] | None = None,
    n_clusters: int = _DEFAULT_N_CLUSTERS,
    *,
    context: Context,
) -> dict[str, Any]:
    """Group sessions by behavioral similarity using tool-call sequence profiles.

    Encodes each session's tool sequence as a bag-of-tools vector,
    then applies KMeans clustering.

    Args:
        glob_path: Glob pattern for JSONL files; used when sequences is not
            provided.
        sequences: Pre-extracted tool sequences from extract_tool_sequences;
            pass this to avoid re-reading files.
        n_clusters: Number of clusters to create via KMeans.
        context: FastMCP context for progress reporting.

    Returns:
        Dict with ``clusters`` mapping cluster_id to list of session_ids,
        and ``cluster_profiles`` mapping cluster_id to the most common
        tools in that cluster.

    Raises:
        ToolError: If neither glob_path nor sequences is provided, or if
            there are no sessions to cluster.
    """
    await context.info("Resolving tool sequences...")
    resolved = await asyncio.to_thread(_resolve_sequences, glob_path, sequences, target_name="target")

    session_ids = list(resolved.keys())
    docs = [" ".join(tools) for tools in resolved.values()]

    effective_clusters = min(n_clusters, len(docs))
    if effective_clusters < 1:
        raise ToolError("Need at least 1 session to cluster")

    await context.info(f"Clustering {len(docs)} sessions into {effective_clusters} clusters...")

    def _run_clustering(documents: list[str], k: int) -> list[int]:
        vectorizer = CountVectorizer()
        feature_matrix = vectorizer.fit_transform(documents)
        km = KMeans(n_clusters=k, random_state=_KMEANS_RANDOM_STATE, n_init=_KMEANS_N_INIT)
        return list(km.fit_predict(feature_matrix))

    labels = await asyncio.to_thread(_run_clustering, docs, effective_clusters)

    clusters: dict[str, list[str]] = {}
    cluster_profiles: dict[str, list[str]] = {}

    for cluster_id in range(effective_clusters):
        cid = str(cluster_id)
        member_indices = [i for i, lbl in enumerate(labels) if lbl == cluster_id]
        clusters[cid] = [session_ids[i] for i in member_indices]

        tool_counts: Counter[str] = Counter()
        for i in member_indices:
            tool_counts.update(resolved[session_ids[i]])
        cluster_profiles[cid] = [t for t, _ in tool_counts.most_common(_TOP_TOOLS_PER_CLUSTER)]

    return {"clusters": clusters, "cluster_profiles": cluster_profiles}


@mcp.tool(annotations=_DASHBOARD_ANNOTATIONS)
def open_dashboard() -> dict[str, str | bool]:
    """Return the Kaizen sentiment dashboard URL.

    Does not open a browser — opening the browser while Tornado is
    initializing causes IOLoop exhaustion and a blank/unresponsive page.
    Copy the returned URL and open it manually.

    Returns:
        Dict with ``url`` and a human-readable ``message``.

    Raises:
        ToolError: If the dashboard is not running.
    """
    from dashboard import get_dashboard_url  # noqa: PLC0415

    url = get_dashboard_url()
    if url is None:
        raise ToolError("Dashboard is not running. The MCP server may have failed to start the dashboard thread.")

    return {
        "url": url,
        "opened_browser": False,
        "message": f"Dashboard is running at {url} — open this URL in your browser",
    }


if __name__ == "__main__":
    from dashboard import start_dashboard

    start_dashboard()
    mcp.run()
