#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Verify plugin structure for uptake-ranked cross-harness MCP candidates.

This is deliberately a mechanical second stage. It consumes the ordered output
of ``discover_cross_harness_mcp_candidates.py`` and fetches only repository
trees. It does not read plugin manifests or MCP configuration contents, clone
repositories, or run a plugin. Those are separate, more expensive stages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from operator import itemgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_utils import run_gh_json

if TYPE_CHECKING:
    from collections.abc import Iterable


def plugin_root(path: str, manifest_directory: str) -> str:
    """Return the plugin root for a manifest path.

    Args:
        path: Path to a plugin manifest in a repository tree.
        manifest_directory: The harness manifest directory name.

    Returns:
        The parent plugin root, with the repository root represented by ``"."``.
    """
    suffix = f"/{manifest_directory}/plugin.json"
    if path == f"{manifest_directory}/plugin.json":
        return "."
    if not path.endswith(suffix):
        raise ValueError(f"Unexpected {manifest_directory} manifest path: {path}")
    return path.removesuffix(suffix)


def mcp_config_paths(paths: Iterable[str], root: str) -> list[str]:
    """Find root-owned MCP configuration files without reading their contents.

    Args:
        paths: Complete repository-tree paths.
        root: Plugin root to evaluate.

    Returns:
        Sorted MCP configuration file paths belonging to the plugin root.
    """
    prefix = "" if root == "." else f"{root}/"
    configs: list[str] = []
    for path in paths:
        if not path.startswith(prefix):
            continue
        relative_path = path.removeprefix(prefix)
        if (
            relative_path == ".mcp.json"
            or (relative_path.startswith(".mcp.") and relative_path.endswith(".json"))
            or (relative_path.startswith("mcp-configs/") and relative_path.endswith(".json"))
        ):
            configs.append(path)
    return sorted(configs)


def inspect_tree(candidate: dict[str, Any]) -> dict[str, Any]:
    """Classify aligned plugin roots using the candidate repository tree.

    Args:
        candidate: One ranked metadata candidate from the discovery stage.

    Returns:
        A structure-only verification record for that candidate.
    """
    repository = candidate["repository"]
    branch = candidate["default_branch"]
    if branch is None:
        return {
            "repository": repository,
            "rank": candidate["rank"],
            "stars": candidate["stars"],
            "forks": candidate["forks"],
            "status": "tree_unavailable",
            "reason": "repository has no default branch",
        }

    tree = run_gh_json(["api", f"repos/{repository}/git/trees/{branch}?recursive=1"])
    paths = sorted(entry["path"] for entry in tree.get("tree", []) if entry.get("type") == "blob")
    claude_manifests = [
        path for path in paths if path.endswith("/.claude-plugin/plugin.json") or path == ".claude-plugin/plugin.json"
    ]
    codex_manifests = [
        path for path in paths if path.endswith("/.codex-plugin/plugin.json") or path == ".codex-plugin/plugin.json"
    ]
    claude_roots = {plugin_root(path, ".claude-plugin"): path for path in claude_manifests}
    codex_roots = {plugin_root(path, ".codex-plugin"): path for path in codex_manifests}
    aligned_roots = sorted(claude_roots.keys() & codex_roots.keys(), key=str.casefold)
    aligned_plugins = [
        {
            "root": root,
            "claude_manifest": claude_roots[root],
            "codex_manifest": codex_roots[root],
            "mcp_config_paths": mcp_config_paths(paths, root),
        }
        for root in aligned_roots
    ]
    has_bundled_mcp = any(plugin["mcp_config_paths"] for plugin in aligned_plugins)
    if tree.get("truncated", False):
        status = "inconclusive_tree_truncated"
    elif has_bundled_mcp:
        status = "accepted_for_semantic_inspection"
    else:
        status = "rejected_no_aligned_bundled_mcp"
    return {
        "repository": repository,
        "rank": candidate["rank"],
        "stars": candidate["stars"],
        "forks": candidate["forks"],
        "tree_truncated": tree.get("truncated", False),
        "claude_manifest_paths": claude_manifests,
        "codex_manifest_paths": codex_manifests,
        "aligned_plugins": aligned_plugins,
        "status": status,
    }


def write_output(
    output: Path,
    input_path: Path,
    input_fingerprint: str,
    input_partial: bool,
    records: list[dict[str, Any]],
    complete: bool,
) -> None:
    """Atomically persist structure records after each requested repository.

    Args:
        output: Destination JSON path.
        input_path: Original ranked-candidate dataset.
        input_fingerprint: Digest of the candidate input used for resumption.
        input_partial: Whether the source dataset was flagged as partial.
        records: Existing rank-ordered structure records.
        complete: Whether every input candidate received a record.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "repository-tree structure only; no manifest or MCP content was read and no plugin was executed",
        "source_rankings": str(input_path),
        "source_rankings_fingerprint": input_fingerprint,
        "source_rankings_partial": input_partial,
        "complete": complete,
        "records": records,
    }
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    Returns:
        Validated command-line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Ranked metadata-only candidate JSON.")
    parser.add_argument("--output", type=Path, required=True, help="Resumable structure-verification JSON.")
    parser.add_argument(
        "--allow-partial-input",
        action="store_true",
        help="Inspect an input that its collector explicitly marked as partial.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.5,
        help="Delay between tree requests to avoid request bursts (default: 0.5).",
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Discard existing records and rerun the ordered structure check."
    )
    return parser.parse_args()


def load_existing_records(output: Path, input_fingerprint: str) -> list[dict[str, Any]]:
    """Load records from a prior interrupted verifier run.

    Returns:
        Existing structure records, or an empty list when no output exists.
    """
    if not output.exists():
        return []
    payload = json.loads(output.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise TypeError(f"Malformed verifier output: {output}")
    if payload.get("source_rankings_fingerprint") != input_fingerprint:
        return []
    return records


def main() -> int:
    """Run the ordered structural verification stage.

    Returns:
        Process exit status.
    """
    args = parse_args()
    candidate_data = json.loads(args.input.read_text(encoding="utf-8"))
    if candidate_data.get("partial") and not args.allow_partial_input:
        raise RuntimeError("Candidate input is partial; pass --allow-partial-input to use it explicitly")
    raw_candidates = candidate_data.get("eligible_candidates")
    if not isinstance(raw_candidates, list):
        raise TypeError(f"Malformed candidate input: {args.input}")
    candidates: list[dict[str, Any]] = []
    for candidate in raw_candidates:
        if not isinstance(candidate, dict):
            raise TypeError(f"Malformed candidate input: {args.input}")
        candidates.append(candidate)

    input_fingerprint = hashlib.sha256(
        json.dumps(candidates, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    records = [] if args.refresh else load_existing_records(args.output, input_fingerprint)
    completed_repositories = {record["repository"] for record in records}
    for rank, candidate in enumerate(candidates, start=1):
        candidate["rank"] = rank
        if candidate["repository"] in completed_repositories:
            continue
        try:
            record = inspect_tree(candidate)
        except RuntimeError as error:
            record = {
                "repository": candidate["repository"],
                "rank": rank,
                "stars": candidate["stars"],
                "forks": candidate["forks"],
                "status": "tree_request_failed",
                "reason": str(error),
            }
        records.append(record)
        records.sort(key=itemgetter("rank"))
        write_output(
            args.output, args.input, input_fingerprint, candidate_data.get("partial", False), records, complete=False
        )
        time.sleep(args.delay_seconds)

    write_output(
        args.output, args.input, input_fingerprint, candidate_data.get("partial", False), records, complete=True
    )
    print(f"Wrote {len(records)} structure records to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
