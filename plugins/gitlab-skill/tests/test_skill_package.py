from __future__ import annotations

import json
import tomllib
from pathlib import Path

import marko
from marko.inline import Link

PLUGIN_ROOT = Path(__file__).parents[1]
SKILL_ROOT = PLUGIN_ROOT / "skills" / "gitlab-skill"

OBSOLETE_STEPS_TERMS = ("CI/CD Steps", "`step:`", "`step.yml`", "${{ step_dir }}", "${{ job.")


def markdown_links(path: Path) -> list[str]:
    """Return link destinations from a Markdown document."""
    document = marko.parse(path.read_text(encoding="utf-8"))
    links: list[str] = []

    def visit(element: object) -> None:
        if isinstance(element, Link):
            links.append(element.dest)
        children = getattr(element, "children", None)
        if isinstance(children, list):
            for child in children:
                visit(child)

    visit(document)
    return links


def load_evals() -> list[dict[str, object]]:
    """Return the GitLab skill's behavioral eval cases."""
    data = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
    assert data["skill_name"] == "gitlab-skill"
    assert isinstance(data["evals"], list)
    return data["evals"]


def test_routed_references_resolve() -> None:
    """Every relative route in the skill router must resolve inside the package."""
    skill_path = SKILL_ROOT / "SKILL.md"
    for destination in markdown_links(skill_path):
        if destination.startswith(("http://", "https://", "#")):
            continue
        target = (skill_path.parent / destination.split("#", maxsplit=1)[0]).resolve()
        assert target.is_file(), f"missing routed reference: {destination}"


def test_references_include_source_metadata() -> None:
    """Every routed reference identifies its evidence source and review date or revision."""
    skill_path = SKILL_ROOT / "SKILL.md"
    routed = [destination for destination in markdown_links(skill_path) if destination.startswith("./references/")]
    for destination in routed:
        content = (SKILL_ROOT / destination).read_text(encoding="utf-8")
        source_lines = [line for line in content.splitlines() if line.startswith("SOURCE: <")]
        assert source_lines, f"{destination} has no source metadata"
        assert all("accessed " in line or "reviewed " in line for line in source_lines)


def test_steps_terminology_is_limited_to_official_migration_mapping() -> None:
    """Obsolete Steps names occur only in the explicit Functions migration section."""
    functions_path = SKILL_ROOT / "references" / "gitlab-functions.md"
    heading = "## Steps-to-Functions Migration Mapping"
    functions_before_migration, migration = functions_path.read_text(encoding="utf-8").split(heading, maxsplit=1)

    active_paths = [SKILL_ROOT / "SKILL.md", PLUGIN_ROOT / "README.md"]
    active_paths.extend(path for path in SKILL_ROOT.joinpath("references").glob("*.md") if path != functions_path)
    active_paths.extend(PLUGIN_ROOT / directory / "plugin.json" for directory in (".claude-plugin", ".codex-plugin"))
    active_content = functions_before_migration + "\n".join(path.read_text(encoding="utf-8") for path in active_paths)
    assert all(term not in active_content for term in OBSOLETE_STEPS_TERMS)
    assert all(term in migration for term in OBSOLETE_STEPS_TERMS)


def test_eval_file_uses_supported_schema() -> None:
    """Every eval has the complete package schema and a unique ID."""
    evaluations = load_evals()
    required = {"id", "should_activate", "reference", "prompt", "expected_output", "expectations"}
    assert evaluations
    assert all(evaluation.keys() == required for evaluation in evaluations)

    ids = [evaluation["id"] for evaluation in evaluations]
    assert all(isinstance(eval_id, int) for eval_id in ids)
    assert len(ids) == len(set(ids))
    assert all(isinstance(evaluation["should_activate"], bool) for evaluation in evaluations)
    assert all(
        isinstance(evaluation["prompt"], str)
        and evaluation["prompt"]
        and isinstance(evaluation["expected_output"], str)
        and evaluation["expected_output"]
        and isinstance(evaluation["expectations"], list)
        and evaluation["expectations"]
        and all(isinstance(expectation, str) and expectation for expectation in evaluation["expectations"])
        for evaluation in evaluations
    )


def test_eval_references_cover_router_behavior() -> None:
    """Positive and negative evals implement the router's reference contract."""
    routed_references = {
        destination.removeprefix("./")
        for destination in markdown_links(SKILL_ROOT / "SKILL.md")
        if destination.startswith("./references/")
    }
    evaluations = load_evals()
    positive_evals = [evaluation for evaluation in evaluations if evaluation["should_activate"]]
    negative_evals = [evaluation for evaluation in evaluations if not evaluation["should_activate"]]
    positive_references = [evaluation["reference"] for evaluation in positive_evals]

    assert all(isinstance(reference, str) for reference in positive_references)
    assert all(evaluation["reference"] is None for evaluation in negative_evals)
    assert len(positive_references) == len(set(positive_references))
    assert set(positive_references) == routed_references


def test_package_has_no_runtime_or_credential_mutation_surface() -> None:
    """The package is a read-only skill with no activation or credential tooling."""
    assert not list(PLUGIN_ROOT.joinpath("commands").glob("*.md"))
    assert not list(PLUGIN_ROOT.joinpath("scripts").glob("*.py"))
    assert not list(SKILL_ROOT.joinpath("scripts").glob("*.py"))


def test_default_pytest_collection_includes_plugin_tests() -> None:
    """The normal repository suite must collect this plugin's tests."""
    pyproject = tomllib.loads((PLUGIN_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert "plugins/gitlab-skill/tests" in pyproject["tool"]["pytest"]["ini_options"]["testpaths"]
