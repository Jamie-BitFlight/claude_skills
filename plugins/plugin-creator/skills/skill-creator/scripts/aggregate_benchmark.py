#!/usr/bin/env python3
"""Aggregate observed run records without inventing measurements or repetitions.

Supports eval-N/<configuration>/run-N and runs/eval-N/<configuration>/run-N.
Missing values remain null. A report accounts for observed directories only; it
cannot establish that an unprovided expected run inventory was completed.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


METRICS = ("pass_rate", "time_seconds", "tokens")


def calculate_stats(values: list[float | int | None]) -> dict[str, float | int | None]:
    """Summarize available observations and retain the missing-value denominator."""
    observed = [v for v in values if v is not None]
    n = len(observed)
    result: dict[str, float | int | None] = {"observed": n, "missing": len(values) - n}
    if not observed:
        return {**result, "mean": None, "stddev": None, "min": None, "max": None}
    mean = sum(observed) / n
    deviation = math.sqrt(sum((v - mean) ** 2 for v in observed) / (n - 1)) if n > 1 else 0.0
    return {**result, "mean": round(mean, 4), "stddev": round(deviation, 4),
            "min": round(min(observed), 4), "max": round(max(observed), 4)}


def _read_object(path: Path, gaps: list[str]) -> dict[str, Any]:
    """Read one record, preserving malformed or inaccessible carriers as gaps."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("record must be an object")
        return value
    except (OSError, ValueError) as exc:
        gaps.append(f"{path}: {exc}")
        return {}


def _number(value: Any, *, integer: bool = False) -> bool:
    """Exclude booleans, non-finite numbers, negative counts and unit mismatches."""
    return (type(value) in (int, float) and math.isfinite(value) and value >= 0
            and (not integer or type(value) is int))


def _resolve_eval_id(eval_dir: Path, eval_idx: int) -> int | str:
    """Use declared eval identity or the directory's identity without inventing a count."""
    metadata = eval_dir / "eval_metadata.json"
    if metadata.exists():
        gaps: list[str] = []
        value = _read_object(metadata, gaps).get("eval_id")
        if type(value) in (int, str):
            return value
        if gaps:
            print("\n".join(gaps), file=sys.stderr)
    suffix = eval_dir.name.removeprefix("eval-")
    return int(suffix) if suffix.isdigit() else suffix or eval_idx


def _load_timing(result: dict, grading: dict, run_dir: Path) -> None:
    """Resolve each measurement independently, retaining its actual unit and carrier.

    timing.json is the runner-owned carrier. metrics.json is a legacy per-run
    spelling, not a shared eval-directory measurement. Grader timing is accepted
    when supplied. Conflicting carriers leave that metric unresolved.
    """
    gaps = result.setdefault("measurement_gaps", [])
    carriers = [("grading.json:timing", grading.get("timing", {}))]
    for filename in ("timing.json", "metrics.json"):
        path = run_dir / filename
        if path.exists():
            carriers.append((filename, _read_object(path, gaps)))
    provenance = result.setdefault("measurement_sources", {})
    for target, source, integer in (("time_seconds", "total_duration_seconds", False), ("tokens", "total_tokens", True)):
        observations = []
        invalid = False
        for name, data in carriers:
            if not isinstance(data, dict):
                gaps.append(f"{name}: expected an object")
                invalid = True
                continue
            value = data.get(source)
            if value is None:
                continue
            if not _number(value, integer=integer):
                gaps.append(f"{name}:{source}: invalid measurement {value!r}")
                invalid = True
            else:
                observations.append((name, value))
        values = {value for _, value in observations}
        if len(values) > 1:
            gaps.append(f"{target}: conflicting measurements {observations!r}")
        result[target] = next(iter(values)) if len(values) == 1 and not invalid else None
        provenance[target] = [name for name, _ in observations]


def _build_run_result(eval_id: int | str, run_number: int, grading: dict, grading_file: Path, run_dir: Path) -> dict:
    """Build a run record; unavailable grading and telemetry never become zero."""
    result: dict[str, Any] = {"eval_id": eval_id, "run_number": run_number, "measurement_gaps": []}
    summary = grading.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    for key in ("passed", "failed", "total"):
        value = summary.get(key)
        result[key] = value if _number(value, integer=True) else None
    counts_valid = (all(result[key] is not None for key in ("passed", "failed", "total"))
                    and result["total"] > 0 and result["passed"] + result["failed"] == result["total"])
    result["pass_rate"] = result["passed"] / result["total"] if counts_valid else None
    if not counts_valid:
        result["measurement_gaps"].append(f"{grading_file}: missing or inconsistent grading counts")
    _load_timing(result, grading, run_dir)
    metrics = grading.get("execution_metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    for target, source in (("tool_calls", "total_tool_calls"), ("errors", "errors_encountered"), ("output_chars", "output_chars")):
        value = metrics.get(source)
        result[target] = value if _number(value, integer=True) else None
        if value is not None and result[target] is None:
            result["measurement_gaps"].append(f"execution_metrics:{source}: invalid measurement {value!r}")
    expectations = grading.get("expectations", [])
    result["expectations"] = expectations if isinstance(expectations, list) else []
    notes = grading.get("user_notes_summary", {})
    result["notes"] = []
    if isinstance(notes, dict):
        for key in ("uncertainties", "needs_review", "workarounds"):
            if isinstance(notes.get(key), list):
                result["notes"].extend(notes[key])
    return result


def _load_config_runs(config_dir: Path, eval_id: int | str, results: dict[str, list]) -> None:
    """Retain every observed run directory, including missing grader returns."""
    runs = results.setdefault(config_dir.name, [])
    for run_dir in sorted(config_dir.glob("run-*")):
        if not run_dir.is_dir():
            continue
        suffix = run_dir.name.removeprefix("run-")
        if not suffix.isdigit():
            raise ValueError(f"invalid run directory identity: {run_dir}")
        gaps: list[str] = []
        grading_file = run_dir / "grading.json"
        grading = _read_object(grading_file, gaps)
        result = _build_run_result(eval_id, int(suffix), grading, grading_file, run_dir)
        result["measurement_gaps"].extend(gaps)
        runs.append(result)


def load_run_results(benchmark_dir: Path) -> dict[str, list]:
    """Load workspace or legacy records, preserving exact configuration names."""
    search_dir = benchmark_dir / "runs" if (benchmark_dir / "runs").is_dir() else benchmark_dir
    results: dict[str, list] = {}
    for eval_idx, eval_dir in enumerate(sorted(search_dir.glob("eval-*"))):
        if not eval_dir.is_dir():
            continue
        eval_id = _resolve_eval_id(eval_dir, eval_idx)
        for config_dir in sorted(eval_dir.iterdir()):
            if config_dir.is_dir() and next(config_dir.glob("run-*"), None) is not None:
                _load_config_runs(config_dir, eval_id, results)
    return results


def aggregate_results(results: dict) -> dict:
    """Report per-metric coverage; compare only complete matching observed arms."""
    stats = {config: {metric: calculate_stats([run.get(metric) for run in runs]) for metric in METRICS}
             for config, runs in results.items()}
    configs = list(results)
    delta = dict.fromkeys(METRICS)
    # The public convention is first configuration minus second configuration.
    # Never invent an absent baseline or compare different observed case/run sets.
    if len(configs) == 2:
        left, right = (results[config] for config in configs)
        left_keys = Counter((run["eval_id"], run["run_number"]) for run in left)
        right_keys = Counter((run["eval_id"], run["run_number"]) for run in right)
        if left and left_keys == right_keys and all(count == 1 for count in left_keys.values()):
            for metric, precision in (("pass_rate", 2), ("time_seconds", 1), ("tokens", 0)):
                a, b = (stats[config][metric] for config in configs)
                if a["missing"] == b["missing"] == 0:
                    delta[metric] = f"{a['mean'] - b['mean']:+.{precision}f}"
    return {**stats, "delta": delta}


def generate_benchmark(benchmark_dir: Path, skill_name: str = "", skill_path: str = "") -> dict:
    """Bind statistics to observed counts and distinguish unavailable measurements."""
    results = load_run_results(benchmark_dir)
    runs = [{"eval_id": run["eval_id"], "configuration": config, "run_number": run["run_number"],
             "result": {key: run.get(key) for key in (*METRICS, "passed", "failed", "total", "tool_calls", "errors", "output_chars")},
             "expectations": run["expectations"], "notes": run["notes"],
             "measurement_gaps": run["measurement_gaps"], "measurement_sources": run["measurement_sources"]}
            for config, records in results.items() for run in records]
    counts = Counter((run["eval_id"], run["configuration"]) for run in runs)
    uniform = set(counts.values())
    run_counts = [{"eval_id": eid, "configuration": config, "observed_runs": count}
                  for (eid, config), count in counts.items()]
    complete = bool(runs) and all(run["result"]["pass_rate"] is not None for run in runs)
    return {"metadata": {"skill_name": skill_name or "<skill-name>", "skill_path": skill_path or "<path/to/skill>",
                         "executor_model": "<model-name>", "analyzer_model": "<model-name>",
                         "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "evals_run": sorted({run["eval_id"] for run in runs}, key=str),
                         "runs_per_configuration": next(iter(uniform)) if len(uniform) == 1 else None,
                         "run_counts": run_counts, "coverage": "observed-directories-only",
                         "units": {"time_seconds": "seconds", "tokens": "tokens", "output_chars": "characters"},
                         "grading_status": "COMPLETE" if complete else "INCOMPLETE"},
            "runs": runs, "run_summary": aggregate_results(results), "notes": []}


def _display(stats: dict, metric: str) -> str:
    """Render unknown values as unknown, never as zero-cost measurements."""
    if stats.get("mean") is None:
        return f"N/A (observed {stats.get('observed', 0)}, missing {stats.get('missing', 0)})"
    scale, suffix = (100, "%") if metric == "pass_rate" else (1, "s" if metric == "time_seconds" else "")
    return (f"{stats['mean'] * scale:.2f}{suffix} ± {stats['stddev'] * scale:.2f}{suffix} "
            f"(n={stats.get('observed', '?')}, missing={stats.get('missing', '?')})")


def generate_markdown(benchmark: dict) -> str:
    """Render all observed configurations with measurement coverage and pairing limits."""
    metadata, summary = benchmark["metadata"], benchmark["run_summary"]
    configs = [key for key in summary if key != "delta"]
    lines = [f"# Skill Benchmark: {metadata['skill_name']}", "", f"**Model**: {metadata['executor_model']}",
             f"**Date**: {metadata['timestamp']}", f"**Grading**: {metadata.get('grading_status', 'UNKNOWN')}",
             "**Coverage**: observed run directories only; missing expected directories are not discoverable.", "",
             "## Observed repetitions", ""]
    for count in metadata.get("run_counts", []):
        lines.append(f"- Eval {count['eval_id']}, {count['configuration']}: {count['observed_runs']} observed run(s)")
    lines.extend(["", "## Summary", "", "| Metric | " + " | ".join(configs) + " | Delta |",
                  "|---|" + "---|" * (len(configs) + 1)])
    for metric in METRICS:
        cells = [_display(summary[config].get(metric, {}), metric) for config in configs]
        lines.append("| " + metric + " | " + " | ".join(cells) + " | " + (summary["delta"].get(metric) or "N/A") + " |")
    lines.extend(["", "Delta is first arm minus second, only for two complete matching observed case/run sets."])
    gaps = [f"Eval {run['eval_id']}/{run['configuration']}/run-{run['run_number']}: {gap}"
            for run in benchmark["runs"] for gap in run.get("measurement_gaps", [])]
    notes = [*benchmark.get("notes", []), *gaps]
    if notes:
        lines.extend(["", "## Notes", "", *(f"- {note}" for note in notes)])
    return "\n".join(lines)


def main() -> None:
    """Write JSON and Markdown artifacts, retaining the existing CLI arguments."""
    parser = argparse.ArgumentParser(description="Aggregate skill benchmark observations")
    parser.add_argument("benchmark_dir", type=Path)
    parser.add_argument("--skill-name", default="")
    parser.add_argument("--skill-path", default="")
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()
    try:
        if not args.benchmark_dir.is_dir():
            raise ValueError(f"directory not found: {args.benchmark_dir}")
        benchmark = generate_benchmark(args.benchmark_dir, args.skill_name, args.skill_path)
        output = args.output or args.benchmark_dir / "benchmark.json"
        output.write_text(json.dumps(benchmark, separators=(",", ":"), allow_nan=False), encoding="utf-8")
        output.with_suffix(".md").write_text(generate_markdown(benchmark), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps({"benchmark": str(output), "report": str(output.with_suffix('.md')),
                      "grading_status": benchmark["metadata"]["grading_status"]}))
    raise SystemExit(0 if benchmark["metadata"]["grading_status"] == "COMPLETE" else 2)


if __name__ == "__main__":
    main()
