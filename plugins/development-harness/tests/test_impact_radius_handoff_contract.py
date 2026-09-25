"""Structural regression tests for the Impact Radius producer/consumer contract."""

from __future__ import annotations

from pathlib import Path

from markdown_it import MarkdownIt

PLUGIN = Path(__file__).resolve().parents[1]
AGENT = PLUGIN / "agents/impact-analyst.md"
GROOM = PLUGIN / "skills/work-backlog-item/references/workflows/groom"
CONTRACT = GROOM / "impact-radius-result.md"
REQUIRED_HEADINGS = {
    "Change Frame",
    "Impact Pathways",
    "Code - Producers",
    "Code - Consumers",
    "Code - Other References",
    "Tests",
    "Documentation",
    "Configuration / CI",
    "Agent Instructions",
    "Data / State / Runtime",
    "Models / Prompts / Context",
    "People / Process / Controls",
    "Systems Inventory",
    "Excluded Candidates and Unknown Frontier",
    "Transition, Rollback, and Observability",
    "Risk Summary",
    "Ecosystem Completeness Checklist",
}


def links(path: Path) -> set[Path]:
    """Resolve local Markdown links from one authored file."""
    result: set[Path] = set()
    for token in MarkdownIt().parse(path.read_text(encoding="utf-8")):
        for child in token.children or ():
            if child.type != "link_open":
                continue
            href = child.attrGet("href")
            if not isinstance(href, str) or not href or "://" in href:
                continue
            result.add((path.parent / href.split("#", 1)[0]).resolve())
    return result


def test_agent_and_grooming_reach_same_contract() -> None:
    """Producer and consumer must share one bundled DH schema owner."""
    assert CONTRACT.resolve() in links(AGENT)
    assert CONTRACT.resolve() in links(GROOM / "swarm.md")


def test_contract_preserves_machine_consumed_scope() -> None:
    """The canonical contract keeps fields used by downstream grooming."""
    text = CONTRACT.read_text(encoding="utf-8")
    assert "SCOPE_EXPANSION:" in text
    assert "IMPACT_RADIUS_COMPLETE:" in text
    assert all(f"### {heading}" in text for heading in REQUIRED_HEADINGS)
    assert "Systems Inventory" in text
    assert "replace_section=True" in text


def test_contract_stays_inside_plugin_bundle() -> None:
    """Adapters must not depend on a repository-only contract path."""
    assert CONTRACT.resolve().is_relative_to(PLUGIN.resolve())
