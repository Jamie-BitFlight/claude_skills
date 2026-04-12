#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# ///
r"""Kage-bunshin session manager — bidirectional orchestrator/claude communication.

Provides CLI subcommands for spawning and managing persistent claude CLI sessions
via claude's built-in --worktree and --tmux flags.

Usage:
    spawn.py [--session-id ID] spawn  --name X [--model MODEL] [--max-budget N] "prompt"
    spawn.py [--session-id ID] send   --name X "message"
    spawn.py [--session-id ID] read   --name X
    spawn.py [--session-id ID] status --name X
    spawn.py [--session-id ID] list
    spawn.py [--session-id ID] stop   --name X
    spawn.py [--session-id ID] kill   --name X

Session Isolation:
    --session-id (or KB_SESSION_ID env var) scopes the registry to a single
    orchestrator session.  Each named session gets its own file:

        ~/.dh/projects/{slug}/kage-bunshin/sessions/{session_id}/{name}.json

    Parallel spawns write to disjoint files — no shared-file race condition.

    Omitting --session-id and KB_SESSION_ID defaults to 'default' for all
    subcommands except 'list', which then shows all session IDs.

Session State Directory:
    ~/.dh/projects/{slug}/kage-bunshin/
    Override base with DH_STATE_HOME environment variable.

    Slug is derived from the git repo root path by replacing '/' with '-'.
    Example: /home/user/repos/claude_skills -> -home-user-repos-claude_skills

Architecture — --worktree + --tmux (interactive mode):
    Each session is spawned via:

        tmux new-session -d -s kb-launcher-{name} \\
            claude --worktree {name} --tmux --dangerously-skip-permissions --model {model}

    This launches claude in interactive REPL mode — no -p, no --output-format, no
    --input-format. The session stays alive indefinitely waiting for input.

    The launcher tmux session provides the TTY that --tmux requires. Claude creates
    its own persistent tmux session named: {repo_dir_name}_worktree-{name}
    (e.g. "claude_skills_worktree-test-1")

    After claude initialises, the initial prompt is sent via tmux send-keys:

        tmux send-keys -t {tmux_session} 'initial prompt' Enter

    Subsequent messages are sent the same way:

        tmux send-keys -t {tmux_session} 'follow-up message' Enter

    Output is read by capturing the tmux pane:

        tmux capture-pane -p -J -t {tmux_session} -S -200

Exit Codes:
    0: Success.
    1: Fatal error (session not found, tmux failure, etc.).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "sonnet"
_NAME_MAX_CHARS = 30
_SLUG_RE = re.compile(r"[^a-z0-9]+")
EFFORT_LEVELS: tuple[str, ...] = ("low", "medium", "high", "max")
# Timeout waiting for the claude tmux session to appear after spawn.
_SPAWN_WAIT_SECONDS = 30
# Timeout waiting for a session to exit gracefully after Ctrl-C.
_GRACEFUL_STOP_TIMEOUT = 30.0
# RAM per kage-bunshin session: 2 GiB in bytes.
_RAM_PER_SESSION_BYTES = 2_147_483_648


# ---------------------------------------------------------------------------
# State directory resolution
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


def _git_repo_root() -> Path:
    """Return the root of the current git repository.

    Returns:
        Absolute path to the repository root.

    Raises:
        SystemExit: If the current directory is not inside a git repository.
    """
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        _die(f"not inside a git repository: {result.stderr.strip()}")
    return Path(result.stdout.strip())


def _repo_slug(repo_root: Path) -> str:
    """Derive the project slug from the repository root path.

    Replaces all '/' separators with '-'. The leading '-' is intentional.

    Args:
        repo_root: Absolute path to the git repository root.

    Returns:
        Slug string derived from the path, e.g. '-home-user-repos-project'.
    """
    return str(repo_root).replace("/", "-")


def _repo_dir_name(repo_root: Path) -> str:
    """Return the final path component of the git repo root (the directory name).

    Claude names its tmux sessions as '{repo_dir_name}_worktree-{name}'.

    Args:
        repo_root: Absolute path to the git repository root.

    Returns:
        Directory name string, e.g. 'claude_skills'.
    """
    return repo_root.name


def _session_state_dir() -> Path:
    """Return (and create) the kage-bunshin state directory for the current repo.

    Returns:
        Path to ~/.dh/projects/{slug}/kage-bunshin/, created if absent.
    """
    repo_root = _git_repo_root()
    slug = _repo_slug(repo_root)
    state_dir = _dh_state_home() / "projects" / slug / "kage-bunshin"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


# ---------------------------------------------------------------------------
# Registry helpers — directory-per-entry design
# ---------------------------------------------------------------------------
#
# Design rationale: the old registry-{session_id}.json approach required every
# writer (spawn) to read the file, append its entry, and write the whole file
# back.  When multiple spawns run in parallel they all read the same (possibly
# empty) file, each builds a single-entry dict, and the last os.replace() wins
# — earlier entries are silently lost.
#
# The fix eliminates the shared file entirely:
#
#   sessions/{session_id}/{name}.json   — one file per named session
#
# Write path (spawn):  write only {name}.json.  No read required, no shared
#   state — parallel spawns touch completely disjoint files.
# Read path (list/status):  glob all {name}.json files and aggregate — pure
#   reads, no write contention.
# Cleanup (stop/kill):  delete {name}.json — no read-modify-write cycle.
#
# Old registry-{session_id}.json files left from prior runs are ignored.


def _session_entries_dir(state_dir: Path, session_id: str) -> Path:
    """Return the directory that holds per-entry JSON files for one session.

    Args:
        state_dir: kage-bunshin state directory.
        session_id: Orchestrator session identifier.

    Returns:
        Path to ``sessions/{session_id}/`` (not created here).
    """
    return state_dir / "sessions" / session_id


def _entry_path(state_dir: Path, session_id: str, name: str) -> Path:
    """Return the path to the per-entry JSON file for a named session.

    Args:
        state_dir: kage-bunshin state directory.
        session_id: Orchestrator session identifier.
        name: Session name.

    Returns:
        Path to ``sessions/{session_id}/{name}.json``.
    """
    return _session_entries_dir(state_dir, session_id) / f"{name}.json"


def _load_registry(state_dir: Path, session_id: str) -> dict[str, Any]:
    """Aggregate all per-entry JSON files for a session into a registry dict.

    Globs ``sessions/{session_id}/*.json``, parses each file, and returns
    a dict mapping session name to session metadata.  Missing or corrupt files
    are silently skipped.  If the directory does not exist, returns an empty
    dict (no error).

    Args:
        state_dir: kage-bunshin state directory.
        session_id: Orchestrator session identifier.

    Returns:
        Dictionary mapping session name to session metadata.
    """
    entries_dir = _session_entries_dir(state_dir, session_id)
    if not entries_dir.exists():
        return {}
    registry: dict[str, Any] = {}
    for path in entries_dir.glob("*.json"):
        try:
            entry = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        name = entry.get("name", path.stem)
        registry[name] = entry
    return registry


def _write_entry(state_dir: Path, session_id: str, name: str, entry: dict[str, Any]) -> None:
    """Write a single session entry atomically to its own JSON file.

    Writes to ``{name}.json.tmp`` then renames to ``{name}.json`` so partial
    writes are never visible to concurrent readers.  Creates the parent
    directory if absent.

    Args:
        state_dir: kage-bunshin state directory.
        session_id: Orchestrator session identifier.
        name: Session name (used as the filename stem).
        entry: Session metadata dictionary to persist.
    """
    entries_dir = _session_entries_dir(state_dir, session_id)
    entries_dir.mkdir(parents=True, exist_ok=True)
    target = entries_dir / f"{name}.json"
    tmp = entries_dir / f"{name}.json.tmp"
    tmp.write_text(json.dumps(entry, indent=2))
    Path(tmp).replace(target)


def _delete_entry(state_dir: Path, session_id: str, name: str) -> None:
    """Remove the per-entry JSON file for a named session.

    Silently ignores the case where the file does not exist.

    Args:
        state_dir: kage-bunshin state directory.
        session_id: Orchestrator session identifier.
        name: Session name.
    """
    path = _entry_path(state_dir, session_id, name)
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


def _get_session(state_dir: Path, session_id: str, name: str) -> dict[str, Any]:
    """Retrieve a session entry from its per-entry JSON file, failing loudly if absent.

    Args:
        state_dir: kage-bunshin state directory.
        session_id: Orchestrator session identifier.
        name: Session name.

    Returns:
        Session metadata dictionary.

    Raises:
        SystemExit: If the named session file does not exist.
    """
    path = _entry_path(state_dir, session_id, name)
    if not path.exists():
        _die(f"session '{name}' not found. Run 'list' to see active sessions.")
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        _die(f"session '{name}' registry file is corrupt: {exc}")


# ---------------------------------------------------------------------------
# tmux helpers
# ---------------------------------------------------------------------------


def _claude_tmux_session_name(repo_dir_name: str, name: str) -> str:
    """Return the tmux session name that claude creates for a worktree session.

    Claude follows the pattern: {repo_dir_name}_worktree-{name}.

    Args:
        repo_dir_name: Last path component of the git repository root.
        name: Session name.

    Returns:
        tmux session name string, e.g. 'claude_skills_worktree-test-1'.
    """
    return f"{repo_dir_name}_worktree-{name}"


def _tmux_alive(tmux_session: str) -> bool:
    """Check whether a tmux session is currently alive by its full session name.

    Args:
        tmux_session: Full tmux session name to check.

    Returns:
        True if the tmux session exists, False otherwise.
    """
    result = subprocess.run(["tmux", "has-session", "-t", tmux_session], capture_output=True, check=False)
    return result.returncode == 0


def _tmux_kill(tmux_session: str) -> None:
    """Kill a tmux session by its full name, ignoring errors if it no longer exists.

    Args:
        tmux_session: Full tmux session name.
    """
    subprocess.run(["tmux", "kill-session", "-t", tmux_session], capture_output=True, check=False)


def _tmux_run_in_session(tmux_session: str, cmd: str) -> None:
    """Run a shell command inside an existing tmux session via send-keys.

    Sends the command string followed by Enter. This delivers input to the
    running shell in the tmux session.

    Args:
        tmux_session: Full tmux session name.
        cmd: Shell command string to execute (newline appended automatically).

    Raises:
        SystemExit: If tmux send-keys returns non-zero.
    """
    result = subprocess.run(
        ["tmux", "send-keys", "-t", tmux_session, cmd, "Enter"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        _die(f"tmux send-keys to {tmux_session} failed: {result.stderr.strip()}")


def _tmux_send_ctrlc(tmux_session: str) -> None:
    """Send Ctrl-C to a tmux session to request graceful shutdown.

    Ignores errors (session may already be exiting).

    Args:
        tmux_session: Full tmux session name.
    """
    subprocess.run(["tmux", "send-keys", "-t", tmux_session, "C-c", ""], capture_output=True, check=False)


def _wait_for_session_exit(tmux_session: str, timeout: float) -> bool:
    """Poll until a tmux session is gone or the timeout elapses.

    Args:
        tmux_session: Full tmux session name to watch.
        timeout: Maximum seconds to wait.

    Returns:
        True if the session exited within the timeout, False otherwise.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _tmux_alive(tmux_session):
            return True
        time.sleep(0.5)
    return not _tmux_alive(tmux_session)


# ---------------------------------------------------------------------------
# Error utilities
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit.

    Args:
        message: Error description.
        code: Exit code (default 1).
    """
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def _slugify(text: str) -> str:
    """Convert text to a URL-safe lowercase slug.

    Args:
        text: Input string.

    Returns:
        Slug with non-alphanumeric runs replaced by hyphens.
    """
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:_NAME_MAX_CHARS].rstrip("-")


# ---------------------------------------------------------------------------
# Session concurrency limit (RAM-based)
# ---------------------------------------------------------------------------


def _read_mem_available_bytes() -> int | None:
    """Read MemAvailable from /proc/meminfo and return the value in bytes.

    Returns:
        Available RAM in bytes, or None if /proc/meminfo is unreadable or the
        key is absent.
    """
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            # Format: "MemAvailable:   <N> kB"
            if len(parts) >= 2:  # noqa: PLR2004
                try:
                    return int(parts[1]) * 1024
                except ValueError:
                    return None
    return None


def _count_active_sessions(state_dir: Path) -> int:
    """Count live kage-bunshin sessions across all registry files in state_dir.

    A session is live when its tmux session appears in ``tmux list-sessions``
    output.  Registry entries whose tmux session is absent from the live tmux
    session list are treated as dead and excluded from the count.

    If tmux is not running the command fails non-zero, and the count is 0.

    Args:
        state_dir: kage-bunshin state directory containing registry files.

    Returns:
        Number of live sessions across all registries.
    """
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        # tmux is not running or no sessions exist.
        return 0

    live_sessions: set[str] = set(result.stdout.splitlines())

    count = 0
    sessions_root = state_dir / "sessions"
    if not sessions_root.exists():
        return 0
    for entry_path in sessions_root.glob("*/*.json"):
        # Skip .tmp files that may be mid-write.
        if entry_path.suffix != ".json" or entry_path.stem.endswith(".tmp"):
            continue
        try:
            entry: dict[str, Any] = json.loads(entry_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        tmux_session = entry.get("tmux_session", "")
        if tmux_session and tmux_session in live_sessions:
            count += 1
    return count


def check_session_limit(session_id: str, state_dir: Path) -> tuple[bool, str]:
    """Check whether a new kage-bunshin session may be spawned given available RAM.

    The limit is floor(available_RAM_bytes / _RAM_PER_SESSION_BYTES) — one
    session per 2 GiB of available RAM.  When /proc/meminfo is unreadable the
    check is skipped and (True, "") is returned so spawning is not blocked on
    unreadable hardware info.

    Args:
        session_id: Current orchestrator session ID (unused in computation,
            present for testability and future scoping).
        state_dir: kage-bunshin state directory; registry files are read from
            here to count live sessions.

    Returns:
        Tuple ``(ok, message)`` where ``ok=True`` means the caller may proceed.
        When ``ok=False``, ``message`` contains the formatted error text ready
        to be printed to stderr.
    """
    mem_bytes = _read_mem_available_bytes()
    if mem_bytes is None:
        # Fail open: cannot read hardware info, do not block spawning.
        return True, ""

    mem_gib = mem_bytes / _RAM_PER_SESSION_BYTES
    max_sessions = int(mem_bytes // _RAM_PER_SESSION_BYTES)
    active = _count_active_sessions(state_dir)
    room = max(0, max_sessions - active)

    if active < max_sessions:
        return True, ""

    message = (
        "Kage-bunshin session limit reached.\n"
        f"  Max sessions:      {max_sessions}   (1 per 2 GiB available RAM)\n"
        f"  Available RAM:     {mem_gib:.1f} GiB\n"
        f"  Active sessions:   {active}\n"
        f"  Room for more:     {room}\n"
        "\nPlease wait for existing sessions to complete before starting new ones."
    )
    return False, message


# ---------------------------------------------------------------------------
# Subcommand: spawn
# ---------------------------------------------------------------------------


def _build_spawn_shell_cmd(
    name: str, model: str, max_budget: float | None, session_id: str, tmux_session_name: str, effort: str | None = None
) -> list[str]:
    """Build the command argv list for launching claude in interactive tmux mode.

    Launches claude as an interactive REPL via --worktree and --tmux flags.
    No -p, no --output-format, no --input-format — claude stays alive
    waiting for input delivered via tmux send-keys.

    Args:
        name: Session name (used as the --worktree value).
        model: Model identifier string.
        max_budget: Optional maximum USD spend, or None.
        session_id: Orchestrator session ID — injected as KAGE_BUNSHIN_PARENT_SESSION_ID
            so child hooks can write to the correct notifications file.
        tmux_session_name: The tmux session name being created — injected as
            KAGE_BUNSHIN_TMUX_SESSION so child hooks can identify themselves.
        effort: Optional effort level (low, medium, high, max) injected as
            CLAUDE_CODE_EFFORT_LEVEL env var so the child session uses the
            correct compute budget. When None, no env var is injected and
            claude uses its default effort for the selected model.

    Returns:
        Argv list suitable for passing directly to subprocess or tmux new-session.
    """
    # Inject env vars so child hooks can:
    #   KAGE_BUNSHIN_CHILD=1                  — skip sibling alerts, block recursive spawns
    #   KAGE_BUNSHIN_PARENT_SESSION_ID=<id>   — write notifications to the correct file
    #   KAGE_BUNSHIN_TMUX_SESSION=<name>      — identify this session in notifications
    parts: list[str] = [
        "env",
        "KAGE_BUNSHIN_CHILD=1",
        f"KAGE_BUNSHIN_PARENT_SESSION_ID={session_id}",
        f"KAGE_BUNSHIN_TMUX_SESSION={tmux_session_name}",
    ]
    if effort is not None:
        parts.append(f"CLAUDE_CODE_EFFORT_LEVEL={effort}")
    parts += ["claude", "--dangerously-skip-permissions", "--worktree", name, "--tmux", "--model", model]
    if max_budget is not None:
        parts += ["--max-budget-usd", str(max_budget)]
    return parts


_CLAUDE_INIT_WAIT_SECONDS = 3.0
"""Seconds to wait for claude's interactive REPL to initialise before sending the prompt."""


def cmd_spawn(args: argparse.Namespace) -> None:
    """Spawn a new claude session in interactive REPL mode via --worktree and --tmux.

    Launches claude without -p so it stays alive as an interactive session.
    Wraps the invocation in a tmux new-session -d to provide the TTY that
    --tmux requires. After claude's own tmux session appears and initialises,
    the initial prompt is sent via tmux send-keys.

    Args:
        args: Parsed arguments containing name, prompt, model, max_budget fields.
    """
    # Recursion prevention — block nested spawns from child sessions.
    if os.environ.get("KAGE_BUNSHIN_CHILD") == "1":
        print("kage-bunshin: recursive spawn blocked — this session is already a kage-bunshin child", file=sys.stderr)
        sys.exit(1)

    if shutil.which("claude") is None:
        _die("claude binary not found in PATH")
    if shutil.which("tmux") is None:
        _die("tmux binary not found in PATH")

    state_dir = _session_state_dir()
    ok, limit_message = check_session_limit(args.session_id, state_dir)
    if not ok:
        print(limit_message, file=sys.stderr)
        sys.exit(1)

    repo_root = _git_repo_root()
    repo_dir = _repo_dir_name(repo_root)
    registry = _load_registry(state_dir, args.session_id)

    name: str = args.name or _slugify(args.prompt[0])
    if not name:
        _die("could not derive a session name from the prompt; pass --name explicitly")

    claude_tmux_session = _claude_tmux_session_name(repo_dir, name)

    if name in registry:
        if _tmux_alive(claude_tmux_session):
            _die(f"session '{name}' already exists and is alive. Kill it first.")
        # Dead entry — remove stale per-entry file before re-spawning.
        _delete_entry(state_dir, args.session_id, name)

    # Build claude argv for interactive REPL mode (no -p, no --output-format).
    # --worktree creates an isolated git worktree for the session.
    # --tmux keeps claude alive in its own named tmux session.
    claude_argv = _build_spawn_shell_cmd(
        name,
        args.model,
        args.max_budget,
        session_id=args.session_id,
        tmux_session_name=claude_tmux_session,
        effort=args.effort,
    )

    # tmux new-session -d provides the TTY that --tmux requires.
    # Pass claude argv directly as the session command (no bash -c wrapper needed).
    launcher_session = f"kb-launcher-{name}"
    result = subprocess.run(
        ["tmux", "new-session", "-d", "-s", launcher_session, *claude_argv], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        _die(f"tmux new-session failed: {result.stderr.strip()}")

    # Wait for claude to create its own tmux session.
    deadline = time.monotonic() + _SPAWN_WAIT_SECONDS
    while not _tmux_alive(claude_tmux_session):
        if time.monotonic() >= deadline:
            _tmux_kill(launcher_session)
            _die(f"timed out waiting for claude tmux session '{claude_tmux_session}' to appear.")
        time.sleep(0.5)

    # Give claude's interactive REPL time to finish initialising before sending input.
    time.sleep(_CLAUDE_INIT_WAIT_SECONDS)

    # Send the initial prompt as keyboard input to the running REPL.
    _tmux_run_in_session(claude_tmux_session, args.prompt[0])

    spawned_at = datetime.now(UTC).isoformat()
    entry: dict[str, Any] = {
        "name": name,
        "model": args.model,
        "spawned_at": spawned_at,
        "worktree": True,
        "tmux_session": claude_tmux_session,
        "repo_dir": repo_dir,
    }
    _write_entry(state_dir, args.session_id, name, entry)

    record: dict[str, Any] = {
        "name": name,
        "tmux_session": claude_tmux_session,
        "model": args.model,
        "spawned_at": spawned_at,
        "worktree": True,
    }
    print(json.dumps(record))


# ---------------------------------------------------------------------------
# Subcommand: send
# ---------------------------------------------------------------------------


def cmd_send(args: argparse.Namespace) -> None:
    """Send a follow-up message to an existing session via tmux send-keys.

    Sends the message text directly to the claude process running in the
    session's tmux pane via 'tmux send-keys'.

    Args:
        args: Parsed arguments with name and message fields.
    """
    state_dir = _session_state_dir()
    session = _get_session(state_dir, args.session_id, args.name)

    tmux_session = session["tmux_session"]
    if not _tmux_alive(tmux_session):
        _die(f"session '{args.name}' tmux session '{tmux_session}' is dead")

    _tmux_run_in_session(tmux_session, args.message[0])
    print(json.dumps({"status": "sent", "name": args.name}))


# ---------------------------------------------------------------------------
# Subcommand: read
# ---------------------------------------------------------------------------


def cmd_read(args: argparse.Namespace) -> None:
    """Read pane content from a session via tmux capture-pane.

    Captures the last ~200 lines of the tmux pane and prints to stdout.
    Exits non-zero if the session is not alive.

    Args:
        args: Parsed arguments with name field.
    """
    state_dir = _session_state_dir()
    session = _get_session(state_dir, args.session_id, args.name)
    tmux_session = session["tmux_session"]

    if not _tmux_alive(tmux_session):
        print("Session not alive", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        ["tmux", "capture-pane", "-p", "-J", "-t", tmux_session, "-S", "-200"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _die(f"tmux capture-pane failed: {result.stderr.strip()}")

    print(result.stdout, end="")


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------


def cmd_status(args: argparse.Namespace) -> None:
    """Print status for a named session.

    Checks tmux liveness and reports registry metadata.

    Args:
        args: Parsed arguments with name field.
    """
    state_dir = _session_state_dir()
    session = _get_session(state_dir, args.session_id, args.name)

    tmux_session = session["tmux_session"]
    alive = _tmux_alive(tmux_session)

    spawned_at = session.get("spawned_at", "unknown")
    try:
        dt = datetime.fromisoformat(spawned_at)
        age_seconds = (datetime.now(UTC) - dt).total_seconds()
        age_str = _format_age(age_seconds)
    except ValueError:
        age_str = "unknown"

    status: dict[str, Any] = {
        "name": args.name,
        "alive": alive,
        "model": session.get("model"),
        "spawned_at": spawned_at,
        "age": age_str,
        "worktree": session.get("worktree"),
        "tmux_session": tmux_session,
    }
    print(json.dumps(status, indent=2))


# ---------------------------------------------------------------------------
# Subcommand: list
# ---------------------------------------------------------------------------


def _list_session_id_registries(state_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Discover all session-id directories under sessions/ and return (session_id, registry) pairs.

    Iterates ``sessions/*/`` subdirectories — each subdirectory name is a
    session_id.  Calls ``_load_registry`` for each to aggregate the per-entry
    JSON files within it.  Subdirectories that contain no readable entries
    are included as empty registries.

    Args:
        state_dir: kage-bunshin state directory.

    Returns:
        List of ``(session_id, registry_dict)`` tuples, sorted by session_id.
    """
    sessions_root = state_dir / "sessions"
    if not sessions_root.exists():
        return []
    results: list[tuple[str, dict[str, Any]]] = []
    for subdir in sorted(sessions_root.iterdir()):
        if not subdir.is_dir():
            continue
        session_id = subdir.name
        registry = _load_registry(state_dir, session_id)
        results.append((session_id, registry))
    return results


def _print_registry_table(rows: list[dict[str, Any]]) -> None:
    """Print a columnar table of session rows.

    Args:
        rows: List of dicts with keys: name, model, status, age, tmux_session.
              May also include session_id when listing all registries.
    """
    if not rows:
        return

    has_session_id = "session_id" in rows[0]

    col_widths: dict[str, int] = {
        "name": max(len(r["name"]) for r in rows),
        "model": max(len(r["model"]) for r in rows),
        "status": 5,
        "age": max(len(r["age"]) for r in rows),
    }
    if has_session_id:
        col_widths["session_id"] = max(len(r["session_id"]) for r in rows)

    if has_session_id:
        header = (
            f"{'SESSION_ID':<{col_widths['session_id']}}  "
            f"{'NAME':<{col_widths['name']}}  "
            f"{'MODEL':<{col_widths['model']}}  "
            f"{'STATUS':<{col_widths['status']}}  "
            f"{'AGE':<{col_widths['age']}}  "
            f"TMUX_SESSION"
        )
    else:
        header = (
            f"{'NAME':<{col_widths['name']}}  "
            f"{'MODEL':<{col_widths['model']}}  "
            f"{'STATUS':<{col_widths['status']}}  "
            f"{'AGE':<{col_widths['age']}}  "
            f"TMUX_SESSION"
        )
    print(header)
    print("-" * len(header))
    for r in rows:
        if has_session_id:
            print(
                f"{r['session_id']:<{col_widths['session_id']}}  "
                f"{r['name']:<{col_widths['name']}}  "
                f"{r['model']:<{col_widths['model']}}  "
                f"{r['status']:<{col_widths['status']}}  "
                f"{r['age']:<{col_widths['age']}}  "
                f"{r['tmux_session']}"
            )
        else:
            print(
                f"{r['name']:<{col_widths['name']}}  "
                f"{r['model']:<{col_widths['model']}}  "
                f"{r['status']:<{col_widths['status']}}  "
                f"{r['age']:<{col_widths['age']}}  "
                f"{r['tmux_session']}"
            )


def _registry_to_rows(registry: dict[str, Any], session_id: str | None = None) -> list[dict[str, Any]]:
    """Convert a registry dict to a list of display rows.

    Args:
        registry: Dictionary mapping session name to session metadata.
        session_id: When provided, adds a ``session_id`` key to each row.

    Returns:
        List of row dicts suitable for ``_print_registry_table``.
    """
    rows: list[dict[str, Any]] = []
    for name, session in registry.items():
        tmux_session = session.get("tmux_session", "")
        alive = _tmux_alive(tmux_session) if tmux_session else False
        spawned_at = session.get("spawned_at", "")
        try:
            dt = datetime.fromisoformat(spawned_at)
            age_str = _format_age((datetime.now(UTC) - dt).total_seconds())
        except ValueError:
            age_str = "unknown"
        row: dict[str, Any] = {
            "name": name,
            "model": session.get("model", "?"),
            "status": "alive" if alive else "dead",
            "age": age_str,
            "worktree": session.get("worktree", False),
            "tmux_session": tmux_session,
        }
        if session_id is not None:
            row["session_id"] = session_id
        rows.append(row)
    return rows


def cmd_list(args: argparse.Namespace) -> None:
    """List registered sessions with live/dead status.

    When ``--session-id`` is provided (or ``KB_SESSION_ID`` is set), lists only
    sessions in that registry.  When neither is provided, iterates all
    ``sessions/*/`` subdirectories and lists every session across all session
    IDs, showing which ``SESSION_ID`` each belongs to.

    Args:
        args: Parsed arguments.  ``args.session_id`` is ``None`` when the user
              did not supply ``--session-id`` and ``KB_SESSION_ID`` is unset.
    """
    state_dir = _session_state_dir()

    if args.session_id is not None:
        # Scoped list: show only this session's registry.
        registry = _load_registry(state_dir, args.session_id)
        if not registry:
            print("No sessions registered.")
            return
        rows = _registry_to_rows(registry)
        _print_registry_table(rows)
        return

    # Unscoped list: aggregate all registries.
    all_pairs = _list_session_id_registries(state_dir)
    rows = []
    for sid, registry in all_pairs:
        rows.extend(_registry_to_rows(registry, session_id=sid))

    if not rows:
        print("No sessions registered.")
        return
    _print_registry_table(rows)


# ---------------------------------------------------------------------------
# Subcommand: stop
# ---------------------------------------------------------------------------


def cmd_stop(args: argparse.Namespace) -> None:
    """Stop a session gracefully by sending Ctrl-C and waiting for clean exit.

    Sends C-c to the claude tmux session to trigger graceful shutdown
    (session persistence, hook execution, cleanup).  Polls until the session
    exits.  If the session does not exit within _GRACEFUL_STOP_TIMEOUT seconds,
    the session is force-killed instead.

    If the tmux session is already dead, the registry entry is cleaned up and
    success is reported.

    The launcher tmux session (kb-launcher-{name}) is also killed if it still
    exists after the main session exits.

    Args:
        args: Parsed arguments with name field.
    """
    state_dir = _session_state_dir()
    session = _get_session(state_dir, args.session_id, args.name)

    tmux_session = session.get("tmux_session", "")
    launcher_session = f"kb-launcher-{args.name}"
    forced = False

    if not tmux_session or not _tmux_alive(tmux_session):
        # Session already dead — just clean up the registry entry.
        _delete_entry(state_dir, args.session_id, args.name)
        _tmux_kill(launcher_session)
        print(json.dumps({"status": "stopped", "name": args.name, "forced": False, "already_dead": True}))
        return

    # Send Ctrl-C to request graceful shutdown.
    _tmux_send_ctrlc(tmux_session)

    exited = _wait_for_session_exit(tmux_session, _GRACEFUL_STOP_TIMEOUT)
    if not exited:
        # Graceful timeout exceeded — force kill.
        _tmux_kill(tmux_session)
        forced = True

    # Clean up launcher session whether or not we force-killed.
    _tmux_kill(launcher_session)

    _delete_entry(state_dir, args.session_id, args.name)

    print(json.dumps({"status": "stopped", "name": args.name, "forced": forced}))


# ---------------------------------------------------------------------------
# Subcommand: kill
# ---------------------------------------------------------------------------


def cmd_kill(args: argparse.Namespace) -> None:
    """Kill a session: kill the claude tmux session and remove its registry entry.

    Args:
        args: Parsed arguments with name field.
    """
    state_dir = _session_state_dir()
    session = _get_session(state_dir, args.session_id, args.name)

    tmux_session = session.get("tmux_session", "")
    if tmux_session:
        _tmux_kill(tmux_session)

    _delete_entry(state_dir, args.session_id, args.name)

    print(json.dumps({"status": "killed", "name": args.name}))


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_age(seconds: float) -> str:
    """Format a duration in seconds as a human-readable age string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Age string like '5m', '2h', '3d', or '45s'.
    """
    seconds = int(seconds)
    if seconds < 60:  # noqa: PLR2004
        return f"{seconds}s"
    if seconds < 3600:  # noqa: PLR2004
        return f"{seconds // 60}m"
    if seconds < 86400:  # noqa: PLR2004
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with all subcommands.

    The ``--session-id`` flag scopes the registry to that orchestrator session,
    preventing concurrent read-modify-write collisions.  Falls back to the
    ``KB_SESSION_ID`` environment variable, then defaults to ``"default"`` for
    backwards compatibility — except for the ``list`` subcommand, where the
    default is ``None`` so that omitting ``--session-id`` lists all registries.

    Returns:
        Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="spawn.py",
        description="Kage-bunshin: bidirectional manager for persistent claude sessions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--session-id",
        default=None,
        metavar="ID",
        help=("Scope registry to this orchestrator session (env: KB_SESSION_ID; default: 'default')."),
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    # spawn
    p_spawn = sub.add_parser("spawn", help="Launch a new claude session.")
    p_spawn.add_argument("prompt", nargs=1, metavar="PROMPT", help="Initial prompt to send.")
    p_spawn.add_argument("--name", default=None, help="Session name (auto-derived from prompt if omitted).")
    p_spawn.add_argument("--model", default=_DEFAULT_MODEL, help=f"Model to use (default: {_DEFAULT_MODEL}).")
    p_spawn.add_argument("--max-budget", type=float, default=None, metavar="USD", help="Maximum USD spend.")
    p_spawn.add_argument(
        "--effort",
        default=None,
        choices=list(EFFORT_LEVELS),
        metavar="LEVEL",
        help="Effort level for the spawned session: low, medium, high, or max (default: inherit from model).",
    )
    p_spawn.set_defaults(func=cmd_spawn)

    # send
    p_send = sub.add_parser("send", help="Send a follow-up message to a running session.")
    p_send.add_argument("--name", required=True, help="Session name.")
    p_send.add_argument("message", nargs=1, metavar="MESSAGE", help="Message text to send.")
    p_send.set_defaults(func=cmd_send)

    # read
    p_read = sub.add_parser("read", help="Read responses from a session.")
    p_read.add_argument("--name", required=True, help="Session name.")
    p_read.add_argument(
        "--wait", type=float, default=0.0, metavar="SECONDS", help="(Unused) Retained for interface compatibility."
    )
    p_read.add_argument(
        "--follow", action="store_true", default=False, help="(Unused) Retained for interface compatibility."
    )
    p_read.set_defaults(func=cmd_read)

    # status
    p_status = sub.add_parser("status", help="Show status of a session.")
    p_status.add_argument("--name", required=True, help="Session name.")
    p_status.set_defaults(func=cmd_status)

    # list
    p_list = sub.add_parser("list", help="List all registered sessions.")
    p_list.set_defaults(func=cmd_list)

    # stop
    p_stop = sub.add_parser(
        "stop", help="Gracefully stop a session by sending Ctrl-C, waiting for clean exit, then cleaning up."
    )
    p_stop.add_argument("--name", required=True, help="Session name.")
    p_stop.set_defaults(func=cmd_stop)

    # kill
    p_kill = sub.add_parser("kill", help="Kill a session and remove its registry entry.")
    p_kill.add_argument("--name", required=True, help="Session name.")
    p_kill.set_defaults(func=cmd_kill)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and dispatch to the appropriate subcommand handler.

    Resolves ``session_id`` after parsing:

    - If ``--session-id`` was explicitly supplied, use that value.
    - Otherwise fall back to the ``KB_SESSION_ID`` environment variable.
    - For all subcommands except ``list``, default to ``"default"`` when
      neither source provides a value.
    - For ``list``, leave ``session_id`` as ``None`` when neither source
      provides a value so that all registries are shown.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Resolve session_id: explicit flag > env var > subcommand default.
    if args.session_id is None:
        env_id = os.environ.get("KB_SESSION_ID", "").strip()
        if env_id:
            args.session_id = env_id
        elif args.command != "list":
            args.session_id = "default"
        # else: leave as None — cmd_list shows all registries

    args.func(args)


if __name__ == "__main__":
    main()
