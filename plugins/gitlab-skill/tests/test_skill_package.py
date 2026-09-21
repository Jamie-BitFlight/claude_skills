from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

import marko
from marko.inline import Link

PLUGIN_ROOT = Path(__file__).parents[1]
SKILL_ROOT = PLUGIN_ROOT / "skills" / "gitlab-skill"

EVAL_REFERENCE_SUPPORT = {
    1: (
        "references/ci-cd-components-and-inputs.md",
        (
            "root `.gitlab-ci.yml`",
            "$CI_COMMIT_SHA",
            "set the project as a Catalog project",
            "recommends configuring the tag pipeline to test components before the release job",
            "release` keyword",
            "semantic-version tag",
            "include:component",
            "spec:inputs",
        ),
    ),
    2: (
        "references/ci-cd-components-and-inputs.md",
        ("pipeline creation time", "up to 20 inputs", "GitLab 17.7", "external secrets management provider"),
    ),
    3: (
        "references/gitlab-functions.md",
        ("not ready for production use", "func.yml", "output_file", "job-level `run`"),
    ),
    4: ("references/pipeline-optimization.md", ("syntax and logic", "pipeline simulation")),
    5: (
        "references/security-and-deprecations.md",
        ("with `default`", "Replace `only` and `except`", "pages.publish", "strategy: mirror", "include:integrity"),
    ),
    6: ("references/gitlab-ci-local-guide.md", ("--skip-input-validation", "Required inputs", "--fetch-includes")),
}


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


def test_skill_has_no_activation_time_source_writes() -> None:
    """The installed skill must not synchronize or collect context on activation."""
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "sync-gitlab-docs" not in skill
    assert "CLAUDE_PLUGIN_ROOT" not in skill
    assert "gitlab_context" not in skill
    assert not list((SKILL_ROOT / "scripts").glob("*"))


def test_checked_in_markdown_links_resolve() -> None:
    """Every relative Markdown link in the skill package must resolve."""
    for markdown_path in SKILL_ROOT.rglob("*.md"):
        for destination in markdown_links(markdown_path):
            if destination.startswith(("http://", "https://", "#")):
                continue
            target = (markdown_path.parent / destination.split("#", maxsplit=1)[0]).resolve()
            assert target.exists(), f"{markdown_path}: missing link target {destination}"


def test_removed_runtime_workflows_are_not_referenced() -> None:
    """Removed context collection and GLFM validation must have no active references."""
    active_paths = [SKILL_ROOT / "SKILL.md", PLUGIN_ROOT / "README.md"]
    for directory in (".claude-plugin", ".codex-plugin"):
        active_paths.extend((PLUGIN_ROOT / directory).glob("*.json"))
    content = "\n".join(path.read_text(encoding="utf-8") for path in active_paths)
    assert "gitlab_context" not in content
    assert "get_gitlab_context" not in content
    assert "validate_glfm" not in content
    assert "sync_gitlab_docs" not in content


def test_steps_terminology_is_limited_to_official_migration_mapping() -> None:
    """Active content must teach Functions, retaining Steps only as migration context."""
    allowed = {SKILL_ROOT / "references" / "gitlab-functions.md", PLUGIN_ROOT / "README.md"}
    active_paths = [SKILL_ROOT / "SKILL.md", PLUGIN_ROOT / "README.md"]
    active_paths.extend(SKILL_ROOT.joinpath("references").glob("*.md"))
    active_paths.extend((PLUGIN_ROOT / directory / "plugin.json") for directory in (".claude-plugin", ".codex-plugin"))
    for path in active_paths:
        if "CI/CD Steps" in path.read_text(encoding="utf-8"):
            assert path in allowed


def test_eval_file_uses_supported_schema() -> None:
    """Each evaluation must include nonempty expectation text."""
    data = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
    assert data["skill_name"] == "gitlab-skill"
    assert all({"id", "prompt", "expected_output", "expectations"} <= evaluation.keys() for evaluation in data["evals"])
    assert all(evaluation["expectations"] for evaluation in data["evals"])


def test_selected_eval_phrases_appear_in_routed_references() -> None:
    """Selected phrases used by behavioral evaluations must appear in their routed references."""
    data = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
    evaluations = {evaluation["id"]: evaluation for evaluation in data["evals"]}

    assert set(EVAL_REFERENCE_SUPPORT) <= evaluations.keys()
    for eval_id, (relative_path, evidence) in EVAL_REFERENCE_SUPPORT.items():
        reference = (SKILL_ROOT / relative_path).read_text(encoding="utf-8")
        missing = [claim for claim in evidence if claim not in reference]
        assert not missing, f"eval {eval_id} is missing reference phrases: {missing}"


def test_component_and_function_evals_assert_documented_behavior() -> None:
    """High-scope evals must score the official test, release, and authoring details they request."""
    data = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
    evaluations = {evaluation["id"]: evaluation for evaluation in data["evals"]}
    component_expectations = "\n".join(evaluations[1]["expectations"])
    function_expectations = "\n".join(evaluations[3]["expectations"])

    for required in (
        "$CI_COMMIT_SHA",
        "Catalog project",
        "release keyword",
        "recommends component tests before the release job",
        "semantic-version tag",
    ):
        assert required in component_expectations
    for required in ("not ready for production", "func.yml", "job-level run", "output_file"):
        assert required in function_expectations


def test_setup_command_routes_to_portable_companion() -> None:
    """The setup command must invoke its shipped Python companion instead of embedding a manager."""
    command = (PLUGIN_ROOT / "commands" / "setup-ci-publish-token.md").read_text(encoding="utf-8")

    companion = PLUGIN_ROOT / "scripts" / "setup_ci_publish_token.py"
    assert companion.is_file()
    assert 'uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/setup_ci_publish_token.py"' in command
    assert "```sh" not in command
    assert "glab variable delete" not in command
    assert "glab token rotate" not in command
    assert "GLAB_ENABLE_CI_AUTOLOGIN=true" in command
    assert "glab release create" in command
    assert "--use-package-registry" in command
    assert "protected branch or protected tag" in command
    assert "Settings > Repository > Branch rules" in command
    assert "Settings > Repository > Protected tags" in command
    assert "Settings > Repository > Protected branches" not in command


def test_token_command_is_disclosed_as_claude_code_only() -> None:
    """Only Claude Code metadata may advertise the Claude-specific command launcher."""
    readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
    claude_manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    codex_manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    catalog = (PLUGIN_ROOT.parents[1] / "README.md").read_text(encoding="utf-8")

    assert "Claude Code only" in readme
    assert "Claude Code-only" in claude_manifest["description"]
    assert "Claude Code only: includes a fallback command for project access-token setup" in catalog
    assert "project access-token setup" not in codex_manifest["description"]
    assert "project access-token setup" not in codex_manifest["interface"]["shortDescription"]
    assert "project access-token setup" not in codex_manifest["interface"]["longDescription"]


def test_default_pytest_collection_includes_plugin_tests() -> None:
    """The normal repository suite must collect this plugin's tests."""
    pyproject = tomllib.loads((PLUGIN_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert "plugins/gitlab-skill/tests" in pyproject["tool"]["pytest"]["ini_options"]["testpaths"]


def test_plugin_package_contains_no_generated_python_cache() -> None:
    """Generated bytecode must not be shipped with the companion."""
    tracked = subprocess.run(
        ["git", "ls-files", str(PLUGIN_ROOT)], cwd=PLUGIN_ROOT.parents[1], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    assert not [path for path in tracked if "__pycache__" in path or path.endswith(".pyc")]


def test_glfm_alert_guidance_uses_documented_lowercase_examples() -> None:
    """Alert examples and guidance use the lowercase forms in GitLab documentation."""
    reference = (SKILL_ROOT / "references" / "glfm-syntax.md").read_text(encoding="utf-8")

    assert "> [!warning]" in reference
    assert "identifiers are case-insensitive" not in reference
    assert "uppercase is invalid" not in reference
    assert "> [!WARNING]" not in reference
