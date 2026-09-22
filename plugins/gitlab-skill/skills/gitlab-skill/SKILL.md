---
name: gitlab-skill
description: Use when designing or validating GitLab CI/CD and automatic release lifecycles, inspecting pipeline and job state read-only, composing non-interactive merge-request commands, or setting up protected refs and release credentials. Also covers reusable components and inputs, GitLab Functions, gitlab-ci-local, glab command composition, and GitLab Flavored Markdown. For pipeline execution or retry requests, provide inspection and command drafting while leaving execution to the operator.
---

# GitLab CI/CD and GLFM

Load each reference whose trigger matches the task:

- [Pipeline Configuration](./references/pipeline-optimization.md) - Load for include merge order, `extends`, `needs`, `parallel:matrix`, compile-time expressions, or CI Lint behavior.
- [CI/CD Components and Inputs](./references/ci-cd-components-and-inputs.md) - Load for component structure, testing, Catalog publication, version selection, consumption, component inputs, or pipeline inputs.
- [GitLab Functions Core](./references/gitlab-functions.md) - Load for Function packages, definitions, job invocation, inputs, outputs, runtime expressions, environment, or composition.
- [GitLab Functions OCI](./references/gitlab-functions-oci.md) - Load only for OCI/file-system loading, OCI build/publication, registry authentication, or Function image tags.
- [Obsolete Functions Migration](./references/gitlab-functions-steps-migration.md) - Load only when interpreting or migrating existing CI/CD Steps, `step.yml`, `step:`, `step_dir`, or `job.<variable>` syntax.
- [Security and Deprecations](./references/security-and-deprecations.md) - Load when reviewing untrusted includes/components, handling credentials, pinning dependencies, or modernizing deprecated CI syntax.
- [GitLab CI Local](./references/gitlab-ci-local-guide.md) - Load for local executors, input validation, include caching, `--skip-input-validation`, or `--fetch-includes`.
- [GitLab Flavored Markdown](./references/glfm-syntax.md) - Load for documented GLFM syntax and rendering constraints.
- [glab CLI](./references/glab-cli.md) - Load before composing `glab` API, repository, CI, merge-request, token, or variable commands, especially for self-managed hosts or environment-token authentication.
- [Automatic Tags and Releases](./references/automatic-tag-and-release.md) - Load for automatic release intake, no-release or release branches, replaceable adapters, release-tag routing, composition, or universal checkpoint reporting; follow its conditional pointers for selected tools, destinations, and credentials.
- [Release Live Evidence](./references/release-live-evidence.md) - Load only when the user requests live proof, sandbox IDs, observed failures, or evidence classification for the release lifecycle.

For uncovered CI/CD subjects, consult the [official GitLab CI/CD documentation](https://docs.gitlab.com/ci/). For uncovered GLFM subjects, consult the [official GitLab Flavored Markdown documentation](https://docs.gitlab.com/user/markdown/). For GitLab CI/CD configuration validation, follow the [official GitLab CI Lint guidance](https://docs.gitlab.com/ci/yaml/lint/).
