"""Shared fixtures for the research_backlinks test suite."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Path setup: make backlink_lib importable
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parents[2] / ".claude" / "skills" / "research-curator" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_REPO_ROOT = Path(__file__).parents[2]
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"
_RUN_BOUNDED: Final = (
    "uv",
    "run",
    "--script",
    str(_REPO_ROOT / "scripts" / "run_bounded.py"),
    "--timeout-seconds",
    "60",
    "--",
)


def validator_command(args: list[str]) -> list[str]:
    """Build one bounded validator command with isolated backlink-cache behavior.

    Args:
        args: Arguments passed to ``validate_research.py``.

    Returns:
        Complete subprocess argument vector.

    Raises:
        RuntimeError: If the uv executable is unavailable.
    """
    found_uv = shutil.which("uv")
    if found_uv is None:
        raise RuntimeError("uv binary not found on PATH — cannot run CLI tests")
    prepared_args = list(args)
    if (
        prepared_args
        and prepared_args[0] == "check-backlinks"
        and not {"--cache-path", "--no-cache"}.intersection(prepared_args)
    ):
        prepared_args.append("--no-cache")
    return [*_RUN_BOUNDED, found_uv, "run", "--script", str(_VALIDATE_SCRIPT), *prepared_args]


# Canonical minimal entry markdown template
_ENTRY_TEMPLATE = """\
# {name}

**Research Date**: 2026-01-01
**Source URL**: https://example.com/{slug}
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

{name} is a test research entry used in pytest fixtures.

## Problem Addressed

Provides a minimal well-formed research entry for testing.

## Key Features

- Feature A
- Feature B

## Technical Architecture

Simple architecture for testing.

## Installation & Usage

```bash
pip install {slug}
```

## Key Statistics

- Stars: 100 (as of 2026-01-01)

## Relevance to Claude Code Development

Relevant for testing purposes.

## References

- [Example](https://example.com) (accessed 2026-01-01)

## Freshness Tracking

- **Last Verified**: 2026-01-01
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2026-07-01
"""


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create an isolated temporary vault with minimal directory structure.

    The vault contains:
    - README.md (master index stub)
    - agent-frameworks/, tools/, context-management/, coding-agents/, ai-observability/ dirs
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "README.md").write_text("# Research Vault\n\nTest vault for research_backlinks tests.\n", encoding="utf-8")
    for category in ["agent-frameworks", "tools", "context-management", "coding-agents", "ai-observability"]:
        (vault / category).mkdir()
    return vault


@pytest.fixture
def make_entry(tmp_vault: Path) -> Callable[..., Path]:
    """Fixture-factory: create a research entry at a given relative vault path.

    Usage::

        path = make_entry("agent-frameworks/alpha.md")
        path = make_entry(
            "tools/beta.md",
            cross_refs=[("../agent-frameworks/alpha.md", "agent-frameworks", "Alpha", "provides embedding")],
        )

    Args:
        relative_path: Path relative to vault root (e.g. "agent-frameworks/foo.md").
        name: Display name for the entry (defaults to filename stem).
        cross_refs: Optional list of (link, category, entry_name, relationship) tuples
            to populate the Cross-References table.
        custom_markdown: If set, writes this exact string instead of generating content.

    Returns:
        Absolute Path to the created file.
    """

    def _make(
        relative_path: str,
        name: str | None = None,
        cross_refs: list[tuple[str, str, str, str]] | None = None,
        custom_markdown: str | None = None,
    ) -> Path:
        full_path = tmp_vault / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if custom_markdown is not None:
            full_path.write_text(custom_markdown, encoding="utf-8")
            return full_path

        slug = full_path.stem
        display_name = name or slug.replace("-", " ").title()
        content = _ENTRY_TEMPLATE.format(name=display_name, slug=slug)

        if cross_refs:
            table_lines = [
                "",
                "---",
                "",
                "## Cross-References",
                "",
                "| Entry | Category | Relationship |",
                "|-------|----------|--------------|",
            ]
            for link, category, entry_name, relationship in cross_refs:
                table_lines.append(f"| [{entry_name}]({link}) | {category} | {relationship} |")
            table_lines.append("")
            content = content.rstrip("\n") + "\n" + "\n".join(table_lines) + "\n"

        full_path.write_text(content, encoding="utf-8")
        return full_path

    return _make
