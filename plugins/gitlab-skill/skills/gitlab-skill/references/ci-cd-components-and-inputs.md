# CI/CD Components and Inputs

## Component Project

A component project must have a root `README.md` documenting every component and a top-level `templates/` directory. Store each component in `templates/<name>.yml` or `templates/<name>/template.yml`.

Use `assets/release-components/` for a complete release-component project shape. Keep orchestration
in the consumer: workflow admission, the full stage list, policy rules, one version-adapter
selection, project builds, dependencies, and immutable component pins. Component templates remain
self-contained and expose configuration through typed inputs.

```yaml
spec:
  inputs:
    stage:
      default: test
---
component-job:
  script: echo job 1
  stage: $[[ inputs.stage ]]
```

All components in a project are versioned together. A project can contain up to 100 components. If a component needs independent versioning, it should be moved to a dedicated project.

SOURCE: <https://docs.gitlab.com/ci/components/#create-a-component-project> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/components/#directory-structure> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/components/#avoid-using-global-keywords> (accessed 2026-09-22)

## Test a Component

GitLab strongly recommends testing component behavior and side effects in the component project's root `.gitlab-ci.yml`. Include the component from the current project at the current commit SHA.

```yaml
include:
  - component: $CI_SERVER_FQDN/$CI_PROJECT_PATH/my-component@$CI_COMMIT_SHA
    inputs:
      stage: build
```

Authentication is required when the project is private.

SOURCE: <https://docs.gitlab.com/ci/components/#test-the-component> (accessed 2026-09-21)

## Publish to the CI/CD Catalog

GitLab documents two publication steps: set the project as a Catalog project, then publish a new release. Setting the Catalog project toggle requires the Owner role. The project becomes discoverable in the Catalog only after a release is published.

Publishing a release requires the Maintainer or Owner role. At the tag's commit SHA, the project must be a Catalog project, have a project description, have a root `README.md`, and contain at least one component under `templates/`. Use the `release` keyword rather than the Releases API.

GitLab recommends configuring the tag pipeline to test components before the release job. The publication steps are:

1. Add a tag-triggered release job to `.gitlab-ci.yml`.
2. Create a semantic-version tag to trigger that pipeline.

```yaml
create-release:
  stage: release
  image: registry.gitlab.com/gitlab-org/cli:latest
  script: echo "Creating release $CI_COMMIT_TAG"
  rules:
    - if: $CI_COMMIT_TAG
  release:
    tag_name: $CI_COMMIT_TAG
    description: "Release $CI_COMMIT_TAG of components in $CI_PROJECT_PATH"
```

The official example above uses the mutable `:latest` image tag. Preserve `:latest` only when quoting the official example; use a SHA digest in production output.

After the release job succeeds, GitLab creates the release and publishes the version to the Catalog. Catalog tags must use semantic versions such as `1.0.0`, `2.3.4`, or `1.0.0-alpha`.

SOURCE: <https://docs.gitlab.com/ci/components/#publish-a-new-release> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/yaml/#release> (accessed 2026-09-21)

## Consume and Select Versions

Use `include:component` with `<fully-qualified-domain-name>/<project-path>/<component-name>@<specific-version>`.

```yaml
include:
  - component: $CI_SERVER_FQDN/my-org/security-components/secret-detection@1.0.0
    inputs:
      stage: build
```

Version selector precedence is commit SHA, tag, branch, then a partial semantic version or `~latest`. Partial semantic versions and `~latest` do not select prereleases. Specify a complete version such as `1.0.1-rc` to select a prerelease. GitLab recommends a Catalog version; branches and SHAs can be used for testing.

Included component configuration merges into the pipeline configuration. Identically named configuration in the component and pipeline can interact unexpectedly.

SOURCE: <https://docs.gitlab.com/ci/components/#use-a-component> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/components/#component-versions> (accessed 2026-09-21)

## Configuration Inputs

Define typed configuration or component inputs in the header with `spec:inputs`. Refer to them outside the header with `$[[ inputs.<input-id> ]]`. Separate the header from jobs with `---`.

SOURCE: <https://docs.gitlab.com/ci/inputs/> (accessed 2026-09-21)

## Pipeline Inputs

Pipeline inputs are parameters supplied when a pipeline starts. They validate at pipeline creation time, and a pipeline accepts up to 20 inputs. Pass values to a downstream pipeline with `trigger:inputs`.

In GitLab 17.7 and later, GitLab recommends pipeline inputs instead of pipeline variables for pipeline parameters and recommends disabling pipeline variables when inputs are used. Store sensitive secrets with an external secrets management provider.

SOURCE: <https://docs.gitlab.com/ci/inputs/#for-a-pipeline> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/pipelines/downstream_pipelines/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/variables/> (accessed 2026-09-21)
