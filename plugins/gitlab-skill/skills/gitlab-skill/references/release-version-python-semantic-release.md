# python-semantic-release Version Adapter

Evidence: **LIVE-VERIFIED behavior** with python-semantic-release `10.6.2`; generalized assets are
**DERIVED + CI-LINT-VERIFIED**.

Copy `assets/release-playbook/python-semantic-release.gitlab-ci.yml` and merge
`pyproject-semantic-release.toml` into project configuration. Replace default-branch regex, tag
format, immutable Python image digest, tool version, and Git identity.

Requirements:

- complete Git history and tags (`GIT_DEPTH: "0"`);
- Git present and detached checkout attached to the actual default branch and upstream;
- credential authorized for protected tag and release commit;
- `--skip-build --no-vcs-release`; and
- every configuration marker replaced.

Validation gate: apply **Gates G2, G3, and G5** from the universal lifecycle, including successful
no-release evaluation on the release-commit pipeline.

SOURCE: <https://python-semantic-release.readthedocs.io/en/latest/api/commands.html#semantic-release-version> (accessed 2026-09-22; python-semantic-release `10.6.2` behavior live verified)
