from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tomllib
from pathlib import Path
from types import ModuleType

import marko
import pytest
import yaml
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


def bash_blocks(path: Path) -> list[str]:
    """Return bash fenced blocks from a Markdown document."""
    parts = path.read_text(encoding="utf-8").split("```bash")
    return [part.split("```", maxsplit=1)[0] for part in parts[1:]]


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


def test_reference_links_resolve() -> None:
    """Every relative link between references resolves inside the package."""
    references = SKILL_ROOT / "references"
    for reference in references.glob("*.md"):
        for destination in markdown_links(reference):
            if not destination.startswith("./"):
                continue
            target = (reference.parent / destination.split("#", maxsplit=1)[0]).resolve()
            assert target.is_file(), f"{reference.name}: missing reference {destination}"


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
    assert 'PROJECT_JSON="$(glab api --hostname "$HOST" "projects/$PROJECT_SELECTOR")"' in reference
    assert all(field in reference for field in (".id", ".path_with_namespace", ".default_branch", ".ssh_url_to_repo"))
    assert 'VARIABLE_KEY="${VARIABLE_KEY:-RELEASE_PUSH_TOKEN}"' in reference
    assert 'case "$PROJECT_ID"' in reference
    assert 'DEFAULT_BRANCH_PATH="$(printf \'%s\' "$DEFAULT_BRANCH" | jq -sRr @uri)"' in reference
    assert "projects/$PROJECT_ID/protected_branches/$DEFAULT_BRANCH_PATH" in reference
    assert 'protected_branches/$DEFAULT_BRANCH"' not in reference


def test_ci_context_references_separate_candidate_and_existing_ref_tools() -> None:
    """CI context links expose distinct pre-merge and existing-ref command surfaces."""
    references = SKILL_ROOT / "references"
    index = references.joinpath("glab-ci-inspection.md")
    candidate = references.joinpath("glab-ci-candidate-validation.md").read_text(encoding="utf-8")
    existing = references.joinpath("glab-ci-existing-ref-inspection.md").read_text(encoding="utf-8")

    assert set(markdown_links(index)) == {"./glab-ci-candidate-validation.md", "./glab-ci-existing-ref-inspection.md"}
    assert "validate_release_candidate.py" in candidate
    assert "glab ci " not in candidate
    assert "validate_release_candidate.py" not in existing
    assert all(command in existing for command in ("glab ci list", "glab ci get", "glab ci trace", "glab ci lint"))


def test_release_gate_links_both_ci_contexts() -> None:
    """The lifecycle discloses pre-merge and existing-ref references from its gate."""
    lifecycle = SKILL_ROOT / "references" / "automatic-tag-and-release.md"
    destinations = set(markdown_links(lifecycle))

    assert "./glab-ci-candidate-validation.md" in destinations
    assert "./glab-ci-existing-ref-inspection.md" in destinations


@pytest.mark.parametrize(
    ("glab_status", "glab_output", "expected", "expected_status"),
    [
        (0, '{"status":"valid"}', "pipeline", 0),
        (1, "The pipeline did not run. Review the workflow:rules configuration.", "no-pipeline", 0),
        (2, "authentication failed", "no-pipeline", 1),
        (
            2,
            "authentication failed: The pipeline did not run. Review the workflow:rules configuration.",
            "no-pipeline",
            1,
        ),
    ],
)
def test_existing_ref_lint_function_preserves_assertion_semantics(
    glab_status: int, glab_output: str, expected: str, expected_status: int
) -> None:
    """Execute the documented function with deterministic glab outcomes."""
    reference = SKILL_ROOT / "references" / "glab-ci-existing-ref-inspection.md"
    block = next(block for block in bash_blocks(reference) if "lint_existing_ref()" in block)
    function = block.split("\n}\n", maxsplit=1)[0] + "\n}\n"
    script = f"""
glab() {{
  printf '%s\\n' "$GLAB_OUTPUT"
  return "$GLAB_STATUS"
}}
{function}
lint_existing_ref test-ref "$EXPECTED"
"""

    result = subprocess.run(
        ["bash", "-c", script],
        env={
            **os.environ,
            "EXPECTED": expected,
            "GLAB_OUTPUT": glab_output,
            "GLAB_STATUS": str(glab_status),
            "REPO": "git@example.test:group/project.git",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    if expected_status == 0:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0


@pytest.mark.parametrize(
    ("credential_mode", "glab_status"), [("environment", 0), ("persisted", 0), ("environment", 23), ("persisted", 24)]
)
def test_auth_probe_uses_resolved_credentials_and_preserves_failure(credential_mode: str, glab_status: int) -> None:
    """Execute the documented auth probe for both glab credential modes."""
    reference = SKILL_ROOT / "references" / "glab-cli.md"
    probe = next(block for block in bash_blocks(reference) if "glab api --silent user" in block)
    script = f"""
glab() {{
  return "$GLAB_STATUS"
}}
{probe}
"""
    environment: dict[str, str] = {**os.environ, "GLAB_STATUS": str(glab_status)}
    if credential_mode == "environment":
        environment["GITLAB_TOKEN"] = "redacted-test-token"
    else:
        environment.pop("GITLAB_TOKEN", None)

    result = subprocess.run(["bash", "-c", script], env=environment, text=True, capture_output=True, check=False)

    assert result.returncode == glab_status
    if glab_status:
        error = result.stderr.casefold()
        assert "ask the user" in error
        assert "authenticate" in error or "credential" in error


@pytest.mark.parametrize(("mode", "expected_status", "request_errors"), [("transient", 0, 1), ("exhaust", 1, 3)])
def test_bounded_polling_handles_request_failures(
    tmp_path: Path, mode: str, expected_status: int, request_errors: int
) -> None:
    """Execute polling through transient recovery and bound exhaustion."""
    reference = SKILL_ROOT / "references" / "glab-ci-existing-ref-inspection.md"
    block = next(block for block in bash_blocks(reference) if "poll_pipeline()" in block)
    counter_file = tmp_path / "poll-count"
    script = f"""
glab() {{
  count=0
  test -f "$COUNTER_FILE" && count="$(<"$COUNTER_FILE")"
  count=$((count + 1))
  printf '%s' "$count" >"$COUNTER_FILE"
  if test "$MODE" = exhaust || test "$count" -eq 1; then
    return 7
  fi
  printf '%s\\n' '{{"status":"success"}}'
}}
sleep() {{ :; }}
{block}
poll_pipeline 5749
"""
    result = subprocess.run(
        ["bash", "-c", script],
        env={
            **os.environ,
            "COUNTER_FILE": str(counter_file),
            "MAX_ATTEMPTS": "3",
            "MODE": mode,
            "POLL_SECONDS": "0",
            "REPO": "git@example.test:group/project.git",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == expected_status
    assert result.stderr.count("request_error") == request_errors
    if mode == "transient":
        assert "attempt=2 status=success" in result.stdout


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
        ".releaserc.cjs",
        "materialize_psr_config.py",
        "live-verified",
    }
    expected_live = {
        "semantic-release.gitlab-ci.yml",
        "python-semantic-release.gitlab-ci.yml",
        ".releaserc.json",
        "pyproject.toml",
    }
    assert {path.name for path in assets.iterdir() if path.name != "__pycache__"} == expected_root
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


def test_version_configs_derive_branch_and_neutral_tag_policy() -> None:
    """All consumers use base tag environment and fail when it is absent."""
    assets = SKILL_ROOT / "assets" / "release-playbook"
    base = yaml.safe_load((assets / "base.gitlab-ci.yml").read_text(encoding="utf-8"))
    base_prefix = base["variables"]["RELEASE_TAG_PREFIX"]
    node = assets.joinpath(".releaserc.cjs").read_text(encoding="utf-8")
    psr_path = assets / "materialize_psr_config.py"
    spec = importlib.util.spec_from_file_location("materialize_psr_config", psr_path)
    assert spec
    assert spec.loader
    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rendered = module.render_config("release/1.x", base_prefix, "upstream")
    psr = tomllib.loads(rendered)["semantic_release"]

    assert "process.env.CI_DEFAULT_BRANCH" in node
    assert "const tagPrefix = process.env.RELEASE_TAG_PREFIX;" in node
    assert "main" not in node
    node_result = subprocess.run(
        [
            "node",
            "-e",
            f"const c=require({json.dumps(str(assets / '.releaserc.cjs'))}); console.log(JSON.stringify(c))",
        ],
        env={**os.environ, "CI_DEFAULT_BRANCH": "release/1.x", "RELEASE_TAG_PREFIX": base_prefix},
        text=True,
        capture_output=True,
        check=True,
    )
    node_config = json.loads(node_result.stdout)
    assert node_config["branches"] == ["release/1.x"]
    assert node_config["tagFormat"] == f"{base_prefix}${{version}}"
    assert psr["tag_format"] == f"{base_prefix}{{version}}"
    assert psr["branches"]["release"]["match"] == r"^release/1\.x$"
    assert psr["remote"]["name"] == "upstream"
    psr_job = assets.joinpath("python-semantic-release.gitlab-ci.yml").read_text(encoding="utf-8")
    assert 'semantic-release --config "$PSR_RUNTIME_CONFIG" version' in psr_job
    assert 'git checkout -B "$CI_DEFAULT_BRANCH" "$CI_COMMIT_SHA"' in psr_job
    assert 'git branch --set-upstream-to="$RELEASE_GIT_REMOTE_NAME/$CI_DEFAULT_BRANCH"' in psr_job
    assert "RELEASE_GIT_REMOTE_NAME: '__RELEASE_GIT_REMOTE_NAME__'" in psr_job

    missing_prefix_env = {key: value for key, value in os.environ.items() if key != "RELEASE_TAG_PREFIX"}
    missing_prefix_env["CI_DEFAULT_BRANCH"] = "release/1.x"
    node_missing = subprocess.run(
        ["node", "-e", f"require({json.dumps(str(assets / '.releaserc.cjs'))})"],
        env=missing_prefix_env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert node_missing.returncode != 0
    assert "RELEASE_TAG_PREFIX is required" in node_missing.stderr
    with pytest.raises(ValueError, match="RELEASE_TAG_PREFIX"):
        module.render_config("release/1.x", "", "upstream")
    with pytest.raises(ValueError, match="RELEASE_GIT_REMOTE_NAME"):
        module.render_config("release/1.x", base_prefix, "")

    credential = (SKILL_ROOT / "references" / "glab-release-credentials.md").read_text(encoding="utf-8")
    assert 'TAG_PATTERN="${RELEASE_TAG_PREFIX}*"' in credential
    assert 'TAG_PATTERN="${TAG_PATTERN:-' not in credential


def test_generalized_assets_use_predefined_identity_and_no_sandbox_literals() -> None:
    """Generalized assets derive identity while evidence-only files retain observed literals."""
    assets = SKILL_ROOT / "assets" / "release-playbook"
    source_suffixes = {".cjs", ".json", ".py", ".toml", ".yaml", ".yml"}
    generalized = [
        path
        for path in assets.rglob("*")
        if path.is_file() and "live-verified" not in path.parts and path.suffix in source_suffixes
    ]
    content = "\n".join(path.read_text(encoding="utf-8") for path in generalized)

    for variable in (
        "CI_PROJECT_ID",
        "CI_PROJECT_NAME",
        "CI_PROJECT_PATH",
        "CI_DEFAULT_BRANCH",
        "CI_COMMIT_SHA",
        "CI_COMMIT_TAG",
        "CI_API_V4_URL",
    ):
        assert variable in content
    assert "RELEASE_TAG_PREFIX: 'v'" in content
    assert "RELEASE_TAG_WILDCARD: 'v*'" in content
    assert "GENERIC_PACKAGE_NAME: '$CI_PROJECT_NAME'" in content
    assert all(
        literal not in content
        for literal in ("jira-ai-evaluation", "jamie.nelson", "projects/529", "release-playbook-v")
    )
    assert '"main"' not in content
    assert "^main$" not in content

    references = SKILL_ROOT / "references"
    generalized_docs = [path for path in references.glob("*.md") if path.name != "release-live-evidence.md"]
    docs_and_runtime = "\n".join(path.read_text(encoding="utf-8") for path in generalized_docs)
    docs_and_runtime += (SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
    docs_and_runtime += (SKILL_ROOT / "scripts" / "validate_release_candidate.py").read_text(encoding="utf-8")
    assert all(
        literal not in docs_and_runtime
        for literal in ("jira-ai-evaluation", "jamie.nelson", "projects/529", "release-playbook-v1")
    )


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
