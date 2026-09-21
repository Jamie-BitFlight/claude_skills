from __future__ import annotations

import json
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


def test_setup_command_uses_current_glab_security_contract() -> None:
    """The setup command must preserve current authentication and token invariants."""
    command = (PLUGIN_ROOT / "commands" / "setup-ci-publish-token.md").read_text(encoding="utf-8")
    script = command.split("```sh\n", maxsplit=1)[1].split("\n```", maxsplit=1)[0]

    assert "${CI_JOB_TOKEN" not in script
    assert "glab variable get" in script
    assert "glab variable list" not in script
    assert "(.hidden | type)" in script
    assert "hidden storage was not verified" in script
    assert "'.value | strings | select(length > 0)'" in script
    assert 'glab token list --repo "${CI_PROJECT_PATH}" --active --output json' in script
    assert "sort_by(.id)" in script
    assert 'new_token_name="${TOKEN_NAME}-$(date -u +%Y%m%d%H%M%S)-$$"' in script
    assert script.count("glab token rotate") == 1
    assert 'glab token rotate "${token_id}"' in script
    assert script.count("glab token create") == 2
    assert "today=$(date -u +%Y-%m-%d)" in script
    assert 'if [ "${expires_int}" -le "${today_int}" ]' in script
    assert "glab variable update" not in script
    assert "glab variable delete" in script
    assert script.index("glab variable delete") < script.index("glab variable set")
    assert "printf '%s' \"${NEW_TOKEN}\" | glab variable set" in script
    assert "--value" not in script
    assert script.count("--duration 8760h") == 3
    assert script.count("--hidden") == 1
    assert script.count("--masked") == 1
    assert script.count("--protected") == 1
    assert "GLAB_ENABLE_CI_AUTOLOGIN=true" in command
    assert "glab release create" in command
    assert "--use-package-registry" in command
    assert "protected branch or protected tag" in command
    assert "Settings > Repository > Branch rules" in command
    assert "Settings > Repository > Protected tags" in command
    assert "Settings > Repository > Protected branches" not in command


def test_glfm_alert_guidance_uses_documented_lowercase_examples() -> None:
    """Alert examples and guidance use the lowercase forms in GitLab documentation."""
    reference = (SKILL_ROOT / "references" / "glfm-syntax.md").read_text(encoding="utf-8")

    assert "> [!warning]" in reference
    assert "identifiers are case-insensitive" not in reference
    assert "uppercase is invalid" not in reference
    assert "> [!WARNING]" not in reference
