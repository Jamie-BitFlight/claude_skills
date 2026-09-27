#!/usr/bin/env python3
"""Render description-selection evidence without treating missing runs as negatives.

The input's legacy test_* fields represent candidate selection, not an untouched
final generalization test. Only the producer's eligible candidate is highlighted.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

# Existing presentation bands, not acceptance gates.
SCORE_GOOD_THRESHOLD = 0.8
SCORE_OK_THRESHOLD = 0.5


def aggregate_runs(results: list[dict] | None) -> tuple[int, int]:
    """Count only valid behavioral observations, including correctly observed negatives."""
    correct = total = 0
    for result in results or []:
        valid = result.get("valid_runs", result.get("runs", 0) if result.get("pass") is not None else 0)
        triggers = result.get("triggers", 0)
        total += valid
        correct += triggers if result.get("should_trigger", True) else valid - triggers
    return correct, total


def score_class(correct: int, total: int) -> str:
    """Select presentation styling; zero observations never receive green styling."""
    if total > 0:
        if correct / total >= SCORE_GOOD_THRESHOLD:
            return "score-good"
        if correct / total >= SCORE_OK_THRESHOLD:
            return "score-ok"
    return "score-bad"


def _build_html_header(title_prefix: str, refresh_tag: str) -> str:
    """Retain the report's table layout with explicit evidence-state styling."""
    return (
        """<!DOCTYPE html>
<html><head><meta charset="utf-8">"""
        + refresh_tag
        + """
<title>"""
        + title_prefix
        + """Skill Description Optimization</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600&family=Lora:wght@400;500&display=swap" rel="stylesheet">
<style>
body { font-family: 'Lora', Georgia, serif; max-width:100%; margin:0 auto; padding:20px; background:#faf9f5; color:#141413; }
h1, th, .legend { font-family:'Poppins',sans-serif; }
.explainer, .summary { background:white; padding:15px; border-radius:6px; margin-bottom:20px; border:1px solid #e8e6dc; }
.explainer { font-size:.875rem; line-height:1.6; }
.summary p { margin:5px 0; }
.best { color:#788c5d; font-weight:bold; }
.table-container { overflow-x:auto; width:100%; }
table { border-collapse:collapse; background:white; border:1px solid #e8e6dc; border-radius:6px; font-size:12px; min-width:100%; }
th,td { padding:8px; text-align:left; border:1px solid #e8e6dc; white-space:normal; overflow-wrap:anywhere; }
th { background:#141413; color:#faf9f5; font-weight:500; }
th.test-col { background:#6a9bcc; }
th.query-col { min-width:200px; }
td.description { font-family:monospace; font-size:11px; max-width:400px; }
td.result { text-align:center; font-size:16px; min-width:40px; }
td.test-result { background:#f0f6fc; }
.pass { color:#788c5d; } .fail { color:#c44; } .inconclusive { color:#946200; }
.rate { font-size:11px; display:block; }
.score { display:inline-block; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px; }
.score-good { background:#eef2e8; color:#788c5d; } .score-ok { background:#fef3c7; color:#946200; } .score-bad { background:#fceaea; color:#c44; }
.best-row { background:#f5f8f2; }
th.positive-col { border-bottom:3px solid #788c5d; } th.negative-col { border-bottom:3px solid #c44; }
.legend { display:flex; gap:20px; margin-bottom:10px; font-size:13px; }
pre { white-space:pre-wrap; text-align:left; font-size:12px; }
</style></head><body><h1>"""
        + title_prefix
        + """Skill Description Optimization</h1>
<div class="explainer">Training cases guide description changes. Selection cases choose among candidates;
the legacy <code>test_*</code> fields do not represent an untouched final test.
Scores count valid observations only. INCONCLUSIVE cases retain execution failures and cannot pass
or qualify a candidate for selection. A matching invocation does not prove successful skill execution.
The report does not apply a description to the skill.</div>
"""
    )


def _build_summary_section(data: dict, best_test_score: object) -> str:
    """Keep unavailable candidate and final-test evidence visible."""
    original = html.escape(str(data.get("original_description") or "N/A"))
    best = html.escape(str(data.get("best_description") or "No eligible candidate"))
    score = html.escape(str(data.get("best_score") or "INCONCLUSIVE"))
    role = "selection" if best_test_score is not None else "training"
    reason = html.escape(str(data.get("exit_reason", "in progress")))
    final = html.escape(str(data.get("final_generalization_test", "NOT_RUN")))
    return f"""<div class="summary">
<p><strong>Original:</strong> {original}</p><p class="best"><strong>Candidate:</strong> {best}</p>
<p><strong>Score:</strong> {score} ({role})</p><p><strong>Exit:</strong> {reason}</p>
<p><strong>Final generalization test:</strong> {final}</p>
<p>Iterations: {data.get("iterations_run", 0)} | Training: {data.get("train_size", "?")} | Selection: {data.get("test_size", "?")}</p>
</div>"""


def _build_table_header_cols(train_queries: list[dict], test_queries: list[dict]) -> list[str]:
    """Preserve per-query polarity and distinct selection columns."""
    cells = []
    for group, extra in ((train_queries, ""), (test_queries, "test-col ")):
        for query in group:
            polarity = "positive-col" if query["should_trigger"] else "negative-col"
            cells.append(f'<th class="{extra}{polarity}">{html.escape(query["query"])}</th>')
    return cells


def _result_cell(result: dict, extra_class: str = "") -> str:
    """Render incomplete observations separately from observed behavioral failures."""
    passed = result.get("pass")
    label, css = (
        ("✓", "pass") if passed is True else (("✗", "fail") if passed is False else ("INCONCLUSIVE", "inconclusive"))
    )
    attempted = result.get("runs", 0)
    valid = result.get("valid_runs", attempted if passed is not None else 0)
    errors = result.get("errors", attempted - valid)
    details = ""
    if errors:
        raw = html.escape(json.dumps(result.get("observations", []), ensure_ascii=False))
        details = f"<details><summary>Execution evidence</summary><pre>{raw}</pre></details>"
    return (
        f'<td class="result {extra_class} {css}">{label}<span class="rate">'
        f"{result.get('triggers', 0)}/{valid} valid; {attempted} attempted; {errors} errors</span>{details}</td>"
    )


def _build_iteration_row(
    history: dict, train_queries: list[dict], test_queries: list[dict], best_iter: object
) -> list[str]:
    """Use the producer's candidate identity, not a second selection algorithm."""
    train = history.get("train_results", history.get("results", [])) or []
    selection = history.get("test_results") or []
    train_by_query = {item["query"]: item for item in train}
    selection_by_query = {item["query"]: item for item in selection}
    row_class = "best-row" if best_iter is not None and history.get("iteration") == best_iter else ""
    complete = history.get("complete") is True
    cells = [
        f'<tr class="{row_class}"><td>{history.get("iteration", "?")}' + ("" if complete else " INCOMPLETE") + "</td>"
    ]
    for group in (train, selection):
        correct, total = aggregate_runs(group)
        cells.append(f'<td><span class="score {score_class(correct, total)}">{correct}/{total} valid</span></td>')
    cells.append(f'<td class="description">{html.escape(history.get("description", ""))}</td>')
    cells.extend(_result_cell(train_by_query.get(query["query"], {})) for query in train_queries)
    cells.extend(_result_cell(selection_by_query.get(query["query"], {}), "test-result") for query in test_queries)
    cells.append("</tr>")
    return cells


def generate_html(data: dict, auto_refresh: bool = False, skill_name: str = "") -> str:
    """Render empty, partial and complete histories without manufacturing a winner."""
    history = data.get("history", [])
    first = history[0] if history else {}
    train = first.get("train_results", first.get("results", [])) or []
    selection = first.get("test_results") or []
    title = html.escape(skill_name + " — ") if skill_name else ""
    # Retain the existing five-second live-display refresh, not an evaluation budget.
    refresh = '<meta http-equiv="refresh" content="5">' if auto_refresh else ""
    parts = [
        _build_html_header(title, refresh),
        _build_summary_section(data, data.get("best_test_score")),
        '<div class="legend">Green underline: should trigger. Red: should not trigger. Blue columns: selection.</div>',
        '<div class="table-container"><table><thead><tr><th>Iter</th><th>Training</th><th>Selection</th><th class="query-col">Description</th>',
        *_build_table_header_cols(train, selection),
        "</tr></thead><tbody>",
    ]
    for entry in history:
        parts.extend(_build_iteration_row(entry, train, selection, data.get("best_iteration")))
    parts.extend(["</tbody></table></div></body></html>"])
    return "".join(parts)


def main() -> None:
    """Render JSON input from a file or stdin using the existing CLI interface."""
    parser = argparse.ArgumentParser(description="Generate HTML report from run_loop output")
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--skill-name", default="")
    args = parser.parse_args()
    data = json.load(sys.stdin) if args.input == "-" else json.loads(Path(args.input).read_text(encoding="utf-8"))
    rendered = generate_html(data, skill_name=args.skill_name)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(rendered)


if __name__ == "__main__":
    main()
