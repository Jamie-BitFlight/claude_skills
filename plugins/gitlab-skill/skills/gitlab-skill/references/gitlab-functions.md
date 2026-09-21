# GitLab Functions

GitLab Functions are an Experiment in active development, subject to breaking changes, available for testing, and not ready for production use.

SOURCE: <https://docs.gitlab.com/ci/functions/> (accessed 2026-09-21)

## Function Package

A function is a directory containing `func.yml` and any implementation files. `func.yml` contains an interface document and an implementation document separated by `---`.

```text
my-function/
|-- func.yml
`-- my-script.sh
```

```yaml
spec:
  inputs:
    message:
      type: string
  outputs:
    result:
      type: string
---
exec:
  command: ["${{ func_dir }}/my-script.sh", "${{ inputs.message }}"]
```

An `exec` definition runs one command without a shell; a nonzero exit code fails the function. A `run` definition invokes child functions sequentially; a failed child prevents later children from running. `work_dir` overrides the default `CI_PROJECT_DIR` only for `exec` definitions.

SOURCE: <https://docs.gitlab.com/ci/functions/create/#create-a-function> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#function-definition> (accessed 2026-09-21)

## Job Invocation

Use job-level `run` instead of `script`. Steps execute in declaration order. Each step has a `name`, either `func` or `script`, and optional `inputs` and `env`. Step names contain only alphanumeric characters and underscores and cannot begin with a number. A Functions job cannot also use job-level `before_script`, `after_script`, or `script`.

```yaml
my-job:
  variables:
    FRIEND: "Sally"
  run:
    - name: say_hi
      func: registry.gitlab.com/gitlab-org/ci-cd/runner-tools/gitlab-functions-examples/echo:1
      inputs:
        message: "Hi ${{ vars.FRIEND }}!"
```

A `script` step runs through `bash`, falling back to `sh` when Bash is unavailable, and supports incremental conversion of existing shell scripts.

```yaml
my-job:
  run:
    - name: say_hi
      script: echo 'Hi ${{ vars.FRIEND }}!'
```

SOURCE: <https://docs.gitlab.com/ci/functions/#use-functions-in-cicd-jobs> (accessed 2026-09-21)

## Inputs and Outputs

Every input and output requires a `type`. Supported types are `array`, `boolean`, `number`, `string`, and `struct`. A value with a `default` is optional; otherwise it is required. Names contain only alphanumeric characters and underscores and cannot begin with a number.

```yaml
spec:
  inputs:
    message:
      type: string
    count:
      type: number
      default: 1
  outputs:
    artifact_path:
      type: string
---
exec:
  command: ["${{ func_dir }}/build.sh", "${{ inputs.message }}", "${{ output_file }}"]
```

Write outputs as newline-delimited JSON objects to `${{ output_file }}`. Each object has non-null `name` and `value` fields.

```shell
echo '{"name":"artifact_path","value":"/dist/app.tar.gz"}' >> "${{ output_file }}"
```

Read a completed step's output as `${{ steps.<step_name>.outputs.<output_name> }}`.

SOURCE: <https://docs.gitlab.com/ci/functions/create/#inputs> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#outputs> (accessed 2026-09-21)

## Composite Functions

A `run` definition composes functions. It can map selected child outputs explicitly:

```yaml
spec:
  inputs:
    environment:
      type: string
  outputs:
    url:
      type: string
---
run:
  - name: build
    func: ./build
  - name: deploy
    func: ./deploy
    inputs:
      env: ${{ inputs.environment }}
      artifact: ${{ steps.build.outputs.artifact_path }}
outputs:
  url: ${{ steps.deploy.outputs.url }}
```

To expose a child's complete output set, declare `spec.outputs: delegate` and select the child with top-level `delegate: <step_name>` in the definition:

```yaml
spec:
  outputs: delegate
---
run:
  - name: deploy
    func: ./deploy
delegate: deploy
```

SOURCE: <https://docs.gitlab.com/ci/functions/create/#composite-functions> (accessed 2026-09-21)

## Expressions and Environment

Functions use runtime Moa expressions in `${{ }}`. This differs from pipeline-creation `$[[ ]]` expressions used for CI/CD configuration inputs. Function contexts include `env`, `vars`, `inputs`, `steps`, `func_dir`, `work_dir`, `output_file`, and `export_file`.

`env` applies to an invocation and its child functions, but not to later peer steps. Export a value for later steps by writing newline-delimited JSON to `${{ export_file }}`. Access CI/CD job variables through `${{ vars.<name> }}`, not `env`.

SOURCE: <https://docs.gitlab.com/ci/functions/moa/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#environment-variables> (accessed 2026-09-21)

## Loading and Publishing

Load functions from an OCI repository or the file system. OCI is the recommended distribution method. Relative file references resolve from the calling function directory, or from `CI_PROJECT_DIR` when called directly by a job. Git repository loading is deprecated and planned for removal.

```yaml
- name: echo
  func: registry.gitlab.com/gitlab-org/ci-cd/runner-tools/gitlab-functions-examples/echo:1
  inputs:
    message: "Hi from GitLab Functions"
```

The built-in `builtin://function/oci/build` creates `function-image.tar`; `builtin://function/oci/publish` publishes it.

```yaml
build_function:
  artifacts:
    paths: [function-image.tar]
  run:
    - name: build
      func: builtin://function/oci/build
      inputs:
        version: "1.2.3"
        common:
          files:
            func.yml: func.yml
            my-script.sh: my-script.sh

publish_function:
  needs: [build_function]
  run:
    - name: publish
      func: builtin://function/oci/publish
      inputs:
        archive: function-image.tar
        to_repository: registry.example.com/my-org/my-function
```

For a private registry, authenticate before publishing; the documented Docker Auth function exports `DOCKER_AUTH_CONFIG` for the publish step. Stable releases update applicable semantic-version and `latest` tags; prereleases create only the exact prerelease tag.

SOURCE: <https://docs.gitlab.com/ci/functions/#load-functions> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#build-and-publish-functions> (accessed 2026-09-21)

## Invocation and CI Lint

The Functions authoring guide demonstrates invoking a file-system function from a job-level `run` list. CI Lint validates `.gitlab-ci.yml` syntax and pipeline creation.

Functions require step runner support. Some executors require manual step runner installation.

SOURCE: <https://docs.gitlab.com/ci/yaml/lint/> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/ci/functions/create/#complete-example> (accessed 2026-09-21)
SOURCE: <https://docs.gitlab.com/runner/install/step-runner/> (accessed 2026-09-21)

## Steps-to-Functions Migration Mapping

Use obsolete names only to interpret or migrate existing configuration.

| Obsolete | Current |
|---|---|
| CI/CD Steps | GitLab Functions |
| `step:` | `func:` |
| `step.yml` | `func.yml` |
| `${{ step_dir }}` | `${{ func_dir }}` |
| `${{ job.<variable_name> }}` | `${{ vars.<variable_name> }}` |

The obsolete syntax is deprecated. Current authoring syntax uses only the names in the Current column.

SOURCE: <https://docs.gitlab.com/ci/functions/#migrate-from-cicd-steps> (accessed 2026-09-21)
