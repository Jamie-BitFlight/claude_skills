# Security and Deprecations

## Components and Credentials

- Review third-party component source before use.
- Pin components to a specific commit SHA, preferably, or a release version tag.
- Run component jobs in ephemeral, isolated runner environments where possible.
- Limit `CI_JOB_TOKEN` project access and permissions.
- Store the most sensitive secrets in a secrets manager.
- Use inputs rather than pipeline variables for pipeline parameters.

SOURCE: <https://docs.gitlab.com/ci/components/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/pipeline_security/> (accessed 2026-09-21)

## Release and Package Authentication

For releases created in CI/CD, use the job's short-lived `CI_JOB_TOKEN`. GitLab's `glab release
create` documentation recommends enabling CI auto-login with `GLAB_ENABLE_CI_AUTOLOGIN=true`; glab
sends the job token in the `JOB-TOKEN` header accepted by the Releases API. When release assets
should be stored as generic packages, `glab release create --use-package-registry` uploads them to
the project's generic package registry. Do not assign `CI_JOB_TOKEN` to `GITLAB_TOKEN`, because glab
sends those credentials with different headers.

The generic package registry accepts `CI_JOB_TOKEN` and recommends job tokens for automated
pipelines. If a job token cannot satisfy a package-registry integration, use only the narrower
documented alternative: a deploy token scoped to `read_package_registry`,
`write_package_registry`, or both. For a release operation that does not support job tokens, glab
documents a project or group access token with `api` scope as the alternative.

SOURCE: <https://docs.gitlab.com/cli/release/create/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/cli/auth/login/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/jobs/ci_job_token/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/user/packages/generic_packages/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/user/project/deploy_tokens/> (accessed 2026-09-22)

## Catalog Publication

Publish a CI/CD Catalog component from a tag pipeline with the CI `release` keyword. GitLab
explicitly directs Catalog publishers to use `release` rather than manually running the underlying
glab catalog-publication option.

SOURCE: <https://docs.gitlab.com/ci/components/#publish-a-new-release> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/yaml/#release> (accessed 2026-09-22)

## Inputs and Secrets

Inputs are typed configuration parameters evaluated when pipeline configuration is created. Inputs
are not secrets. Use an external secrets provider for API tokens, credentials, private keys,
and other sensitive values; jobs must explicitly request those secrets.

SOURCE: <https://docs.gitlab.com/ci/inputs/> (accessed 2026-09-22)
SOURCE: <https://docs.gitlab.com/ci/secrets/> (accessed 2026-09-22)

## Immutable References

- Use SHA digests for Docker images.
- Use specific refs for includes and components where possible.
- Use `include:integrity` with `include:remote` to specify the remote file's SHA256 hash. GitLab rejects a remote file when its content does not match the hash.

SOURCE: <https://docs.gitlab.com/ci/pipeline_security/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/yaml/#includeintegrity> (accessed 2026-09-21)

## Deprecated Configuration

- Replace global `image`, `services`, `cache`, `before_script`, and `after_script` with `default`.
- Replace `only` and `except` with `rules`.
- Replace legacy Pages publication forms with the `pages` and `pages.publish` keywords.
- Prefer `strategy: mirror` to `strategy: depend` when the trigger job must match downstream pipeline status.

SOURCE: <https://docs.gitlab.com/ci/yaml/deprecated_keywords/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/pipelines/downstream_pipelines/> (accessed 2026-09-21)

GitLab deprecates features that are no longer recommended and removes each deprecated feature in a future release. On GitLab.com, removal can occur at any time during the month leading up to that release.

SOURCE: <https://docs.gitlab.com/update/deprecations/> (accessed 2026-09-21)
