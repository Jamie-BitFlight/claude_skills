"""Health subcommand — team member JSONL action inspection and tmux pane capture."""

from __future__ import annotations

import json
import operator
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_TEAMS_DIR = Path.home() / ".claude/teams"


def capture_pane_by_id(pane_id: str) -> str:
    """Capture the visible output of a specific tmux pane by its pane ID.

    Returns the full pane content as a string (no line limit), or an error
    description if the capture fails.

    Args:
        pane_id: tmux pane identifier (e.g. '%0', 'session:window.pane').

    Returns:
        Captured pane content, or an error string beginning with '('.
    """
    if not pane_id:
        return ""
    if not (tmux := shutil.which("tmux")):
        return "(tmux not found)"
    try:
        result = subprocess.run(
            [tmux, "capture-pane", "-t", pane_id, "-p"], capture_output=True, text=True, timeout=5, check=False
        )
    except subprocess.TimeoutExpired:
        return f"(tmux timeout capturing pane {pane_id})"
    except OSError as exc:
        return f"(tmux error: {exc})"
    else:
        if result.returncode == 0:
            return result.stdout
        return f"(pane {pane_id} not found)"


def jsonl_dir_for_project() -> Path:
    """Derive the JSONL project directory from the current git repository slug.

    Falls back to ~/.claude/projects/ if git is unavailable.

    Returns:
        Path to the directory containing .jsonl session files.
    """
    git = shutil.which("git")
    if git:
        result = subprocess.run([git, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            slug = result.stdout.strip().replace("/", "-")
            return Path.home() / ".claude" / "projects" / slug
    return Path.home() / ".claude" / "projects"


def latest_team() -> str | None:
    """Return the name of the most recently modified team.

    Returns:
        Team directory name, or None if no teams exist.
    """
    teams = sorted(_TEAMS_DIR.glob("*/config.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    return teams[0].parent.name if teams else None


def extract_actions(text: str, n: int | None) -> list[str]:
    """Extract tool-use and text actions from a JSONL session.

    Args:
        text: Full contents of a .jsonl session file.
        n: Maximum number of actions to return, or None to return all actions.

    Returns:
        List of formatted action strings, newest last.
    """
    lines = text.splitlines()
    actions: list[str] = []
    for ln in lines:
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if rec.get("type") != "assistant":
            continue
        ts = rec.get("timestamp", "")[:19].replace("T", " ")
        for item in rec.get("content", []):
            if item.get("type") == "tool_use":
                inp = str(item.get("input", {})).replace("\n", " ")
                actions.append(f"  {ts}  {item['name']}({inp})")
            elif item.get("type") == "text" and item.get("text", "").strip():
                text_content = item["text"].strip().replace("\n", " ")
                actions.append(f"  {ts}  [text] {text_content}")
    return actions[-n:] if n is not None else actions


def agent_last_actions(
    name: str, lead_session: str | None, jsonl_dir: Path, n: int | None = None, agent_id: str | None = None
) -> tuple[list[str], str]:
    """Find the agent's JSONL session and return last N actions.

    For the team-lead:  use lead_session directly (exact file known).
    For sub-agents: search each session for the agent name or agentId. The
                    team-lead session references teammate names too, so choose
                    the candidate where either search term appears earliest.

    Args:
        name: Bare agent name (e.g. ``t1-step-procedures``).
        lead_session: Session ID for the team lead, or None for sub-agents.
        jsonl_dir: Directory containing .jsonl session files.
        n: Maximum number of actions to return, or None to return all actions.
        agent_id: Full agentId string (e.g. ``t1-step-procedures@impl-p1135``).
            When provided, both ``name`` and ``agent_id`` are searched; the
            earlier match position in each file is used as the sort key.

    Returns:
        Tuple of (action_lines, session_filename). Empty list and empty string on failure.
    """
    jsonl_files = sorted(jsonl_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)

    if lead_session:
        jf = jsonl_dir / f"{lead_session}.jsonl"
        try:
            text = jf.read_text()
        except OSError:
            return [], ""
        return extract_actions(text, n), jf.name

    candidates: list[tuple[int, Path]] = []
    for jf in jsonl_files:
        try:
            text = jf.read_text(errors="ignore")
        except OSError:
            continue
        positions: list[int] = []
        pos_name = text.find(name)
        if pos_name != -1:
            positions.append(pos_name)
        if agent_id:
            pos_id = text.find(agent_id)
            if pos_id != -1:
                positions.append(pos_id)
        if positions:
            candidates.append((min(positions), jf))

    if not candidates:
        return [], ""

    candidates.sort(key=operator.itemgetter(0))
    _, best = candidates[0]
    try:
        text = best.read_text()
    except OSError:
        return [], ""
    return extract_actions(text, n), best.name


def run_health(team_name: str | None, jsonl_dir: Path | None, action_limit: int | None = None) -> None:
    """Display last JSONL actions and tmux pane content for each team member.

    Args:
        team_name: Team name to inspect, or None to use the most recently modified team.
        jsonl_dir: Directory containing .jsonl files. Derived from git slug if None.
        action_limit: Maximum actions per member, or None to print all actions.
    """
    resolved_team = team_name or latest_team()
    if not resolved_team:
        print("No teams found.")
        return

    resolved_jsonl_dir = jsonl_dir if jsonl_dir is not None else jsonl_dir_for_project()

    cfg_path = _TEAMS_DIR / resolved_team / "config.json"
    if not cfg_path.exists():
        print(f"Team not found: {resolved_team}")
        return

    try:
        cfg: dict[str, Any] = json.loads(cfg_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read team config: {exc}")
        return

    members: list[dict[str, Any]] = cfg.get("members", [])
    lead_session: str | None = cfg.get("leadSessionId")

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'━' * 64}")
    print(f"  Team : {resolved_team}")
    print(f"  Now  : {now}")
    print(f"  Agents: {len(members)}")
    print(f"{'━' * 64}")

    for m in members:
        member_name: str = m.get("name", "?")
        atype: str = m.get("agentType", "")
        pane_id: str = m.get("tmuxPaneId", "")
        is_lead = member_name == "team-lead"

        print(f"\n▶ {member_name}  [{atype}]")

        actions, session = agent_last_actions(
            name=member_name,
            lead_session=lead_session if is_lead else None,
            jsonl_dir=resolved_jsonl_dir,
            n=action_limit,
            agent_id=m.get("agentId"),
        )
        if session:
            print(f"  session: {session}")
        if actions:
            for a in actions:
                print(a)
        else:
            print("  (no actions found in sessions)")

        if pane_id:
            content = capture_pane_by_id(pane_id)
            tail = content.replace("\n", "↵")
            print(f"  tmux[{pane_id}]: …{tail}")
        else:
            print("  tmux: no pane assigned")

    print(f"\n{'━' * 64}\n")
