#!/usr/bin/env python3
"""Aggregate individual run results into benchmark summary statistics.

Reads grading.json files from run directories and produces:
- run_summary with mean, stddev, min, max for each metric
- delta between with_skill and without_skill configurations

Usage:
    python aggregate_benchmark.py <benchmark_dir>

Example:
    python aggregate_benchmark.py benchmarks/2026-01-15T10-30-00/

The script supports two directory layouts:

    Workspace layout (from skill-creator iterations):
    <benchmark_dir>/
    └── eval-N/
        ├── with_skill/
        │   ├── run-1/grading.json
        │   └── run-2/grading.json
        └── without_skill/
            ├── run-1/grading.json
            └── run-2/grading.json

    Legacy layout (with runs/ subdirectory):
    <benchmark_dir>/
    └── runs/
        └── eval-N/
            ├── with_skill/
            │   └── run-1/grading.json
            └── without_skill/
                └── run-1/grading.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

MIN_CONFIGS_FOR_DELTA = 2
DEFAULT_RUNS_PER_CONFIGURATION = 3
MIN_CONFIGS_FOR_LABEL = 1

ConfigStats = dict[str, dict[str, float | int]]


def calculate_stats(values: list[float]) -> dict:
    """Calculate mean, stddev, min, max for a list of values.

    Args:
        values: List of numeric values to summarise.

    Returns:
        Dict with keys ``mean``, ``stddev``, ``min``, ``max``, each rounded
        to 4 decimal places.  All values are 0.0 when ``values`` is empty.
    """
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}

    n = len(values)
    mean = sum(values) / n

    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0

    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def _resolve_eval_id(eval_dir: Path, eval_idx: int) -> int | str:
    """Resolve the eval ID for a given eval directory.

    Args:
        eval_dir: Path to the eval directory.
        eval_idx: Fallback index used when the ID cannot be determined.

    Returns:
        The eval ID from ``eval_metadata.json``, parsed from the directory
        name, or ``eval_idx`` as a last resort.
    """
    metadata_path = eval_dir / "eval_metadata.json"
    if metadata_path.exists():
        try:
            with metadata_path.open(encoding="utf-8") as mf:
                return json.load(mf).get("eval_id", eval_idx)
        except (json.JSONDecodeError, OSError):
            return eval_idx
    try:
        return int(eval_dir.name.split("-")[1])
    except ValueError:
        return eval_idx


def _load_timing(result: dict, grading: dict, run_dir: Path) -> None:
    """Populate ``time_seconds`` and ``tokens`` from grading or sibling timing.json.

    Args:
        result: The run result dict to update in place.
        grading: The parsed grading.json data.
        run_dir: Path to the run directory (for locating ``timing.json``).
    """
    timing = grading.get("timing", {})
    result["time_seconds"] = timing.get("total_duration_seconds", 0.0)
    timing_file = run_dir / "timing.json"
    if not result["time_seconds"] and timing_file.exists():
        try:
            with timing_file.open(encoding="utf-8") as tf:
                timing_data = json.load(tf)
            result["time_seconds"] = timing_data.get("total_duration_seconds", 0.0)
            result["tokens"] = timing_data.get("total_tokens", 0)
        except json.JSONDecodeError:
            pass


def _build_run_result(eval_id: int | str, run_number: int, grading: dict, grading_file: Path, run_dir: Path) -> dict:
    """Build the result dict for a single run.

    Args:
        eval_id: The eval identifier.
        run_number: The run number within the eval.
        grading: The parsed grading.json data.
        grading_file: Path to grading.json (used for warning messages).
        run_dir: Path to the run directory.

    Returns:
        A dict with keys: ``eval_id``, ``run_number``, ``pass_rate``,
        ``passed``, ``failed``, ``total``, ``time_seconds``, ``tokens``,
        ``tool_calls``, ``errors``, ``expectations``, ``notes``.
    """
    summary = grading.get("summary", {})
    result: dict = {
        "eval_id": eval_id,
        "run_number": run_number,
        "pass_rate": summary.get("pass_rate", 0.0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "total": summary.get("total", 0),
    }

    _load_timing(result, grading, run_dir)

    metrics = grading.get("execution_metrics", {})
    result["tool_calls"] = metrics.get("total_tool_calls", 0)
    if not result.get("tokens"):
        result["tokens"] = metrics.get("output_chars", 0)
    result["errors"] = metrics.get("errors_encountered", 0)

    raw_expectations = grading.get("expectations", [])
    for exp in raw_expectations:
        if "text" not in exp or "passed" not in exp:
            print(f"Warning: expectation in {grading_file} missing required fields (text, passed, evidence): {exp}")
    result["expectations"] = raw_expectations

    notes_summary = grading.get("user_notes_summary", {})
    notes: list[str] = []
    notes.extend(notes_summary.get("uncertainties", []))
    notes.extend(notes_summary.get("needs_review", []))
    notes.extend(notes_summary.get("workarounds", []))
    result["notes"] = notes

    return result


def _load_config_runs(config_dir: Path, eval_id: int | str, results: dict[str, list]) -> None:
    """Load all run results for one config directory into ``results``.

    Args:
        config_dir: Path to the config directory (e.g. ``with_skill/``).
        eval_id: The eval identifier to attach to each run result.
        results: The accumulator dict to update in place.
    """
    config = config_dir.name
    if config not in results:
        results[config] = []

    for run_dir in sorted(config_dir.glob("run-*")):
        run_number = int(run_dir.name.split("-")[1])
        grading_file = run_dir / "grading.json"

        if not grading_file.exists():
            print(f"Warning: grading.json not found in {run_dir}")
            continue

        try:
            with grading_file.open(encoding="utf-8") as f:
                grading = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {grading_file}: {e}")
            continue

        results[config].append(_build_run_result(eval_id, run_number, grading, grading_file, run_dir))


def load_run_results(benchmark_dir: Path) -> dict:
    """Load all run results from a benchmark directory.

    Args:
        benchmark_dir: Root benchmark directory to search.

    Returns:
        Dict keyed by config name (e.g. ``"with_skill"``/``"without_skill"``
        or ``"new_skill"``/``"old_skill"``), each value being a list of run
        result dicts.  Returns an empty dict when no eval directories are found.
    """
    # Support both layouts: eval dirs directly under benchmark_dir, or under runs/
    runs_dir = benchmark_dir / "runs"
    if runs_dir.exists():
        search_dir = runs_dir
    elif list(benchmark_dir.glob("eval-*")):
        search_dir = benchmark_dir
    else:
        print(f"No eval directories found in {benchmark_dir} or {benchmark_dir / 'runs'}")
        return {}

    results: dict[str, list] = {}

    for eval_idx, eval_dir in enumerate(sorted(search_dir.glob("eval-*"))):
        eval_id = _resolve_eval_id(eval_dir, eval_idx)

        # Discover config directories dynamically rather than hardcoding names
        for config_dir in sorted(eval_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            # Skip non-config directories (inputs, outputs, etc.)
            if not next(config_dir.glob("run-*"), None):
                continue
            _load_config_runs(config_dir, eval_id, results)

    return results


def aggregate_results(results: dict) -> dict[str, ConfigStats | dict[str, str]]:
    """Aggregate run results into summary statistics.

    Args:
        results: Dict from :func:`load_run_results`.

    Returns:
        Dict with per-config stats and a ``"delta"`` key comparing the first
        two configs.
    """
    config_stats: dict[str, ConfigStats] = {}
    configs = list(results.keys())

    for config in configs:
        runs = results.get(config, [])

        if not runs:
            config_stats[config] = {
                "pass_rate": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "time_seconds": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "tokens": {"mean": 0, "stddev": 0, "min": 0, "max": 0},
            }
            continue

        pass_rates = [r["pass_rate"] for r in runs]
        times = [r["time_seconds"] for r in runs]
        tokens = [r.get("tokens", 0) for r in runs]

        config_stats[config] = {
            "pass_rate": calculate_stats(pass_rates),
            "time_seconds": calculate_stats(times),
            "tokens": calculate_stats(tokens),
        }

    # Calculate delta between the first two configs (if two exist)
    if len(configs) >= MIN_CONFIGS_FOR_DELTA:
        primary = config_stats.get(configs[0], {})
        baseline = config_stats.get(configs[1], {})
    else:
        primary = config_stats.get(configs[0], {}) if configs else {}
        baseline = {}

    delta_pass_rate = primary.get("pass_rate", {}).get("mean", 0) - baseline.get("pass_rate", {}).get("mean", 0)
    delta_time = primary.get("time_seconds", {}).get("mean", 0) - baseline.get("time_seconds", {}).get("mean", 0)
    delta_tokens = primary.get("tokens", {}).get("mean", 0) - baseline.get("tokens", {}).get("mean", 0)

    run_summary: dict[str, ConfigStats | dict[str, str]] = dict(config_stats)
    run_summary["delta"] = {
        "pass_rate": f"{delta_pass_rate:+.2f}",
        "time_seconds": f"{delta_time:+.1f}",
        "tokens": f"{delta_tokens:+.0f}",
    }

    return run_summary


def generate_benchmark(benchmark_dir: Path, skill_name: str = "", skill_path: str = "") -> dict:
    """Generate complete benchmark.json from run results.

    Args:
        benchmark_dir: Root benchmark directory.
        skill_name: Optional skill name for metadata.
        skill_path: Optional skill path for metadata.

    Returns:
        Complete benchmark dict ready for JSON serialisation.
    """
    results = load_run_results(benchmark_dir)
    run_summary = aggregate_results(results)

    # Build runs array for benchmark.json
    runs = []
    for config in results:
        runs.extend(
            {
                "eval_id": result["eval_id"],
                "configuration": config,
                "run_number": result["run_number"],
                "result": {
                    "pass_rate": result["pass_rate"],
                    "passed": result["passed"],
                    "failed": result["failed"],
                    "total": result["total"],
                    "time_seconds": result["time_seconds"],
                    "tokens": result.get("tokens", 0),
                    "tool_calls": result.get("tool_calls", 0),
                    "errors": result.get("errors", 0),
                },
                "expectations": result["expectations"],
                "notes": result["notes"],
            }
            for result in results[config]
        )

    # Determine eval IDs from results
    eval_ids = sorted({r["eval_id"] for config in results.values() for r in config})

    return {
        "metadata": {
            "skill_name": skill_name or "<skill-name>",
            "skill_path": skill_path or "<path/to/skill>",
            "executor_model": "<model-name>",
            "analyzer_model": "<model-name>",
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evals_run": eval_ids,
            "runs_per_configuration": DEFAULT_RUNS_PER_CONFIGURATION,
        },
        "runs": runs,
        "run_summary": run_summary,
        "notes": [],  # To be filled by analyzer
    }


def generate_markdown(benchmark: dict) -> str:
    """Generate human-readable benchmark.md from benchmark data.

    Args:
        benchmark: Dict produced by :func:`generate_benchmark`.

    Returns:
        Markdown string with summary table and optional notes section.
    """
    metadata = benchmark["metadata"]
    run_summary = benchmark["run_summary"]

    # Determine config names (excluding "delta")
    configs = [k for k in run_summary if k != "delta"]
    config_a = configs[0] if len(configs) >= MIN_CONFIGS_FOR_LABEL else "config_a"
    config_b = configs[1] if len(configs) >= MIN_CONFIGS_FOR_DELTA else "config_b"
    label_a = config_a.replace("_", " ").title()
    label_b = config_b.replace("_", " ").title()

    lines = [
        f"# Skill Benchmark: {metadata['skill_name']}",
        "",
        f"**Model**: {metadata['executor_model']}",
        f"**Date**: {metadata['timestamp']}",
        f"**Evals**: {', '.join(map(str, metadata['evals_run']))} ({metadata['runs_per_configuration']} runs each per configuration)",
        "",
        "## Summary",
        "",
        f"| Metric | {label_a} | {label_b} | Delta |",
        "|--------|------------|---------------|-------|",
    ]

    a_summary = run_summary.get(config_a, {})
    b_summary = run_summary.get(config_b, {})
    delta = run_summary.get("delta", {})

    # Format pass rate
    a_pr = a_summary.get("pass_rate", {})
    b_pr = b_summary.get("pass_rate", {})
    lines.append(
        f"| Pass Rate | {a_pr.get('mean', 0) * 100:.0f}% ± {a_pr.get('stddev', 0) * 100:.0f}%"
        f" | {b_pr.get('mean', 0) * 100:.0f}% ± {b_pr.get('stddev', 0) * 100:.0f}%"
        f" | {delta.get('pass_rate', '—')} |"
    )

    # Format time
    a_time = a_summary.get("time_seconds", {})
    b_time = b_summary.get("time_seconds", {})
    lines.append(
        f"| Time | {a_time.get('mean', 0):.1f}s ± {a_time.get('stddev', 0):.1f}s"
        f" | {b_time.get('mean', 0):.1f}s ± {b_time.get('stddev', 0):.1f}s"
        f" | {delta.get('time_seconds', '—')}s |"
    )

    # Format tokens
    a_tokens = a_summary.get("tokens", {})
    b_tokens = b_summary.get("tokens", {})
    lines.append(
        f"| Tokens | {a_tokens.get('mean', 0):.0f} ± {a_tokens.get('stddev', 0):.0f}"
        f" | {b_tokens.get('mean', 0):.0f} ± {b_tokens.get('stddev', 0):.0f}"
        f" | {delta.get('tokens', '—')} |"
    )

    # Notes section
    if benchmark.get("notes"):
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in benchmark["notes"])

    return "\n".join(lines)


def main() -> None:
    """Parse arguments, generate benchmark.json and benchmark.md, print summary."""
    parser = argparse.ArgumentParser(description="Aggregate benchmark run results into summary statistics")
    parser.add_argument("benchmark_dir", type=Path, help="Path to the benchmark directory")
    parser.add_argument("--skill-name", default="", help="Name of the skill being benchmarked")
    parser.add_argument("--skill-path", default="", help="Path to the skill being benchmarked")
    parser.add_argument(
        "--output", "-o", type=Path, help="Output path for benchmark.json (default: <benchmark_dir>/benchmark.json)"
    )

    args = parser.parse_args()

    if not args.benchmark_dir.exists():
        print(f"Directory not found: {args.benchmark_dir}")
        sys.exit(1)

    # Generate benchmark
    benchmark = generate_benchmark(args.benchmark_dir, args.skill_name, args.skill_path)

    # Determine output paths
    output_json = args.output or (args.benchmark_dir / "benchmark.json")
    output_md = output_json.with_suffix(".md")

    # Write benchmark.json
    with Path(output_json).open("w", encoding="utf-8") as f:
        json.dump(benchmark, f, indent=2)
    print(f"Generated: {output_json}")

    # Write benchmark.md
    markdown = generate_markdown(benchmark)
    Path(output_md).write_text(markdown, encoding="utf-8")
    print(f"Generated: {output_md}")

    # Print summary
    run_summary = benchmark["run_summary"]
    configs = [k for k in run_summary if k != "delta"]
    delta = run_summary.get("delta", {})

    print("\nSummary:")
    for config in configs:
        pr = run_summary[config]["pass_rate"]["mean"]
        label = config.replace("_", " ").title()
        print(f"  {label}: {pr * 100:.1f}% pass rate")
    print(f"  Delta:         {delta.get('pass_rate', '—')}")


if __name__ == "__main__":
    main()
