#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21", "ruamel.yaml>=0.18"]
# ///
"""SOLID judgement system runner CLI.

Subcommands
-----------
plan   Run plan_ensemble.py over the ruleset (deterministic, free).
score  Score all enabled arms against gold.json; emit payoff-per-cost ranking.
run    Dispatch every enabled arm from the manifest (costs tokens).
all    plan -> run -> score.

Arms are declared in arms.yaml at the experiment root.  Each arm is a directory
with its own .claude/ configuration.  Adding a new arm = new directory + manifest
entry.  No Python code change required.

Run from the experiment root or repo root.  The runner locates all files
relative to this script's parent directory.
"""

from __future__ import annotations

import json
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
    from runner.manifest import ArmEntry
    from runner.scorer import ArmMetrics

from runner.cost import TokenUsage, compute_cost
from runner.dispatch import run_arm
from runner.gold_loader import decoy_keys, load_gold, positive_keys
from runner.manifest import ArmType, load_manifest
from runner.scorer import ArmBExtras, ArmRanking, rank_arms, score_arm_a, score_arm_b

# ---------------------------------------------------------------------------
# Path constants — all resolved relative to the experiment root so the CLI
# works regardless of cwd.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_EXPERIMENT_ROOT = _HERE.parent
_PROMPT_PATH = _EXPERIMENT_ROOT / "PROMPT.md"
_GOLD_PATH = _EXPERIMENT_ROOT / "corpus" / "gold.json"
_RULESET_PATH = _EXPERIMENT_ROOT / "ruleset" / "solid-rules.json"
_MANIFEST_PATH = _EXPERIMENT_ROOT / "arms.yaml"
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

app = typer.Typer(
    name="solid-ab",
    help="Runner and scorer for the SOLID judgement system (N-arm manifest-driven).",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------------------
# plan subcommand
# ---------------------------------------------------------------------------


@app.command()
def plan(
    window: Annotated[int, typer.Option(help="Rotating overlap window (groups per worker).")] = 2,
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON plan.")] = False,
    report_dir: Annotated[
        Path, typer.Option(help="Directory for worker OUTFILE paths (default: first ensemble arm directory).")
    ] = _EXPERIMENT_ROOT / "multi-low-intelligence-focused-agents",
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
# run subcommand — manifest-driven N-arm dispatch
# ---------------------------------------------------------------------------


@app.command(name="run")
def run_arms(manifest: Annotated[Path, typer.Option(help="Path to arms.yaml manifest.")] = _MANIFEST_PATH) -> None:
    """Dispatch every enabled arm from the manifest (costs tokens).

    Each arm runs the IDENTICAL claude -p invocation with cwd set to the arm
    directory.  The arm's .claude/SKILL.md governs model selection and procedure.

    After each arm completes, findings/run-meta.json is written so the score
    command can compute deterministic costs from the manifest price table.
    """
    if not _PROMPT_PATH.is_file():
        console.print(f"[red]PROMPT.md not found: {_PROMPT_PATH}[/red]")
        raise typer.Exit(code=1)

    mf = load_manifest(manifest)
    arms = mf.enabled_arms()
    if not arms:
        console.print("[yellow]No enabled arms in manifest.[/yellow]")
        raise typer.Exit(code=0)

    console.print(Panel(f":rocket: Running {len(arms)} arm(s) from {manifest.name}", title="solid-ab run"))

    failed = False
    for arm in arms:
        console.print(f"[cyan]  {arm.name}: dispatching (cwd={arm.dir}) ...[/cyan]")
        result = run_arm(arm.dir)
        console.print(
            f"  [green]{arm.name} complete.[/green]  "
            f"Files: {len(result.findings_paths)}  "
            f"Reported cost: ${result.reported_cost_usd:.4f}  "
            f"Latency: {result.duration_ms:.0f}ms"
        )
        if result.errors:
            for err in result.errors:
                console.print(f"    [red]ERROR: {err}[/red]")
            failed = True

    if failed:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# score subcommand — manifest-driven N-arm scoring + payoff-per-cost ranking
# ---------------------------------------------------------------------------


@app.command()
def score(
    manifest: Annotated[Path, typer.Option(help="Path to arms.yaml manifest.")] = _MANIFEST_PATH,
    gold: Annotated[Path, typer.Option(help="Path to gold.json.")] = _GOLD_PATH,
) -> None:
    """Score all enabled arms and emit a payoff-per-cost ranking (pure, no LLM calls).

    For each arm:
      - Reads findings/findings.md for P/R/F1.
      - Reads findings/run-meta.json for token counts and timing (written by run).
      - Computes cost deterministically from the manifest price table.

    Emits individual arm metric tables, then a ranked comparison across all arms.
    Payoff-per-cost = (F1 gain over the lowest-cost arm) / cost_usd.
    """
    if not gold.is_file():
        console.print(f"[red]gold.json not found: {gold}[/red]")
        raise typer.Exit(code=1)

    mf = load_manifest(manifest)
    arms = mf.enabled_arms()
    if not arms:
        console.print("[yellow]No enabled arms in manifest.[/yellow]")
        raise typer.Exit(code=0)

    gold_entries = load_gold(gold)
    pos_keys = positive_keys(gold_entries)
    dec_keys = decoy_keys(gold_entries)

    console.print(
        Panel(
            f"Gold positives (true+systematic): [bold]{len(pos_keys)}[/bold]   Decoys: [bold]{len(dec_keys)}[/bold]",
            title=":microscope: SOLID Judgement System — Score Report",
        )
    )

    scored: list[tuple[str, ArmMetrics]] = []
    b_arm_extras: dict[str, object] = {}

    for arm in arms:
        arm_metrics = _score_arm(arm, pos_keys, dec_keys, mf.prices, b_arm_extras)
        if arm_metrics is not None:
            scored.append((arm.name, arm_metrics))

    if not scored:
        console.print("[yellow]No arms produced scoreable findings.[/yellow]")
        raise typer.Exit(code=0)

    # Render arm-B-specific E1/E0 diagnostics
    for arm_name, extras in b_arm_extras.items():
        _render_arm_b_extras(arm_name, extras)

    # Judgement ranking table
    rankings = rank_arms(scored)
    _render_ranking_table(rankings)


def _load_run_meta(arm_dir: Path) -> dict[str, float | int]:
    """Load findings/run-meta.json written by the run command.

    Args:
        arm_dir: Arm root directory.

    Returns:
        Dict with keys input_tokens, output_tokens, duration_ms,
        total_cost_usd_reported.  Returns all-zeros dict when file absent.
    """
    meta_path = arm_dir / "findings" / "run-meta.json"
    if not meta_path.is_file():
        return {"input_tokens": 0, "output_tokens": 0, "duration_ms": 0.0, "total_cost_usd_reported": 0.0}
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "input_tokens": int(raw.get("input_tokens", 0)),
        "output_tokens": int(raw.get("output_tokens", 0)),
        "duration_ms": float(raw.get("duration_ms", 0.0)),
        "total_cost_usd_reported": float(raw.get("total_cost_usd_reported", 0.0)),
    }


def _score_arm(
    arm: ArmEntry, pos_keys: set[tuple[str, str]], dec_keys: set[tuple[str, str]], prices: dict, b_arm_extras_out: dict
) -> ArmMetrics | None:
    """Score one arm and render its individual metrics table.

    Reads run-meta.json to populate latency and cost fields on ArmMetrics.
    Selects the scoring path from arm.arm_type (declared in arms.yaml) — never
    inferred from the filesystem so a failed run that leaves an empty directory
    is caught explicitly rather than falling through silently.

    Args:
        arm: ArmEntry from the manifest.
        pos_keys: Gold positive (group, location) keys.
        dec_keys: Gold decoy (group, location) keys.
        prices: Manifest price table (model id -> ModelPrice).
        b_arm_extras_out: Output dict — populated with ArmBExtras when the arm
            uses the ensemble pattern (for later rendering).

    Returns:
        Populated ArmMetrics with cost/latency set, or None when findings absent.
    """
    meta = _load_run_meta(arm.dir)
    latency_ms = float(meta["duration_ms"])

    # Compute deterministic cost from manifest prices using primary model.
    cost_usd = 0.0
    if arm.models:
        primary_model_id = arm.models[0].id
        usage = TokenUsage(
            input_tokens=int(meta["input_tokens"]), output_tokens=int(meta["output_tokens"]), model_id=primary_model_id
        )
        cost_usd = compute_cost(usage, prices)

    if arm.arm_type is ArmType.ENSEMBLE:
        workers_dir = arm.dir / "findings" / "workers"
        if not workers_dir.is_dir():
            console.print(
                f"[yellow]{arm.name}: ensemble arm declared but workers/ directory not found at {workers_dir}[/yellow]"
            )
            return None
        try:
            metrics, extras, warnings = score_arm_b(workers_dir, pos_keys, dec_keys, glob="worker-*.md")
        except ValueError as exc:
            console.print(f"[yellow]{arm.name}: {exc}[/yellow]")
            return None
        for w in warnings:
            console.print(f"[yellow]{w}[/yellow]")
        metrics.latency_ms = latency_ms
        metrics.cost_usd = cost_usd
        b_arm_extras_out[arm.name] = extras
    elif arm.arm_type is ArmType.SINGLE:
        findings_path = arm.dir / "findings" / "findings.md"
        if not findings_path.is_file():
            console.print(f"[yellow]{arm.name}: findings not found: {findings_path}[/yellow]")
            return None
        metrics, warnings = score_arm_a(findings_path, pos_keys, dec_keys)
        for w in warnings:
            console.print(f"[yellow]{w}[/yellow]")
        metrics.latency_ms = latency_ms
        metrics.cost_usd = cost_usd
    else:
        raise ValueError(f"Unrecognised arm_type: {arm.arm_type!r}")

    _render_arm_metrics(arm.name, metrics)
    return metrics


def _render_arm_b_extras(arm_name: str, extras: object) -> None:
    """Render E1 ablation and E0 per-decoy weight tables for one ensemble arm.

    Args:
        arm_name: Display label for the arm.
        extras: ArmBExtras instance from score_arm_b.
    """
    if not isinstance(extras, ArmBExtras):
        return

    e1_table = Table(title=f":bar_chart: E1 Ablation — {arm_name}", show_lines=True)
    e1_table.add_column("keep_threshold", style="cyan")
    e1_table.add_column("F1", style="green")
    e1_table.add_row("1 (dedup only)", f"{extras.f1_at_threshold_1:.3f}")
    e1_table.add_row("2 (corroboration gate)", f"{extras.f1_at_threshold_2:.3f}")
    e1_table.add_row("delta (threshold=2 minus 1)", f"{extras.f1_delta:+.3f}")
    console.print(e1_table)

    if extras.per_decoy_weight:
        decoy_table = Table(title=f":warning: E0 — Per-Decoy Corroboration Weight ({arm_name})", show_lines=True)
        decoy_table.add_column("Decoy (group, location)", style="yellow")
        decoy_table.add_column("Workers that flagged it", style="red")
        decoy_table.add_column("Risk", style="bold")
        for (grp, loc), weight in sorted(extras.per_decoy_weight.items()):
            risk = "HIGH — boosted false positive" if weight >= _CORROBORATION_RISK_THRESHOLD else "low"
            decoy_table.add_row(f"({grp}, {loc})", str(weight), risk)
        console.print(decoy_table)
    else:
        console.print(f"[green]:white_check_mark: No decoys flagged by {arm_name} workers.[/green]")


def _render_arm_metrics(arm_label: str, metrics: ArmMetrics) -> None:
    """Render a Rich table of precision/recall/F1 and FP rate for one arm.

    Args:
        arm_label: Display label for the arm.
        metrics: ArmMetrics dataclass instance.
    """
    table = Table(title=f":scales: {arm_label}", show_lines=True)
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
        table.add_row("Cost (USD)", f"${metrics.cost_usd:.6f}")
    console.print(table)


def _render_ranking_table(rankings: list[ArmRanking]) -> None:
    """Render the judgement system payoff-per-cost comparison table.

    Args:
        rankings: Sorted list from rank_arms (rank 1 = best payoff-per-cost).
    """
    table = Table(title=":trophy: Judgement System — Payoff-per-Cost Ranking", show_lines=True)
    table.add_column("Rank", style="bold yellow")
    table.add_column("Arm", style="cyan")
    table.add_column("F1", style="green")
    table.add_column("Cost (USD)", style="magenta")
    table.add_column("Payoff / Cost", style="bold")
    table.add_column("Note", style="dim")

    for r in rankings:
        ppc_str = f"{r.payoff_per_cost:.4f}" if r.payoff_per_cost is not None else "N/A"
        if r.payoff_per_cost is None:
            note = "no cost data"
        elif not r.payoff_per_cost:
            note = "baseline"
        elif r.payoff_per_cost < 0:
            note = "worse than baseline"
        else:
            note = ""
        cost_str = f"${r.metrics.cost_usd:.6f}" if r.metrics.cost_usd else "---"
        table.add_row(str(r.rank), r.arm_name, f"{r.metrics.f1:.3f}", cost_str, ppc_str, note)

    console.print(table)
    console.print(
        "[dim]Payoff-per-cost = (F1 - baseline_F1) / cost_usd. Baseline = lowest-cost arm. Higher is better.[/dim]"
    )


# ---------------------------------------------------------------------------
# all subcommand
# ---------------------------------------------------------------------------


@app.command(name="all")
def run_all(
    manifest: Annotated[Path, typer.Option(help="Path to arms.yaml manifest.")] = _MANIFEST_PATH,
    gold: Annotated[Path, typer.Option(help="Path to gold.json.")] = _GOLD_PATH,
) -> None:
    """Run the full judgement experiment: plan -> run -> score (costs tokens).

    Executes all three stages in order and prints the complete score report
    including the payoff-per-cost ranking across all enabled arms.
    """
    console.print(Panel(":rocket: Running full SOLID judgement experiment", title="solid-ab all"))

    plan()
    run_arms(manifest=manifest)
    score(manifest=manifest, gold=gold)


if __name__ == "__main__":
    app()
