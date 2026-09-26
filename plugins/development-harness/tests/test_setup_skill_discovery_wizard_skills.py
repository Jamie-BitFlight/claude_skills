"""Structural regression: the wizard's skill_rules mappings name real skills.

skill_discovery-schema.md requires each `use` element to be `provider:skill-name`, and
Phase 3 passes it to the harness's skill loader. An agent name or a bare name in a
wizard-questions.md mapping produces a config the consumer cannot load.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from markdown_it import MarkdownIt

PLUGIN = Path(__file__).resolve().parents[1]
WIZARD = PLUGIN / "skills/setup-skill-discovery/references/wizard-questions.md"
PLUGINS_ROOT = PLUGIN.parent
SKILL_ID = re.compile(r"^[a-z0-9-]+:[a-z0-9-]+$")


def local_plugin_dirs() -> dict[str, Path]:
    """Map each sibling plugin's install name to its directory."""
    dirs = {}
    for manifest in PLUGINS_ROOT.glob("*/.claude-plugin/plugin.json"):
        dirs[json.loads(manifest.read_text(encoding="utf-8"))["name"]] = manifest.parents[1]
    return dirs


def wizard_use_entries() -> list[str]:
    """Every `use` element from the wizard's YAML `skill_rules` mappings."""
    entries = []
    for token in MarkdownIt().parse(WIZARD.read_text(encoding="utf-8")):
        if token.type != "fence" or token.info.strip() != "yaml":
            continue
        for rule in yaml.safe_load(token.content) or []:
            # A `use:` holding only a comment is resolved from the run's candidate_skills.
            entries.extend(rule.get("use") or [])
    return entries


def test_wizard_mappings_are_parsed() -> None:
    assert wizard_use_entries(), "no skill_rules use entries parsed from wizard-questions.md"


@pytest.mark.parametrize("skill_id", wizard_use_entries())
def test_wizard_use_entry_names_a_skill(skill_id: str) -> None:
    assert SKILL_ID.match(skill_id), f"{skill_id!r} is not in provider:skill-name format"
    provider, name = skill_id.split(":")
    plugin_dir = local_plugin_dirs().get(provider)
    if plugin_dir is None:
        pytest.skip(f"provider {provider!r} is not a plugin in this checkout")
    assert (plugin_dir / "skills" / name / "SKILL.md").is_file(), (
        f"{skill_id!r} does not resolve to a skill in {plugin_dir.name}"
        + (" (it names an agent)" if (plugin_dir / "agents" / f"{name}.md").is_file() else "")
    )
