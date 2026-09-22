# GitLab Generic Publication Adapter

Evidence: **LIVE-VERIFIED** publication and read-back; generalized publication asset is **DERIVED +
CI-LINT-VERIFIED**.

Copy `assets/release-playbook/generic-package.gitlab-ci.yml`. It extends only `.release_publish`,
consumes the build artifact, and uploads it with `CI_JOB_TOKEN`. Select the separate
`gitlab-release.gitlab-ci.yml` once for the complete lifecycle.

The base defaults package name to `CI_PROJECT_NAME`; package version is `CI_COMMIT_TAG`; project and
API coordinates use `CI_PROJECT_ID` and `CI_API_V4_URL`. Artifact path/name remain explicit policy
inputs because GitLab cannot derive project build outputs. Override shared defaults once in root CI.

Run `verify_release_playbook.py --help` for the authoritative Generic verification inputs, repeated
option semantics, JSON contract, scope, and exit codes.

Validation gate: apply **Gates G2, G3, G6, G7, and G8**.

SOURCE: <https://docs.gitlab.com/user/packages/generic_packages/> (accessed 2026-09-22; publication and read-back live verified twice)
