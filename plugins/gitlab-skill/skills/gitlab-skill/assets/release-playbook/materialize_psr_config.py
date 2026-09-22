"""Materialize untracked python-semantic-release config from GitLab CI policy."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


def render_config(default_branch: str, tag_prefix: str, remote_name: str) -> str:
    """Render a standalone PSR TOML configuration.

    Returns:
        Deterministic TOML text.
    """
    if not default_branch:
        raise ValueError("CI_DEFAULT_BRANCH is required")
    if not tag_prefix or any(character.isspace() for character in tag_prefix):
        raise ValueError("RELEASE_TAG_PREFIX must be non-empty and contain no whitespace")
    if not remote_name or any(character.isspace() for character in remote_name):
        raise ValueError("RELEASE_GIT_REMOTE_NAME must be non-empty and contain no whitespace")
    branch_pattern = re.escape(default_branch)
    escaped_pattern = branch_pattern.replace("\\", "\\\\").replace('"', '\\"')
    escaped_prefix = tag_prefix.replace("\\", "\\\\").replace('"', '\\"')
    escaped_remote = remote_name.replace("\\", "\\\\").replace('"', '\\"')
    return f"""[semantic_release]
commit_parser = "conventional"
tag_format = "{escaped_prefix}{{version}}"
version_toml = ["pyproject.toml:project.version"]

[semantic_release.branches.release]
match = "^{escaped_pattern}$"
prerelease = false

[semantic_release.remote]
name = "{escaped_remote}"
type = "gitlab"
token = {{ env = "GITLAB_TOKEN" }}
"""


def main() -> None:
    """Write runtime config outside tracked project configuration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    content = render_config(
        os.environ.get("CI_DEFAULT_BRANCH", ""),
        os.environ.get("RELEASE_TAG_PREFIX", ""),
        os.environ.get("RELEASE_GIT_REMOTE_NAME", ""),
    )
    options.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
