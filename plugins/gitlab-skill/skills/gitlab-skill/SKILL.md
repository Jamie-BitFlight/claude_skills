---
name: gitlab-skill
description: Build, review, and validate documented GitLab CI/CD configuration and GitLab Flavored Markdown. Use when working with `.gitlab-ci.yml` semantics, reusable CI/CD components, component or pipeline inputs, GitLab Functions, `gitlab-ci-local` checks, or GLFM syntax; do not use for general GitLab administration, pipeline operations, issue management, or non-GitLab CI systems.
---

# GitLab CI/CD and GLFM

Load each reference whose trigger matches the task:

- [Pipeline Configuration](./references/pipeline-optimization.md) - Load for include merge order, `extends`, `needs`, `parallel:matrix`, compile-time expressions, or CI Lint behavior.
- [CI/CD Components and Inputs](./references/ci-cd-components-and-inputs.md) - Load for component structure, testing, Catalog publication, version selection, consumption, component inputs, or pipeline inputs.
- [GitLab Functions](./references/gitlab-functions.md) - Load for experimental Function packages, authoring syntax, invocation, inputs, outputs, composition, loading, OCI publication, constraints, or migration from obsolete Steps names.
- [Security and Deprecations](./references/security-and-deprecations.md) - Load when reviewing untrusted includes/components, handling credentials, pinning dependencies, or modernizing deprecated CI syntax.
- [GitLab CI Local](./references/gitlab-ci-local-guide.md) - Load for local executors, input validation, include caching, `--skip-input-validation`, or `--fetch-includes`.
- [GitLab Flavored Markdown](./references/glfm-syntax.md) - Load for documented GLFM syntax and rendering constraints.

For uncovered CI/CD subjects, consult the [official GitLab CI/CD documentation](https://docs.gitlab.com/ci/). For uncovered GLFM subjects, consult the [official GitLab Flavored Markdown documentation](https://docs.gitlab.com/user/markdown/). For GitLab CI/CD configuration validation, follow the [official GitLab CI Lint guidance](https://docs.gitlab.com/ci/yaml/lint/).
