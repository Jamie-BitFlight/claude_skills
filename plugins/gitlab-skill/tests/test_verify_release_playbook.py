from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPT = PLUGIN_ROOT / "skills" / "gitlab-skill" / "scripts" / "verify_release_playbook.py"
FIXTURE = Path(__file__).parent / "fixtures" / "release_playbook_live_redacted.json"
TAG_SHA = "95f5b4c72107f88f090ca605ae24a424aa493d4e"
MAIN_SHA = "37f0a7f9a7a604c8c06b0feb4e326505806187b6"
ASSET_SHA256 = "1da05508757a66e07442a12599162752cf5d5a75ab28fec535e312d2566406f3"
ASSET_URL = (
    "https://gitlab.example/api/v4/projects/529/packages/generic/"
    "release-playbook/release-playbook-v1.1.0/release-playbook.txt"
)


def load_module() -> ModuleType:
    """Load the standalone verifier without package installation."""
    spec = importlib.util.spec_from_file_location("verify_release_playbook", SCRIPT)
    assert spec
    assert spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_runner(fixture: dict[str, Any], calls: list[list[str]], asset_error: Exception | None = None):
    """Return a fake glab runner backed by redacted live responses."""

    def run(arguments: list[str], _timeout: float) -> str:
        calls.append(arguments)
        joined = " ".join(arguments)
        if "graphql" in arguments:
            key = "variables"
        else:
            routes = (
                ("/protected_branches/", "protected_branch"),
                ("/protected_tags", "protected_tags"),
                ("/access_tokens/", "token"),
                ("/repository/tags/", "tag"),
                ("/pipelines/5690/jobs", "main_jobs"),
                ("/pipelines/5690", "main_pipeline"),
                ("/pipelines/5692/jobs", "tag_jobs"),
                ("/pipelines/5692", "tag_pipeline"),
                ("/package_files", "package_files"),
                ("/packages?", "packages"),
                ("/releases/", "release"),
                ("/packages/generic/", "asset_content"),
            )
            key = next((value for marker, value in routes if marker in joined), "project")
        if key == "asset_content" and asset_error is not None:
            raise asset_error
        value = fixture[key]
        return value if isinstance(value, str) else json.dumps(value)

    return run


def verify(module: ModuleType, fixture: dict[str, Any], calls: list[list[str]]) -> dict[str, Any]:
    """Run the complete successful verification case."""
    return module.verify_release_playbook(
        host="gitlab.example",
        project="jamie.nelson/jira-ai-evaluation",
        default_branch="main",
        branch_push_access_level=40,
        tag="release-playbook-v1.1.0",
        expected_tag_sha=TAG_SHA,
        tag_pattern="release-playbook-v*",
        tag_access_level=30,
        main_pipeline_id=5690,
        main_sha=MAIN_SHA,
        version_job="semantic_version_tag",
        version_stage="tag",
        tag_pipeline_id=5692,
        token_id=564,
        token_access_level=40,
        token_scopes=["write_repository"],
        token_expires_at="2026-10-22",
        release_commit_required=True,
        variable_key="RELEASE_PUSH_TOKEN",
        variable_type="ENV_VAR",
        variable_scope="*",
        package_name="release-playbook",
        package_status="default",
        asset_name="release-playbook.txt",
        asset_size=76,
        asset_sha256=ASSET_SHA256,
        asset_url=ASSET_URL,
        release_description_contains=TAG_SHA,
        notes_jobs=["build_release_asset"],
        build_jobs=["build_release_asset"],
        publish_jobs=["publish_generic_asset"],
        release_job="create_gitlab_release",
        lifecycle_stages=["build", "publish", "release"],
        timeout=5,
        runner=fixture_runner(fixture, calls),
    )


def checks(result: dict[str, Any]) -> dict[str, bool]:
    """Index check verdicts by name."""
    return {item["name"]: item["ok"] for item in result["checks"]}


def test_live_redacted_fixture_passes_complete_read_only_contract() -> None:
    """The exact redacted live state passes every explicit Generic check."""
    module = load_module()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    calls: list[list[str]] = []
    result = verify(module, fixture, calls)

    assert result["ok"] is True
    assert result["scope"] == "gitlab_generic_only"
    assert all(call[:3] == ["api", "--hostname", "gitlab.example"] for call in calls)
    assert all(not any(verb in call for verb in ("POST", "PUT", "PATCH", "DELETE")) for call in calls)
    assert "variable get" not in " ".join(" ".join(call) for call in calls)
    assert checks(result) == {
        "protected_default_branch": True,
        "protected_tag_creator": True,
        "token_metadata": True,
        "credential_authorization": True,
        "variable_metadata": True,
        "main_pipeline": True,
        "version_job": True,
        "main_lifecycle_stages_absent": True,
        "tag_commit": True,
        "tag_pipeline": True,
        "ordered_jobs": True,
        "generic_package": True,
        "package_file": True,
        "gitlab_release": True,
        "package_asset_link": True,
        "package_asset_resolves": True,
    }


@pytest.mark.parametrize(
    ("mutation", "failed_check"),
    [
        (lambda data: data["protected_branch"]["push_access_levels"].clear(), "protected_default_branch"),
        (lambda data: data["protected_tags"][0]["create_access_levels"].clear(), "protected_tag_creator"),
        (lambda data: data["token"].update(active=False), "token_metadata"),
        (
            lambda data: data["variables"]["data"]["project"]["ciVariables"]["nodes"][0].update(
                environmentScope="staging"
            ),
            "variable_metadata",
        ),
        (lambda data: data["main_pipeline"].update(sha="wrong"), "main_pipeline"),
        (lambda data: data["main_jobs"][0].update(status="failed"), "version_job"),
        (
            lambda data: data["main_jobs"].append({
                "id": 9999,
                "name": "premature_release",
                "stage": "release",
                "status": "success",
            }),
            "main_lifecycle_stages_absent",
        ),
        (lambda data: data["token"].update(access_level=20), "credential_authorization"),
        (lambda data: data["tag"]["commit"].update(id="wrong"), "tag_commit"),
        (lambda data: data["tag_pipeline"].update(sha="wrong"), "tag_pipeline"),
        (lambda data: data["tag_jobs"][1].update(stage="release"), "ordered_jobs"),
        (lambda data: data["packages"][0].update(status="error"), "generic_package"),
        (lambda data: data["package_files"][0].update(file_sha256="wrong"), "package_file"),
        (lambda data: data["release"].update(description=""), "gitlab_release"),
        (lambda data: data["release"]["assets"]["links"].clear(), "package_asset_link"),
    ],
)
def test_each_contract_mismatch_fails(mutation, failed_check: str) -> None:
    """Every required metadata claim has a failing fixture mutation."""
    module = load_module()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    mutation(fixture)
    result = verify(module, fixture, [])
    assert result["ok"] is False
    assert checks(result)[failed_check] is False


def test_unrelated_main_job_in_undeclared_stage_is_allowed() -> None:
    """Project jobs outside declared lifecycle-only stages do not fail isolation."""
    module = load_module()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fixture["main_jobs"].append({"id": 9998, "name": "project_test", "stage": "test", "status": "success"})
    result = verify(module, fixture, [])
    assert result["ok"] is True
    assert checks(result)["main_lifecycle_stages_absent"] is True


def test_package_asset_resolution_failure_is_reported() -> None:
    """A failed package URL read returns a named false check."""
    module = load_module()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    runner = fixture_runner(fixture, [], module.VerificationCommandError("api", 1))
    result = module.verify_release_playbook(
        host="gitlab.example",
        project="529",
        default_branch="main",
        branch_push_access_level=40,
        tag="release-playbook-v1.1.0",
        expected_tag_sha=TAG_SHA,
        tag_pattern="release-playbook-v*",
        tag_access_level=30,
        main_pipeline_id=5690,
        main_sha=MAIN_SHA,
        version_job="semantic_version_tag",
        version_stage="tag",
        tag_pipeline_id=5692,
        token_id=564,
        token_access_level=40,
        token_scopes=["write_repository"],
        token_expires_at="2026-10-22",
        release_commit_required=True,
        variable_key="RELEASE_PUSH_TOKEN",
        variable_type="ENV_VAR",
        variable_scope="*",
        package_name="release-playbook",
        package_status="default",
        asset_name="release-playbook.txt",
        asset_size=76,
        asset_sha256=ASSET_SHA256,
        asset_url=ASSET_URL,
        release_description_contains=TAG_SHA,
        notes_jobs=["build_release_asset"],
        build_jobs=["build_release_asset"],
        publish_jobs=["publish_generic_asset"],
        release_job="create_gitlab_release",
        lifecycle_stages=["build", "publish", "release"],
        timeout=5,
        runner=runner,
    )
    assert result["ok"] is False
    assert checks(result)["package_asset_resolves"] is False


def cli_arguments() -> list[str]:
    """Return the complete explicit CLI contract."""
    return [
        "--host",
        "gitlab.example",
        "--project",
        "529",
        "--default-branch",
        "main",
        "--branch-push-access-level",
        "40",
        "--tag",
        "release-playbook-v1.1.0",
        "--expected-tag-sha",
        TAG_SHA,
        "--tag-pattern",
        "release-playbook-v*",
        "--tag-access-level",
        "30",
        "--main-pipeline-id",
        "5690",
        "--main-sha",
        MAIN_SHA,
        "--version-job",
        "semantic_version_tag",
        "--version-stage",
        "tag",
        "--tag-pipeline-id",
        "5692",
        "--lifecycle-stage",
        "build",
        "--lifecycle-stage",
        "publish",
        "--lifecycle-stage",
        "release",
        "--token-id",
        "564",
        "--token-access-level",
        "40",
        "--token-scope",
        "write_repository",
        "--token-expires-at",
        "2026-10-22",
        "--release-commit-required",
        "--variable-key",
        "RELEASE_PUSH_TOKEN",
        "--variable-type",
        "ENV_VAR",
        "--variable-scope",
        "*",
        "--package-name",
        "release-playbook",
        "--package-status",
        "default",
        "--asset-name",
        "release-playbook.txt",
        "--asset-size",
        "76",
        "--asset-sha256",
        ASSET_SHA256,
        "--asset-url",
        ASSET_URL,
        "--release-description-contains",
        TAG_SHA,
        "--notes-job",
        "build_release_asset",
        "--build-job",
        "build_release_asset",
        "--publish-job",
        "publish_generic_asset",
        "--release-job",
        "create_gitlab_release",
    ]


def test_main_emits_compact_json(monkeypatch, capsys) -> None:
    """CLI emits one compact result for the complete contract."""
    module = load_module()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    monkeypatch.setattr(module, "run_glab", fixture_runner(fixture, []))
    assert module.main(cli_arguments()) == 0
    output = capsys.readouterr().out
    assert "\n" not in output.rstrip("\n")
    assert json.loads(output)["ok"] is True


def test_help_is_the_complete_agent_facing_contract(capsys) -> None:
    """Help groups inputs, repeated semantics, output fields, scope, and exits."""
    module = load_module()
    with pytest.raises(SystemExit) as exit_info:
        module.parse_arguments(["--help"])

    help_text = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "GitLab target and protected refs" in help_text
    assert "Main and tag pipelines" in help_text
    assert "Release credential and variable metadata" in help_text
    assert "GitLab Generic package and Release" in help_text
    assert "Repeat --token-scope, --lifecycle-stage, --notes-job, --build-job, and" in help_text
    assert "exclude the main version-evaluation stage" in help_text
    assert "scope` is always `gitlab_generic_only`" in help_text
    assert all(f"Exit {code}:" in help_text for code in (0, 1, 2))


def test_asset_url_must_target_selected_host() -> None:
    """The resolver rejects cross-host package links before requests."""
    module = load_module()
    with pytest.raises(ValueError, match="selected host"):
        module.asset_endpoint("gitlab.example", "https://other.example/api/v4/projects/1/packages/generic/x/1/x")


def test_main_reports_bounded_command_failure(monkeypatch, capsys) -> None:
    """A glab failure reports operation metadata without stderr."""
    module = load_module()

    def fail(_arguments: list[str], _timeout: float) -> str:
        raise module.VerificationCommandError("api", 1)

    monkeypatch.setattr(module, "run_glab", fail)
    assert module.main(cli_arguments()) == 2
    assert json.loads(capsys.readouterr().out) == {
        "ok": False,
        "error": "VerificationCommandError",
        "operation": "api",
        "returncode": 1,
    }
