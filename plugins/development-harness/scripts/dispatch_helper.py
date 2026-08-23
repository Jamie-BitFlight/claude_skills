"""Dispatch helper -- assembles the 5 inputs for generic agent dispatch.

The generic stage agent receives:
1. Stage workflow skill (from dh)
2. Cross-cutting SDLC stage skill (from dh)
3. Domain skills (from resolved manifest stage_skills)
4. Task address (plan address plus task ID, read through the task operations)
5. Quality gate commands (from resolved manifest quality_gates)
6. Output artifact target (registered through the artifact operations)

No stage passes data to a later stage through a file. Inputs are read and outputs
are registered through the backend operations, so the addresses below are logical
identifiers, never filesystem paths.
"""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from manifest_schema import LanguageManifest


def _format_quality_gates(manifest: LanguageManifest) -> str:
    """Format quality gates as runnable commands.

    Returns:
        Newline-joined quality gate commands, or a message if none configured.
    """
    if manifest.quality_gates is None:
        return "No quality gates configured."

    gates: list[str] = []
    qg = manifest.quality_gates
    if qg.format:
        gates.append(f"- Format: `{qg.format}`")
    if qg.lint:
        gates.append(f"- Lint: `{qg.lint}`")
    if qg.typecheck:
        gates.append(f"- Typecheck: `{qg.typecheck}`")
    if qg.test:
        gates.append(f"- Test: `{qg.test}`")
    if qg.standards:
        gates.append(f"- Standards: Load skill `{qg.standards}`")

    if not gates:
        return "No quality gates configured."
    return "\n".join(gates)


def _format_skill_loads(skills: list[str]) -> str:
    """Format skill loading instructions.

    Returns:
        Newline-joined Skill() call instructions, or a message if none.
    """
    if not skills:
        return "No domain skills for this stage."
    lines: list[str] = [f'- Load: `Skill(skill="{skill}")`' for skill in skills]
    return "\n".join(lines)


def build_dispatch_prompt(
    stage: str,
    manifest: LanguageManifest,
    plan: str,
    task: str,
    stage_workflow_skill: str,
    cross_cutting_skill: str | None,
    item_id: int | str | None = None,
    artifact_type: str | None = None,
    artifact_id: str | None = None,
) -> str:
    """Build the dispatch prompt for a generic stage agent.

    Assembles all 5 inputs (plus the output artifact target) into a structured
    prompt that the generic stage agent can follow mechanically.

    Args:
        stage: The SDLC stage identifier (e.g., "implementation").
        manifest: The fully resolved language manifest.
        plan: Plan address holding the task (e.g., "P123-my-feature").
        task: Task ID within the plan (e.g., "T1").
        stage_workflow_skill: Skill name for the stage workflow (e.g., "development-harness:execution").
        cross_cutting_skill: Optional cross-cutting SDLC skill name.
        item_id: Backlog item identifier the output artifact is registered against.
        artifact_type: Artifact type string for the stage output.
        artifact_id: Logical artifact identifier for the stage output.

    Returns:
        Formatted dispatch prompt string.
    """
    domain_skills = manifest.stage_skills.get(stage, [])
    output_section = (
        dedent(f"""\
            Register your output through the artifact operations:
            `artifact_register(item_id={item_id!r}, artifact_type="{artifact_type}", artifact_id="{artifact_id}", content=<full document>)`
            Report only the artifact type and identifier. Do not write the document to a file.""")
        if item_id is not None and artifact_type and artifact_id
        else dedent("""\
            Append your output to the task body:
            `sam_task(plan=..., task=..., config={"action": "update", "append_section": <heading>, "section_content": <body>})`
            Do not write the output to a file.""")
    )

    cross_cutting_section = (
        dedent(f"""\
            ## Input 2: Cross-Cutting Stage Skill
            Load: `Skill(skill="{cross_cutting_skill}")`
            This provides SDLC-stage-level guidance applicable across all languages.""")
        if cross_cutting_skill
        else dedent("""\
            ## Input 2: Cross-Cutting Stage Skill
            No cross-cutting skill for this stage.""")
    )

    # Written flush-left: interpolated sections are already dedented, so an indented
    # template plus dedent() would leave their continuation lines ragged.
    return f"""\
# Stage Dispatch: {stage}
**Language:** {manifest.language} | **Stack:** {manifest.stack or "base"} | **Manifest:** {manifest.name}

## Input 1: Stage Workflow
Load the stage workflow skill: `Skill(skill="{stage_workflow_skill}")`
Follow the workflow mermaid from this skill step by step.

{cross_cutting_section}

## Input 3: Domain Skills
{_format_skill_loads(domain_skills)}

## Input 4: Task Address
Read your task context through the task operations:
`sam_task(plan="{plan}", task="{task}", config={{"action": "read"}})`
Plan-level context and every task field arrive in that response. The address is a
logical identifier — do not treat it as a filesystem path.

## Input 5: Quality Gates
Run ALL of these before declaring completion:
{_format_quality_gates(manifest)}

**Note on `{{files}}` in quality gate commands**: Commands containing `{{files}}`
use Python `str.format()` syntax. Substitute `{{files}}` with the actual
space-separated file paths you are checking before running the command.

## Output Artifact
{output_section}"""
