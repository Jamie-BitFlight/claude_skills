# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Verify the complete live-tested GitLab Generic release contract with read-only requests."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import signal
import subprocess
import sys
import urllib.parse
from collections.abc import Callable, Sequence

CommandRunner = Callable[[Sequence[str], float], str]
JsonObject = dict[str, object]
MIN_LIFECYCLE_STAGE_COUNT = 3
SEPARATE_NOTES_BUILD_STAGE_COUNT = 4

VARIABLE_QUERY = """query($fullPath: ID!) {
  project(fullPath: $fullPath) {
    ciVariables {
      nodes { key variableType protected masked hidden raw environmentScope }
    }
  }
}"""


class VerificationCommandError(RuntimeError):
    """Report a bounded command failure without returning command output."""

    def __init__(self, operation: str, returncode: int | None) -> None:
        """Initialize a failure using non-sensitive operation metadata."""
        super().__init__(f"{operation} failed")
        self.operation = operation
        self.returncode = returncode


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Terminate the subprocess and descendants on POSIX and Windows."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        taskkill = shutil.which("taskkill")
        if taskkill is None:
            process.kill()
            return
        subprocess.run(
            [taskkill, "/PID", str(process.pid), "/T", "/F"], check=False, capture_output=True, text=True, timeout=10
        )
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)


def run_glab(arguments: Sequence[str], timeout: float) -> str:
    """Run glab from an argument array with a process-group timeout.

    Returns:
        Standard output from a successful command.
    """
    glab = shutil.which("glab")
    if glab is None:
        raise VerificationCommandError("glab", None)
    process = subprocess.Popen(
        [glab, *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    try:
        stdout, _stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        terminate_process_tree(process)
        process.communicate()
        raise VerificationCommandError(arguments[0], None) from error
    if process.returncode != 0:
        raise VerificationCommandError(arguments[0], process.returncode)
    return stdout


def api_arguments(host: str, endpoint: str) -> list[str]:
    """Build an explicit-host read-only API command.

    Returns:
        The glab argument array.
    """
    return ["api", "--hostname", host, endpoint]


def request_json(runner: CommandRunner, arguments: Sequence[str], timeout: float) -> object:
    """Run a read-only glab request and decode JSON.

    Returns:
        The decoded value.
    """
    return json.loads(runner(arguments, timeout))


def as_object(value: object) -> JsonObject:
    """Require a string-keyed JSON object.

    Returns:
        The narrowed object.
    """
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise TypeError("expected JSON object")
    return value


def as_object_list(value: object) -> list[JsonObject]:
    """Require an array of JSON objects.

    Returns:
        The narrowed list.
    """
    if not isinstance(value, list):
        raise TypeError("expected JSON array")
    return [as_object(item) for item in value]


def as_int(value: object) -> int:
    """Require an integer or decimal string.

    Returns:
        The normalized integer.
    """
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError("expected integer")
    return int(value)


def as_str_list(value: object) -> list[str]:
    """Require an array of strings.

    Returns:
        The narrowed list.
    """
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError("expected string array")
    return value


def check(name: str, passed: bool, details: JsonObject) -> JsonObject:
    """Build one compact result.

    Returns:
        A JSON-compatible check.
    """
    return {"name": name, "ok": passed, "details": details}


def asset_endpoint(host: str, asset_url: str) -> str:
    """Convert a same-host GitLab API asset URL to a glab endpoint.

    Returns:
        The endpoint below `/api/v4/`.
    """
    parsed = urllib.parse.urlparse(asset_url)
    prefix = "/api/v4/"
    if parsed.scheme != "https" or parsed.hostname != host or not parsed.path.startswith(prefix):
        raise ValueError("asset URL must be an HTTPS API URL on the selected host")
    return parsed.path.removeprefix(prefix)


def fetch_release_state(
    *,
    host: str,
    project: str,
    default_branch: str,
    token_id: int,
    tag: str,
    main_pipeline_id: int,
    tag_pipeline_id: int,
    package_name: str,
    asset_url: str,
    timeout: float,
    runner: CommandRunner,
) -> JsonObject:
    """Fetch the complete Generic release contract through read-only endpoints.

    Returns:
        State required by every verifier check.
    """
    encoded_project = urllib.parse.quote(project, safe="")
    project_data = as_object(request_json(runner, api_arguments(host, f"projects/{encoded_project}"), timeout))
    project_id = str(project_data["id"])
    full_path = str(project_data["path_with_namespace"])
    packages = as_object_list(
        request_json(
            runner,
            api_arguments(
                host,
                f"projects/{project_id}/packages?package_type=generic&package_name={urllib.parse.quote(package_name, safe='')}&per_page=100",
            ),
            timeout,
        )
    )
    matching_packages = [item for item in packages if item.get("name") == package_name and item.get("version") == tag]
    package_files: list[JsonObject] = []
    if matching_packages:
        package_files = as_object_list(
            request_json(
                runner,
                api_arguments(host, f"projects/{project_id}/packages/{matching_packages[0]['id']}/package_files"),
                timeout,
            )
        )
    try:
        runner(api_arguments(host, asset_endpoint(host, asset_url)), timeout)
        asset_resolved = True
    except VerificationCommandError:
        asset_resolved = False
    return {
        "project": project_data,
        "protected_branch": as_object(
            request_json(
                runner,
                api_arguments(
                    host, f"projects/{project_id}/protected_branches/{urllib.parse.quote(default_branch, safe='')}"
                ),
                timeout,
            )
        ),
        "protected_tags": as_object_list(
            request_json(runner, api_arguments(host, f"projects/{project_id}/protected_tags"), timeout)
        ),
        "token": as_object(
            request_json(runner, api_arguments(host, f"projects/{project_id}/access_tokens/{token_id}"), timeout)
        ),
        "variables": as_object(
            request_json(
                runner,
                ["api", "--hostname", host, "graphql", "-f", f"query={VARIABLE_QUERY}", "-f", f"fullPath={full_path}"],
                timeout,
            )
        ),
        "tag": as_object(
            request_json(
                runner,
                api_arguments(host, f"projects/{project_id}/repository/tags/{urllib.parse.quote(tag, safe='')}"),
                timeout,
            )
        ),
        "main_pipeline": as_object(
            request_json(runner, api_arguments(host, f"projects/{project_id}/pipelines/{main_pipeline_id}"), timeout)
        ),
        "main_jobs": as_object_list(
            request_json(
                runner,
                api_arguments(host, f"projects/{project_id}/pipelines/{main_pipeline_id}/jobs?per_page=100"),
                timeout,
            )
        ),
        "tag_pipeline": as_object(
            request_json(runner, api_arguments(host, f"projects/{project_id}/pipelines/{tag_pipeline_id}"), timeout)
        ),
        "tag_jobs": as_object_list(
            request_json(
                runner,
                api_arguments(host, f"projects/{project_id}/pipelines/{tag_pipeline_id}/jobs?per_page=100"),
                timeout,
            )
        ),
        "packages": matching_packages,
        "package_files": package_files,
        "release": as_object(
            request_json(
                runner,
                api_arguments(host, f"projects/{project_id}/releases/{urllib.parse.quote(tag, safe='')}"),
                timeout,
            )
        ),
        "asset_resolved": asset_resolved,
    }


def variable_metadata(state: JsonObject, variable_key: str) -> JsonObject | None:
    """Select metadata for one variable without requesting its value.

    Returns:
        Matching metadata, or None.
    """
    variables = as_object(state["variables"])
    data = as_object(variables.get("data"))
    project = as_object(data.get("project"))
    ci_variables = as_object(project.get("ciVariables"))
    nodes = as_object_list(ci_variables.get("nodes"))
    return next((item for item in nodes if item.get("key") == variable_key), None)


def access_levels(resource: JsonObject, field: str) -> set[int]:
    """Return integer access levels from protected-ref metadata.

    Returns:
        Access levels present in the selected field.
    """
    return {as_int(item["access_level"]) for item in as_object_list(resource.get(field))}


def jobs_are_ordered(
    state: JsonObject,
    notes_jobs: Sequence[str],
    build_jobs: Sequence[str],
    publish_jobs: Sequence[str],
    release_job: str,
    lifecycle_stages: Sequence[str],
) -> tuple[bool, list[str]]:
    """Validate successful notes/build/publish/release stage order.

    Returns:
        Verdict and de-duplicated ordered names.
    """
    jobs = as_object_list(state["tag_jobs"])
    jobs_by_name = {str(item.get("name")): item for item in jobs}
    ordered_names = list(dict.fromkeys([*notes_jobs, *build_jobs, *publish_jobs, release_job]))
    selected = [jobs_by_name.get(name) for name in ordered_names]
    if not all(item is not None and item.get("status") == "success" for item in selected):
        return False, ordered_names
    stages = [str(item.get("stage")) for item in selected if item]
    ranks = {stage: index for index, stage in enumerate(lifecycle_stages)}
    if len(ranks) != len(lifecycle_stages) or len(lifecycle_stages) < MIN_LIFECYCLE_STAGE_COUNT:
        return False, ordered_names
    notes_stage = lifecycle_stages[0]
    build_stage = lifecycle_stages[1] if len(lifecycle_stages) >= SEPARATE_NOTES_BUILD_STAGE_COUNT else notes_stage
    publish_stage = lifecycle_stages[-2]
    release_stage = lifecycle_stages[-1]
    expected: dict[str, set[str]] = {name: {notes_stage} for name in notes_jobs}
    for name in build_jobs:
        expected[name] = expected.get(name, {build_stage}) & {build_stage}
    for name in publish_jobs:
        expected[name] = {publish_stage}
    expected[release_job] = {release_stage}
    valid_stages = all(stage in expected[name] for name, stage in zip(ordered_names, stages, strict=True))
    return valid_stages and [ranks[stage] for stage in stages] == sorted(
        ranks[stage] for stage in stages
    ), ordered_names


def release_link_matches(release: JsonObject, asset_name: str, asset_url: str) -> bool:
    """Check the exact Generic package Release link.

    Returns:
        True for one exact package link.
    """
    assets = as_object(release.get("assets"))
    links = as_object_list(assets.get("links"))
    return any(
        item.get("name") == asset_name and item.get("link_type") == "package" and item.get("url") == asset_url
        for item in links
    )


def verify_release_playbook(  # ruff: ignore[too-many-locals] - one report binds every explicit contract input to fetched state
    *,
    host: str,
    project: str,
    default_branch: str,
    branch_push_access_level: int,
    tag: str,
    expected_tag_sha: str,
    tag_pattern: str,
    tag_access_level: int,
    main_pipeline_id: int,
    main_sha: str,
    version_job: str,
    version_stage: str,
    tag_pipeline_id: int,
    token_id: int,
    token_access_level: int,
    token_scopes: Sequence[str],
    token_expires_at: str,
    release_commit_required: bool,
    variable_key: str,
    variable_type: str,
    variable_scope: str,
    package_name: str,
    package_status: str,
    asset_name: str,
    asset_size: int,
    asset_sha256: str,
    asset_url: str,
    release_description_contains: str,
    notes_jobs: Sequence[str],
    build_jobs: Sequence[str],
    publish_jobs: Sequence[str],
    release_job: str,
    lifecycle_stages: Sequence[str],
    timeout: float,
    runner: CommandRunner = run_glab,
) -> JsonObject:
    """Verify every declared Generic release invariant.

    Returns:
        A JSON-compatible verification report.
    """
    state = fetch_release_state(
        host=host,
        project=project,
        default_branch=default_branch,
        token_id=token_id,
        tag=tag,
        main_pipeline_id=main_pipeline_id,
        tag_pipeline_id=tag_pipeline_id,
        package_name=package_name,
        asset_url=asset_url,
        timeout=timeout,
        runner=runner,
    )
    project_data = as_object(state["project"])
    protected_branch = as_object(state["protected_branch"])
    protected_tags = as_object_list(state["protected_tags"])
    token = as_object(state["token"])
    tag_data = as_object(state["tag"])
    tag_commit = as_object(tag_data.get("commit"))
    main_pipeline = as_object(state["main_pipeline"])
    main_jobs = as_object_list(state["main_jobs"])
    tag_pipeline = as_object(state["tag_pipeline"])
    packages = as_object_list(state["packages"])
    package_files = as_object_list(state["package_files"])
    release = as_object(state["release"])
    variable = variable_metadata(state, variable_key)
    protected_rule = next(
        (item for item in protected_tags if item.get("name") == tag_pattern and fnmatch.fnmatch(tag, tag_pattern)), None
    )
    branch_levels = access_levels(protected_branch, "push_access_levels")
    tag_levels = access_levels(protected_rule, "create_access_levels") if protected_rule else set()
    actual_token_access_level = as_int(token.get("access_level"))
    credential_authorized = actual_token_access_level >= tag_access_level and (
        not release_commit_required or actual_token_access_level >= branch_push_access_level
    )
    version = next((item for item in main_jobs if item.get("name") == version_job), None)
    lifecycle_stage_set = set(lifecycle_stages)
    main_job_stages = {str(item.get("stage")) for item in main_jobs}
    ordered, ordered_names = jobs_are_ordered(
        state, notes_jobs, build_jobs, publish_jobs, release_job, lifecycle_stages
    )
    package = next((item for item in packages if item.get("status") == package_status), None)
    package_file = next(
        (
            item
            for item in package_files
            if item.get("file_name") == asset_name
            and item.get("size") == asset_size
            and item.get("file_sha256") == asset_sha256
        ),
        None,
    )
    checks = [
        check(
            "protected_default_branch",
            project_data.get("default_branch") == default_branch
            and protected_branch.get("name") == default_branch
            and branch_push_access_level in branch_levels,
            {"branch": default_branch, "push_access_level": branch_push_access_level},
        ),
        check(
            "protected_tag_creator",
            protected_rule is not None and tag_access_level in tag_levels,
            {"pattern": tag_pattern, "create_access_level": tag_access_level},
        ),
        check(
            "token_metadata",
            str(token.get("id")) == str(token_id)
            and token.get("access_level") == token_access_level
            and set(as_str_list(token.get("scopes"))) == set(token_scopes)
            and token.get("active") is True
            and token.get("revoked") is False
            and token.get("expires_at") == token_expires_at,
            {"token_id": token_id, "access_level": token_access_level, "scopes": list(token_scopes)},
        ),
        check("credential_authorization", credential_authorized, {"release_commit_required": release_commit_required}),
        check(
            "variable_metadata",
            variable is not None
            and all(variable.get(field) is True for field in ("protected", "masked", "hidden", "raw"))
            and variable.get("variableType") == variable_type
            and variable.get("environmentScope") == variable_scope,
            {"key": variable_key, "type": variable_type, "scope": variable_scope},
        ),
        check(
            "main_pipeline",
            main_pipeline.get("id") == main_pipeline_id
            and main_pipeline.get("ref") == default_branch
            and main_pipeline.get("sha") == main_sha
            and main_pipeline.get("source") == "push"
            and main_pipeline.get("status") == "success",
            {"pipeline_id": main_pipeline_id, "sha": main_sha},
        ),
        check(
            "version_job",
            version is not None and version.get("status") == "success" and version.get("stage") == version_stage,
            {"job": version_job, "stage": version_stage},
        ),
        check(
            "main_lifecycle_stages_absent",
            lifecycle_stage_set.isdisjoint(main_job_stages),
            {"lifecycle_only_stages": list(lifecycle_stages)},
        ),
        check(
            "tag_commit",
            tag_data.get("name") == tag
            and tag_data.get("protected") is True
            and tag_commit.get("id") == expected_tag_sha,
            {"tag": tag, "sha": expected_tag_sha},
        ),
        check(
            "tag_pipeline",
            tag_pipeline.get("id") == tag_pipeline_id
            and tag_pipeline.get("ref") == tag
            and tag_pipeline.get("sha") == expected_tag_sha
            and tag_pipeline.get("source") == "push"
            and tag_pipeline.get("status") == "success",
            {"pipeline_id": tag_pipeline_id, "sha": expected_tag_sha},
        ),
        check("ordered_jobs", ordered, {"jobs": ordered_names}),
        check("generic_package", package is not None, {"name": package_name, "version": tag, "status": package_status}),
        check(
            "package_file", package_file is not None, {"asset": asset_name, "size": asset_size, "sha256": asset_sha256}
        ),
        check(
            "gitlab_release",
            release.get("tag_name") == tag and release_description_contains in str(release.get("description", "")),
            {"tag": tag, "description_contains": release_description_contains},
        ),
        check("package_asset_link", release_link_matches(release, asset_name, asset_url), {"url": asset_url}),
        check("package_asset_resolves", state.get("asset_resolved") is True, {"url": asset_url}),
    ]
    return {
        "ok": all(item["ok"] for item in checks),
        "project": {"id": project_data["id"], "path": project_data["path_with_namespace"]},
        "tag": tag,
        "main_pipeline_id": main_pipeline_id,
        "tag_pipeline_id": tag_pipeline_id,
        "scope": "gitlab_generic_only",
        "checks": checks,
    }


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse explicit expected contract values.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Output and exits:
  stdout is one compact JSON object. `scope` is always `gitlab_generic_only`.
  `checks` contains every named boolean verdict; `ok` is true only when all pass.
  Exit 0: all checks pass. Exit 1: requests succeeded but one or more checks fail.
  Exit 2: input, JSON decoding, or bounded glab execution failed; output contains
  `ok:false`, `error`, and command metadata when available.

Repeated options:
  Repeat --token-scope, --lifecycle-stage, --notes-job, --build-job, and
  --publish-job once per expected value. Supply --lifecycle-stage in GitLab
  stage order and exclude the main version-evaluation stage. Use three stages
  when notes/build share the first stage, or four when they are separate.
""",
    )
    target = parser.add_argument_group("GitLab target and protected refs")
    target.add_argument("--host", required=True, help="Bare GitLab hostname used by every read-only glab request.")
    target.add_argument(
        "--project", required=True, help="Numeric project ID or namespaced path identifying the API target."
    )
    target.add_argument(
        "--default-branch", required=True, help="Project-reported default branch expected to be protected."
    )
    target.add_argument(
        "--branch-push-access-level",
        required=True,
        type=int,
        help="Expected protected-branch push access level from API metadata.",
    )
    target.add_argument("--tag", required=True, help="Existing release tag verified by repository and Release APIs.")
    target.add_argument(
        "--expected-tag-sha", required=True, help="Dereferenced commit SHA expected for the tag and tag pipeline."
    )
    target.add_argument("--tag-pattern", required=True, help="Exact protected-tag wildcard expected to match --tag.")
    target.add_argument(
        "--tag-access-level",
        required=True,
        type=int,
        help="Expected protected-tag creator access level from API metadata.",
    )

    pipelines = parser.add_argument_group("Main and tag pipelines")
    pipelines.add_argument(
        "--main-pipeline-id",
        required=True,
        type=int,
        help="Default-branch push pipeline ID that ran version evaluation.",
    )
    pipelines.add_argument("--main-sha", required=True, help="Commit SHA reported by the main pipeline.")
    pipelines.add_argument(
        "--version-job", required=True, help="Successful version-evaluation job expected in the main pipeline."
    )
    pipelines.add_argument(
        "--version-stage", required=True, help="Project-selected main stage containing only version evaluation."
    )
    pipelines.add_argument(
        "--tag-pipeline-id", required=True, type=int, help="Ordinary tag-push pipeline ID for --tag."
    )
    pipelines.add_argument(
        "--lifecycle-stage",
        required=True,
        action="append",
        help="Tag-only lifecycle stage in GitLab order; repeat for notes/build/publication/release equivalents.",
    )
    pipelines.add_argument(
        "--notes-job",
        required=True,
        action="append",
        help="Expected tag-lifecycle notes job, absent from main; repeat for multiple jobs.",
    )
    pipelines.add_argument(
        "--build-job",
        required=True,
        action="append",
        help="Expected tag-lifecycle build job, absent from main; repeat for multiple jobs.",
    )
    pipelines.add_argument(
        "--publish-job",
        required=True,
        action="append",
        help="Expected tag-lifecycle Generic publish job, absent from main; repeat for multiple jobs.",
    )
    pipelines.add_argument(
        "--release-job", required=True, help="Single tag-lifecycle release job after publications and absent from main."
    )

    credential = parser.add_argument_group("Release credential and variable metadata")
    credential.add_argument(
        "--token-id", required=True, type=int, help="Project access-token numeric ID read from setup output."
    )
    credential.add_argument(
        "--token-access-level", required=True, type=int, help="Expected project access-token numeric role level."
    )
    credential.add_argument(
        "--token-scope", required=True, action="append", help="Expected token scope; repeat once per exact scope."
    )
    credential.add_argument(
        "--token-expires-at", required=True, help="Expected token expiry date in GitLab API YYYY-MM-DD form."
    )
    credential.add_argument(
        "--release-commit-required",
        action="store_true",
        help="Require token authorization for protected default-branch push as well as tag creation.",
    )
    credential.add_argument(
        "--variable-key", required=True, help="Protected CI variable key holding the Git credential."
    )
    credential.add_argument(
        "--variable-type", required=True, help="Expected GraphQL variableType value, for example ENV_VAR."
    )
    credential.add_argument(
        "--variable-scope", required=True, help="Expected GraphQL environmentScope value, for example *."
    )

    package = parser.add_argument_group("GitLab Generic package and Release")
    package.add_argument(
        "--package-name", required=True, help="Exact Generic package name selected by project coordinates."
    )
    package.add_argument("--package-status", required=True, help="Expected package API status, for example default.")
    package.add_argument("--asset-name", required=True, help="Exact Generic package file and Release-link name.")
    package.add_argument(
        "--asset-size", required=True, type=int, help="Expected package-file size in bytes from API metadata."
    )
    package.add_argument("--asset-sha256", required=True, help="Expected package-file SHA-256 from API metadata.")
    package.add_argument(
        "--asset-url",
        required=True,
        help="Exact same-host HTTPS Generic API URL expected in the Release and read back.",
    )
    package.add_argument(
        "--release-description-contains",
        required=True,
        help="Project-selected text required in the created Release description.",
    )

    runtime = parser.add_argument_group("Execution bound")
    runtime.add_argument(
        "--timeout", type=float, default=30.0, help="Per-glab-request timeout in seconds (default: 30)."
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Emit compact JSON and return nonzero when verification fails.

    Returns:
        Zero for success, one for failed checks, or two for execution/input errors.
    """
    options = parse_arguments(arguments)
    try:
        result = verify_release_playbook(
            host=options.host,
            project=options.project,
            default_branch=options.default_branch,
            branch_push_access_level=options.branch_push_access_level,
            tag=options.tag,
            expected_tag_sha=options.expected_tag_sha,
            tag_pattern=options.tag_pattern,
            tag_access_level=options.tag_access_level,
            main_pipeline_id=options.main_pipeline_id,
            main_sha=options.main_sha,
            version_job=options.version_job,
            version_stage=options.version_stage,
            tag_pipeline_id=options.tag_pipeline_id,
            token_id=options.token_id,
            token_access_level=options.token_access_level,
            token_scopes=options.token_scope,
            token_expires_at=options.token_expires_at,
            release_commit_required=options.release_commit_required,
            variable_key=options.variable_key,
            variable_type=options.variable_type,
            variable_scope=options.variable_scope,
            package_name=options.package_name,
            package_status=options.package_status,
            asset_name=options.asset_name,
            asset_size=options.asset_size,
            asset_sha256=options.asset_sha256,
            asset_url=options.asset_url,
            release_description_contains=options.release_description_contains,
            notes_jobs=options.notes_job,
            build_jobs=options.build_job,
            publish_jobs=options.publish_job,
            release_job=options.release_job,
            lifecycle_stages=options.lifecycle_stage,
            timeout=options.timeout,
            runner=run_glab,
        )
    except (VerificationCommandError, ValueError, json.JSONDecodeError, KeyError, TypeError) as error:
        payload: JsonObject = {"ok": False, "error": type(error).__name__}
        if isinstance(error, VerificationCommandError):
            payload.update({"operation": error.operation, "returncode": error.returncode})
        print(json.dumps(payload, separators=(",", ":")))
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
