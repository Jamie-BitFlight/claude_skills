# python-semantic-release Version Adapter

Evidence: **LIVE-VERIFIED + EXECUTABLE-FIXTURE-VERIFIED** with python-semantic-release `10.6.2`.
See [Hardened Transport Component Evidence](./release-live-evidence.md#hardened-transport-component-evidence)
for initiating, release-commit, tag, publication, and Release proof.

Include `assets/release-components/templates/python-semantic-release-version.yml` from a dedicated
component project. Pass a unique job name, the consumer's version stage and rules, a digest-pinned
Python image, exact tool version, Git identity, remote name, credential-free repository URL, tag
prefix, and the dedicated version environment. Require HTTPS. It writes untracked runtime TOML from its typed
inputs and `CI_DEFAULT_BRANCH`, then passes it through PSR's documented `--config` option. The
remote name and URL have no defaults. Pass a collision-free credential variable name; its
same-scope `_SHA256` companion must match before remote mutation. Because this adapter uses
`--no-vcs-release`, it supplies no separate GitLab API token; `ignore_token_for_push = true` prevents
token-derived Git transport if project configuration adds one later. Basic authorization is scoped
only to the selected remote's effective HTTPS URL.

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

SOURCE: <https://python-semantic-release.readthedocs.io/en/latest/api/commands.html#semantic-release-version> (accessed 2026-09-22; command contract documentation-verified and fixture-tested)
SOURCE: <https://docs.gitlab.com/ci/environments/#limit-the-environment-scope-of-a-cicd-variable> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/environments/#access-an-environment-for-preparation-or-verification-purposes> (accessed 2026-09-22)
SOURCE: <https://git-scm.com/docs/git-config#Documentation/git-config.txt-httpextraHeader> (accessed 2026-09-22; process-scoped transport fixture verified)
