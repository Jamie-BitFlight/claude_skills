# python-semantic-release Version Adapter

Evidence: **LIVE-VERIFIED behavior** with python-semantic-release `10.6.2`; the reusable component
is derived from that evidence.

Include `assets/release-components/templates/python-semantic-release-version.yml` from a dedicated
component project. Pass a unique job name, the consumer's version stage and rules, a digest-pinned
Python image, exact tool version, Git identity, remote name, credential-free repository URL, tag
prefix, and the dedicated version environment. The component clears configured credential helpers,
rewrites the selected remote, and forces askpass to read `RELEASE_PUSH_TOKEN` at runtime. It writes
untracked runtime TOML from its typed inputs and `CI_DEFAULT_BRANCH`, then passes it through PSR's
documented `--config` option. The remote name and URL have no defaults.

Requirements:

- complete Git history and tags (`GIT_DEPTH: "0"`);
- Git present and detached checkout attached to the actual default branch and upstream;
- credential authorized for protected tag and release commit;
- `--skip-build --no-vcs-release`; and
- generated runtime config matches the resolved branch/tag contract and remains uncommitted.

Component setup is complete when the rendered runtime config names the same remote used by the
attached default branch and the consumer includes no second version component.

Apply the exact variable scope and secret-handling boundary from the
[component-project README](../assets/release-components/README.md).

Apply the structure, composition, credential, and main
[validation gates](./automatic-tag-and-release.md#validation-gates), including successful
no-release evaluation on the release-commit pipeline.

SOURCE: <https://python-semantic-release.readthedocs.io/en/latest/api/commands.html#semantic-release-version> (accessed 2026-09-22; python-semantic-release `10.6.2` behavior live verified)
SOURCE: <https://docs.gitlab.com/ci/environments/#limit-the-environment-scope-of-a-cicd-variable> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/environments/#access-an-environment-for-preparation-or-verification-purposes> (accessed 2026-09-22)
