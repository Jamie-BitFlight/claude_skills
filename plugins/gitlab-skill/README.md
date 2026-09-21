<p align="center">
  <img src="./assets/hero.png" alt="GitLab CI/CD and Documentation" width="800" />
</p>

# GitLab CI/CD and Documentation

This plugin provides current, source-backed guidance for documented GitLab CI/CD semantics, reusable components and inputs, experimental GitLab Functions, and GitLab Flavored Markdown (GLFM), plus behavior verified against the upstream `gitlab-ci-local` project. In Claude Code only, it includes an explicit fallback command for project access-token setup; the companion is portable Python, but the installed command launcher relies on Claude Code's `${CLAUDE_PLUGIN_ROOT}` substitution.

The plugin ships curated references and directs uncovered topics to official GitLab documentation. It does not synchronize documentation or write fetched content into the installed plugin.

## Installation

Add the marketplace and install the plugin in Claude Code:

```text
/plugin marketplace add Jamie-BitFlight/claude_skills
/plugin install gitlab-skill@jamie-bitflight-skills
```

## Supported Topics

- Apply documented `.gitlab-ci.yml` include, dependency, matrix, expression, and CI Lint semantics.
- Create, test, publish, version, and consume CI/CD components with component or pipeline inputs.
- Author experimental GitLab Functions with current syntax and documented loading or OCI publishing methods.
- Use documented GLFM syntax and rendering constraints.
- Run pipelines locally with shell or Docker execution using verified `gitlab-ci-local` behavior.
- Use GitLab CI Lint for syntax and logic checks or pipeline simulation.
- In Claude Code only, set up a project access token as a protected CI/CD variable when `CI_JOB_TOKEN` cannot perform the required operation.

## Source-Backed Examples

Consume a component with `include:component`. Component references use `<fully-qualified-domain-name>/<project-path>/<component-name>@<specific-version>`.

Define typed inputs under `spec:inputs`, separate the header from jobs with `---`, and interpolate values with `$[[ inputs.<input-id> ]]`. Inputs validate at pipeline creation time.

Test the current component from a root `.gitlab-ci.yml` by referencing `$CI_SERVER_FQDN/$CI_PROJECT_PATH/<component>@$CI_COMMIT_SHA`. Catalog publication requires a Catalog project and a semantic-version tag pipeline whose successful `release` job publishes the version.

When migrating from the former CI/CD Steps name, use `func:`, `func.yml`, `${{ func_dir }}`, and `${{ vars.<variable_name> }}`. Existing shell scripts can run through a `script` step in a `run` list during incremental migration.

Use CI Lint to check configuration syntax and logic. Its pipeline simulation runs as a Git `push` event on the default branch.

SOURCE: <https://docs.gitlab.com/ci/components/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/inputs/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/yaml/lint/> (accessed 2026-09-21)
