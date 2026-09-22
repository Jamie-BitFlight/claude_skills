from __future__ import annotations

import json
import subprocess
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
    """Obsolete names stay out of core/OCI content and live in the migration branch."""
    migration_path = SKILL_ROOT / "references" / "gitlab-functions-steps-migration.md"
    migration = migration_path.read_text(encoding="utf-8")

    active_paths = [PLUGIN_ROOT / "README.md"]
    active_paths.extend(path for path in SKILL_ROOT.joinpath("references").glob("*.md") if path != migration_path)
    active_paths.extend(PLUGIN_ROOT / directory / "plugin.json" for directory in (".claude-plugin", ".codex-plugin"))
    active_content = "\n".join(path.read_text(encoding="utf-8") for path in active_paths)
    assert all(term not in active_content for term in OBSOLETE_STEPS_TERMS)
    assert all(term in migration for term in OBSOLETE_STEPS_TERMS)
    assert "./references/gitlab-functions-steps-migration.md" in (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")


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
    assert routed_references <= set(positive_references)
    for reference in positive_references:
        assert SKILL_ROOT.joinpath(str(reference)).is_file(), reference


def test_negative_evals_exclude_supported_inspection_and_drafting() -> None:
    """Negative prompts request no supported read-only or command-composition branch."""
    negative_prompts = [
        str(evaluation["prompt"]).casefold() for evaluation in load_evals() if not evaluation["should_activate"]
    ]
    supported_terms = ("inspect", "job log", "draft", "compose", "read-only")
    assert all(term not in prompt for prompt in negative_prompts for term in supported_terms)


def test_release_credential_branch_encodes_default_branch_path() -> None:
    """Protected-branch inspection requires numeric project ID and an encoded branch segment."""
    reference = (SKILL_ROOT / "references" / "glab-release-credentials.md").read_text(encoding="utf-8")
    encoded = subprocess.run(
        ["jq", "-sRr", "@uri"], input="release/1.x", text=True, capture_output=True, check=True
    ).stdout.strip()

    assert encoded == "release%2F1.x"
    assert 'case "$PROJECT_ID"' in reference
    assert 'DEFAULT_BRANCH_PATH="$(printf \'%s\' "$DEFAULT_BRANCH" | jq -sRr @uri)"' in reference
    assert "projects/$PROJECT_ID/protected_branches/$DEFAULT_BRANCH_PATH" in reference
    assert 'protected_branches/$DEFAULT_BRANCH"' not in reference


def test_release_evals_select_one_adapter_without_loading_siblings() -> None:
    """Adapter-selection evals name one branch; ordinary lifecycle evals load no evidence."""
    evaluations = load_evals()
    selections: dict[object, list[str]] = {}
    for evaluation in evaluations:
        expectations = evaluation["expectations"]
        assert isinstance(expectations, list)
        selections[evaluation["id"]] = [
            expectation
            for expectation in expectations
            if isinstance(expectation, str) and expectation.startswith("Loads references/release-")
        ]

    assert all(len(selections[eval_id]) == 1 for eval_id in (23, 24, 25))
    assert all(len(links) == 0 for eval_id, links in selections.items() if eval_id not in (23, 24, 25))
    ordinary = [evaluation for evaluation in evaluations if evaluation["id"] in (13, 15, 16, 17, 19)]
    assert all(evaluation["reference"] != "references/release-live-evidence.md" for evaluation in ordinary)
    for evaluation in ordinary:
        expectations = evaluation["expectations"]
        assert isinstance(expectations, list)
        assert "release-live-evidence" not in " ".join(str(expectation) for expectation in expectations)


def test_package_has_no_runtime_or_credential_mutation_surface() -> None:
    """Activation exposes no command or credential-mutation automation."""
    assert not list(PLUGIN_ROOT.joinpath("commands").glob("*.md"))
    assert not list(PLUGIN_ROOT.joinpath("scripts").glob("*.py"))
    helper = SKILL_ROOT / "scripts" / "verify_release_playbook.py"
    assert helper.is_file()
    helper_text = helper.read_text(encoding="utf-8")
    assert all(verb not in helper_text for verb in ('"POST"', '"PUT"', '"PATCH"', '"DELETE"'))
    assert "variable get" not in helper_text


def test_release_playbook_assets_exist() -> None:
    """Universal, derived adapter, and exact live-evidence assets ship together."""
    assets = SKILL_ROOT / "assets" / "release-playbook"
    expected_root = {
        "base.gitlab-ci.yml",
        "semantic-release.gitlab-ci.yml",
        "python-semantic-release.gitlab-ci.yml",
        "generic-package.gitlab-ci.yml",
        "release-notes.gitlab-ci.yml",
        "release-build.gitlab-ci.yml",
        "gitlab-release.gitlab-ci.yml",
        ".releaserc.json",
        "pyproject-semantic-release.toml",
        "live-verified",
    }
    expected_live = {
        "semantic-release.gitlab-ci.yml",
        "python-semantic-release.gitlab-ci.yml",
        ".releaserc.json",
        "pyproject.toml",
    }
    assert {path.name for path in assets.iterdir()} == expected_root
    assert {path.name for path in assets.joinpath("live-verified").iterdir()} == expected_live


def test_release_playbook_routes_conditional_adapter_references() -> None:
    """The universal playbook discloses implementation and evidence only by branch."""
    playbook = (SKILL_ROOT / "references" / "automatic-tag-and-release.md").read_text(encoding="utf-8")
    destinations = set(markdown_links(SKILL_ROOT / "references" / "automatic-tag-and-release.md"))

    assert "## Invariant State Machine" in playbook
    assert "No release:" in playbook
    assert "Release:" in playbook
    assert "## Project Intake" in playbook
    assert "## Adapter Interfaces" in playbook
    assert "## Composition Contract" in playbook
    assert "## Validation Gates" in playbook
    assert "./release-version-adapters.md" in destinations
    assert "./release-publication-adapters.md" in destinations
    assert "./glab-release-credentials.md" in destinations
    assert "./release-live-evidence.md" not in destinations


def test_release_playbook_base_contains_only_shared_contracts() -> None:
    """The base defines routing and hidden contracts without selecting project tools."""
    base = (SKILL_ROOT / "assets" / "release-playbook" / "base.gitlab-ci.yml").read_text(encoding="utf-8")

    assert "workflow:" in base
    assert "stages:" in base
    assert all(
        contract in base
        for contract in (
            ".release_version:",
            ".release_notes:",
            ".release_build:",
            ".release_publish:",
            ".release_create:",
        )
    )
    assert "RELEASE_TAG_REGEX" in base
    assert all(
        stage in base
        for stage in ("release-version", "release-notes", "release-build", "release-publish", "release-create")
    )
    assert "script:" not in base
    assert "image:" not in base
    assert "semantic-release" not in base


def test_derived_adapters_include_and_extend_one_base() -> None:
    """Derived adapters contain implementation only and consume shared contracts."""
    assets = SKILL_ROOT / "assets" / "release-playbook"
    adapters = {
        "semantic-release.gitlab-ci.yml": ".release_version",
        "python-semantic-release.gitlab-ci.yml": ".release_version",
        "release-notes.gitlab-ci.yml": ".release_notes",
        "release-build.gitlab-ci.yml": ".release_build",
        "generic-package.gitlab-ci.yml": ".release_publish",
        "gitlab-release.gitlab-ci.yml": ".release_create",
    }
    for name, contract in adapters.items():
        content = assets.joinpath(name).read_text(encoding="utf-8")
        assert "base.gitlab-ci.yml" in content
        assert f"extends: {contract}" in content
        assert "workflow:" not in content
        assert "stages:" not in content
        assert "DERIVED + CI-LINT-VERIFIED" in content


def test_version_configs_require_project_branch_and_tag_substitution() -> None:
    """Both version tools expose detectable branch and tag markers."""
    assets = SKILL_ROOT / "assets" / "release-playbook"
    node = assets.joinpath(".releaserc.json").read_text(encoding="utf-8")
    psr = assets.joinpath("pyproject-semantic-release.toml").read_text(encoding="utf-8")

    assert "__DEFAULT_BRANCH__" in node
    assert "__RELEASE_TAG_FORMAT__" in node
    assert "__DEFAULT_BRANCH_REGEX__" in psr
    assert "__RELEASE_TAG_FORMAT__" in psr
    assert '"main"' not in node
    assert 'match = "^main$"' not in psr


def test_tag_contracts_require_the_release_regex() -> None:
    """No generic tag condition can select lifecycle tag jobs."""
    base = (SKILL_ROOT / "assets" / "release-playbook" / "base.gitlab-ci.yml").read_text(encoding="utf-8")
    tag_rule = '$CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_TAG =~ $RELEASE_TAG_REGEX'

    assert base.count(tag_rule) == 5
    assert '$CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_TAG\'' not in base


def test_disclosed_release_references_resolve_and_carry_evidence_dates() -> None:
    """Every conditional release branch resolves and identifies dated sources."""
    reference_root = SKILL_ROOT / "references"
    playbook = reference_root / "automatic-tag-and-release.md"
    disclosed = [destination for destination in markdown_links(playbook) if destination.startswith("./")]

    for destination in disclosed:
        target = (reference_root / destination).resolve()
        assert target.is_file(), destination
        source_lines = [
            line for line in target.read_text(encoding="utf-8").splitlines() if line.startswith("SOURCE: <")
        ]
        assert source_lines, destination
        assert all("2026-09-22" in line for line in source_lines)


def test_adapter_indexes_create_real_branch_boundaries() -> None:
    """Each adapter index points to one file per selectable implementation."""
    references = SKILL_ROOT / "references"
    version_links = [
        destination
        for destination in markdown_links(references / "release-version-adapters.md")
        if destination.startswith("./release-version-")
    ]
    publication_links = [
        destination
        for destination in markdown_links(references / "release-publication-adapters.md")
        if destination.startswith("./release-publication-")
    ]

    assert len(version_links) == 2
    assert len(publication_links) == 5
    for destination in [*version_links, *publication_links]:
        assert references.joinpath(destination).is_file(), destination


def test_default_pytest_collection_includes_plugin_tests() -> None:
    """The normal repository suite must collect this plugin's tests."""
    pyproject = tomllib.loads((PLUGIN_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert "plugins/gitlab-skill/tests" in pyproject["tool"]["pytest"]["ini_options"]["testpaths"]
