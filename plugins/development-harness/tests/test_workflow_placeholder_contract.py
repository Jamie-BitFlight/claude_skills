"""Cross-component contract between workflow placeholders and the invocation parser."""

from __future__ import annotations

import json
import re
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_WORKFLOWS_ROOT = _PLUGIN_ROOT / "skills" / "work-backlog-item" / "references" / "workflows"
_PARSE_SCHEMA = _PLUGIN_ROOT / "skills" / "work-backlog-item" / "scripts" / "parser" / "parse.schema.json"
_PLACEHOLDER_RE = re.compile(r"<([a-z_]+)/>")


def test_every_workflow_placeholder_is_a_declared_parser_field() -> None:
    """Every workflow substitution key is produced by the parser schema."""
    schema = json.loads(_PARSE_SCHEMA.read_text(encoding="utf-8"))
    declared = set(schema["properties"])

    used: set[str] = set()
    for path in _WORKFLOWS_ROOT.rglob("*.md"):
        used.update(_PLACEHOLDER_RE.findall(path.read_text(encoding="utf-8")))

    undeclared = used - declared
    assert not undeclared, (
        "Workflow placeholders have no parser output field: "
        f"{sorted(undeclared)!r}. Add a real parser field or remove the unsupported placeholder."
    )
