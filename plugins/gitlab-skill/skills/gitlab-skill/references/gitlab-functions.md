# GitLab Functions Core Authoring and Composition

GitLab Functions are an Experiment in active development, subject to breaking changes, available
for testing, and not ready for production use.

## Package and Definition

A function directory contains `func.yml` and implementation files. `func.yml` has an interface and
implementation separated by `---`:

```yaml
spec:
  inputs:
    message: {type: string}
  outputs:
    result: {type: string}
---
exec:
  command: ["${{ func_dir }}/my-script.sh", "${{ inputs.message }}"]
```

`exec` runs one command without a shell; nonzero fails. `run` invokes child functions sequentially;
a failed child stops later children. `work_dir` applies only to `exec`.

SOURCE: <https://docs.gitlab.com/ci/functions/create/#create-a-function> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#function-definition> (accessed 2026-09-21)

## Job Invocation and Interface

Job-level `run` contains ordered named entries with `func` or `script`, plus optional `inputs` and
`env`. A Functions job does not also use job-level `before_script`, `after_script`, or `script`.

```yaml
my-job:
  run:
    - name: say_hi
      func: ./my-function
      inputs:
        message: "Hi ${{ vars.FRIEND }}!"
```

Every input/output declares `array`, `boolean`, `number`, `string`, or `struct`; inputs without a
default are required. Write outputs as newline-delimited JSON `{name,value}` objects to
`${{ output_file }}` and read them as `${{ steps.<name>.outputs.<output> }}`.

SOURCE: <https://docs.gitlab.com/ci/functions/#use-functions-in-cicd-jobs> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#inputs> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#outputs> (accessed 2026-09-21)

## Composition and Environment

A `run` definition composes functions and maps child outputs. `spec.outputs: delegate` plus
top-level `delegate: <name>` exposes one child's complete output set.

Functions use runtime Moa `${{ }}` expressions, distinct from pipeline-creation `$[[ ]]`
expressions. Contexts include `env`, `vars`, `inputs`, `steps`, `func_dir`, `work_dir`, `output_file`,
and `export_file`. `env` reaches an invocation and children; export newline-delimited JSON for later
peer entries. Access CI/CD variables through `vars`.

CI Lint validates `.gitlab-ci.yml` syntax and pipeline creation. Runtime execution requires step
runner support; some executors require manual installation.

SOURCE: <https://docs.gitlab.com/ci/functions/create/#composite-functions> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/moa/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#environment-variables> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/yaml/lint/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/runner/install/step-runner/> (accessed 2026-09-21)
