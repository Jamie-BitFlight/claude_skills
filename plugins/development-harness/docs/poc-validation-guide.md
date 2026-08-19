# PoC Validation Guide — Generic Stage Agent Dispatch

This guide walks through the end-to-end validation of the development harness generic stage
agent dispatch. Follow each step in sequence to verify that manifest discovery, resolution, and
dispatch input assembly work correctly for a real project.

**Worked example throughout:** Python 3 manifest, planning-context-integration stage (S3).

---

## Prerequisites

- `uv` installed and available on `PATH` (version 0.10.0 or newer — run `uv self update` to
  confirm)
- The `claude_skills` repository checked out locally
- Working directory: the repository root (`/path/to/claude_skills`)
- The python3 manifest lives at:
  `plugins/python3-development/manifests/python3/language-manifest.yaml`

The scripts in `plugins/development-harness/scripts/` depend on each other as modules. All
commands below must be run from the `plugins/development-harness/scripts/` directory so that
relative imports resolve correctly.

```bash
cd plugins/development-harness/scripts
```

---

## Step 1: Discover the Manifest

The `manifest_resolver.py show` subcommand loads and displays a single manifest file as JSON
without performing discovery or extends-chain resolution. Use this to confirm the manifest
parses correctly before running the full resolution pipeline.

```bash
uv run manifest_resolver.py show \
  ../../python3-development/manifests/python3/language-manifest.yaml
```

**Expected output shape:**

```json
{
  "name": "python3",
  "language": "python",
  "version": "1.0",
  "project_detection": {
    "markers": ["pyproject.toml", "setup.py", "setup.cfg"],
    "source_patterns": ["src/**/*.py", "**/*.py"],
    "test_patterns": ["tests/**/*.py", "test_*.py", "*_test.py"]
  },
  "stage_skills": {
    "discovery": ["python3-discovery"],
    "design": ["python3-design"],
    "planning-context-integration": ["python3-implementation"],
    "planning-task-decomposition": ["python3-planning-task-decomposition"],
    "implementation": ["python3-implementation"],
    "testing-forensic-review": ["python3-testing-forensic-review"],
    "testing-final-verification": ["python3-testing"]
  },
  "quality_gates": {
    "format": "uv run ruff format {files}",
    "lint": "uv run ruff check {files}",
    "typecheck": "uv run mypy {files}",
    "test": "uv run pytest tests/ --tb=short",
    "standards": "/python3-development:modernpython"
  },
  "extends": null
}
```

**What to verify:**

- Exit code is 0
- `name` is `"python3"`
- `stage_skills` contains the stage keys listed above — note that the planning stage key in
  the manifest is `planning-context-integration`, not `planning`
- `quality_gates` includes the gate types: `format`, `lint`, `typecheck`, `test`,
  `standards`

---

## Step 2: Resolve the Manifest for a Project

The `manifest_resolver.py resolve` subcommand runs the full pipeline: detect project markers,
discover all matching manifests across priority levels, score by dependency specificity, select
the best candidate, and resolve any `extends` chain.

Use the repository root as the project root. The `--plugin-dir` flag points to any plugin
directory that contains a `manifests/` subdirectory.

```bash
uv run manifest_resolver.py resolve \
  ../../.. \
  --plugin-dir ../../python3-development
```

The first argument (`../../..`) is the path to the project root (three levels up from
`scripts/`). The `--plugin-dir` flag can be repeated for additional plugins.

**Expected outcome:**

The command prints the fully resolved manifest JSON to stdout, identical in shape to the `show`
output above. The resolver selects `python3` because the repository root contains
`pyproject.toml`, which matches the manifest's `project_detection.markers`.

**What to verify:**

- Exit code is 0; a non-zero exit with "No matching manifest found" means no marker file was
  detected in the project root — see Troubleshooting
- `name` in the output is `"python3"` (not another language manifest)
- `stage_skills.planning-context-integration` is `["python3-implementation"]`

---

## Step 3: Build the Dispatch Inputs

`dispatch_helper.py` is a library module, not a CLI. Call `build_dispatch_prompt()` directly
via `uv run python` with an inline script. The function assembles the five inputs the generic
stage agent receives.

The five inputs are:

1. **Stage workflow skill** — the dh skill that owns this stage's process steps
2. **Cross-cutting stage skill** — optional dh skill applying SDLC-level guidance
3. **Domain skills** — from `manifest.stage_skills[stage]`
4. **Task/artifact file path** — the file the agent reads for task context
5. **Quality gate commands** — from `manifest.quality_gates`

Run the following from the `plugins/development-harness/scripts/` directory:

```bash
uv run python - <<'EOF'
from pathlib import Path
from manifest_schema import load_manifest
from dispatch_helper import build_dispatch_prompt

manifest = load_manifest(
    Path("../../python3-development/manifests/python3/language-manifest.yaml")
)

prompt = build_dispatch_prompt(
    stage="planning-context-integration",
    manifest=manifest,
    task_file=".planning/harness/plan-my-feature.md",
    stage_workflow_skill="dh:context-integration",
    cross_cutting_skill="dh:planning",
    output_artifact_path=Path(".planning/harness/context-my-feature.md"),
)
print(prompt)
EOF
```

**Expected output:**

```text
# Stage Dispatch: planning-context-integration
**Language:** python | **Stack:** base | **Manifest:** python3

## Input 1: Stage Workflow
Load the stage workflow skill: `Skill(skill="dh:context-integration")`
Follow the workflow mermaid from this skill step by step.

## Input 2: Cross-Cutting Stage Skill
Load: `Skill(skill="dh:planning")`
This provides SDLC-stage-level guidance applicable across all languages.

## Input 3: Domain Skills
- Load: `Skill(skill="python3-implementation")`

## Input 4: Task/Artifact File
Read this file for your task context: `.planning/harness/plan-my-feature.md`

## Input 5: Quality Gates
Run ALL of these before declaring completion:
- Format: `uv run ruff format {files}`
- Lint: `uv run ruff check {files}`
- Typecheck: `uv run mypy {files}`
- Test: `uv run pytest tests/ --tb=short`
- Standards: Load skill `/python3-development:modernpython`

**Note on `{files}` in quality gate commands**: Commands containing `{files}`
use Python `str.format()` syntax. Substitute `{files}` with the actual
space-separated file paths you are checking before running the command.

## Output Artifact
Write your output artifact to: `.planning/harness/context-my-feature.md`
```

**What to verify:**

- Input 3 lists `python3-implementation` — the domain skill mapped to
  `planning-context-integration` in the manifest
- Input 5 lists all five quality gates
- The output artifact path matches what you passed as `output_artifact_path`

---

## Expected Output

The planning stage (S2/S3 in the SAM pipeline) produces a **PLAN artifact** or **CONTEXT
artifact** written to `.planning/harness/` in the project root.

Per [artifact-conventions.md](../skills/development-harness/references/artifact-conventions.md):

- **S2 Planning artifact** — `plan-{feature-slug}.md`
  - Token: `ARTIFACT:PLAN({feature-slug})`
  - Contains: RT-ICA gap analysis, task graph with dependencies, task skeletons with
    acceptance criteria, quality gate schedule

- **S3 Context Integration artifact** — `context-{feature-slug}.md`
  - Token: `ARTIFACT:CONTEXT({feature-slug})`
  - Amends S2 — contains validation results, codebase discrepancies, plan amendments,
    confirmed integration points

**Example paths for a feature slug `my-feature`:**

```text
.planning/harness/plan-my-feature.md
.planning/harness/context-my-feature.md
```

Each artifact includes a YAML frontmatter header linking it to predecessor and successor
artifacts:

```yaml
---
artifact: ARTIFACT:CONTEXT(my-feature)
predecessor: ARTIFACT:PLAN(my-feature)
successor: ARTIFACT:TASK(001)
feature: my-feature
stage: S3
created: 2026-03-18
---
```

---

## Troubleshooting

### "No matching manifest found" from `manifest_resolver.py resolve`

The resolver detected no marker files from the manifest's `project_detection.markers` list in
the project root.

**Check:** Confirm the project root argument is correct and that `pyproject.toml` exists there:

```bash
ls ../../..   # from scripts/ — should show pyproject.toml
```

If `pyproject.toml` is absent, the python3 manifest will not match. Either use a project root
that contains a Python marker file, or pass a different `--plugin-dir` with a manifest whose
markers match.

### Stage name not found in `stage_skills`

`build_dispatch_prompt()` returns an empty domain skills list when the `stage` argument does
not match any key in `manifest.stage_skills`. No error is raised — Input 3 will read "No
domain skills for this stage."

**Check:** The manifest uses exact hyphenated stage names. The planning stage identifier is
`planning-context-integration` — not `planning`, not `s3`, not `context-integration`.

Print the available keys to confirm:

```bash
uv run python - <<'EOF'
from pathlib import Path
from manifest_schema import load_manifest

manifest = load_manifest(
    Path("../../python3-development/manifests/python3/language-manifest.yaml")
)
print("Available stage_skills keys:")
for key in manifest.stage_skills:
    print(f"  {key}")
EOF
```

### Domain skill missing from `stage_skills`

If the domain skill listed in `stage_skills` does not exist as a loadable skill in the harness,
the dispatched agent will fail when it calls `Skill(skill="...")`.

**Check:** Confirm the skill name exists under `plugins/`:

```bash
# From repo root
ls plugins/python3-development/skills/
```

### Manifest fails to parse

If `manifest_resolver.py show` exits with a YAML error, the manifest file is malformed.

**Validate the YAML directly:**

```bash
uv run python - <<'EOF'
from ruamel.yaml import YAML
yaml = YAML()
with open("../../python3-development/manifests/python3/language-manifest.yaml") as f:
    data = yaml.load(f)
print("YAML is valid. Top-level keys:", list(data.keys()))
EOF
```

A `YAMLError` traceback identifies the line and column of the syntax problem.

### `ModuleNotFoundError` when running scripts

All scripts import each other as sibling modules. If you run `uv run manifest_resolver.py` from
the repo root instead of from `plugins/development-harness/scripts/`, Python cannot find
`manifest_discovery`, `manifest_schema`, or `manifest_merge`.

**Fix:** Always `cd plugins/development-harness/scripts` before running any script in this
guide.
