# STATUS Block Contract

Canonical definition of the STATUS block format used by all rewrite-room agents and workflows.
Every response from a rewrite-room agent MUST include a STATUS block in this format.

## Base Format

```text
STATUS: DONE|BLOCKED|FAILED
SUMMARY: [1-2 sentences, factual, no speculation]
ARTIFACTS: [list of files created/modified with paths, or "none"]
VALIDATION: [validators run and PASS/FAIL results]
NOTES: [only if needed — omit section if nothing to add]
```

## Field Rules

| Field | Allowed Values | Behavior |
|-------|---------------|----------|
| `STATUS` | `DONE`, `BLOCKED`, `FAILED` | Required. One value only. |
| `SUMMARY` | 1-2 sentences | Factual. No speculation. No hedging. |
| `ARTIFACTS` | File paths (relative) or `"none"` | List all files created or modified. |
| `VALIDATION` | Validators run with PASS/FAIL results | See workflow-specific subfields below. |
| `NOTES` | Any text | Optional. Omit the section entirely if nothing to add. |

**For BLOCKED**: add `NEEDED:` field listing exactly what is missing before the agent can proceed.

```text
STATUS: BLOCKED
SUMMARY: [what was attempted and where it stopped]
ARTIFACTS: none
VALIDATION: not run
NEEDED:
  - [specific missing input 1]
  - [specific missing input 2]
```

**For FAILED**: SUMMARY describes what failed and why. VALIDATION shows which checks failed.

## Workflow-Specific VALIDATION Subfields

Each workflow extends the base VALIDATION field with workflow-specific validators.
Add these subfields inline in the VALIDATION block when operating within that workflow.

### audit workflow

```text
VALIDATION:
  - citation-check: PASS|FAIL  (drift-audit only — all findings have file:line evidence)
  - link-check: PASS|FAIL      (if markdown files were modified)
```

### optimize workflow

```text
VALIDATION:
  - frontmatter-check: PASS|FAIL  (normalize_frontmatter.py exit code)
  - skilllint-check: PASS|FAIL    (uvx skilllint@latest exit code)
```

### author workflow

```text
VALIDATION:
  - glfm-check: PASS|FAIL        (validate_glfm.py exit code)
  - citation-check: PASS|FAIL    (all claims have cited sources)
```

### cite workflow

```text
VALIDATION:
  - citation-check: PASS|FAIL    (all claims have cited sources)
  - source-attribution: PASS|FAIL (all sources named and linked)
```

### doc-converter workflow

```text
VALIDATION:
  - skilllint-check: PASS|FAIL    (uvx skilllint@latest exit code on output skill)
  - frontmatter-check: PASS|FAIL  (required fields present in SKILL.md)
```
