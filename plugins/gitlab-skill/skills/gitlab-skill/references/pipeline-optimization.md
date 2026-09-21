# GitLab CI/CD Configuration Semantics

## Include Merge Order

GitLab reads included files in their defined order. Nested includes merge first. When included parameters overlap, the last included file takes precedence. After all includes merge, the main configuration merges with the included configuration.

SOURCE: <https://docs.gitlab.com/ci/yaml/includes/> (accessed 2026-09-21)

## Reuse and Dependencies

Prefer `extends` for reusable configuration; GitLab documents it as more flexible and readable than YAML anchors. Use `needs` to execute jobs out of stage order.

SOURCE: <https://docs.gitlab.com/ci/yaml/yaml_optimization/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/yaml/> (accessed 2026-09-21)

## Parallel Matrix Jobs

Use `parallel:matrix` to create multiple similar jobs with different variable values.

SOURCE: <https://docs.gitlab.com/ci/yaml/yaml_optimization/> (accessed 2026-09-21)

## Configuration Expressions

Configuration expressions use `$[[ ]]` and resolve at pipeline creation time. They cannot access runtime job state or perform dynamic logic.

SOURCE: <https://docs.gitlab.com/ci/yaml/expressions/> (accessed 2026-09-21)

## CI Lint

CI Lint checks configuration syntax and logic. Its pipeline simulation runs as a Git `push` event on the default branch.

SOURCE: <https://docs.gitlab.com/ci/yaml/lint/> (accessed 2026-09-21)
