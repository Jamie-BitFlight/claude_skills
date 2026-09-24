#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0"
# ]
# ///
"""Create a new Claude Code plugin with validated structure.

This script scaffolds a complete plugin directory structure with:
- .claude-plugin/plugin.json (validated against schema)
- Optional skills, agents directories
- Template files for each component type

Note: Commands in plugins are deprecated. Use skills instead.

Self-validates all created files before reporting success (CoVe pattern).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, Any

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table

MAX_NAME_LENGTH = 64

console = Console()
error_console = Console(stderr=True)


def _get_table_width(table: Table) -> int:
    """Get natural width of table using temporary wide console.

    Source: python-engineering python3-core skill - tool-library-registry.md

    Returns:
        The natural width of the table in characters.
    """
    temp_console = Console(width=99999)
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)


app = typer.Typer(
    name="create-plugin", help="Create a new Claude Code plugin with validated structure", rich_markup_mode="rich"
)


class ComponentType(StrEnum):
    """Plugin component types."""

    SKILL = "skill"
    AGENT = "agent"
    HOOK = "hook"


@dataclass
class ValidationResult:
    """Result of validating a created file or structure."""

    path: Path
    valid: bool
    message: str


@dataclass
class PluginSpec:
    """Specification for plugin creation."""

    name: str
    description: str
    version: str = "1.0.0"
    author_name: str = ""
    author_email: str = ""
    license: str = "MIT"
    skills: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    include_hooks: bool = False


def validate_plugin_name(name: str) -> tuple[bool, str]:
    """Validate plugin name against schema requirements.

    Requirements (from official docs):
    - Lowercase letters, numbers, hyphens only
    - Max 64 characters
    - Must start with a letter

    Returns:
        Tuple of (is_valid, message) where message describes the validation result.
    """
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Name exceeds {MAX_NAME_LENGTH} characters (got {len(name)})"

    if not re.match(r"^[a-z][a-z0-9-]*$", name):
        return (False, "Name must be lowercase, start with letter, contain only letters/numbers/hyphens")

    return True, "Valid"


def create_plugin_json(spec: PluginSpec) -> dict[str, Any]:
    """Create plugin.json content from spec.

    Returns:
        Dictionary representing the plugin.json manifest content.
    """
    manifest: dict[str, Any] = {"name": spec.name, "version": spec.version, "description": spec.description}

    if spec.author_name:
        author: dict[str, str] = {"name": spec.author_name}
        if spec.author_email:
            author["email"] = spec.author_email
        manifest["author"] = author

    if spec.license:
        manifest["license"] = spec.license

    # Add component paths
    if spec.skills:
        manifest["skills"] = [f"./skills/{s}" for s in spec.skills]

    if spec.agents:
        manifest["agents"] = "./agents"

    if spec.include_hooks:
        manifest["hooks"] = "./hooks/hooks.json"

    return manifest


def create_skill_template(name: str, plugin_name: str) -> str:
    """Create SKILL.md template content.

    Returns:
        Markdown content for a SKILL.md file with frontmatter.
    """
    return f"""---
name: {name}
description: 'Describe what this skill does and when to use it. Include trigger keywords for auto-invocation.'
---

# {name.replace("-", " ").title()}

## Purpose

[Describe what this skill enables Claude to do]

## When to Use

Use this skill when:

- [Trigger condition 1]
- [Trigger condition 2]

## Instructions

[Core instructions for Claude - keep under 500 lines]

---

## Sources

- [Source 1](https://example.com) - What this source covers
"""


def create_agent_template(name: str) -> str:
    """Create agent file template content.

    Returns:
        Markdown content for an agent .md file with frontmatter.
    """
    return f"""---
name: {name}
description: 'Describe when to delegate to this agent. Include trigger keywords.'
model: sonnet
---

# {name.replace("-", " ").title()} Agent

## Purpose

[What this agent specializes in]

## Instructions

[System prompt for the agent]
"""


def create_hooks_template() -> dict[str, Any]:
    """Create hooks.json template content.

    Returns:
        Dictionary representing the hooks.json configuration.
    """
    return {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {"type": "command", "command": "echo 'File modified: $CLAUDE_PROJECT_DIR'", "timeout": 10}
                    ],
                }
            ]
        }
    }


def validate_json_file(path: Path) -> ValidationResult:
    """Validate a JSON file exists and is parseable.

    Returns:
        ValidationResult indicating whether the file is valid JSON.
    """
    if not path.exists():
        return ValidationResult(path, False, "File does not exist")

    try:
        with path.open(encoding="utf-8") as f:
            json.load(f)
        return ValidationResult(path, True, "Valid JSON")
    except json.JSONDecodeError as e:
        return ValidationResult(path, False, f"Invalid JSON: {e}")


def validate_yaml_frontmatter(path: Path) -> ValidationResult:
    """Validate a file has valid YAML frontmatter.

    Returns:
        ValidationResult indicating whether the file has valid frontmatter.
    """
    if not path.exists():
        return ValidationResult(path, False, "File does not exist")

    try:
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return ValidationResult(path, False, "Missing YAML frontmatter delimiter")

        # Find closing delimiter
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return ValidationResult(path, False, "Missing closing frontmatter delimiter")

        # Basic YAML validation - check for multiline indicators (forbidden)
        frontmatter = content[3:end_idx]
        if ">-" in frontmatter or "|-" in frontmatter or ">|" in frontmatter:
            return ValidationResult(path, False, "Contains YAML multiline indicators (>- or |-) which break parsing")

        return ValidationResult(path, True, "Valid frontmatter structure")
    except (OSError, UnicodeDecodeError) as e:
        return ValidationResult(path, False, f"Error reading file: {e}")


def validate_directory_structure(plugin_dir: Path, spec: PluginSpec) -> list[ValidationResult]:
    """Validate the created plugin structure.

    Returns:
        List of ValidationResult for each validated file in the plugin.
    """
    results: list[ValidationResult] = []

    # Check .claude-plugin/plugin.json
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    results.append(validate_json_file(manifest_path))

    # Check skills
    for skill_name in spec.skills:
        skill_path = plugin_dir / "skills" / skill_name / "SKILL.md"
        results.append(validate_yaml_frontmatter(skill_path))

    # Check agents
    for agent_name in spec.agents:
        agent_path = plugin_dir / "agents" / f"{agent_name}.md"
        results.append(validate_yaml_frontmatter(agent_path))

    # Check hooks
    if spec.include_hooks:
        hooks_path = plugin_dir / "hooks" / "hooks.json"
        results.append(validate_json_file(hooks_path))

    return results


def create_plugin(base_dir: Path, spec: PluginSpec) -> tuple[Path, list[ValidationResult]]:
    """Create plugin directory structure and files.

    Returns:
        Tuple of (plugin_path, validation_results)
    """
    plugin_dir = base_dir / spec.name

    # Create directories
    (plugin_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)

    # Create plugin.json
    manifest = create_plugin_json(spec)
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    # Create skills
    for skill_name in spec.skills:
        skill_dir = plugin_dir / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(create_skill_template(skill_name, spec.name))

    # Create agents
    if spec.agents:
        agent_dir = plugin_dir / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        for agent_name in spec.agents:
            agent_path = agent_dir / f"{agent_name}.md"
            agent_path.write_text(create_agent_template(agent_name))

    # Create hooks
    if spec.include_hooks:
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hooks_path = hooks_dir / "hooks.json"
        with hooks_path.open("w") as f:
            json.dump(create_hooks_template(), f, indent=2)
            f.write("\n")

    # Validate created structure (CoVe pattern)
    validation_results = validate_directory_structure(plugin_dir, spec)

    return plugin_dir, validation_results


def display_results(plugin_dir: Path, results: list[ValidationResult]) -> bool:
    """Display validation results and return overall success.

    Returns:
        True if all validations passed, False otherwise.
    """
    table = Table(title="Validation Results (CoVe)", box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Message", style="white", no_wrap=True)

    all_valid = True
    for result in results:
        rel_path = result.path.relative_to(plugin_dir) if result.path.is_relative_to(plugin_dir) else result.path
        status = "[green]✓ PASS[/green]" if result.valid else "[red]✗ FAIL[/red]"
        table.add_row(str(rel_path), status, result.message)
        if not result.valid:
            all_valid = False

    # Set table width to prevent wrapping (per python-engineering guidelines)
    table.width = _get_table_width(table)
    console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)
    return all_valid


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Plugin name (kebab-case)")],
    *,
    description: Annotated[str, typer.Option("--description", "-d", help="Plugin description")] = "",
    skills: Annotated[list[str] | None, typer.Option("--skill", "-s", help="Skill names to create")] = None,
    agents: Annotated[list[str] | None, typer.Option("--agent", "-a", help="Agent names to create")] = None,
    hooks: Annotated[bool, typer.Option("--hooks", help="Include hooks template")] = False,
    author: Annotated[str, typer.Option("--author", help="Author name")] = "",
    email: Annotated[str, typer.Option("--email", help="Author email")] = "",
    output_dir: Annotated[Path, typer.Option("--output", "-o", help="Output directory (default: ./plugins)")] = Path(
        "./plugins"
    ),
) -> None:
    """Create a new Claude Code plugin with validated structure.

    Examples:
        # Create a simple plugin with one skill
        uv run create_plugin.py my-plugin -d "My plugin description" -s my-skill

        # Create plugin with multiple components
        uv run create_plugin.py my-plugin -s skill1 -s skill2 -a agent1 --hooks
    """
    # Validate name
    if agents is None:
        agents = []
    if skills is None:
        skills = []
    valid, msg = validate_plugin_name(name)
    if not valid:
        error_console.print(f"[red]Invalid plugin name:[/red] {msg}")
        raise typer.Exit(1)

    # Default description if not provided
    if not description:
        description = f"{name.replace('-', ' ').title()} plugin"

    # Default to one skill with same name if no components specified
    if not skills and not agents:
        skills = [name]

    spec = PluginSpec(
        name=name,
        description=description,
        author_name=author,
        author_email=email,
        skills=list(skills),
        agents=list(agents),
        include_hooks=hooks,
    )

    console.print(f"[cyan]Creating plugin:[/cyan] {name}")
    console.print(f"[cyan]Output directory:[/cyan] {output_dir}")

    try:
        plugin_dir, results = create_plugin(output_dir, spec)
    except Exception as e:
        error_console.print(f"[red]Error creating plugin:[/red] {e}")
        raise typer.Exit(1) from e

    console.print()
    all_valid = display_results(plugin_dir, results)

    if all_valid:
        console.print()
        console.print(
            Panel(
                f"[green]Plugin created successfully![/green]\n\n"
                f"Location: {plugin_dir}\n\n"
                f"Next steps:\n"
                f"1. Edit the generated templates\n"
                f"2. Run: [cyan]uv run validate_plugin.py {plugin_dir}[/cyan]\n"
                f"3. Test: [cyan]claude --plugin-dir {plugin_dir}[/cyan]",
                title="Success",
                border_style="green",
            ),
            crop=False,
            overflow="ignore",
        )
    else:
        error_console.print()
        error_console.print(
            Panel(
                "[red]Plugin created but validation failed![/red]\n\n"
                "Please fix the issues above before using the plugin.",
                title="Validation Failed",
                border_style="red",
            ),
            crop=False,
            overflow="ignore",
        )
        raise typer.Exit(1)


@app.command()
def validate(plugin_dir: Annotated[Path, typer.Argument(help="Path to plugin directory")]) -> None:
    """Validate an existing plugin directory structure.

    Checks:
    - plugin.json exists and is valid JSON
    - All referenced skills have valid SKILL.md
    - All agents have valid frontmatter
    - No YAML multiline indicators in descriptions
    """
    if not plugin_dir.exists():
        error_console.print(f"[red]Plugin directory not found:[/red] {plugin_dir}")
        raise typer.Exit(1)

    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        error_console.print("[red]Not a valid plugin:[/red] missing .claude-plugin/plugin.json")
        raise typer.Exit(1)

    # Load manifest to get components
    try:
        with manifest_path.open() as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        error_console.print(f"[red]Invalid plugin.json:[/red] {e}")
        raise typer.Exit(1) from e

    # Build spec from manifest
    skills = []
    if "skills" in manifest:
        for skill_path in manifest["skills"]:
            # Extract skill name from path like "./skills/my-skill"
            skill_name = Path(skill_path).name
            skills.append(skill_name)

    agents = []
    if "agents" in manifest:
        agent_dir = plugin_dir / "agents"
        if agent_dir.exists():
            agents = [p.stem for p in agent_dir.glob("*.md")]

    spec = PluginSpec(
        name=manifest.get("name", plugin_dir.name),
        description=manifest.get("description", ""),
        skills=skills,
        agents=agents,
        include_hooks="hooks" in manifest,
    )

    results = validate_directory_structure(plugin_dir, spec)

    console.print(f"[cyan]Validating plugin:[/cyan] {plugin_dir}")
    console.print()

    all_valid = display_results(plugin_dir, results)

    if all_valid:
        console.print()
        console.print(
            Panel("[green]All validations passed![/green]", border_style="green"), crop=False, overflow="ignore"
        )
    else:
        console.print()
        console.print(
            Panel("[red]Validation failed - see issues above[/red]", border_style="red"), crop=False, overflow="ignore"
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
