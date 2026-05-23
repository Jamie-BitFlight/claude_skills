"""Live delivery surface validation step for the feature verifier (Step 8).

Implements the live_validation branch logic described in the feature-verifier agent.
Reads quality_gates.live_validation from .dh/language-manifest.yaml and returns
a structured outcome following the feature verifier Step 8 protocol.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from manifest_schema import ManifestValidationError, load_manifest

# Sentinel values that defer live validation to other systems
SENTINEL_AGENT_BROWSER = "agent-browser"
SENTINEL_CLAUDE_SKILL = "claude-skill"

# Exact gap message text mandated by the feature verifier Step 8 protocol
GAP_MESSAGE_NO_LIVE_VALIDATION = (
    "LIVE_VALIDATION: SKIPPED — no live_validation command declared in language manifest.\n"
    "Add quality_gates.live_validation to your .dh/language-manifest.yaml"
    " to enable live delivery surface validation."
)

# Canonical path to the language manifest, relative to project root
MANIFEST_RELATIVE_PATH = Path(".dh") / "language-manifest.yaml"

# Subprocess timeout in seconds for live validation commands
_COMMAND_TIMEOUT = 120


class LiveValidationResult(StrEnum):
    """Result codes for the live validation step."""

    PASS = "PASS"
    GAPS_FOUND = "GAPS_FOUND"
    DEFERRED_BROWSER = "DEFERRED_BROWSER"
    DEFERRED_SKILL = "DEFERRED_SKILL"
    SKIPPED = "SKIPPED"


@dataclass(slots=True)
class LiveValidationOutcome:
    """Structured outcome from the live validation step."""

    result: LiveValidationResult
    gap_message: str | None = None
    command: str | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


def check_live_validation(project_root: Path) -> LiveValidationOutcome:
    """Run live delivery surface validation for a project.

    Reads .dh/language-manifest.yaml from project_root, inspects
    quality_gates.live_validation, and returns a structured outcome
    following the feature verifier Step 8 protocol:

    - Sentinel ``agent-browser`` → DEFERRED_BROWSER (no gap).
    - Sentinel ``claude-skill``  → DEFERRED_SKILL (no gap). The caller is responsible
      for invoking the script manually from the project root::

          ./plugins/development-harness/scripts/run_live_validation_skill.py \
              --skill-path <path> --query <prompt>

      This function does not call it automatically.
    - Absent live_validation     → GAPS_FOUND with gap message.
    - No quality_gates section   → SKIPPED.
    - Command exits 0            → PASS (no gap).
    - Command exits non-zero     → GAPS_FOUND.

    Args:
        project_root: Absolute path to the project root directory.

    Returns:
        LiveValidationOutcome describing the result and captured evidence.
    """
    manifest_path = project_root / MANIFEST_RELATIVE_PATH

    if not manifest_path.exists():
        return LiveValidationOutcome(result=LiveValidationResult.SKIPPED)

    try:
        manifest = load_manifest(manifest_path)
    except (FileNotFoundError, ManifestValidationError):
        return LiveValidationOutcome(result=LiveValidationResult.SKIPPED)

    if manifest.quality_gates is None:
        return LiveValidationOutcome(result=LiveValidationResult.SKIPPED)

    live_val = manifest.quality_gates.live_validation
    if not live_val:
        return LiveValidationOutcome(result=LiveValidationResult.GAPS_FOUND, gap_message=GAP_MESSAGE_NO_LIVE_VALIDATION)

    if live_val == SENTINEL_AGENT_BROWSER:
        return LiveValidationOutcome(result=LiveValidationResult.DEFERRED_BROWSER, command=live_val)

    # DEFERRED_SKILL is intentional: the claude-skill sentinel signals that live validation
    # is delegated to a separate manual invocation of the script at:
    #   ./plugins/development-harness/scripts/run_live_validation_skill.py
    # The caller supplies --skill-path and --query; those arguments are not available
    # at this call site and are outside this function's contract.
    if live_val == SENTINEL_CLAUDE_SKILL:
        return LiveValidationOutcome(result=LiveValidationResult.DEFERRED_SKILL, command=live_val)

    # Run the command verbatim from project root
    try:
        proc = subprocess.run(
            live_val,
            shell=True,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=_COMMAND_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return LiveValidationOutcome(
            result=LiveValidationResult.GAPS_FOUND,
            command=live_val,
            gap_message=(
                f"LIVE_VALIDATION: TIMEOUT — command did not complete within {_COMMAND_TIMEOUT}s.\nCommand: {live_val}"
            ),
        )

    result = LiveValidationResult.PASS if proc.returncode == 0 else LiveValidationResult.GAPS_FOUND
    return LiveValidationOutcome(
        result=result, command=live_val, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr
    )
