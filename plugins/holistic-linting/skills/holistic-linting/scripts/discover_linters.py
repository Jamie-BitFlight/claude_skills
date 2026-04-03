#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "tomlkit>=0.13.0",
#     "ruamel.yaml>=0.18.0",
#     "gitpython>=3.1.45",
# ]
# ///
"""Discover project linters and generate LINTERS section for CLAUDE.md.

This script scans project configuration files to identify formatters and linters,
then generates a standardized LINTERS section documenting the project's quality tools.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, Any

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import git
import tomlkit
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from ruamel.yaml import YAML, YAMLError
from tomlkit.exceptions import ParseError as TOMLParseError

# Console setup
console = Console()
error_console = Console(stderr=True, style="bold red")


@dataclass
class LinterConfig:
    """Configuration for a discovered linter."""

    name: str
    patterns: list[str]
    is_formatter: bool = False
    is_linter: bool = False


@dataclass
class ProjectLinters:
    """Discovered linting configuration for a project."""

    git_hooks_enabled: bool = False
    pre_commit_tool: str | None = None
    formatters: list[LinterConfig] = field(default_factory=list)
    linters: list[LinterConfig] = field(default_factory=list)


def check_git_hooks() -> bool:
    """Check if git pre-commit hooks are installed and enabled.

    Returns:
        True if hooks are installed and enabled
    """
    try:
        repo = git.Repo(search_parent_directories=True)
        hooks_path_str = repo.config_reader().get_value("core", "hooksPath", None)
        hooks_path = Path(str(hooks_path_str)) if hooks_path_str is not None else Path(repo.git_dir) / "hooks"

        pre_commit_hook = hooks_path / "pre-commit"
        return pre_commit_hook.exists() and pre_commit_hook.stat().st_size > 0

    except git.InvalidGitRepositoryError:
        return False


def detect_pre_commit_tool(project_root: Path) -> str | None:
    """Detect which pre-commit tool is used.

    Args:
        project_root: Project root directory

    Returns:
        Name of pre-commit tool (husky, pre-commit, manual) or None
    """
    # Check for .pre-commit-config.yaml
    if (project_root / ".pre-commit-config.yaml").exists():
        return "pre-commit"

    # Check for husky
    husky_dir = project_root / ".husky"
    if husky_dir.exists() and husky_dir.is_dir():
        return "husky"

    # Check for git hooks directory with custom scripts
    git_hooks = project_root / ".git" / "hooks"
    if git_hooks.exists():
        pre_commit_hook = git_hooks / "pre-commit"
        if pre_commit_hook.exists():
            return "manual"

    return None


# Hook ID to LinterConfig mapping
_HOOK_CONFIGS: dict[str, LinterConfig] = {
    "ruff": LinterConfig(name="ruff check", patterns=["*.py"], is_linter=True),
    "ruff-format": LinterConfig(name="ruff format", patterns=["*.py"], is_formatter=True),
    "prettier": LinterConfig(name="prettier", patterns=["*.{ts,tsx,js,jsx,json,md}"], is_formatter=True),
    "eslint": LinterConfig(name="eslint", patterns=["*.{ts,tsx,js,jsx}"], is_linter=True),
    "markdownlint": LinterConfig(name="markdownlint", patterns=["*.{md,markdown}"], is_linter=True),
    "shellcheck": LinterConfig(name="shellcheck", patterns=["*.{sh,bash,zsh,fish}"], is_linter=True),
    "shfmt": LinterConfig(name="shfmt", patterns=["*.{sh,bash,zsh,fish}"], is_formatter=True),
}


def _map_hook_to_linter(hook_id: str) -> LinterConfig | None:
    """Map a pre-commit hook ID to a LinterConfig.

    Args:
        hook_id: Hook ID from pre-commit config

    Returns:
        LinterConfig if hook is recognized, None otherwise
    """
    return _HOOK_CONFIGS.get(hook_id)


def scan_pre_commit_config(config_file: Path) -> list[LinterConfig]:
    """Scan .pre-commit-config.yaml for hooks.

    Args:
        config_file: Path to .pre-commit-config.yaml

    Returns:
        List of discovered linter configurations
    """
    linters: list[LinterConfig] = []

    try:
        with config_file.open(encoding="utf-8") as f:
            config = YAML(typ="safe").load(f)

        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_id = hook.get("id", "")
                linter_config = _map_hook_to_linter(hook_id)
                if linter_config:
                    linters.append(linter_config)

    except (OSError, YAMLError, KeyError, TypeError) as e:
        console.print(f"[yellow]Warning: Failed to parse .pre-commit-config.yaml: {e}[/yellow]")

    return linters


def scan_pyproject_toml(config_file: Path) -> list[LinterConfig]:
    """Scan pyproject.toml for Python tool configurations.

    Args:
        config_file: Path to pyproject.toml

    Returns:
        List of discovered linter configurations
    """
    linters: list[LinterConfig] = []

    try:
        config: dict[str, Any] = tomlkit.parse(config_file.read_text(encoding="utf-8")).unwrap()

        # Check for ruff
        if "tool" in config and "ruff" in config["tool"]:
            linters.extend((
                LinterConfig(name="ruff format", patterns=["*.py"], is_formatter=True),
                LinterConfig(name="ruff check", patterns=["*.py"], is_linter=True),
            ))

        # Check for pyright
        if "tool" in config and "pyright" in config["tool"]:
            linters.append(LinterConfig(name="pyright", patterns=["*.py"], is_linter=True))

        # Check for bandit
        if "tool" in config and "bandit" in config["tool"]:
            linters.append(LinterConfig(name="bandit", patterns=["*.py"], is_linter=True))

    except (OSError, TOMLParseError, KeyError, TypeError) as e:
        console.print(f"[yellow]Warning: Failed to parse pyproject.toml: {e}[/yellow]")

    return linters


def scan_package_json(config_file: Path) -> list[LinterConfig]:
    """Scan package.json for JavaScript/TypeScript tools.

    Args:
        config_file: Path to package.json

    Returns:
        List of discovered linter configurations
    """
    linters: list[LinterConfig] = []

    try:
        with config_file.open(encoding="utf-8") as f:
            config = json.load(f)

        dev_deps = config.get("devDependencies", {})

        # Check for prettier
        if "prettier" in dev_deps:
            linters.append(LinterConfig(name="prettier", patterns=["*.{ts,tsx,js,jsx,json,md}"], is_formatter=True))

        # Check for eslint
        if "eslint" in dev_deps or any("eslint" in dep for dep in dev_deps):
            linters.append(LinterConfig(name="eslint", patterns=["*.{ts,tsx,js,jsx}"], is_linter=True))

        # Check for markdownlint
        if any("markdownlint" in dep for dep in dev_deps):
            linters.append(LinterConfig(name="markdownlint", patterns=["*.{md,markdown}"], is_linter=True))

    except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        console.print(f"[yellow]Warning: Failed to parse package.json: {e}[/yellow]")

    return linters


def scan_config_files(project_root: Path) -> list[LinterConfig]:
    """Scan standalone config files for linters.

    Args:
        project_root: Project root directory

    Returns:
        List of discovered linter configurations
    """
    linters: list[LinterConfig] = []

    # Check for ESLint config
    eslint_configs = [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml"]
    if any((project_root / config).exists() for config in eslint_configs):
        linters.append(LinterConfig(name="eslint", patterns=["*.{ts,tsx,js,jsx}"], is_linter=True))

    # Check for Prettier config
    prettier_configs = [".prettierrc", ".prettierrc.js", ".prettierrc.json", ".prettierrc.yml", ".prettierrc.yaml"]
    if any((project_root / config).exists() for config in prettier_configs):
        linters.append(LinterConfig(name="prettier", patterns=["*.{ts,tsx,js,jsx,json,md}"], is_formatter=True))

    # Check for markdownlint config
    markdownlint_configs = [".markdownlint.json", ".markdownlint.yaml", ".markdownlintrc"]
    if any((project_root / config).exists() for config in markdownlint_configs):
        linters.append(LinterConfig(name="markdownlint", patterns=["*.{md,markdown}"], is_linter=True))

    return linters


def discover_linters(project_root: Path) -> ProjectLinters:
    """Discover all linters configured in the project.

    Args:
        project_root: Project root directory

    Returns:
        ProjectLinters object with all discovered configuration
    """
    project_linters = ProjectLinters()

    # Check git hooks
    project_linters.git_hooks_enabled = check_git_hooks()
    project_linters.pre_commit_tool = detect_pre_commit_tool(project_root)

    # Collect all linters from various sources
    all_linters: list[LinterConfig] = []

    # Scan .pre-commit-config.yaml
    pre_commit_config = project_root / ".pre-commit-config.yaml"
    if pre_commit_config.exists():
        all_linters.extend(scan_pre_commit_config(pre_commit_config))

    # Scan pyproject.toml
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        all_linters.extend(scan_pyproject_toml(pyproject))

    # Scan package.json
    package_json = project_root / "package.json"
    if package_json.exists():
        all_linters.extend(scan_package_json(package_json))

    # Scan standalone config files
    all_linters.extend(scan_config_files(project_root))

    # Deduplicate and categorize
    seen_names: set[str] = set()
    for linter in all_linters:
        if linter.name not in seen_names:
            seen_names.add(linter.name)
            if linter.is_formatter:
                project_linters.formatters.append(linter)
            if linter.is_linter:
                project_linters.linters.append(linter)

    return project_linters


def generate_linters_section(linters: ProjectLinters) -> str:
    """Generate LINTERS section markdown.

    Args:
        linters: Discovered linter configuration

    Returns:
        Markdown string for LINTERS section
    """
    lines = ["## LINTERS", ""]

    # Git hooks status
    hooks_status = "enabled" if linters.git_hooks_enabled else "disabled"
    lines.append(f"git pre-commit hooks: {hooks_status}")

    tool_name = linters.pre_commit_tool or "none"
    lines.extend((f"pre-commit tool: {tool_name}", ""))

    # Formatters
    if linters.formatters:
        lines.extend(("### Formatters", ""))
        for formatter in sorted(linters.formatters, key=lambda x: x.name):
            patterns_str = ", ".join(formatter.patterns)
            lines.append(f"- {formatter.name} [{patterns_str}]")
        lines.append("")

    # Linters
    if linters.linters:
        lines.extend(("### Static Checking and Linting", ""))
        for linter in sorted(linters.linters, key=lambda x: x.name):
            patterns_str = ", ".join(linter.patterns)
            lines.append(f"- {linter.name} [{patterns_str}]")
        lines.append("")

    return "\n".join(lines)


def update_claude_md(output_file: Path, linters_section: str, force: bool) -> bool:
    """Update CLAUDE.md file with LINTERS section.

    Args:
        output_file: Path to CLAUDE.md file
        linters_section: Generated LINTERS section markdown
        force: If True, replace existing LINTERS section

    Returns:
        True if update succeeded, False if conflicts prevented update

    Raises:
        OSError: If file operations fail
    """
    # Read existing content if file exists
    if output_file.exists():
        existing_content = output_file.read_text(encoding="utf-8")

        # Check for existing LINTERS section
        if re.search(r"^## LINTERS\b", existing_content, re.MULTILINE):
            if not force:
                error_console.print(":cross_mark: [red]LINTERS section already exists in CLAUDE.md[/red]")

                # Extract and show existing section
                match = re.search(r"(^## LINTERS\b.*?)(?=^## |\Z)", existing_content, re.MULTILINE | re.DOTALL)
                if match:
                    existing_section = match.group(1).strip()
                    console.print("\n[yellow]Existing LINTERS section:[/yellow]")
                    console.print(Panel(existing_section, border_style="yellow"))

                error_console.print("\n[yellow]To overwrite the existing section, use:[/yellow] --force")
                return False

            # Remove existing LINTERS section
            console.print(":warning: [yellow]Replacing existing LINTERS section[/yellow]")
            existing_content = re.sub(
                r"^## LINTERS\b.*?(?=^## |\Z)", "", existing_content, flags=re.MULTILINE | re.DOTALL
            )
            # Clean up any excessive blank lines
            existing_content = re.sub(r"\n{3,}", "\n\n", existing_content)

        # Append new section
        if not existing_content.endswith("\n\n"):
            existing_content = existing_content.rstrip() + "\n\n"
        new_content = existing_content + linters_section
    else:
        # Create new file with just the LINTERS section
        new_content = linters_section

    # Write the file
    output_file.write_text(new_content, encoding="utf-8")
    return True


app = typer.Typer(
    name="discover_linters",
    help="Discover project linters and generate LINTERS section for CLAUDE.md",
    rich_markup_mode="rich",
)


@app.command()
def main(
    output: Annotated[Path, typer.Option(help="Output file path (default: ./CLAUDE.md)")] = Path("CLAUDE.md"),
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing LINTERS section if present")] = False,
) -> None:
    """Discover project linters and generate LINTERS section for CLAUDE.md.

    Scans project configuration files (.pre-commit-config.yaml, pyproject.toml,
    package.json, etc.) to identify formatters and linters, then generates a
    standardized LINTERS section.

    Args:
        output: Output file path
        force: Overwrite existing LINTERS section

    Raises:
        typer.Exit: On discovery failure or conflicts
    """
    project_root = Path.cwd()

    console.print("[cyan]Scanning project for linting configuration...[/cyan]\n")

    # Discover linters
    linters = discover_linters(project_root)

    # Show discovery results
    table = Table(title="Discovered Linting Tools")
    table.add_column("Category", style="cyan")
    table.add_column("Tools", style="green")

    hooks_status = ":white_check_mark: enabled" if linters.git_hooks_enabled else ":cross_mark: disabled"
    table.add_row("Git Pre-commit Hooks", hooks_status)

    if linters.pre_commit_tool:
        table.add_row("Pre-commit Tool", linters.pre_commit_tool)

    if linters.formatters:
        formatter_names = ", ".join(f.name for f in linters.formatters)
        table.add_row("Formatters", formatter_names)

    if linters.linters:
        linter_names = ", ".join(ln.name for ln in linters.linters)
        table.add_row("Linters", linter_names)

    console.print(table)
    console.print()

    if not linters.formatters and not linters.linters:
        error_console.print(":cross_mark: [yellow]No linters discovered in project configuration[/yellow]")
        error_console.print(
            "\n[dim]Looked for: .pre-commit-config.yaml, pyproject.toml, package.json, "
            ".eslintrc*, .prettierrc*, .markdownlint*[/dim]"
        )
        raise typer.Exit(code=0)

    # Generate LINTERS section
    linters_section = generate_linters_section(linters)

    console.print("[cyan]Generated LINTERS section:[/cyan]")
    console.print(Panel(linters_section, border_style="cyan"))
    console.print()

    # Update CLAUDE.md
    try:
        success = update_claude_md(output, linters_section, force)
        if not success:
            raise typer.Exit(code=1)

        console.print(f":white_check_mark: [green]LINTERS section written to:[/green] {output}")
    except OSError as e:
        error_console.print(f":cross_mark: [red]Failed to write CLAUDE.md:[/red] {e}")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
