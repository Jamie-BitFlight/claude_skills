"""Guards CLI-instruction docs against reproducing a Claude Code bash-guard false positive.

A worktree-isolated Claude Code session refuses any Bash command carrying the bare word
``complete`` as its own shell word: the guard reads it as the ``complete`` builtin, which can run
an arbitrary string (``complete -C <command>``) it cannot verify stays inside the worktree, and
refuses the whole command. ``dh_core.ledger_spec`` lists ``complete`` as an accepted value for two
CLI flags -- ``finish --result`` and ``state --new-status`` -- so a doc that tells an agent to type
either flag followed by a bare ``complete`` reproduces the refusal. Backlog item #4015 traced this
to ``dh:start-task`` instructing exactly that command to close every task, with no way to finish
one inside such a session.

The fix removed the need to type the token at all on the ordinary path:

- ``finish``'s ``--result`` now defaults to ``complete`` when omitted (see
  ``sam_schema/sam_plan.py``'s ``finish`` command) -- the runner-contract's other three outcomes
  (``failed``, ``blocked``, ``needs-input``) stay explicit and collide with nothing.
- The two ``state --new-status`` instruction sites that still need the literal value spell it
  ``--new-status=complete``. The ``=`` form is one shell word, so the guard's bare-word match never
  fires; passing the value with a following space, quoted or not, still reproduces the refusal
  (verified against the actual guard while fixing this).

This module derives the colliding pairs from ``ledger_spec.COMMANDS`` itself rather than
hard-coding them, so a flag added later with a colliding value is caught the same way.
"""

from __future__ import annotations

import re
from pathlib import Path

from dh_core import ledger_spec

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PLUGIN_ROOT.parent.parent

# Bash builtins that run or evaluate a string -- the guard's own stated concern (#4015).
_STRING_EXECUTING_BUILTINS = frozenset({
    "complete",
    "compgen",
    "eval",
    "exec",
    "source",
    ".",
    "command",
    "builtin",
    "trap",
    "time",
    "coproc",
    "enable",
    "fc",
})

# The same roots the #4015 reproduction command scanned: every agent-facing instruction surface.
_SEARCH_ROOTS: tuple[str, ...] = ("plugins", "docs", "rules", ".claude")
_ADDITIONAL_FILES: tuple[str, ...] = ("AGENTS.md",)

# Extensions that carry agent-facing instructions or CLI flag specifications in this repository.
_SCANNED_SUFFIXES = frozenset({".md", ".py", ".json", ".yaml", ".yml"})

# graphify-out/ is a generated knowledge-graph cache already excluded from every mechanical check
# in .pre-commit-config.yaml; scanning it here would fail on a docstring edit that has not yet
# been re-synced by a graphify run, which is not the drift this test exists to catch.
_EXCLUDED_DIR_NAMES = frozenset({"graphify-out"})


def _colliding_flag_values() -> dict[str, str]:
    """Every ``ledger_spec`` flag whose accepted value collides with a string-executing builtin.

    Returns:
        Flag name to its one colliding value (there is exactly one per flag today).
    """
    collisions: dict[str, str] = {}
    for command in ledger_spec.COMMANDS:
        for flag in command.flags:
            if not flag.value:
                continue
            for candidate in flag.value.split("|"):
                if candidate in _STRING_EXECUTING_BUILTINS:
                    collisions[flag.name] = candidate
    return collisions


def _candidate_files() -> list[Path]:
    """Every scanned-suffix file under the search roots, minus generated caches and this file.

    Returns:
        Sorted absolute file paths.
    """
    self_path = Path(__file__).resolve()
    files: list[Path] = []
    for root_name in _SEARCH_ROOTS:
        root = _REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in _SCANNED_SUFFIXES or not path.is_file():
                continue
            if path.resolve() == self_path:
                continue
            if any(part in _EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            files.append(path)
    for name in _ADDITIONAL_FILES:
        path = _REPO_ROOT / name
        if path.exists():
            files.append(path)
    return sorted(files)


def _bare_instruction_pattern(flag: str, value: str) -> re.Pattern[str]:
    """Match ``flag`` followed by ``value`` as its own shell word: space- or quote-separated.

    ``--flag=value`` is a single shell word and never matches; that is exactly what distinguishes
    a safe instruction from the guard's bare-word reading this test must not find.

    Args:
        flag: The long option, e.g. ``--result``.
        value: The colliding value, e.g. ``complete``.

    Returns:
        A compiled pattern to search documentation text with.
    """
    return re.compile(rf"{re.escape(flag)}[ \t]+\"?{re.escape(value)}\b")


def test_no_documented_invocation_types_a_colliding_bare_value() -> None:
    """No scanned file instructs typing a builtin-colliding value as its own shell word."""
    collisions = _colliding_flag_values()
    assert collisions, "ledger_spec.COMMANDS named no colliding flag; update this test's premise"

    patterns = {flag: _bare_instruction_pattern(flag, value) for flag, value in collisions.items()}
    offenders: list[str] = []
    for path in _candidate_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in patterns.values():
            match = pattern.search(text)
            if match is None:
                continue
            line_number = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(_REPO_ROOT)}:{line_number}: {match.group(0)!r}")

    assert not offenders, (
        "These instructions type a bash-guard-colliding value as a bare shell word; omit the flag "
        "to take its default, or write it as a single --flag=value token instead:\n"
        + "\n".join(f"  {offender}" for offender in offenders)
    )
