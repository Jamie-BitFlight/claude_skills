from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import threading
import tomllib
from base64 import b64encode
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import marko
import pytest
import yaml
from marko.inline import Link

PLUGIN_ROOT = Path(__file__).parents[1]
SKILL_ROOT = PLUGIN_ROOT / "skills" / "gitlab-skill"
REPOSITORY_ROOT = PLUGIN_ROOT.parents[1]

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
            if destination.startswith(("http://", "https://", "#")):
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
    optional = {"loads"}
    assert evaluations
    assert all(required <= evaluation.keys() <= required | optional for evaluation in evaluations)

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
    for evaluation in evaluations:
        loads = evaluation.get("loads", [])
        assert isinstance(loads, list)
        assert all(isinstance(reference, str) and SKILL_ROOT.joinpath(reference).is_file() for reference in loads)


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


def test_ci_inspection_routes_only_to_existing_refs() -> None:
    """The CI inspection index exposes the supported remote inspection surface."""
    references = SKILL_ROOT / "references"
    index = references.joinpath("glab-ci-inspection.md")

    assert set(markdown_links(index)) == {"./glab-ci-existing-ref-inspection.md"}


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
    """Structured eval routes select one adapter and keep evidence conditional."""
    evaluations = load_evals()
    selections: dict[object, list[str]] = {}
    for evaluation in evaluations:
        loads = evaluation.get("loads", [])
        assert isinstance(loads, list)
        assert all(isinstance(reference, str) for reference in loads)
        selections[evaluation["id"]] = [str(reference) for reference in loads]

    assert selections[13] == [
        "references/release-version-adapters.md",
        "references/release-notes-adapters.md",
        "references/release-publication-adapters.md",
    ]
    assert selections[23] == ["references/release-version-semantic-release.md"]
    assert selections[24] == ["references/release-version-python-semantic-release.md"]
    assert selections[25] == ["references/release-publication-generic.md"]
    assert all(len(links) == 0 for eval_id, links in selections.items() if eval_id not in (13, 23, 24, 25))
    ordinary = [evaluation for evaluation in evaluations if evaluation["id"] in (13, 15, 16, 17, 19)]
    assert all(evaluation["reference"] != "references/release-live-evidence.md" for evaluation in ordinary)


def release_component_documents(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Load a component header and its executable document."""
    documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    assert len(documents) == 2
    assert all(isinstance(document, dict) for document in documents)
    return documents[0], documents[1]


def component_inputs(path: Path) -> dict[str, object]:
    """Return one component's typed input map."""
    header, _ = release_component_documents(path)
    specification = header["spec"]
    assert isinstance(specification, dict)
    inputs = specification["inputs"]
    assert isinstance(inputs, dict)
    return inputs


def component_job(path: Path) -> dict[str, object]:
    """Return one component's executable job contract."""
    _, executable = release_component_documents(path)
    job = executable["$[[ inputs.job-name ]]"]
    assert isinstance(job, dict)
    return job


def object_map(value: object) -> dict[str, object]:
    """Narrow a parsed YAML mapping."""
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return {str(key): item for key, item in value.items()}


def string_list(value: object) -> list[str]:
    """Narrow a parsed YAML string sequence."""
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
    return [str(item) for item in value]


def component_manifest(root: Path) -> set[str]:
    """Return the authoritative component template inventory."""
    manifest = json.loads(root.joinpath("component-manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"templates"}
    templates = manifest["templates"]
    assert isinstance(templates, list)
    assert all(isinstance(name, str) for name in templates)
    return {str(name) for name in templates}


def test_release_component_project_matches_authoritative_manifest() -> None:
    """The publishable project shape exposes exactly its declared contracts."""
    root = SKILL_ROOT / "assets" / "release-components"
    templates = root / "templates"
    expected = component_manifest(root)

    assert {path.name for path in templates.glob("*.yml")} == expected
    assert root.joinpath("README.md").is_file()
    assert root.joinpath(".gitlab-ci.yml").is_file()
    assert root.joinpath("examples", "consumer.gitlab-ci.yml").is_file()

    for path in templates.glob("*.yml"):
        header, executable = release_component_documents(path)
        assert set(header) == {"spec"}
        specification = header["spec"]
        assert isinstance(specification, dict)
        assert isinstance(specification.get("inputs"), dict)
        assert len(executable) == 1
        assert next(iter(executable)) == "$[[ inputs.job-name ]]"


def test_release_components_are_self_contained_and_pipeline_safe() -> None:
    """Components expose jobs without mutating the consumer's global configuration."""
    templates = SKILL_ROOT / "assets" / "release-components" / "templates"
    forbidden = {"workflow", "stages", "default", "variables", "include"}

    for path in templates.glob("*.yml"):
        header, executable = release_component_documents(path)
        content = path.read_text(encoding="utf-8")
        assert forbidden.isdisjoint(executable)
        assert "spec:component" not in content
        assert "extends:" not in content
        assert "include:" not in content
        assert not any(str(name).startswith(".") for name in executable)
        specification = header["spec"]
        assert isinstance(specification, dict)
        inputs = specification["inputs"]
        assert isinstance(inputs, dict)
        assert {"job-name", "stage", "rules", "image"} <= set(inputs)
        rules = inputs["rules"]
        assert isinstance(rules, dict)
        assert rules["type"] == "array"
        job = component_job(path)
        string_list(job.get("before_script", []))
        string_list(job["script"])


def test_consumer_owns_release_orchestration_and_one_version_adapter() -> None:
    """The composition selects one adapter while retaining all project policy and build work."""
    path = SKILL_ROOT / "assets" / "release-components" / "examples" / "consumer.gitlab-ci.yml"
    consumer = yaml.safe_load(path.read_text(encoding="utf-8"))
    includes = consumer["include"]
    component_refs = [entry["component"] for entry in includes]
    version_refs = [reference for reference in component_refs if "semantic-release-version@" in reference]
    pins = [reference.rsplit("@", maxsplit=1)[1] for reference in component_refs]

    assert len(version_refs) == 1
    assert all(re.fullmatch(r"[0-9a-f]{40}", pin) for pin in pins)
    assert "workflow" in consumer
    assert consumer["stages"] == [
        "verify",
        "release-version",
        "release-notes",
        "release-build",
        "release-publish",
        "release-create",
    ]
    assert "RELEASE_TAG_REGEX" in consumer["variables"]
    assert "project-verify" in consumer
    assert "build-release-artifact" in consumer
    assert all("rules" in entry["inputs"] and "stage" in entry["inputs"] for entry in includes)
    version_include = next(entry for entry in includes if "-version@" in entry["component"])
    assert version_include["inputs"]["credential-variable"] == "PROJECT_RELEASE_PUSH_TOKEN"


def test_release_components_use_runtime_identity_and_secret_boundaries() -> None:
    """Parsed jobs use predefined identity and restrict the release credential to version jobs."""
    root = SKILL_ROOT / "assets" / "release-components"
    templates = root / "templates"
    version_names = {"semantic-release-version.yml", "python-semantic-release-version.yml"}

    for name in component_manifest(root):
        job = component_job(templates / name)
        serialized_job = json.dumps(job)
        if name in version_names:
            assert "RELEASE_CREDENTIAL_VARIABLE" in serialized_job
            assert "RELEASE_CREDENTIAL_DIGEST_VARIABLE" in serialized_job
        else:
            assert "RELEASE_CREDENTIAL_VARIABLE" not in serialized_job
            assert "RELEASE_CREDENTIAL_DIGEST_VARIABLE" not in serialized_job

    generic_job = json.dumps(component_job(templates / "generic-package.yml"))
    release_job = json.dumps(component_job(templates / "gitlab-release.yml"))
    assert all(
        variable in generic_job for variable in ("CI_JOB_TOKEN", "CI_API_V4_URL", "CI_PROJECT_ID", "CI_COMMIT_TAG")
    )
    assert all(
        variable in release_job for variable in ("CI_API_V4_URL", "CI_PROJECT_ID", "CI_PROJECT_PATH", "CI_COMMIT_TAG")
    )


def test_component_project_tests_every_template_at_its_commit_sha() -> None:
    """The project resolves each template at its SHA with every mandatory input."""
    root = SKILL_ROOT / "assets" / "release-components"
    pipeline = yaml.safe_load(root.joinpath(".gitlab-ci.yml").read_text(encoding="utf-8"))
    includes = pipeline["include"]
    component_refs = [entry["component"] for entry in includes]
    included_names = {
        reference.rsplit("/", maxsplit=1)[1].split("@", maxsplit=1)[0] + ".yml" for reference in component_refs
    }

    assert included_names == component_manifest(root)
    assert all(reference.startswith("$CI_SERVER_FQDN/$CI_PROJECT_PATH/") for reference in component_refs)
    assert all(reference.endswith("@$CI_COMMIT_SHA") for reference in component_refs)
    for entry in includes:
        name = entry["component"].rsplit("/", maxsplit=1)[1].split("@", maxsplit=1)[0]
        inputs = component_inputs(root / "templates" / f"{name}.yml")
        mandatory = {key for key, definition in inputs.items() if "default" not in object_map(definition)}
        assert mandatory <= entry["inputs"].keys()


def test_component_project_publishes_catalog_only_from_semantic_version_tags() -> None:
    """Catalog publication is release-keyword based and follows component validation."""
    root = SKILL_ROOT / "assets" / "release-components"
    pipeline = yaml.safe_load(root.joinpath(".gitlab-ci.yml").read_text(encoding="utf-8"))
    publication = pipeline["publish-component-catalog"]

    assert publication["stage"] == "release"
    assert set(publication["needs"]) == {
        "validate-component-tree",
        "test-release-basic-header",
        "test-release-tag-selection",
    }
    assert publication["release"]["tag_name"] == "$CI_COMMIT_TAG"
    assert publication["rules"][0]["if"].startswith("$CI_COMMIT_TAG =~ /")
    for value in pipeline.values():
        if isinstance(value, dict) and "script" in value:
            string_list(value["script"])


def test_component_project_tag_selection_fixture_executes_without_side_effects(tmp_path: Path) -> None:
    """The component project proves patterned previous-tag selection in a local repository."""
    root = SKILL_ROOT / "assets" / "release-components"
    pipeline = yaml.safe_load(root.joinpath(".gitlab-ci.yml").read_text(encoding="utf-8"))
    commands = string_list(pipeline["test-release-tag-selection"]["script"])
    result = subprocess.run(
        ["bash", "-c", "set -eu\n" + "\n".join(commands)], cwd=tmp_path, text=True, capture_output=True, check=False
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "version", ["0.0.0", "1.2.3", "1.2.3-alpha", "1.2.3-alpha.1", "1.2.3+build.5", "1.2.3-rc.1+build-7"]
)
def test_catalog_tag_expression_accepts_semver_2_versions(version: str) -> None:
    """Catalog publication accepts SemVer 2.0 core, prerelease, and build forms."""
    root = SKILL_ROOT / "assets" / "release-components"
    pipeline = yaml.safe_load(root.joinpath(".gitlab-ci.yml").read_text(encoding="utf-8"))
    expression = pipeline["publish-component-catalog"]["rules"][0]["if"]
    pattern = expression.removeprefix("$CI_COMMIT_TAG =~ /").removesuffix("/")

    assert all(unsupported not in pattern for unsupported in ("(?:", "(?=", "(?<", "\\d"))
    assert re.fullmatch(pattern, version)


@pytest.mark.parametrize(
    "version", ["", "v1.2.3", "01.2.3", "1.02.3", "1.2.03", "1.2.3-01", "1.2.3-alpha..1", "1.2.3+"]
)
def test_catalog_tag_expression_rejects_non_semver_versions(version: str) -> None:
    """Catalog publication rejects prefixes, leading zeroes, and empty identifiers."""
    root = SKILL_ROOT / "assets" / "release-components"
    pipeline = yaml.safe_load(root.joinpath(".gitlab-ci.yml").read_text(encoding="utf-8"))
    expression = pipeline["publish-component-catalog"]["rules"][0]["if"]
    pattern = expression.removeprefix("$CI_COMMIT_TAG =~ /").removesuffix("/")

    assert re.fullmatch(pattern, version) is None


def test_consumer_verification_gates_both_lifecycle_pipeline_types() -> None:
    """Project verification runs before default-branch versioning and tag publication."""
    path = SKILL_ROOT / "assets" / "release-components" / "examples" / "consumer.gitlab-ci.yml"
    consumer = yaml.safe_load(path.read_text(encoding="utf-8"))
    conditions = {rule["if"] for rule in consumer["project-verify"]["rules"]}

    assert conditions == {
        '$CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH',
        '$CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_TAG =~ $RELEASE_TAG_REGEX',
    }


def test_consumer_builds_once_and_feeds_each_publication_destination() -> None:
    """Every publication consumes the one consumer-owned immutable build artifact."""
    path = SKILL_ROOT / "assets" / "release-components" / "examples" / "consumer.gitlab-ci.yml"
    consumer = yaml.safe_load(path.read_text(encoding="utf-8"))
    build_jobs = [
        name for name, value in consumer.items() if isinstance(value, dict) and value.get("stage") == "release-build"
    ]
    publication_includes = [entry for entry in consumer["include"] if entry["inputs"]["stage"] == "release-publish"]

    assert build_jobs == ["build-release-artifact"]
    assert publication_includes
    for entry in publication_includes:
        assert entry["inputs"]["needs"] == [{"job": "build-release-artifact", "artifacts": True}]


def test_version_components_require_explicit_remote_selection() -> None:
    """Both adapters require a remote and semantic-release receives the selected URL."""
    templates = SKILL_ROOT / "assets" / "release-components" / "templates"
    semantic_path = templates / "semantic-release-version.yml"
    python_path = templates / "python-semantic-release-version.yml"
    semantic_inputs = component_inputs(semantic_path)
    python_inputs = component_inputs(python_path)
    semantic_job = component_job(semantic_path)
    python_job = component_job(python_path)

    assert "default" not in object_map(semantic_inputs["git-remote-name"])
    assert "default" not in object_map(semantic_inputs["repository-url"])
    assert "default" not in object_map(python_inputs["git-remote-name"])
    assert "default" not in object_map(python_inputs["repository-url"])
    assert object_map(semantic_inputs["credential-variable"])["default"] == "RELEASE_PUSH_TOKEN"
    assert object_map(python_inputs["credential-variable"])["default"] == "RELEASE_PUSH_TOKEN"
    semantic_variables = object_map(semantic_job["variables"])
    python_variables = object_map(python_job["variables"])
    assert semantic_variables["RELEASE_REPOSITORY_URL"] == "$[[ inputs.repository-url ]]"
    assert {"GL_TOKEN", "GITLAB_TOKEN"}.isdisjoint(semantic_variables)
    assert {"GL_TOKEN", "GITLAB_TOKEN"}.isdisjoint(python_variables)
    commands = [*string_list(semantic_job["before_script"]), *string_list(semantic_job["script"])]
    script = "\n".join(commands)
    assert "git remote set-url" in script
    assert 'test "$(git remote get-url' not in script
    assert "repositoryUrl" in script


@pytest.mark.parametrize(
    ("template_name", "input_name"),
    [
        ("semantic-release-version.yml", "semantic-release-version"),
        ("python-semantic-release-version.yml", "python-semantic-release-version"),
    ],
)
@pytest.mark.parametrize(
    "version", ["0.0.0", "1.2.3", "1.2.3-alpha", "1.2.3-alpha.1", "1.2.3+build.5", "1.2.3-rc.1+build-7"]
)
def test_version_tool_input_regex_accepts_exact_semver(template_name: str, input_name: str, version: str) -> None:
    """Version-tool inputs accept complete SemVer core, prerelease, and build forms."""
    path = SKILL_ROOT / "assets" / "release-components" / "templates" / template_name
    definition = object_map(component_inputs(path)[input_name])
    pattern = str(definition["regex"])

    assert all(unsupported not in pattern for unsupported in ("(?:", "(?=", "(?<", "\\d"))
    assert re.fullmatch(pattern, version)


@pytest.mark.parametrize(
    ("template_name", "input_name"),
    [
        ("semantic-release-version.yml", "semantic-release-version"),
        ("python-semantic-release-version.yml", "python-semantic-release-version"),
    ],
)
@pytest.mark.parametrize(
    "version",
    [
        "",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "1.2.3-01",
        "^1.2.3",
        "1.x",
        ">=1.2.3",
        "1.2.3 || echo bad",
        "1.2.3;id",
        " 1.2.3",
    ],
)
def test_version_tool_input_regex_rejects_ranges_and_shell_values(
    template_name: str, input_name: str, version: str
) -> None:
    """Version-tool inputs reject non-SemVer ranges, whitespace, and shell syntax."""
    path = SKILL_ROOT / "assets" / "release-components" / "templates" / template_name
    pattern = str(object_map(component_inputs(path)[input_name])["regex"])

    assert re.fullmatch(pattern, version) is None


def test_version_tool_inputs_reach_shell_only_as_quoted_job_variables() -> None:
    """Executable shell never receives raw component interpolation for package versions."""
    templates = SKILL_ROOT / "assets" / "release-components" / "templates"
    contracts = (
        (
            "semantic-release-version.yml",
            "semantic-release-version",
            "SEMANTIC_RELEASE_VERSION",
            '"semantic-release@${SEMANTIC_RELEASE_VERSION}"',
        ),
        (
            "python-semantic-release-version.yml",
            "python-semantic-release-version",
            "PYTHON_SEMANTIC_RELEASE_VERSION",
            '"python-semantic-release==${PYTHON_SEMANTIC_RELEASE_VERSION}"',
        ),
    )
    for template_name, input_name, variable_name, quoted_argument in contracts:
        job = component_job(templates / template_name)
        variables = object_map(job["variables"])
        shell = "\n".join([*string_list(job.get("before_script", [])), *string_list(job["script"])])
        assert variables[variable_name] == f"$[[ inputs.{input_name} ]]"
        assert f"$[[ inputs.{input_name} ]]" not in shell
        assert quoted_argument in shell


@pytest.mark.parametrize("template_name", ["semantic-release-version.yml", "python-semantic-release-version.yml"])
@pytest.mark.parametrize(
    ("repository_url", "expected_status"),
    [("https://gitlab.example/group/project.git", 0), ("http://gitlab.example/group/project.git", 1)],
)
def test_version_before_script_accepts_runner_rewritten_remote_without_literal_equality(
    template_name: str, repository_url: str, expected_status: int, tmp_path: Path
) -> None:
    """The complete setup succeeds when Runner rewrites the selected credential-free URL."""
    path = SKILL_ROOT / "assets" / "release-components" / "templates" / template_name
    before_script = string_list(component_job(path)["before_script"])
    before_script = [
        "true" if command.startswith(("apk add ", "python -m pip install ")) else command for command in before_script
    ]
    setup = "set -eu\n" + "\n".join(before_script)
    setup = setup.replace("$[[ inputs.python-semantic-release-version ]]", "10.6.2")
    assert re.search(r"test[^\n]*git remote get-url", setup) is None

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for command_name in ("apk", "python"):
        executable = bin_dir / command_name
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o700)
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True, timeout=10)
    subprocess.run(["git", "remote", "add", "origin", repository_url], cwd=tmp_path, check=True, timeout=10)
    subprocess.run(
        ["git", "config", "url.https://gitlab-ci-token:job-token@gitlab.example/.insteadOf", "https://gitlab.example/"],
        cwd=tmp_path,
        check=True,
        timeout=10,
    )
    sentinel = "before-script-release-sentinel"
    variable_name = "RUNNER_REWRITE_RELEASE_TOKEN"
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CI_DEFAULT_BRANCH": "main",
        "CI_PIPELINE_SOURCE": "push",
        "CI_COMMIT_BRANCH": "main",
        "CI_COMMIT_REF_PROTECTED": "true",
        "RELEASE_GIT_REMOTE_NAME": "origin",
        "RELEASE_REPOSITORY_URL": repository_url,
        "RELEASE_CREDENTIAL_VARIABLE": variable_name,
        "RELEASE_CREDENTIAL_DIGEST_VARIABLE": f"{variable_name}_SHA256",
        variable_name: sentinel,
        f"{variable_name}_SHA256": hashlib.sha256(sentinel.encode()).hexdigest(),
    }
    result = run_bounded(["bash", "-c", setup], tmp_path, environment)

    assert result.returncode == expected_status, result.stderr
    if expected_status:
        return
    effective_url = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=tmp_path, text=True, capture_output=True, check=True, timeout=10
    ).stdout.strip()
    assert effective_url != repository_url
    assert effective_url.startswith("https://gitlab-ci-token:job-token@gitlab.example/")
    persisted = "\n".join(
        file.read_text(encoding="utf-8", errors="replace") for file in tmp_path.rglob("*") if file.is_file()
    )
    assert sentinel not in persisted


def test_python_semantic_release_runtime_config_leaves_git_auth_to_process_scoped_http_extra_header(
    tmp_path: Path,
) -> None:
    """The PSR config leaves Git push authentication to process-scoped http.extraHeader."""
    path = SKILL_ROOT / "assets" / "release-components" / "templates" / "python-semantic-release-version.yml"
    job = component_job(path)
    generator = next(command for command in string_list(job["script"]) if command.startswith("python - <<'PY'"))
    result = subprocess.run(
        ["bash", "-c", generator],
        cwd=tmp_path,
        env={
            **os.environ,
            "CI_DEFAULT_BRANCH": "release/1.x",
            "RELEASE_TAG_PREFIX": "v",
            "RELEASE_GIT_REMOTE_NAME": "upstream",
            "RELEASE_VERSION_TOML": "pyproject.toml:project.version",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    config = tomllib.loads(tmp_path.joinpath(".release-component.toml").read_text(encoding="utf-8"))
    remote = config["semantic_release"]["remote"]
    assert "token" not in remote
    assert remote["ignore_token_for_push"] is True


def credential_verification_command(template_name: str) -> str:
    """Return the credential check that must run before remote mutation."""
    path = SKILL_ROOT / "assets" / "release-components" / "templates" / template_name
    before_script = string_list(component_job(path)["before_script"])
    verification = next(
        command
        for command in before_script
        if "RELEASE_CREDENTIAL_DIGEST_VARIABLE" in command and "sha256sum" in command
    )
    mutation_index = next(index for index, command in enumerate(before_script) if "git remote set-url" in command)
    assert before_script.index(verification) < mutation_index
    return verification


@pytest.mark.parametrize("template_name", ["semantic-release-version.yml", "python-semantic-release-version.yml"])
@pytest.mark.parametrize(
    ("variable_name", "secret", "digest_mode", "expected_status"),
    [
        ("COLD_RUN_RELEASE_TOKEN", "release-credential-sentinel", "correct", 0),
        ("COLD_RUN_RELEASE_TOKEN", "", "correct", 1),
        ("COLD_RUN_RELEASE_TOKEN", "release-credential-sentinel", "missing", 1),
        ("COLD_RUN_RELEASE_TOKEN", "release-credential-sentinel", "wrong", 1),
        ("9INVALID", "release-credential-sentinel", "correct", 1),
        ("INVALID-NAME", "release-credential-sentinel", "correct", 1),
    ],
)
def test_version_credential_variable_and_digest_fail_closed(
    template_name: str, variable_name: str, secret: str, digest_mode: str, expected_status: int
) -> None:
    """Credential indirection validates names, presence, and its non-secret digest companion."""
    command = credential_verification_command(template_name)
    correct_digest = hashlib.sha256(secret.encode()).hexdigest()
    digest = {"correct": correct_digest, "missing": "", "wrong": "0" * 64}[digest_mode]
    result = subprocess.run(
        ["bash", "-c", command],
        env={
            **os.environ,
            "RELEASE_CREDENTIAL_VARIABLE": variable_name,
            "RELEASE_CREDENTIAL_DIGEST_VARIABLE": f"{variable_name}_SHA256",
            variable_name: secret,
            f"{variable_name}_SHA256": digest,
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == expected_status
    if secret:
        assert secret not in result.stdout
        assert secret not in result.stderr


def write_fake_release_command(path: Path) -> None:
    """Write a child command that exercises process-scoped Git authorization."""
    path.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        'git ls-remote "$TRANSPORT_TEST_URL" >/dev/null\n'
        'git ls-remote "$SECOND_TRANSPORT_TEST_URL" >/dev/null\n'
        'test -z "$(printenv "$RELEASE_CREDENTIAL_VARIABLE" || true)"\n'
        'test -z "${GITLAB_TOKEN:-}"\n'
        'test -z "${GL_TOKEN:-}"\n',
        encoding="utf-8",
    )
    path.chmod(0o700)


def run_bounded(
    arguments: list[str], cwd: Path, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess through the repository's process-group timeout wrapper."""
    return subprocess.run(
        [
            "uv",
            "run",
            "--script",
            str(REPOSITORY_ROOT / "scripts" / "run_bounded.py"),
            "--timeout-seconds",
            "10",
            "--",
            *arguments,
        ],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )


def create_http_git_repository(tmp_path: Path) -> Path:
    """Create a bare repository for git-http-backend."""
    work = tmp_path / "work"
    project_root = tmp_path / "http-root"
    project_root.mkdir()
    initialized = run_bounded(["git", "init", "--quiet", str(work)], tmp_path)
    assert initialized.returncode == 0, initialized.stderr
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=work, check=True, timeout=10)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=work, check=True, timeout=10)
    work.joinpath("README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=work, check=True, timeout=10)
    subprocess.run(["git", "commit", "--quiet", "-m", "fixture"], cwd=work, check=True, timeout=10)
    cloned = run_bounded(["git", "clone", "--quiet", "--bare", str(work), str(project_root / "repo.git")], tmp_path)
    assert cloned.returncode == 0, cloned.stderr
    return project_root


def create_self_signed_certificate(tmp_path: Path) -> tuple[Path, Path]:
    """Create a temporary certificate for the local HTTPS fixture."""
    certificate = tmp_path / "fixture.crt"
    private_key = tmp_path / "fixture.key"
    generated = run_bounded(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(private_key),
            "-out",
            str(certificate),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
        ],
        tmp_path,
    )
    assert generated.returncode == 0, generated.stderr
    return certificate, private_key


def start_git_http_server(
    project_root: Path, accepted_authorization: str | None, certificate: Path, private_key: Path
) -> tuple[ThreadingHTTPServer, threading.Thread, list[str | None]]:
    """Serve a local HTTPS Git repository and capture Authorization headers."""
    observed: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            authorization = self.headers.get("Authorization")
            observed.append(authorization)
            if accepted_authorization is not None and authorization is None:
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="fixture"')
                self.end_headers()
                return
            if authorization != accepted_authorization:
                self.send_response(403)
                self.end_headers()
                return

            parsed = urlsplit(self.path)
            backend = subprocess.run(
                ["git", "http-backend"],
                env={
                    **os.environ,
                    "GIT_PROJECT_ROOT": str(project_root),
                    "GIT_HTTP_EXPORT_ALL": "1",
                    "REQUEST_METHOD": "GET",
                    "PATH_INFO": parsed.path,
                    "QUERY_STRING": parsed.query,
                    "REMOTE_USER": "release-bot",
                },
                capture_output=True,
                check=False,
                timeout=10,
            )
            assert backend.returncode == 0, backend.stderr.decode(errors="replace")
            header_blob, body = backend.stdout.split(b"\r\n\r\n", maxsplit=1)
            response_headers: list[tuple[str, str]] = []
            status = 200
            for header in header_blob.decode().split("\r\n"):
                name, value = header.split(":", maxsplit=1)
                if name.casefold() == "status":
                    status = int(value.strip().split(maxsplit=1)[0])
                else:
                    response_headers.append((name, value.strip()))
            self.send_response(status)
            for name, value in response_headers:
                self.send_header(name, value)
            if not any(name.casefold() == "content-length" for name, _value in response_headers):
                self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def log_message(self, *_arguments: object, **_keywords: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, private_key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, observed


@pytest.mark.parametrize(
    ("template_name", "command_name"),
    [("semantic-release-version.yml", "npx"), ("python-semantic-release-version.yml", "semantic-release")],
)
def test_version_process_uses_selected_header_over_runner_credentials_without_persistence(
    template_name: str, command_name: str, tmp_path: Path
) -> None:
    """The release child receives only selected process-scoped Basic authorization."""
    templates = SKILL_ROOT / "assets" / "release-components" / "templates"
    job = component_job(templates / template_name)
    release_command = next(command for command in string_list(job["script"]) if "extraHeader" in command)
    release_command = release_command.replace("$[[ inputs.semantic-release-version ]]", "25.0.9")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_fake_release_command(bin_dir / command_name)
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    project_root = create_http_git_repository(tmp_path)
    certificate, private_key = create_self_signed_certificate(tmp_path)
    sentinel = "release-credential-sentinel"
    selected_authorization = "Basic " + b64encode(f"oauth2:{sentinel}".encode()).decode()
    job_authorization = "Basic " + b64encode(b"gitlab-ci-token:job-token").decode()
    server, thread, observed = start_git_http_server(project_root, selected_authorization, certificate, private_key)
    second_server, second_thread, second_observed = start_git_http_server(project_root, None, certificate, private_key)
    port = server.server_address[1]
    second_port = second_server.server_address[1]
    transport_url = "https://gitlab.example/repo.git"
    second_transport_url = f"https://127.0.0.1:{second_port}/repo.git"
    rewritten_base = f"https://127.0.0.1:{port}/"
    subprocess.run(["git", "remote", "add", "origin", transport_url], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "credential.interactive", "never"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", f"url.{rewritten_base}.insteadOf", "https://gitlab.example/"], cwd=tmp_path, check=True
    )
    subprocess.run(
        [
            "git",
            "config",
            f"credential.https://127.0.0.1:{port}.helper",
            '!f() { test "$1" = get || exit 0; printf \'username=gitlab-ci-token\\npassword=job-token\\n\'; }; f "$@"',
        ],
        cwd=tmp_path,
        check=True,
    )
    variable_name = "COLD_RUN_RELEASE_TOKEN"
    environment = {key: value for key, value in os.environ.items() if key not in {"GL_TOKEN", "GITLAB_TOKEN"}}
    test_environment = {
        **environment,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "EXPECTED_RELEASE_CREDENTIAL": sentinel,
        "RELEASE_CREDENTIAL_VARIABLE": variable_name,
        "RELEASE_GIT_REMOTE_NAME": "origin",
        "RELEASE_REPOSITORY_URL": transport_url,
        "SEMANTIC_RELEASE_VERSION": "25.0.9",
        "PYTHON_SEMANTIC_RELEASE_VERSION": "10.6.2",
        "TRANSPORT_TEST_URL": transport_url,
        "SECOND_TRANSPORT_TEST_URL": second_transport_url,
        "GIT_SSL_NO_VERIFY": "1",
        variable_name: sentinel,
    }

    try:
        pre_fix = run_bounded(["git", "ls-remote", transport_url], tmp_path, test_environment)
        pre_fix_headers = list(observed)
        observed.clear()
        result = run_bounded(["bash", "-c", release_command], tmp_path, test_environment)
        fixed_headers = list(observed)
        cross_host_headers = list(second_observed)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        second_server.shutdown()
        second_thread.join(timeout=5)
        second_server.server_close()

    assert pre_fix.returncode != 0
    assert job_authorization in pre_fix_headers
    assert selected_authorization not in pre_fix_headers
    assert result.returncode == 0, {
        "stderr": result.stderr,
        "selected_headers": fixed_headers,
        "cross_host_headers": cross_host_headers,
    }
    assert selected_authorization in fixed_headers
    assert job_authorization not in fixed_headers
    assert cross_host_headers
    assert all(header is None for header in cross_host_headers)
    assert sentinel not in result.stdout
    assert sentinel not in result.stderr
    assert (
        subprocess.run(
            ["git", "config", "--get-all", "http.extraHeader"], cwd=tmp_path, capture_output=True, check=False
        ).returncode
        != 0
    )
    assert (
        subprocess.run(
            ["git", "config", "--get-all", f"http.{rewritten_base}repo.git.extraHeader"],
            cwd=tmp_path,
            capture_output=True,
            check=False,
        ).returncode
        != 0
    )
    persisted = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in tmp_path.rglob("*") if path.is_file()
    )
    assert sentinel not in persisted


def test_release_token_environment_scope_exists_only_on_version_jobs() -> None:
    """Parsed jobs expose the scoped token boundary only to version adapters."""
    root = SKILL_ROOT / "assets" / "release-components"
    templates = root / "templates"
    version_names = {"semantic-release-version.yml", "python-semantic-release-version.yml"}

    for name in component_manifest(root):
        job = component_job(templates / name)
        if name in version_names:
            assert job["environment"] == {"name": "$[[ inputs.environment ]]", "action": "verify"}
            assert "environment" in component_inputs(templates / name)
        else:
            assert "environment" not in job

    consumer = yaml.safe_load(root.joinpath("examples", "consumer.gitlab-ci.yml").read_text(encoding="utf-8"))
    version_includes = [entry for entry in consumer["include"] if "-version@" in entry["component"]]
    publication_includes = [entry for entry in consumer["include"] if "-version@" not in entry["component"]]
    assert [entry["inputs"]["environment"] for entry in version_includes] == ["release-version"]
    assert all("environment" not in entry["inputs"] for entry in publication_includes)

    project_pipeline = yaml.safe_load(root.joinpath(".gitlab-ci.yml").read_text(encoding="utf-8"))
    project_versions = [entry for entry in project_pipeline["include"] if "-version@" in entry["component"]]
    project_publications = [entry for entry in project_pipeline["include"] if "-version@" not in entry["component"]]
    assert all(entry["inputs"]["environment"] == "release-version" for entry in project_versions)
    assert all("environment" not in entry["inputs"] for entry in project_publications)


def test_release_notes_limit_history_to_the_selected_tag_pattern() -> None:
    """Release-note history and current-tag validation share one mandatory pattern."""
    path = SKILL_ROOT / "assets" / "release-components" / "templates" / "release-notes.yml"
    inputs = component_inputs(path)
    job = component_job(path)
    script = "\n".join(string_list(job["script"]))

    assert "default" not in object_map(inputs["release-tag-pattern"])
    variables = object_map(job["variables"])
    assert variables["RELEASE_TAG_PATTERN"] == "$[[ inputs.release-tag-pattern ]]"
    assert 'git describe --tags --match "$RELEASE_TAG_PATTERN"' in script


def test_components_assert_expected_protected_push_contexts_at_runtime() -> None:
    """Version and publication jobs fail closed outside their required push contexts."""
    templates = SKILL_ROOT / "assets" / "release-components" / "templates"
    version_names = {"semantic-release-version.yml", "python-semantic-release-version.yml"}

    for path in templates.glob("*.yml"):
        job = component_job(path)
        commands = [*string_list(job.get("before_script", [])), *string_list(job["script"])]
        script = "\n".join(commands)
        assert "CI_PIPELINE_SOURCE" in script
        assert "CI_COMMIT_REF_PROTECTED" in script
        if path.name in version_names:
            assert "CI_COMMIT_BRANCH" in script
            assert "CI_DEFAULT_BRANCH" in script
        else:
            assert "CI_COMMIT_TAG" in script


def test_live_evidence_remains_separate_from_reusable_components() -> None:
    """Observed sandbox configurations retain their evidence boundary."""
    root = SKILL_ROOT / "assets" / "release-components"
    live = root / "live-verified"
    expected = {
        "semantic-release.gitlab-ci.yml",
        "python-semantic-release.gitlab-ci.yml",
        ".releaserc.json",
        "pyproject.toml",
    }
    reusable = "\n".join(path.read_text(encoding="utf-8") for path in root.joinpath("templates").glob("*.yml"))

    assert {path.name for path in live.iterdir()} == expected
    assert all(literal not in reusable for literal in ("jira-ai-evaluation", "projects/529", "release-playbook-v"))


def test_disclosed_release_references_resolve_and_carry_evidence_dates() -> None:
    """Lifecycle routes and every indexed adapter branch carry valid dated sources."""
    reference_root = SKILL_ROOT / "references"
    playbook = reference_root / "automatic-tag-and-release.md"
    targets = {
        (reference_root / destination).resolve()
        for destination in markdown_links(playbook)
        if destination.startswith("./")
    }
    adapter_indexes = sorted(reference_root.glob("release-*-adapters.md"))
    assert adapter_indexes
    for index in adapter_indexes:
        branch_targets = {
            (index.parent / destination).resolve()
            for destination in markdown_links(index)
            if destination.startswith("./")
        }
        assert branch_targets, index
        targets.update(branch_targets)

    for target in targets:
        assert target.is_file(), target
        source_lines = [
            line for line in target.read_text(encoding="utf-8").splitlines() if line.startswith("SOURCE: <")
        ]
        assert source_lines, target
        for line in source_lines:
            match = re.search(r"\b(?:accessed|reviewed) (\d{4}-\d{2}-\d{2})\b", line)
            assert match, line
            date.fromisoformat(match.group(1))


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
    notes_links = [
        destination
        for destination in markdown_links(references / "release-notes-adapters.md")
        if destination.startswith("./release-notes-")
    ]

    assert len(version_links) == 2
    assert len(publication_links) == 5
    assert len(notes_links) == 2
    for destination in [*version_links, *publication_links, *notes_links]:
        assert references.joinpath(destination).is_file(), destination


def test_default_pytest_collection_includes_plugin_tests() -> None:
    """The normal repository suite must collect this plugin's tests."""
    pyproject = tomllib.loads((PLUGIN_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert "plugins/gitlab-skill/tests" in pyproject["tool"]["pytest"]["ini_options"]["testpaths"]
