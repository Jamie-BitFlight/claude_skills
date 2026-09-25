"""Structural regressions for the authored Fact-Check handoff, not agent evaluations.

Load the real producer and consumer instructions as Markdown. These tests detect
schema/routing drift; they do not prove a model followed the instructions or that
a live backlog write succeeded. Behavioral cases live with work-backlog-item.
"""

from pathlib import Path

import pytest
from markdown_it import MarkdownIt

PLUGIN = Path(__file__).resolve().parents[1]
GROOM = PLUGIN / "skills/work-backlog-item/references/workflows/groom"
AGENT = PLUGIN / "agents/fact-checker.md"
REQUIRED_FIELDS = {"verdict", "claim", "evidence", "source"}
READERS = (
    (AGENT, "Step 4: Return Verdict"),
    (GROOM / "swarm.md", "Fact-Checker output contract"),
    (GROOM / "finalize.md", "RT-ICA Final Pass"),
    (GROOM / "finalize.md", "Output Validation Gate"),
    (GROOM / "finalize.md", "Hypothesis Resolution"),
)


def section_text(path: Path, heading: str) -> str:
    """Read a real Markdown section, excluding its following sibling sections."""
    text = path.read_text(encoding="utf-8")
    tokens = MarkdownIt().parse(text)
    start = None
    level = 0
    lines = text.splitlines(keepends=True)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.map is None:
            continue
        if start is not None and int(token.tag[1:]) <= level:
            return "".join(lines[start : token.map[0]])
        if tokens[index + 1].content == heading:
            start = token.map[0]
            level = int(token.tag[1:])
    if start is None:
        raise AssertionError(f"Missing contract section {heading!r} in {path}")
    return "".join(lines[start:])


def result_contract(path: Path, heading: str) -> tuple[Path, dict[str, str]]:
    """Resolve the inline legacy template or the bundled canonical reference."""
    tokens = MarkdownIt().enable("table").parse(section_text(path, heading))
    for token in tokens:
        if token.type == "fence" and token.info == "text":
            fields = {}
            for line in token.content.splitlines():
                if line and not line[0].isspace() and ":" in line:
                    key, value = line.split(":", 1)
                    fields[key] = value.strip()
            if any(key.lower() == "verdict" for key in fields):
                return path.resolve(), fields
    for token in tokens:
        for child in token.children or ():
            if child.type != "link_open":
                continue
            href = child.attrGet("href") or ""
            relative = href.split("#", 1)[0]
            if Path(relative).name == "fact-check-result.md":
                target = (path.parent / relative).resolve()
                assert target.is_relative_to(PLUGIN.resolve()), "Contract must ship inside DH"
                return result_contract(target, "Result record")
    raise AssertionError(f"No Fact-Check result contract reachable from {path}#{heading}")


def test_producer_template_satisfies_existing_consumer_fields() -> None:
    """The original uppercase producer fails the actual lowercase swarm contract."""
    _, producer = result_contract(AGENT, "Step 4: Return Verdict")
    _, consumer = result_contract(GROOM / "swarm.md", "Fact-Checker output contract")
    assert REQUIRED_FIELDS <= consumer.keys()
    assert REQUIRED_FIELDS <= producer.keys(), f"Producer fields: {sorted(producer)}"
    assert producer["verdict"] == consumer["verdict"]


@pytest.mark.parametrize(("path", "heading"), READERS)
def test_each_reader_reaches_the_same_bundled_contract(path: Path, heading: str) -> None:
    """Publication, field validation and identity matching have one schema owner."""
    owner, fields = result_contract(path, heading)
    assert owner == (GROOM / "fact-check-result.md").resolve()
    assert REQUIRED_FIELDS <= fields.keys()
    assert {value.strip() for value in fields["verdict"].split("|")} == {
        "VERIFIED",
        "REFUTED",
        "INCONCLUSIVE",
    }


def test_unavailable_evidence_example_is_an_explicit_inconclusive_result() -> None:
    """Lack of a source cannot masquerade as a supported positive verdict."""
    text = section_text(GROOM / "fact-check-result.md", "Unavailable evidence")
    blocks = [token.content for token in MarkdownIt().parse(text) if token.type == "fence"]
    assert len(blocks) == 1
    fields = dict(line.split(": ", 1) for line in blocks[0].splitlines() if ": " in line)
    assert REQUIRED_FIELDS <= fields.keys()
    assert fields["verdict"] == "INCONCLUSIVE"
    assert fields["evidence"].startswith("unavailable — ")
    assert fields["source"].startswith("unavailable — ")
