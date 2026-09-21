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
