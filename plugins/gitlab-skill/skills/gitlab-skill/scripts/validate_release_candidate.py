# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Resolve worktree-local GitLab CI includes and submit one static CI Lint candidate."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

JsonObject = dict[str, object]
LintRunner = Callable[[Sequence[str], str, float], str]


class CandidateValidationError(RuntimeError):
    """Describe a bounded candidate-resolution or lint failure."""


def deep_merge(base: JsonObject, overlay: Mapping[str, object]) -> JsonObject:
    """Apply GitLab-style map merge where later scalar/list values replace earlier ones.

    Returns:
        A new merged mapping.
    """
    merged = dict(base)
    for key, value in overlay.items():
        previous = merged.get(key)
        if isinstance(previous, dict) and isinstance(value, Mapping):
            merged[key] = deep_merge(previous, value)
        else:
            merged[key] = value
    return merged


def local_include_paths(value: object) -> list[str]:
    """Return local include paths and reject include types requiring remote resolution.

    Returns:
        Ordered project-local paths.
    """
    entries = value if isinstance(value, list) else [value]
    paths: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            paths.append(entry)
        elif isinstance(entry, dict) and set(entry) == {"local"} and isinstance(entry["local"], str):
            paths.append(entry["local"])
        else:
            raise CandidateValidationError("candidate includes must be project-local paths")
    return paths


def load_yaml_mapping(path: Path) -> JsonObject:
    """Load one YAML mapping.

    Returns:
        String-keyed configuration.
    """
    loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        raise CandidateValidationError(f"candidate file is not a mapping: {path.name}")
    return loaded


def resolve_candidate(root_file: Path) -> JsonObject:
    """Resolve nested project-local includes from the worktree in declared order.

    Returns:
        One include-free candidate mapping.
    """
    root_file = root_file.resolve(strict=True)
    project_root = root_file.parent
    active: set[Path] = set()

    def resolve(path: Path) -> JsonObject:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(project_root):
            raise CandidateValidationError("local include escapes the candidate project root")
        if resolved in active:
            raise CandidateValidationError("local include cycle detected")
        active.add(resolved)
        content = load_yaml_mapping(resolved)
        include_value = content.pop("include", None)
        merged: JsonObject = {}
        if include_value is not None:
            for include_path in local_include_paths(include_value):
                relative = include_path.removeprefix("/")
                merged = deep_merge(merged, resolve(project_root / relative))
        active.remove(resolved)
        return deep_merge(merged, content)

    return resolve(root_file)


def validate_tag_contract(candidate: JsonObject) -> None:
    """Require release tag prefix, regex, and wildcard to describe one policy."""
    variables = candidate.get("variables")
    if not isinstance(variables, dict):
        return
    keys = {"RELEASE_TAG_PREFIX", "RELEASE_TAG_REGEX", "RELEASE_TAG_WILDCARD"}
    present = keys & set(variables)
    if not present:
        return
    if present != keys or not all(isinstance(variables[key], str) for key in keys):
        raise CandidateValidationError("release tag contract requires string prefix, regex, and wildcard")
    prefix = variables["RELEASE_TAG_PREFIX"]
    escaped_prefix = re.escape(prefix).replace(r"\-", "-")
    expected_regex = rf"/^{escaped_prefix}[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$/"
    if variables["RELEASE_TAG_REGEX"] != expected_regex or variables["RELEASE_TAG_WILDCARD"] != f"{prefix}*":
        raise CandidateValidationError("release tag prefix, regex, and wildcard are inconsistent")


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Terminate a timed-out glab process and descendants."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        taskkill = shutil.which("taskkill")
        if taskkill:
            subprocess.run(
                [taskkill, "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            process.kill()
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)


def run_glab(arguments: Sequence[str], payload: str, timeout: float) -> str:
    """Run one bounded glab request with JSON stdin.

    Returns:
        Standard output.
    """
    glab = shutil.which("glab")
    if glab is None:
        raise CandidateValidationError("glab is unavailable")
    process = subprocess.Popen(
        [glab, *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    try:
        stdout, _stderr = process.communicate(payload, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        terminate_process_tree(process)
        process.communicate()
        raise CandidateValidationError("CI Lint request timed out") from error
    if process.returncode != 0:
        raise CandidateValidationError("CI Lint request failed")
    return stdout


def validate_candidate(
    *, root_file: Path, host: str, project_id: int, timeout: float, runner: LintRunner = run_glab
) -> JsonObject:
    """Resolve and statically lint one candidate without remote include lookup.

    Returns:
        Compact agent-facing result data.
    """
    candidate = resolve_candidate(root_file)
    validate_tag_contract(candidate)
    content = yaml.safe_dump(candidate, sort_keys=False)
    payload = json.dumps({"content": content, "include_jobs": True}, separators=(",", ":"))
    response: Any = json.loads(
        runner(
            [
                "api",
                "--hostname",
                host,
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "--input",
                "-",
                f"projects/{project_id}/ci/lint",
            ],
            payload,
            timeout,
        )
    )
    if not isinstance(response, dict):
        raise CandidateValidationError("CI Lint returned a non-object response")
    jobs = response.get("jobs", [])
    job_names = [item.get("name") for item in jobs if isinstance(item, dict) and isinstance(item.get("name"), str)]
    valid = response.get("valid") is True
    errors = response.get("errors", [])
    if not isinstance(errors, list) or not all(isinstance(item, str) for item in errors):
        raise CandidateValidationError("CI Lint returned malformed errors")
    return {
        "ok": valid,
        "valid": valid,
        "errors": errors,
        "jobs": job_names,
        "pre_merge_contexts": ["static"],
        "deferred_contexts": ["default_branch", "matching_tag", "nonmatching_tag"],
    }


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse candidate target inputs.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Candidate root .gitlab-ci.yml in the worktree.")
    parser.add_argument("--host", required=True, help="Bare GitLab hostname.")
    parser.add_argument("--project-id", type=int, required=True, help="Numeric project ID providing CI Lint context.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Bound for the one CI Lint request.")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Emit one compact JSON result.

    Returns:
        Zero for valid, one for lint-invalid, or two for execution/input error.
    """
    options = parse_arguments(arguments)
    try:
        result = validate_candidate(
            root_file=options.root, host=options.host, project_id=options.project_id, timeout=options.timeout
        )
    except (CandidateValidationError, FileNotFoundError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(json.dumps({"ok": False, "error": type(error).__name__, "message": str(error)}, separators=(",", ":")))
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
