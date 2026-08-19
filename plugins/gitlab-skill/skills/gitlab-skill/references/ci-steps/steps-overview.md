# GitLab CI/CD Steps: Overview and Specifications

Comprehensive technical reference for GitLab CI/CD Steps feature syntax, capabilities, and step definition structure.

Source: <https://docs.gitlab.com/ci/steps/>

## Feature Definition

Steps are reusable units of work at the job level that replace traditional `script` keyword. They enable:

- Reusability across jobs and projects
- Composability through input/output chaining
- Independence through explicit contracts
- Testability of discrete units
- Retrieval of supporting files

## Job Execution Model

Jobs using `run` keyword execute steps sequentially. Steps run in Docker containers created by GitLab (container image: <https://gitlab.com/gitlab-org/step-runner/-/blob/main/Dockerfile>).

Steps access:

- CI/CD job variables (restricted: CI*, DOCKER*, GITLAB\_ prefixed only)
- Environment variables
- File system (project directory per CI_PROJECT_DIR)
- Networking

Current limitations:

- Linux only (Windows/macOS in development)
- Run in dedicated containers (job environment execution planned)
- Cannot combine `run` with `script`, `before_script`, `after_script`

## Step Specification Structure

Step `step.yml` file contains two YAML documents separated by `---`:

### Document 1: Specification

Defines input/output contracts and types. Syntax:

```yaml
spec:
  inputs:
    input_name:
      type: [string|number|boolean|array|struct]
      default: value # optional, makes input optional
  outputs:
    output_name:
      type: [string|number|boolean|array|struct]
      default: value # optional, returned if step doesn't provide
```

Input/output names: alphanumeric and underscores only, must not start with number.

Special case - delegated outputs: Return all sub-step outputs:

```yaml
spec:
  outputs: delegate
```

No inputs or outputs: Use empty spec:

```yaml
spec:
```

### Document 2: Definition

Specifies step implementation. Patterns:

#### Pattern 1: Environment Variables

```yaml
env:
  VARIABLE_NAME: value
  ANOTHER_VAR: "${{inputs.some_input}}"
```

Variables available to executable command or all sub-steps in sequence.

#### Pattern 2: Command Execution

```yaml
exec:
  work_dir: ${{step_dir}}
  command:
    - bash
    - -c
    - "command here"
```

Fields:

- `command` (required): Array of command tokens
- `work_dir` (optional): Working directory path, defaults to step directory

Environment variables set in `env` keyword available to process.

#### Pattern 3: Step Sequencing

```yaml
run:
  - name: step_one
    step: ./step-one
    inputs:
      param1: value
    env:
      VAR: value
  - name: step_two
    step: ./step-two
    inputs:
      data: "${{steps.step_one.outputs.result}}"
```

Sub-steps run sequentially. Each step requires:

- `name` (alphanumeric, underscore, not starting with number)
- One of: `step`, `script`, `action`

Optional: `inputs`, `env`, `env` at sequence level applies to all steps.

## Step Locations

### File System

Load from relative path:

```yaml
step: ./path/to/step
```

Path format: forward slashes always, even on Windows. Folder must contain `step.yml`.

### Git Repository

Load from Git source with revision specifier:

```yaml
step: gitlab.com/components/echo@v1.0.0
step: gitlab.com/components/echo@main
step: gitlab.com/components/echo@commit_sha
```

Loads `step.yml` from `steps` folder by default.

### Expanded Git Syntax

Specify custom directory and filename:

```yaml
step:
  git:
    url: gitlab.com/components/echo
    rev: main
    dir: my-steps/sub-directory # optional, defaults to repo root
    file: my-step.yml # optional, defaults to step.yml
```

## Expressions

Mini-language for dynamic values. Enclosed in `${{ }}`. Evaluated at step execution (before step runs), distinguished from component expressions `$[[ ]]` (evaluated at pipeline creation).

Valid in:

- Input values
- Environment variable values
- Step location URL
- Executable command
- Executable work directory
- Step sequence outputs
- `script` steps
- `action` steps

### Expression Variables

| Variable       | Syntax                             | Description                                                          | Access Rules                         |
| -------------- | ---------------------------------- | -------------------------------------------------------------------- | ------------------------------------ |
| Environment    | `${{env.VAR}}`                     | Environment variables set in execution environment or previous steps | All                                  |
| Inputs         | `${{inputs.name}}`                 | Step inputs                                                          | Within step only                     |
| Job            | `${{job.VAR}}`                     | CI/CD variables                                                      | CI*, DOCKER*, GITLAB\_ prefixed only |
| Prior outputs  | `${{steps.step_name.outputs.var}}` | Prior step outputs                                                   | After that step executes             |
| Step directory | `${{step_dir}}`                    | Downloaded step location                                             | Executable steps                     |
| Work directory | `${{work_dir}}`                    | Current working directory                                            | Executable steps                     |
| Output file    | `${{output_file}}`                 | Path to output file                                                  | Executable steps                     |
| Export file    | `${{export_file}}`                 | Path to environment export file                                      | Executable steps                     |

## Input/Output Handling

### Inputs

Inputs are optional unless no default specified. Passed when using a step:

```yaml
run:
  - name: my_step
    step: ./step
    inputs:
      greeting: "hello world"
      count: 42
```

Input types:

- `string`: Text
- `number`: 64-bit float
- `boolean`: true/false
- `array`: List of untyped items
- `struct`: Structured object with key-value pairs

### Outputs from Executable Steps

Write to `${{output_file}}` in JSON Lines format. Each line: JSON object with `name` (string) and `value` (must match declared output type):

```bash
echo '{"name":"result","value":"value_string"}' >${{output_file}}
echo '{"name":"count","value":42}' >${{output_file}}
echo '{"name":"items","value":["a","b"]}' >${{output_file}}
```

Value types must match step specification:

- `array` → JSON array
- `boolean` → JSON boolean
- `number` → JSON number
- `string` → JSON string
- `struct` → JSON object

### Outputs from Step Sequences

Return from sub-steps using `outputs` keyword:

```yaml
run:
  - name: install_java
    step: ./common/install-java
outputs:
  java_version: "${{steps.install_java.outputs.java_version}}"
```

Or delegate all outputs:

```yaml
run:
  - name: install_java
    step: ./common/install-java
outputs:
  delegate: install_java
```

## Environment Variables

### Setting Variables

Set in step `env` keyword or passed when invoking step:

```yaml
spec:
---
env:
  FIRST_NAME: Sally
  LAST_NAME: Seashells
```

Executable step environment variables available to command. Sequence environment variables available to all sub-steps.

### Exporting Variables

Executable steps export for subsequent steps by writing to `${{export_file}}` in JSON Lines format:

```bash
echo '{"name":"GOPATH","value":"/go"}' >${{export_file}}
```

### Precedence (Highest to Lowest)

1. `step.yml` `env` keyword
2. Passed `env` keyword (when using step)
3. Sequence-level `env` keyword
4. Previously exported variables (step `${{export_file}}`)
5. Runner environment
6. Container environment

## Using Steps in Jobs

Basic job structure:

```yaml
my_job:
  run:
    - name: step_identifier
      step: step_location
      inputs:
        param1: value
      env:
        VAR: value
    - name: another_step
      step: ./another
      inputs:
        data: "${{steps.step_identifier.outputs.result}}"
```

Cannot use `script`, `before_script`, `after_script` when using `run` keyword.

## Step Types in Sequences

### Step Type

Reference external step definition:

```yaml
- name: my_step
  step: gitlab.com/components/echo@v1.0.0
  inputs:
    message: "text"
```

### Script Type

Execute shell command:

```yaml
- name: my_script
  script: echo hello ${{job.GITLAB_USER_LOGIN}}
```

Shell: `bash`, fallback to `sh`. Runs in CI_PROJECT_DIR. Environment variables passed via `env` set in shell.

### Action Type

Execute GitHub Action (requires `dind` service):

```yaml
- name: use_action
  action: mikefarah/yq@master
  inputs:
    cmd: echo ["data"] | yq .[0]
```

Inputs and environment passed directly to action. Action outputs returned as step outputs.

Known limitation: Actions cannot upload artifacts directly; write to filesystem and cache instead, select with `artifacts` and `cache` keywords.

## Combining with CI/CD Components

Components use `$[[ ]]` expressions (pipeline creation time), Steps use `${{ }}` (job execution time). Components provide job-level configuration; steps handle job composition.

Example component using steps internally:

```yaml
spec:
  inputs:
    fmt_packages:
      description: Go packages to format
    go_version:
      default: "1.22"
---
format_code:
  run:
    - name: install_go
      step: ./languages/go/install
      inputs:
        version: $[[ inputs.go_version ]]
    - name: format_code
      step: ./languages/go/go-fmt
      inputs:
        go_binary: ${{ steps.install_go.outputs.go_binary }}
        fmt_packages: $[[ inputs.fmt_packages ]]
```

## Troubleshooting

### HTTPS Certificate Validation Failures

Error: `tls: failed to verify certificate: x509: certificate signed by unknown authority`

Cause: Docker image lacks trusted root certificates.

Resolution options:

1. Install certificates in container before fetching steps:

```yaml
ubuntu_job:
  image: ubuntu:24.04
  run:
    - name: install_certs
      script: apt update && apt install --assume-yes --no-install-recommends ca-certificates
    - name: fetch_step
      step: https://gitlab.com/user/my_steps/hello_world@main
```

2. Bake certificates into job image.

3. For Runner-based resolution: Install certificates in Runner Docker executor configuration.
