#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""BLOCKED Declaration Generator — scaffolds a BLOCKED declaration from prompts or args.

Outputs the completed declaration to stdout for copy-paste into task output.

Usage:
    uv run .claude/skills/boil/scripts/generate_blocked.py
    uv run .claude/skills/boil/scripts/generate_blocked.py --reason "..." --completed "..." --remains "..." --condition "..."

Exit codes:
    0 — declaration generated successfully
    1 — required field missing or user cancelled
"""

from __future__ import annotations

import argparse
import sys


def prompt_field(name: str, description: str, required: bool = True) -> str:
    """Prompt the user for a single field value.

    Returns:
        The stripped input value, or exits with code 1 if required and empty.
    """
    print(f"\n{name}")
    print(f"  {description}")
    value = input("  > ").strip()
    if required and not value:
        print(f"  ERROR: {name} is required.")
        sys.exit(1)
    return value


def build_declaration(reason: str, completed: str, remains: str, condition: str) -> str:
    """Assemble a BLOCKED declaration string from the four required fields.

    Returns:
        Formatted multi-line BLOCKED declaration string ready for stdout.
    """
    completed_lines = [f"  - {line.strip()}" for line in completed.splitlines() if line.strip()]
    remains_lines = [f"  - {line.strip()}" for line in remains.splitlines() if line.strip()]

    completed_str = (
        "\n".join(completed_lines) if completed_lines else "  - nothing — constraint encountered before work began"
    )
    remains_str = (
        "\n".join(remains_lines) if remains_lines else "  - (specify remaining steps with file paths and commands)"
    )

    return f"""BLOCKED: {reason}
- What was completed:
{completed_str}
- What remains:
{remains_str}
- Unblocking condition: {condition}"""


def main() -> int:
    """Entry point — parse args and generate or interactively build a BLOCKED declaration.

    Returns:
        0 on success, 1 if a required field is missing or user cancels.
    """
    parser = argparse.ArgumentParser(
        description="Generate a BLOCKED declaration for tasks that cannot be completed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode (no args):
    uv run scripts/generate_blocked.py

  Inline mode:
    uv run scripts/generate_blocked.py \\
      --reason "pyproject.toml is read-only in CI" \\
      --completed "identified failing import at src/runner.py:14" \\
      --remains "add fastmcp[tasks] to pyproject.toml; run uv lock; re-run pytest" \\
      --condition "pyproject.toml is writable and fastmcp[tasks] is in dependencies"
        """,
    )
    parser.add_argument("--reason", help="Specific external constraint (one sentence)")
    parser.add_argument("--completed", help="What was completed (newline-separated list)")
    parser.add_argument("--remains", help="What remains (newline-separated list with paths/commands)")
    parser.add_argument("--condition", help="Observable, testable unblocking condition")

    args = parser.parse_args()

    if args.reason and args.completed and args.remains and args.condition:
        # Inline mode
        declaration = build_declaration(args.reason, args.completed, args.remains, args.condition)
    else:
        # Interactive mode
        print("BLOCKED Declaration Generator")
        print("=" * 40)
        print("Answer each prompt. The declaration will be printed when complete.")
        print("See references/blocked-declaration-contract.md for field definitions.")

        reason = args.reason or prompt_field("BLOCKED reason", "One sentence naming the specific external constraint.")
        completed = args.completed or prompt_field(
            "What was completed",
            "List completed steps (one per line). Empty line to finish.\n  Enter 'nothing' if work could not begin.",
            required=False,
        )
        remains = args.remains or prompt_field(
            "What remains", "List remaining steps with file paths and commands (one per line)."
        )
        condition = args.condition or prompt_field(
            "Unblocking condition", "Observable, testable change that enables completion."
        )

        declaration = build_declaration(reason, completed or "", remains, condition)

    print("\n" + "=" * 40)
    print(declaration)
    print("=" * 40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
