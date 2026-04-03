#!/usr/bin/env python3
"""Get task context for implementation manager dynamic injection."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# dh_paths is at plugins/development-harness/dh_paths.py.
# This script lives at plugins/development-harness/skills/implementation-manager/scripts/
# parents[0]=scripts, [1]=implementation-manager, [2]=skills, [3]=development-harness
_DH_PLUGIN_DIR = Path(__file__).resolve().parents[3]
if str(_DH_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_DH_PLUGIN_DIR))

import dh_paths as _dh_paths


def get_available_features() -> dict[str, Any]:
    """Get list of features with task files.

    Returns:
        Dictionary containing features array, count, and optional message.
    """
    try:
        plan_path = _dh_paths.plan_dir()
    except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError) as e:
        return {"features": [], "count": 0, "message": f"Could not resolve plan dir: {e}"}

    if not plan_path.exists():
        return {
            "features": [],
            "count": 0,
            "message": f"Not in a project with task files (no plan/ directory at {plan_path})",
        }

    try:
        # Run implementation_manager.py list-features
        script_path = Path(__file__).parent / "implementation_manager.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "list-features", "."], capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            parsed: dict[str, Any] = json.loads(result.stdout)
        else:
            return {"features": [], "count": 0, "message": f"Failed to list features: {result.stderr}"}
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return {"features": [], "count": 0, "message": f"Error running implementation_manager.py: {e}"}
    else:
        return parsed


def get_active_task() -> str:
    """Get active task context if any.

    Reads from the DH state context directory (``~/.dh/projects/{slug}/context/``
    or DH_STATE_HOME override) rather than the legacy ``.claude/context/`` path.
    The legacy path is no longer used after the T05 migration.

    Returns:
        JSON content of active task file, or message if no active task.
    """
    try:
        ctx_dir = _dh_paths.context_dir()
    except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError) as e:
        return f"No active task (could not resolve context dir: {e})"

    if not ctx_dir.exists():
        return "No active task"

    # Find active-task-*.json files
    task_files = list(ctx_dir.glob("active-task-*.json"))
    if not task_files:
        return "No active task"

    # Return first match
    try:
        return task_files[0].read_text(encoding="utf-8")
    except OSError as e:
        return f"Error reading task context: {e}"


def main() -> None:
    """Print task context information."""
    features = get_available_features()
    print(f"**Available features:**\n```json\n{json.dumps(features, indent=2)}\n```\n")

    active_task = get_active_task()
    print(f"**Active task context:**\n{active_task}")


if __name__ == "__main__":
    main()
