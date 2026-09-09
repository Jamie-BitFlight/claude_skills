# Stack Profile Schema

Stack profiles are optional extensions to language manifests. They declare architecture patterns, toolchain presets, and reference examples.

---

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `stack` | string | Unique stack identifier (e.g., `python-fastapi`, `python-cli`) |
| `display_name` | string | Human-readable name (e.g., "Python + FastAPI") |
| `language` | string | Base language (e.g., `python`, `typescript`) |

---

## Optional Fields

| Field | Type | Description |
|-------|------|--------------|
| `extends` | string | Parent stack profile (e.g., `daily_releases` extends `changelog_generation`) |
| `architecture_patterns` | string[] | Paths or references to architecture docs |
| `toolchain_presets` | object | pyproject.toml snippets, package.json configs |
| `reference_examples` | string[] | Paths to example projects or task templates |
| `research_refs` | string[] | research/ entries (e.g., `api-frameworks/fastapi.md`) |

---

## STATUS Block (Output Contract)

Output contract for stack workflows:

- **STATUS**: DONE | BLOCKED | FAILED
- **SUMMARY**: Brief outcome
- **ARTIFACTS**: List of produced artifacts
- **VALIDATION**: What was verified
- **NOTES**: Optional context

---

## Workflow Definition Schema

For workflow definitions within stack profiles:

| Field | Required | Description |
|-------|----------|-------------|
| `workflow` | Yes | Workflow name |
| `version` | Yes | Semantic version |
| `output_contract` | Yes | STATUS block or custom |
| `canonical_agent` | No | Primary agent for this workflow |
| `canonical_skill` | No | Primary skill for this workflow |
| `canonical_path` | No | Path to workflow definition |
| `validation_gates` | No | HARD_STOP, SOFT_STOP |

---

## Example Stack Profiles

- `python-fastapi` — Python web API
- `python-tornado` — Python async web
- `python-cli` — Python CLI tool
- `typescript-react` — TypeScript frontend
- `documentation-authoring` — Portable documentation workflows (rwr)
- `changelog_generation` — Changelog workflows
- `daily_releases` — Extends changelog_generation
