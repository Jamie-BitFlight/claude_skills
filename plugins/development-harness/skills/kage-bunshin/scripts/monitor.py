#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# ///
"""Kage-bunshin session monitor — detects interactive states in child Claude Code sessions.

Subcommands:
  poll   Poll tmux sessions registered for the current orchestrator session and exit as soon as
         a state requiring intervention is detected, or when all sessions complete/idle.
  health Show last JSONL actions + tmux pane content for each teammate in a team.

Usage:
    uv run monitor.py poll --session-id <id> [--state-dir <path>] [--interval <s>] [--timeout <s>]
    uv run monitor.py health [team-name] [--jsonl-dir <path>]

Exit codes (poll subcommand):
    0: Success (all_complete, intervention_needed, or timeout — check JSON status field).
    1: Fatal error (registry missing, unexpected failure).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

from health import run_health

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[mGKHFJA-Za-z]|\x1b\][^\x07]*\x07|\x1b[()][AB012]")

# Interactive-state detection patterns (applied to captured pane lines).
# U+276F = HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT (Claude REPL prompt char)
# U+25CF = BLACK CIRCLE (used as radio-button selector in some TUI permission prompts)
_PATTERN_PERMISSION = re.compile(r"^[\u276f>][\u25cf]?\s+(?:Allow|Deny)", re.IGNORECASE)
_PATTERN_YES_NO = re.compile(r"\[Y/n\]|\[y/N\]", re.IGNORECASE)
_PATTERN_ASK_USER = re.compile(r"AskUserQuestion", re.IGNORECASE)
_PATTERN_QUESTION_PHRASE = re.compile(r"Do you want to|Would you like to", re.IGNORECASE)

# Idle prompt: bare U+276F or $ at end of line (U+276F is the Claude REPL cursor)
_PATTERN_IDLE = re.compile(r"^[\u276f$]\s*$")

# Number of tail lines checked for yes/no prompts
_YES_NO_TAIL_LINES = 5
# Number of content lines included in intervention_needed output
_CONTENT_TAIL_LINES = 10


# ---------------------------------------------------------------------------
# State directory / registry resolution
# ---------------------------------------------------------------------------


def _dh_state_home() -> Path:
    """Return the DH state home directory, respecting DH_STATE_HOME override.

    Returns:
        Path to the base DH state directory (~/.dh/ or $DH_STATE_HOME).
    """
    override = os.environ.get("DH_STATE_HOME", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".dh"


def _require_exe(name: str) -> str:
    """Return the full path to an executable, or exit with an error.

    Args:
        name: Executable name to locate via PATH.

    Returns:
        Full absolute path to the executable.

    Raises:
        SystemExit: If the executable is not found.
    """
    if not (path := shutil.which(name)):
        _emit_error(f"required executable not found: {name}")
        sys.exit(1)
    return path


def _git_repo_slug() -> str:
    """Derive the project slug from the current git repository root.

    Returns:
        Slug string with '/' replaced by '-', e.g. '-home-user-repos-project'.

    Raises:
        SystemExit: If not inside a git repository.
    """
    git = _require_exe("git")
    result = subprocess.run([git, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        _emit_error(f"not inside a git repository: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip().replace("/", "-")


def _resolve_state_dir(explicit_state_dir: str | None) -> Path:
    """Resolve the base state directory.

    Args:
        explicit_state_dir: User-supplied --state-dir value, or None.

    Returns:
        Resolved Path to the base state directory (not the kage-bunshin subdir).
    """
    if explicit_state_dir:
        return Path(explicit_state_dir).expanduser()
    slug = _git_repo_slug()
    return _dh_state_home() / "projects" / slug


def _registry_path(state_dir: Path, session_id: str) -> Path:
    """Return the path to the session-scoped registry file.

    Args:
        state_dir: Base state directory (e.g. ~/.dh/projects/{slug}/).
        session_id: Orchestrator session identifier.

    Returns:
        Path to kage-bunshin/registry-{session_id}.json.
    """
    return state_dir / "kage-bunshin" / f"registry-{session_id}.json"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _emit(payload: dict[str, Any]) -> None:
    """Write a JSON payload to stdout and flush.

    Args:
        payload: Dictionary to serialise as JSON.
    """
    print(json.dumps(payload), flush=True)


def _emit_error(message: str) -> None:
    """Emit an error status JSON object.

    Args:
        message: Human-readable error description.
    """
    _emit({"status": "error", "message": message})


# ---------------------------------------------------------------------------
# ANSI stripping
# ---------------------------------------------------------------------------


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from a string.

    Args:
        text: Raw terminal output potentially containing ANSI codes.

    Returns:
        Plain text with ANSI codes removed.
    """
    return _ANSI_ESCAPE_RE.sub("", text)


# ---------------------------------------------------------------------------
# tmux interface
# ---------------------------------------------------------------------------


def _live_tmux_sessions() -> set[str]:
    """Return the set of tmux session names currently running.

    Returns:
        Set of session name strings. Empty set if tmux is not running or has
        no sessions.
    """
    if not (tmux := shutil.which("tmux")):
        return set()
    result = subprocess.run(
        [tmux, "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _capture_pane(session_name: str, lines: int = 30) -> list[str] | None:
    """Capture the last N lines of a tmux pane as plain-text lines.

    Args:
        session_name: tmux session name to capture.
        lines: Number of history lines to include (negative offset).

    Returns:
        List of stripped plain-text lines, or None if capture failed.
    """
    if not (tmux := shutil.which("tmux")):
        return None
    result = subprocess.run(
        [tmux, "capture-pane", "-p", "-J", "-t", session_name, "-S", f"-{lines}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    raw = _strip_ansi(result.stdout)
    return list(raw.splitlines())


# ---------------------------------------------------------------------------
# Interactive state detection
# ---------------------------------------------------------------------------


def _detect_interactive_state(lines: list[str]) -> str | None:
    """Analyse pane output lines for interactive states requiring intervention.

    Args:
        lines: Last N lines of captured tmux pane output (ANSI stripped).

    Returns:
        Interaction type string if detected, or None if no intervention needed.
    """
    tail5 = lines[-_YES_NO_TAIL_LINES:] if len(lines) >= _YES_NO_TAIL_LINES else lines
    for line in tail5:
        if _PATTERN_YES_NO.search(line):
            return "yes_no_prompt"

    for line in lines:
        if _PATTERN_PERMISSION.match(line.strip()):
            return "permission_approval"
        if _PATTERN_ASK_USER.search(line):
            return "question"
        if _PATTERN_QUESTION_PHRASE.search(line):
            return "question"

    for line in reversed(lines):
        stripped = line.rstrip()
        if not stripped:
            continue
        if _PATTERN_IDLE.match(stripped):
            break
        if stripped.endswith("?"):
            return "question"
        break

    return None


def _is_idle(lines: list[str]) -> bool:
    """Return True if the session appears idle (waiting at a bare shell/repl prompt).

    A session is idle if the last non-empty line is a bare prompt and no interactive
    pattern was detected.

    Args:
        lines: Last N lines of captured tmux pane output (ANSI stripped).

    Returns:
        True if the session is at an idle prompt with no pending interaction.
    """
    for line in reversed(lines):
        stripped = line.rstrip()
        if stripped:
            return bool(_PATTERN_IDLE.match(stripped))
    return False


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


def _load_registry(registry_path: Path) -> list[dict[str, Any]] | None:
    """Load the kage-bunshin registry JSON file.

    Args:
        registry_path: Path to the registry JSON file.

    Returns:
        List of session entry dicts, or None if the file cannot be read/parsed.
    """
    try:
        raw = registry_path.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        return cast("list[dict[str, Any]]", list(data.values()))
    if isinstance(data, list):
        return cast("list[dict[str, Any]]", data)
    return None


# ---------------------------------------------------------------------------
# Poll subcommand — main loop
# ---------------------------------------------------------------------------


def _run_monitor(session_id: str, state_dir: Path, interval: float, timeout: float) -> None:
    """Run the monitoring poll loop.

    Args:
        session_id: Orchestrator session identifier.
        state_dir: Base state directory.
        interval: Seconds between polls.
        timeout: Maximum seconds to run before emitting timeout status.
    """
    reg_path = _registry_path(state_dir, session_id)

    if not reg_path.exists():
        _emit_error(f"registry not found: {reg_path}")
        sys.exit(1)

    registry = _load_registry(reg_path)
    if registry is None:
        _emit_error(f"registry not found: {reg_path}")
        sys.exit(1)

    registered_sessions: set[str] = {
        entry["tmux_session"] for entry in registry if isinstance(entry, dict) and "tmux_session" in entry
    }

    if not registered_sessions:
        _emit({"status": "all_complete"})
        return

    deadline = time.monotonic() + timeout

    while True:
        live = _live_tmux_sessions()
        active_sessions = registered_sessions & live

        if not active_sessions:
            _emit({"status": "all_complete"})
            return

        for session_name in sorted(active_sessions):
            lines = _capture_pane(session_name)
            if lines is None:
                continue

            interaction_type = _detect_interactive_state(lines)
            if interaction_type is not None:
                content_lines = lines[-_CONTENT_TAIL_LINES:] if len(lines) >= _CONTENT_TAIL_LINES else lines
                content = "\n".join(line.rstrip() for line in content_lines)
                _emit({
                    "status": "intervention_needed",
                    "session": session_name,
                    "type": interaction_type,
                    "content": content,
                })
                return

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _emit({"status": "timeout", "active_sessions": sorted(active_sessions)})
            return

        time.sleep(min(interval, remaining))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with poll and health subcommands.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Kage-bunshin monitor: poll sessions for interactive states or inspect team health.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="subcommand")

    # --- poll subcommand ---
    poll = sub.add_parser(
        "poll",
        help="Poll tmux sessions for interactive states requiring orchestrator attention.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    poll.add_argument(
        "--session-id", required=True, metavar="ID", help="Claude orchestrator session ID — resolves registry-<ID>.json"
    )
    poll.add_argument(
        "--state-dir", default=None, metavar="PATH", help="Base state directory (default: ~/.dh/projects/<git-slug>/)"
    )
    poll.add_argument(
        "--interval", type=float, default=5.0, metavar="SECONDS", help="Seconds between polls (default: 5)"
    )
    poll.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        metavar="SECONDS",
        help="Maximum seconds to run before emitting timeout status (default: 300)",
    )

    # --- health subcommand ---
    health = sub.add_parser(
        "health",
        help="Show last JSONL actions and tmux pane content per team member.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    health.add_argument(
        "team_name", nargs="?", default=None, metavar="TEAM", help="Team name (default: most recently modified team)"
    )
    health.add_argument(
        "--jsonl-dir",
        default=None,
        metavar="PATH",
        help="Directory containing .jsonl session files (default: derived from git repo slug)",
    )

    return parser


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.subcommand == "poll":
        try:
            state_dir = _resolve_state_dir(args.state_dir)
        except OSError as exc:
            _emit_error(f"failed to resolve state directory: {exc}")
            sys.exit(1)
        try:
            _run_monitor(session_id=args.session_id, state_dir=state_dir, interval=args.interval, timeout=args.timeout)
        except (OSError, subprocess.CalledProcessError, KeyError, ValueError) as exc:
            _emit_error(f"unexpected error: {exc}")
            sys.exit(1)

    elif args.subcommand == "health":
        jsonl_dir = Path(args.jsonl_dir).expanduser() if args.jsonl_dir else None
        run_health(team_name=args.team_name, jsonl_dir=jsonl_dir)

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
