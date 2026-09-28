#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Finalize one daily-release analysis with deterministic metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_json(path: Path) -> object:
    """Load JSON from a UTF-8 file.

    Returns:
        The decoded JSON value.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def finalize_day(day_dir: Path) -> Path:
    """Finalize the analysis for one day.

    Returns:
        The finalized analysis file path.
    """
    summaries = sorted((day_dir / "summaries").glob("bucket_*.json"))
    analysis_file = day_dir / "analysis.json"
    if not summaries and not analysis_file.exists():
        raise ValueError(f"No bucket summaries or synthesized analysis found in {day_dir}")
    source = summaries[0] if len(summaries) == 1 else analysis_file
    if not source.exists():
        raise ValueError(f"Synthesized analysis not found: {analysis_file}")

    analysis = _load_json(source)
    if not isinstance(analysis, dict):
        raise TypeError(f"Analysis must be a JSON object: {source}")
    files_path = day_dir / "dataset/files.json"
    commits_path = day_dir / "dataset/commits.json"
    files = _load_json(files_path) if files_path.exists() else []
    commits = _load_json(commits_path) if commits_path.exists() else []
    if not isinstance(files, list) or not isinstance(commits, list):
        raise TypeError("Dataset files and commits must be JSON arrays")
    summary = analysis.pop("bucket_summary", None) or analysis.get("summary")
    if not summary:
        summary = "No summary provided."

    analysis.update({
        "title": f"Daily Release {day_dir.name}",
        "summary": summary,
        "statistics": {
            "commit_count": len(commits),
            "files_changed": len(files),
            "lines_added": sum(item.get("lines_added", 0) for item in files if isinstance(item, dict)),
            "lines_deleted": sum(item.get("lines_deleted", 0) for item in files if isinstance(item, dict)),
        },
    })

    temporary = analysis_file.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    temporary.replace(analysis_file)
    return analysis_file


def main() -> int:
    """Run the finalizer CLI.

    Returns:
        A process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("day_dir", type=Path)
    args = parser.parse_args()
    try:
        analysis_file = finalize_day(args.day_dir)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps({"analysis_file": str(analysis_file.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
