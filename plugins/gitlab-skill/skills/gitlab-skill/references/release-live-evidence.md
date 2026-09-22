# Release Lifecycle Live Evidence

Evidence date: 2026-09-22. Environment: self-managed GitLab `18.7.0-ee`, project `529`, and
`glab 1.118.0`. This file is the single ledger summary; generalized templates are not labeled as
live-executed.

## Exact Fixtures

The redacted files fetched from the successful commits are preserved under
`assets/release-components/live-verified/`:

- `semantic-release.gitlab-ci.yml` and `.releaserc.json` from commit `c6de8fb`.
- `python-semantic-release.gitlab-ci.yml` and `pyproject.toml` from release commit `95f5b4c`.

Their `live-verified` directory is the evidence label. They retain the sandbox's `main` branch,
`release-playbook-v*` naming, exact commands, and mutable images as observed evidence; they are not
general project templates.

## Observed Chains

- semantic-release `25.0.9`: main pipeline `5680`, version job `7068`, tag
  `release-playbook-v1.0.0`, tag pipeline `5681`, jobs `7069 -> 7070 -> 7071`.
- python-semantic-release `10.6.2`: main pipeline `5690`, version job `7085`, release commit
  `95f5b4c`, tag `release-playbook-v1.1.0`, no-release release-commit pipeline `5691`, tag pipeline
  `5692`, jobs `7088 -> 7089 -> 7090`.
- Both tag pipelines created one Generic package file with `201 Created`, then a GitLab Release with
  generated Markdown description and durable `link_type: package` URL.

## Corrected Failures

- Job `7065` failed because the Node Alpine image lacked Git; installing Git produced successful job
  `7068`.
- Job `7074` failed from detached HEAD; attaching the actual branch and upstream produced successful
  job `7085`.
- The release-commit pipeline `5691` reported that `1.1.0` was already released and created no
  duplicate tag, demonstrating the no-release branch.

## Credential Evidence

- Tag-only token `562`: Developer, `write_repository`; exercised, then revoked.
- Release-commit token `563`: Maintainer, `write_repository`; exercised, then rotated.
- Rotated token `564`: Maintainer, `write_repository`, active, expiry `2026-10-22`; not exercised for
  Git authentication after rotation.
- Protected wildcard `release-playbook-v*` allowed Developer creation. Protected variable metadata
  was ENV_VAR, environment scope `*`, protected, masked, hidden, and raw.

## Evidence Boundary

LIVE-VERIFIED: the two named version-tool behaviors, ordinary tag-push handoff, Generic publication,
release-last ordering, release descriptions, and package links. These copied pipeline files predate
the component refactor and remain evidence, not reusable component templates.

DOCUMENTATION-VERIFIED, NOT LIVE-TESTED: GitLab PyPI, GitLab npm, PyPI.org, and npmjs.com adapters.

SOURCE: <https://docs.gitlab.com/ci/> (reviewed 2026-09-22; IDs and files verified against the sandbox ledger and current read-only APIs)
