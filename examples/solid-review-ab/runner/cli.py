#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21"]
# ///
"""SOLID A/B experiment runner CLI.

Subcommands
-----------
plan       Run plan_ensemble.py over the ruleset (deterministic, free).
score      Score one or both arms against gold.json (pure, no LLM calls).
run-arm-a  Dispatch the live single-Sonnet arm (costs tokens).
run-arm-b  Dispatch the live multi-Haiku ensemble arm (costs tokens).
all        plan -> run-arm-a -> run-arm-b -> score.

Both arms use the IDENTICAL claude -p call.  The divergence (single-agent vs
ensemble) lives in each arm's .claude/skills/review-against-solid-principles/
SKILL.md, not in this Python module.

Run from the experiment root or repo root.  The runner locates all files
relative to this script's parent directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# sys.path bootstrap — ensures the runner package is importable when cli.py is
# invoked as a script (uv run runner/cli.py) from any working directory.
#
# uv run adds the script's own directory (runner/) to sys.path, not its parent.
# The runner package lives at examples/solid-review-ab/runner/, so its parent
# — examples/solid-review-ab/ — must be on sys.path for `from runner.X import`
# to resolve.  Path(__file__).parent.parent is that parent regardless of cwd.
# ---------------------------------------------------------------------------
_PACKAGE_ROOT = Path(__file__).parent.parent
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

if TYPE_CHECKING:
    from runner.scorer import ArmMetrics

from runner.dispatch import run_arm_a, run_arm_b
from runner.gold_loader import decoy_keys, load_gold, positive_keys
from runner.scorer import score_arm_a, score_arm_b

# ---------------------------------------------------------------------------
# Path constants — all resolved relative to the experiment root so the CLI
# works regardless of cwd.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_EXPERIMENT_ROOT = _HERE.parent
_PROMPT_PATH = _EXPERIMENT_ROOT / "PROMPT.md"
_GOLD_PATH = _EXPERIMENT_ROOT / "corpus" / "gold.json"
_RULESET_PATH = _EXPERIMENT_ROOT / "ruleset" / "solid-rules.json"
_ARM_A_DIR = _EXPERIMENT_ROOT / "single-high-intelligence-agent"
_ARM_B_DIR = _EXPERIMENT_ROOT / "multi-low-intelligence-focused-agents"
_PLAN_ENSEMBLE = (
    Path(__file__).parents[3]
    / "plugins"
    / "plugin-creator"
    / "skills"
    / "ensemble-rule-review"
    / "scripts"
    / "plan_ensemble.py"
)

# Decoy weight at or above this threshold indicates corroboration is boosting a shared error.
_CORROBORATION_RISK_THRESHOLD = 2

app = typer.Typer(name="solid-ab", help="Runner and scorer for the SOLID A/B review experiment.", no_args_is_help=True)
console = Console()


# ---------------------------------------------------------------------------
# plan subcommand
# ---------------------------------------------------------------------------


@app.command()
def plan(
    window: Annotated[int, typer.Option(help="Rotating overlap window (groups per worker).")] = 2,
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON plan.")] = False,
    report_dir: Annotated[
        Path, typer.Option(help="Absolute directory for worker OUTFILE paths (default: arm B directory).")
    ] = _ARM_B_DIR,
) -> None:
    """Run plan_ensemble.py over the SOLID ruleset (deterministic, free).

    Prints the rotating-overlap worker plan: which SOLID groups each worker
    covers, uniform redundancy check, and recommended keep-threshold.
    """
    if not _PLAN_ENSEMBLE.is_file():
        console.print(f"[red]plan_ensemble.py not found at {_PLAN_ENSEMBLE}[/red]")
        raise typer.Exit(code=1)
    if not _RULESET_PATH.is_file():
        console.print(f"[red]solid-rules.json not found at {_RULESET_PATH}[/red]")
        raise typer.Exit(code=1)

    cmd = [
        sys.executable,
        str(_PLAN_ENSEMBLE),
        str(_RULESET_PATH),
        "--report-dir",
        str(report_dir.resolve()),
        "--window",
        str(window),
    ]
    if as_json:
        cmd.append("--json")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        console.print(f"[red]plan_ensemble.py failed:[/red]\n{result.stderr}")
        raise typer.Exit(code=result.returncode)

    console.print(result.stdout)


# ---------------------------------------------------------------------------
# score subcommand
# ---------------------------------------------------------------------------


@app.command()
def score(
    arm_a_dir: Annotated[Path, typer.Option(help="Arm A root directory (contains findings/findings.md).")] = _ARM_A_DIR,
    arm_b_dir: Annotated[
        Path, typer.Option(help="Arm B root directory (contains findings/workers/ and findings/findings.md).")
    ] = _ARM_B_DIR,
    gold: Annotated[Path, typer.Option(help="Path to gold.json.")] = _GOLD_PATH,
    arm: Annotated[str, typer.Option(help="Which arm(s) to score: 'a', 'b', or 'both'.")] = "both",
) -> None:
    """Score arm A and/or B against gold.json (pure — no LLM calls).

    Computes Precision/Recall/F1 on (group, normalised_location) for
    true_violation and systematic_miss gold entries; decoy false-positive rate;
    per-decoy corroboration weight for arm B (E0 diagnostic); and E1 ablation
    (F1 at keep_threshold=1 vs 2).

    Both arms are scored from their findings/findings.md.  Arm B also reads
    findings/workers/worker-*.md for the E0/E1 diagnostics.

    Requires arms to have run first (run-arm-a / run-arm-b).
    """
    if not gold.is_file():
        console.print(f"[red]gold.json not found: {gold}[/red]")
        raise typer.Exit(code=1)

    gold_entries = load_gold(gold)
    pos_keys = positive_keys(gold_entries)
    dec_keys = decoy_keys(gold_entries)

    console.print(
        Panel(
            f"Gold positives (true+systematic): [bold]{len(pos_keys)}[/bold]   Decoys: [bold]{len(dec_keys)}[/bold]",
            title=":microscope: SOLID A/B Experiment — Score Report",
        )
    )

    if arm in {"a", "both"}:
        _score_arm_a(arm_a_dir, pos_keys, dec_keys)

    if arm in {"b", "both"}:
        _score_arm_b(arm_b_dir, pos_keys, dec_keys)


def _score_arm_a(arm_dir: Path, pos_keys: set[tuple[str, str]], dec_keys: set[tuple[str, str]]) -> None:
    """Score arm A from its consolidated findings file and render results.

    Args:
        arm_dir: Arm A root directory.
        pos_keys: Gold positive (group, location) keys.
        dec_keys: Gold decoy (group, location) keys.
    """
    findings_path = arm_dir / "findings" / "findings.md"
    if not findings_path.is_file():
        console.print(f"[yellow]Arm A: findings not found: {findings_path}[/yellow]")
        return

    metrics, warnings = score_arm_a(findings_path, pos_keys, dec_keys)
    for w in warnings:
        console.print(f"[yellow]{w}[/yellow]")
    _render_arm_metrics("A — Single Sonnet", metrics)


def _score_arm_b(arm_dir: Path, pos_keys: set[tuple[str, str]], dec_keys: set[tuple[str, str]]) -> None:
    """Score arm B ensemble from worker reports and render results.

    Reads worker files from findings/workers/ for the E1/E0 diagnostics.

    Args:
        arm_dir: Arm B root directory.
        pos_keys: Gold positive (group, location) keys.
        dec_keys: Gold decoy (group, location) keys.
    """
    workers_dir = arm_dir / "findings" / "workers"
    if not workers_dir.is_dir():
        console.print(f"[yellow]Arm B: workers directory not found: {workers_dir}[/yellow]")
        return

    try:
        metrics, extras, warnings = score_arm_b(workers_dir, pos_keys, dec_keys, glob="worker-*.md")
    except ValueError as exc:
        console.print(f"[yellow]Arm B: {exc}[/yellow]")
        return

    for w in warnings:
        console.print(f"[yellow]{w}[/yellow]")

    _render_arm_metrics("B — Multi-Haiku Ensemble (keep_threshold=2)", metrics)

    # E1 ablation table
    e1_table = Table(title=":bar_chart: E1 Ablation — Corroboration Weighting", show_lines=True)
    e1_table.add_column("keep_threshold", style="cyan")
    e1_table.add_column("F1", style="green")
    e1_table.add_row("1 (dedup only)", f"{extras.f1_at_threshold_1:.3f}")
    e1_table.add_row("2 (corroboration gate)", f"{extras.f1_at_threshold_2:.3f}")
    e1_table.add_row("delta (threshold=2 minus 1)", f"{extras.f1_delta:+.3f}")
    console.print(e1_table)

    if extras.per_decoy_weight:
        decoy_table = Table(title=":warning: E0 — Per-Decoy Corroboration Weight", show_lines=True)
        decoy_table.add_column("Decoy (group, location)", style="yellow")
        decoy_table.add_column("Workers that flagged it", style="red")
        decoy_table.add_column("Risk", style="bold")
        for (grp, loc), weight in sorted(extras.per_decoy_weight.items()):
            risk = "HIGH — boosted false positive" if weight >= _CORROBORATION_RISK_THRESHOLD else "low"
            decoy_table.add_row(f"({grp}, {loc})", str(weight), risk)
        console.print(decoy_table)
    else:
        console.print("[green]:white_check_mark: No decoys flagged by arm B workers.[/green]")


def _render_arm_metrics(arm_label: str, metrics: ArmMetrics) -> None:
    """Render a Rich table of precision/recall/F1 and FP rate for one arm.

    Args:
        arm_label: Display label for the arm.
        metrics: ArmMetrics dataclass instance.
    """
    table = Table(title=f":scales: Arm {arm_label}", show_lines=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")
    table.add_row("True Positives", str(metrics.true_positives))
    table.add_row("False Positives", str(metrics.false_positives))
    table.add_row("False Negatives", str(metrics.false_negatives))
    table.add_row("Precision", f"{metrics.precision:.3f}")
    table.add_row("Recall", f"{metrics.recall:.3f}")
    table.add_row("F1", f"{metrics.f1:.3f}")
    table.add_row("Decoys flagged (of total)", f"{metrics.decoys_flagged} / {metrics.total_gold_decoys}")
    table.add_row("Decoy FP rate", f"{metrics.decoy_false_positive_rate:.3f}")
    if metrics.latency_ms:
        table.add_row("Latency (ms)", f"{metrics.latency_ms:.0f}")
    if metrics.cost_usd:
        table.add_row("Cost (USD)", f"${metrics.cost_usd:.4f}")
    console.print(table)


# ---------------------------------------------------------------------------
# run-arm-a subcommand
# ---------------------------------------------------------------------------


@app.command(name="run-arm-a")
def run_arm_a_cmd(arm_dir: Annotated[Path, typer.Option(help="Arm A root directory.")] = _ARM_A_DIR) -> None:
    """Dispatch arm A: the arm's SKILL.md runs the single-Sonnet review (costs tokens).

    The arm writes findings to arm_dir/findings/findings.md.
    Run `score` afterwards to compute metrics.

    PROMPT.md is read at runtime from the experiment root.  All model selection,
    corpus paths, and schema are governed by the arm's .claude/ SKILL.md.
    """
    if not _PROMPT_PATH.is_file():
        console.print(f"[red]PROMPT.md not found: {_PROMPT_PATH}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Arm A: dispatching claude -p (cwd={arm_dir}) ...[/cyan]")
    result = run_arm_a(arm_dir)

    console.print(
        f"[green]Arm A complete.[/green]  Files: {len(result.findings_paths)}  "
        f"Cost: ${result.cost_usd:.4f}  Latency: {result.duration_ms:.0f}ms"
    )
    if result.errors:
        for err in result.errors:
            console.print(f"[red]  ERROR: {err}[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# run-arm-b subcommand
# ---------------------------------------------------------------------------


@app.command(name="run-arm-b")
def run_arm_b_cmd(arm_dir: Annotated[Path, typer.Option(help="Arm B root directory.")] = _ARM_B_DIR) -> None:
    """Dispatch arm B: the arm's SKILL.md runs the ensemble review (costs tokens).

    The arm writes findings to arm_dir/findings/findings.md and worker files
    to arm_dir/findings/workers/.
    Run `score` afterwards to compute metrics.

    PROMPT.md is read at runtime from the experiment root.  All model selection,
    fan-out, reduce step, and schema are governed by the arm's .claude/ SKILL.md.
    """
    if not _PROMPT_PATH.is_file():
        console.print(f"[red]PROMPT.md not found: {_PROMPT_PATH}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Arm B: dispatching claude -p (cwd={arm_dir}) ...[/cyan]")
    result = run_arm_b(arm_dir)

    console.print(
        f"[green]Arm B complete.[/green]  Files: {len(result.findings_paths)}  "
        f"Cost: ${result.cost_usd:.4f}  Latency: {result.duration_ms:.0f}ms"
    )
    if result.errors:
        for err in result.errors:
            console.print(f"[red]  ERROR: {err}[/red]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# all subcommand
# ---------------------------------------------------------------------------


@app.command(name="all")
def run_all() -> None:
    """Run the full experiment: plan -> arm A -> arm B -> score (costs tokens).

    Executes all four stages in order and prints the complete score report.
    """
    console.print(Panel(":rocket: Running full SOLID A/B experiment", title="solid-ab all"))

    # Stage 1: plan (informational — always runs)
    plan(window=2, as_json=False, report_dir=_ARM_B_DIR)

    # Stage 2: arm A
    run_arm_a_cmd(arm_dir=_ARM_A_DIR)

    # Stage 3: arm B
    run_arm_b_cmd(arm_dir=_ARM_B_DIR)

    # Stage 4: score both arms
    score(arm_a_dir=_ARM_A_DIR, arm_b_dir=_ARM_B_DIR, gold=_GOLD_PATH, arm="both")


if __name__ == "__main__":
    app()
