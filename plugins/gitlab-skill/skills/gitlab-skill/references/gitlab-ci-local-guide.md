# Verified GitLab CI Local Behavior

`gitlab-ci-local` runs GitLab pipelines locally with shell or Docker executors.

By default, it validates input types, options, and regular expressions. Use `--skip-input-validation` to render a pipeline without those checks when an outdated component declares an incompatible input type. Required inputs and interpolation keys remain validated.

External includes are fetched once and cached. Use `--fetch-includes` to fetch their latest content.

SOURCE: <https://github.com/firecow/gitlab-ci-local> (upstream README revision reviewed 2026-09-21)

GitLab CI Lint checks CI/CD configuration syntax and logic and can simulate pipeline creation to find more complicated configuration problems.

SOURCE: <https://docs.gitlab.com/ci/yaml/lint/> (accessed 2026-09-21)
