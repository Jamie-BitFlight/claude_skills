#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic>=0.89.0", "ruamel-yaml>=0.19.1"]
#
# [tool.ty.environment]
# root = ["..", "."]
# ///
"""Optimize descriptions using training and candidate-selection observations.

Legacy test_* JSON keys name the selection set, not an untouched final test.
Incomplete execution is not a negative observation or an eligible candidate.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

import anthropic

if __package__:
    from .generate_report import generate_html
    from .improve_description import improve_description
    from .run_eval import find_project_root, run_eval, validate_eval_set
    from .utils import parse_skill_md
else:
    from generate_report import generate_html
    from improve_description import improve_description
    from run_eval import find_project_root, run_eval, validate_eval_set
    from utils import parse_skill_md


def split_eval_set(eval_set: list[dict], holdout: float, seed: int = 42) -> tuple[list[dict], list[dict]]:
    """Split unique cases without starving training or claiming an absent holdout.

    The seed preserves the prior reproducible split default, without mutating
    global RNG state. Singleton classes stay in training.
    """
    validate_eval_set(eval_set)
    if not math.isfinite(holdout) or not 0 <= holdout < 1:
        raise ValueError("holdout must be in [0, 1)")
    if holdout == 0:
        return list(eval_set), []
    rng = random.Random(seed)
    train, selection = [], []
    for label in (True, False):
        group = [item for item in eval_set if item["should_trigger"] is label]
        rng.shuffle(group)
        count = min(len(group) - 1, max(1, int(len(group) * holdout))) if len(group) > 1 else 0
        selection.extend(group[:count])
        train.extend(group[count:])
    if not train or not selection:
        raise ValueError("not enough cases for nonempty training and selection; add cases or use --holdout 0")
    return train, selection


def _summarize(results: list[dict]) -> dict:
    """Keep case failures and inconclusive observations separate."""
    return {
        "total": len(results),
        "passed": sum(r.get("pass") is True for r in results),
        "failed": sum(r.get("pass") is False for r in results),
        "inconclusive": sum(r.get("pass") is None for r in results),
    }


def _split_results(all_results: dict, train_set: list[dict]) -> tuple[dict, dict | None]:
    """Partition already-validated unique query identities for reporting."""
    train_queries = {item["query"] for item in train_set}
    train = [r for r in all_results["results"] if r["query"] in train_queries]
    selection = [r for r in all_results["results"] if r["query"] not in train_queries]
    return (
        {"results": train, "summary": _summarize(train)},
        {"results": selection, "summary": _summarize(selection)} if selection else None,
    )


def _build_history_entry(iteration: int, description: str, train_results: dict, test_results: dict | None) -> dict:
    """Retain legacy field names while making completeness an explicit gate."""
    entry = {"iteration": iteration, "description": description}
    for prefix, result in (("train", train_results), ("test", test_results)):
        entry[f"{prefix}_results"] = result["results"] if result else []
        for key in ("passed", "failed", "total", "inconclusive"):
            entry[f"{prefix}_{key}"] = result["summary"][key] if result else None
    entry.update(train_results["summary"])
    entry["results"] = train_results["results"]
    entry["complete"] = not (entry["train_inconclusive"] or entry["test_inconclusive"])
    return entry


def _compute_best(history: list[dict], test_set: list[dict]) -> tuple[dict | None, str]:
    """Select only fully observed candidates; a holdout used here is a selection set."""
    eligible = [
        h
        for h in history
        if h.get("complete") is True
        and h.get("train_total", 0) > 0
        and (not test_set or h.get("test_total", 0) == len(test_set))
    ]
    if not eligible:
        return None, "INCONCLUSIVE"
    prefix = "test" if test_set else "train"
    best = max(eligible, key=lambda h: h[f"{prefix}_passed"] / h[f"{prefix}_total"])
    return best, f"{best[f'{prefix}_passed']}/{best[f'{prefix}_total']}"


def _propose_description(**kwargs) -> str:
    """Open a provider client only after completed evidence actually needs improvement."""
    with anthropic.Anthropic() as client:
        return improve_description(client=client, **kwargs)


def run_loop(
    eval_set: list[dict],
    skill_path: Path,
    description_override: str | None,
    num_workers: int,
    timeout: int,
    max_iterations: int,
    runs_per_query: int,
    trigger_threshold: float,
    holdout: float,
    model: str,
    verbose: bool,
    live_report_path: Path | None = None,
    log_dir: Path | None = None,
) -> dict:
    """Run comparable iterations, retaining errors and selection provenance.

    No description is applied to the source skill. Selection proposes a candidate;
    any final generalization assessment belongs to a separate untouched case set.
    """
    train_set, test_set = split_eval_set(eval_set, holdout)
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    project_root = find_project_root()
    name, original_description, content = parse_skill_md(skill_path)
    current_description = description_override or original_description
    history = []
    exit_reason = "max_iterations"
    output = {}
    for iteration in range(1, max_iterations + 1):
        started = time.monotonic()
        result = run_eval(
            train_set + test_set,
            name,
            current_description,
            num_workers,
            timeout,
            project_root,
            runs_per_query,
            trigger_threshold,
            model,
        )
        # Missing/duplicate/unexpected case returns invalidate the comparison.
        expected = {item["query"] for item in eval_set}
        actual = [item["query"] for item in result["results"]]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError("evaluator returned a different case inventory")
        train, selection = _split_results(result, train_set)
        entry = _build_history_entry(iteration, current_description, train, selection)
        history.append(entry)
        if verbose:
            print(
                json.dumps({
                    "iteration": iteration,
                    "train": train["summary"],
                    "selection": selection["summary"] if selection else None,
                    "elapsed_seconds": time.monotonic() - started,
                }),
                file=sys.stderr,
            )
        best, score = _compute_best(history, test_set)
        output = {
            "original_description": original_description,
            "best_description": best["description"] if best else None,
            "best_iteration": best["iteration"] if best else None,
            "best_score": score,
            "best_train_score": f"{best['train_passed']}/{best['train_total']}" if best else None,
            "best_test_score": f"{best['test_passed']}/{best['test_total']}" if best and test_set else None,
            "final_description": current_description,
            "iterations_run": len(history),
            "holdout": holdout,
            "train_size": len(train_set),
            "test_size": len(test_set),
            "history": history,
            "holdout_role": "candidate-selection" if test_set else "none",
            "final_generalization_test": "NOT_RUN",
            "environment": result.get("environment", {}),
        }
        if live_report_path:
            live_report_path.write_text(generate_html(output, auto_refresh=True, skill_name=name), encoding="utf-8")
        if not entry["complete"]:
            exit_reason = "inconclusive_evaluation"
            break
        if train["summary"]["failed"] == 0:
            exit_reason = "training_complete"
            break
        if iteration == max_iterations:
            break
        # Selection observations are never fed to the description-writing model.
        blinded = [{k: v for k, v in item.items() if not k.startswith("test_") and k != "complete"} for item in history]
        current_description = _propose_description(
            skill_name=name,
            skill_content=content,
            current_description=current_description,
            eval_results=train,
            history=blinded,
            model=model,
            log_dir=log_dir,
            iteration=iteration,
        )
    output["exit_reason"] = exit_reason
    # Earlier complete results remain recorded after a later failed experiment,
    # but an incomplete comparison never supplies an actionable recommendation.
    if exit_reason == "inconclusive_evaluation":
        output.update(
            best_description=None,
            best_iteration=None,
            best_score="INCONCLUSIVE",
            best_train_score=None,
            best_test_score=None,
        )
    return output


def main() -> None:
    """Preserve CLI/report artifacts; exit nonzero when evidence is incomplete."""
    parser = argparse.ArgumentParser(description="Run description evaluation and improvement")
    parser.add_argument("--eval-set", required=True)
    parser.add_argument("--skill-path", required=True)
    parser.add_argument("--description", default=None)
    # Existing experiment defaults; these are budgets, not universal quality gates.
    parser.add_argument("--num-workers", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--runs-per-query", type=int, default=3)
    parser.add_argument("--trigger-threshold", type=float, default=0.5)
    parser.add_argument("--holdout", type=float, default=0.4, help="Candidate-selection fraction (0 disables)")
    parser.add_argument("--model", required=True)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--report", default="auto")
    parser.add_argument("--results-dir", default=None)
    args = parser.parse_args()
    report = None
    results_dir = None
    try:
        cases = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
        skill = Path(args.skill_path)
        # Validate inputs before creating artifacts or launching the browser/provider.
        split_eval_set(cases, args.holdout)
        parse_skill_md(skill)
        if args.report != "none":
            if args.report == "auto":
                with tempfile.NamedTemporaryFile(prefix="skill-description-", suffix=".html", delete=False) as file:
                    report = Path(file.name)
            else:
                report = Path(args.report)
            report.write_text(
                "<html><body>Evaluation starting<meta http-equiv='refresh' content='5'></body></html>", encoding="utf-8"
            )
            webbrowser.open(str(report))
        if args.results_dir:
            parent = Path(args.results_dir)
            parent.mkdir(parents=True, exist_ok=True)
            results_dir = Path(tempfile.mkdtemp(prefix=time.strftime("%Y-%m-%d_%H%M%S_"), dir=parent))
        output = run_loop(
            cases,
            skill,
            args.description,
            args.num_workers,
            args.timeout,
            args.max_iterations,
            args.runs_per_query,
            args.trigger_threshold,
            args.holdout,
            args.model,
            args.verbose,
            report,
            results_dir / "logs" if results_dir else None,
        )
        serialized = json.dumps(output, separators=(",", ":"), allow_nan=False)
        print(serialized)
        if results_dir:
            (results_dir / "results.json").write_text(serialized, encoding="utf-8")
        if report:
            html = generate_html(output, skill_name=skill.name)
            report.write_text(html, encoding="utf-8")
            if results_dir:
                (results_dir / "report.html").write_text(html, encoding="utf-8")
            print(f"Report: {report}", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc
    raise SystemExit(2 if output["exit_reason"] == "inconclusive_evaluation" else 0)


if __name__ == "__main__":
    main()
