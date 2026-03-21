"""Root conftest.py for the claude_skills repository.

Excludes standalone sub-projects that have their own pyproject.toml and pytest
configuration from root-level collection. These projects must be tested
independently via ``uv run pytest`` from their own directory.

Without this exclusion, pytest resolves their conftest.py files relative to the
sub-project root (which uv adds to sys.path as an installable package), producing
module names that collide with other ``tests/conftest.py`` files also resolved
from their respective package roots on sys.path.
"""

from __future__ import annotations

# Standalone sub-projects with their own pyproject.toml + pytest config.
# Each is excluded from root collection to prevent conftest module name collisions.
collect_ignore_glob = ["plugins/scientific-method/*"]
