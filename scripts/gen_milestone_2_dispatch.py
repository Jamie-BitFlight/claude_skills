#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic", "ruamel.yaml"]
#
# [tool.ty.environment]
# extra-paths = ["../plugins/development-harness"]
# ///
"""Generate plan/milestone-2-dispatch.yaml for milestone #2: dh-feedbackloop-meta-refactor."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from repo root via: uv run scripts/gen_milestone_2_dispatch.py
sys.path.insert(0, str(Path(__file__).parent.parent / "plugins" / "development-harness"))

from dispatch_schema.core.models import DispatchPlan, ItemPriority, MilestoneHeader, QualityGates, Wave, WaveItem
from dispatch_schema.writers.yaml_writer import write_dispatch_plan

plan = DispatchPlan(
    milestone=MilestoneHeader(
        number=2, title="dh-feedbackloop-meta-refactor", integration_branch="milestone/2-dh-feedbackloop-meta-refactor"
    ),
    conflict_groups=[],
    waves=[
        Wave(
            wave=1,
            parallel=True,
            items=[
                WaveItem(
                    issue=1003, title="Refactor local-workflow.md to use MCP tools only", priority=ItemPriority.P1
                ),
                WaveItem(issue=986, title="Add dispatch orchestration MCP tools", priority=ItemPriority.P1),
                WaveItem(issue=1011, title="Automated agent frontmatter health check", priority=ItemPriority.P1),
                WaveItem(issue=1010, title="Fluid milestone creation", priority=ItemPriority.P1),
            ],
        ),
        Wave(
            wave=2,
            parallel=True,
            items=[
                WaveItem(issue=994, title="Systematic agent output verification", priority=ItemPriority.P1),
                WaveItem(
                    issue=1000, title="Re-run plan validator — enforce mechanical READY gate", priority=ItemPriority.P1
                ),
                WaveItem(issue=999, title="Add scope confirmation step before SAM planning", priority=ItemPriority.P1),
            ],
        ),
        Wave(
            wave=3,
            parallel=True,
            items=[
                WaveItem(issue=1004, title="Quality gate findings auto-create backlog items", priority=ItemPriority.P1),
                WaveItem(issue=1005, title="Persistent cross-session discovery store", priority=ItemPriority.P1),
                WaveItem(issue=997, title="Per-wave concern triage", priority=ItemPriority.P1),
            ],
        ),
        Wave(
            wave=4,
            parallel=True,
            items=[
                WaveItem(
                    issue=1006,
                    title="Agent-level persistent memory from code review findings",
                    priority=ItemPriority.P1,
                ),
                WaveItem(
                    issue=1001, title="Add grooming feedback loop — architect rejection", priority=ItemPriority.P1
                ),
                WaveItem(
                    issue=1002,
                    title="Route upstream artifact quality concerns to remediation",
                    priority=ItemPriority.P1,
                ),
                WaveItem(issue=995, title="Cross-task contract verification", priority=ItemPriority.P1),
            ],
        ),
        Wave(
            wave=5,
            parallel=True,
            items=[
                WaveItem(issue=993, title="Severity gate — HIGH findings block completion", priority=ItemPriority.P1),
                WaveItem(issue=996, title="Design intent alignment check", priority=ItemPriority.P1),
                WaveItem(issue=998, title="Grooming-to-planning via kage-bunshin", priority=ItemPriority.P1),
                WaveItem(issue=1012, title="Reorder complete-implementation phases", priority=ItemPriority.P1),
            ],
        ),
        Wave(
            wave=6,
            parallel=True,
            items=[
                WaveItem(issue=1007, title="Adversarial review teams", priority=ItemPriority.P2),
                WaveItem(issue=1008, title="Red team agent", priority=ItemPriority.P2),
                WaveItem(issue=1009, title="Pattern detection agent", priority=ItemPriority.P2),
            ],
        ),
    ],
    quality_gates=QualityGates(
        pre_merge=["uv run pytest plugins/development-harness/tests/ -x -q", "uv run prek run --all-files"],
        post_merge=["uv run pytest plugins/development-harness/tests/ -q"],
    ),
)

output_path = Path(__file__).parent.parent / "plan" / "milestone-2-dispatch.yaml"
written = write_dispatch_plan(plan, output_path)
print(f"Written: {written}")

# Verify item count
total_items = sum(len(w.items) for w in plan.waves)
print(f"Waves: {len(plan.waves)}, Items: {total_items}")
