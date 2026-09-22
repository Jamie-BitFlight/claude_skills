# python-semantic-release Version Adapter

Evidence: **LIVE-VERIFIED behavior** with python-semantic-release `10.6.2`; generalized assets are
**DERIVED + CI-LINT-VERIFIED**.

Copy `assets/release-playbook/python-semantic-release.gitlab-ci.yml` and
`materialize_psr_config.py`. The job writes untracked runtime TOML from `CI_DEFAULT_BRANCH` and the
required base-provided `RELEASE_TAG_PREFIX`, then passes it through PSR's documented `--config`
option. Resolve the selected Git remote name into `__RELEASE_GIT_REMOTE_NAME__`; the job uses that
name for upstream tracking and writes it into PSR's runtime remote configuration. Resolve immutable
Python image digest, tool version, and Git identity.

Requirements:

- complete Git history and tags (`GIT_DEPTH: "0"`);
- Git present and detached checkout attached to the actual default branch and upstream;
- credential authorized for protected tag and release commit;
- `--skip-build --no-vcs-release`; and
- generated runtime config matches the resolved branch/tag contract and remains uncommitted.

Adapter setup is complete when no substitution marker remains and the rendered runtime config names
the same remote used by the attached default branch.

Validation gate: apply **Gates G2, G3, and G5** from the universal lifecycle, including successful
no-release evaluation on the release-commit pipeline.

SOURCE: <https://python-semantic-release.readthedocs.io/en/latest/api/commands.html#semantic-release-version> (accessed 2026-09-22; python-semantic-release `10.6.2` behavior live verified)
