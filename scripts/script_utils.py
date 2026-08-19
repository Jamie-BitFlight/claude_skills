"""Small helpers shared across standalone scripts/*.py maintenance tools."""

from __future__ import annotations

import json
import subprocess
from shutil import which
from typing import Any


def run_gh_json(arguments: list[str]) -> dict[str, Any]:
    """Run ``gh`` and parse its JSON response without exposing authentication data.

    Returns:
        Decoded JSON object emitted by the GitHub CLI.
    """
    gh_binary = which("gh")
    if gh_binary is None:
        raise RuntimeError("GitHub CLI executable 'gh' was not found on PATH")
    process = subprocess.run([gh_binary, *arguments], check=False, capture_output=True, text=True)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or f"gh exited with {process.returncode}")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("gh returned invalid JSON") from error


def title_case_from_kebab(name: str) -> str:
    """Convert a kebab-case plugin identifier to a display name.

    Returns:
        The display name.
    """
    return " ".join(part.capitalize() for part in name.split("-") if part)
