# Verdict Schema — Multi-Perspective Review

Reference file for the structured verdict block schema, summary line format, SKIP detection
rule, and gate logic used by the `dh:multi-perspective-review` skill and all four reviewer
agents.

**Authoritative source**: All four reviewer agents (`reviewer-security.md`,
`reviewer-performance.md`, `reviewer-quality.md`, `reviewer-accessibility.md`) reference this
file for schema version, summary tokens, and SKIP patterns. Do NOT duplicate or embed these
definitions in agent instruction bodies.

**#1430 compatibility**: The `gate(verdicts) -> GateResult` interface defined in §2.4 is
stable. Issue #1430 replaces the gate function body only; callers and schema version routing
remain unchanged.

---

## §2.1 Structured Verdict Block

Each reviewer agent emits exactly one verdict block in its SendMessage to the team lead. The
block is JSON-serializable and version-stamped for #1430 compatibility.

```json
{
  "schema_version": "1.0",
  "perspective": "security | performance | quality | accessibility",
  "verdict": "APPROVE | REJECT | SKIP",
  "findings": [
    {
      "severity": "BLOCKER | MINOR | INFO",
      "file": "relative/path/to/file.py",
      "line": 42,
      "description": "Human-readable description of the finding",
      "rule": "optional-rule-identifier"
    }
  ],
  "skip_reason": "optional — present only when verdict == SKIP; explains why SKIP applies"
}
```

**Field constraints:**

- `schema_version`: always `"1.0"` until #1430 defines a migration path
- `perspective`: one of the four literal values listed above; lowercase
- `verdict`: exactly one of `APPROVE`, `REJECT`, `SKIP`
- `findings`: array; empty array `[]` is valid (APPROVE with no findings)
- `findings[].severity`: `BLOCKER` means the verdict is `REJECT`; `MINOR` and `INFO` do not block
- `findings[].line`: integer or `null` if not line-specific
- `skip_reason`: required when `verdict == SKIP`; omitted otherwise

---

## §2.2 Summary Line Format

The orchestrating skill (`multi-perspective-review/SKILL.md`) prints one summary line per
perspective in canonical format. AC6 defines the expected shape:

```text
Security: APPROVE (0 findings) | Performance: REJECT (1 finding) | Quality: APPROVE (2 minor) | Accessibility: SKIP (no UI changes)
```

Mapping from verdict struct to summary token:

| Verdict | Findings | Summary token |
|---------|----------|---------------|
| `APPROVE` | 0 findings | `APPROVE (0 findings)` |
| `APPROVE` | N findings | `APPROVE ({N} minor)` where N counts MINOR+INFO severity |
| `REJECT` | 1 BLOCKER finding | `REJECT (1 finding)` |
| `REJECT` | N BLOCKER findings | `REJECT ({N} findings)` |
| `SKIP` | — | `SKIP ({skip_reason})` |

**Note:** The singular `finding` vs plural `findings` applies to REJECT tokens only. APPROVE
always uses `findings` (plural).

---

## §2.3 SKIP Detection Rule (Accessibility Perspective)

SKIP applies to the accessibility perspective when **none** of the changed files matches the UI
file pattern list below. The accessibility reviewer checks this list first; if no match is
found, it emits `verdict: SKIP` immediately without scanning file content.

**This list is the authoritative source.** Do not embed or duplicate it in agent instruction
bodies. The `reviewer-accessibility.md` agent references this file for the pattern list.

**UI file pattern list (v1.0):**

```text
*.html
*.css
*.scss
*.sass
*.less
*.jsx
*.tsx
*.vue
*.svelte
*.astro
**/components/**
**/templates/**
**/views/**
**/pages/**
**/ui/**
**/frontend/**
```

**Pattern matching rule:** A file matches if its path matches any glob pattern above using
standard Unix glob semantics, case-insensitive. Matching applies to the relative file path as
returned by `git diff --name-only`.

**Extensibility:** Future perspectives may define additional SKIP detection rules using the
same pattern-list structure in this file.

---

## §2.4 Gate Logic (Stub Consolidation — Pre-#1430)

```text
PASS conditions:
  - All verdicts are APPROVE or SKIP, with at least one APPROVE

  Edge case — all SKIP:
    Treated as PASS (no applicable changes reviewed; no blocker found).
    Summary output MUST include the warning line:
      NOTE: No perspectives reviewed — all skipped

FAIL conditions:
  - Any verdict is REJECT → FAIL immediately; list all blocking findings
  - Missing verdict (an agent did not send a verdict) → FAIL with message:
      "Perspective {X} did not return a verdict"
```

The gate function signature (stable interface for #1430 swap):

```text
gate(verdicts: list[VerdictBlock]) -> GateResult

GateResult:
  passed: bool
  summary_line: str            — canonical format per §2.2
  blocking_findings: list[Finding]   — empty when passed
```

**Pre-#1430 stub logic:**

```text
verdicts = [parse_verdict(msg) for msg in collected_messages]
missing = [p for p in PERSPECTIVES if no verdict received for p]
if missing:
    FAIL — "Perspective {X} did not return a verdict"
rejecting = [v for v in verdicts if v.verdict == "REJECT"]
if rejecting:
    FAIL — list each blocking finding
all_skip = all(v.verdict == "SKIP" for v in verdicts)
if all_skip:
    PASS — emit warning: "NOTE: No perspectives reviewed — all skipped"
PASS
```

**#1430 compatibility contract:**

- The `schema_version: "1.0"` field allows #1430 to detect schema version and apply
  confidence/deduplication logic
- The `findings` array structure is stable; #1430 may add `confidence` and `dedup_key` fields
  per finding without breaking v1 consumers
- Issue #1430 replaces the gate function body only; callers (the skill body) do not change
- The stub consolidation above implements the stable interface; #1430 swaps only the internals
