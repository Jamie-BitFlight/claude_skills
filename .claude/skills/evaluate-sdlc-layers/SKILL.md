---
name: evaluate-sdlc-layers
description: Evaluate and iterate on the SDLC Layer Separation Architecture implementation. Runs validation checks (cross-references, doc completeness, layer metadata, integration points), produces a findings report, and supports iterative fixes. Use when validating first-pass implementation, before claiming layer work is complete, or when improving layer docs/schema.
argument-hint: '[--dry-run | --fix]'
user-invocable: true
---

# Evaluate SDLC Layers

Systematically evaluate the SDLC Layer Separation Architecture implementation and support iterative improvement. Treats the implementation as first-pass until validated.

## Arguments

- **`--dry-run`** — Run all checks, produce report only. Do not apply fixes.
- **`--fix`** — After evaluation, apply safe fixes for broken references, missing metadata, or obvious gaps. Report what was changed.
- (no args) — Evaluate and produce report; offer to fix or delegate fixes.

---

## Evaluation Checklist

Run each check and record PASS / FAIL / SKIP with evidence.

### 1. Cross-Reference Validation

For each linked path in `.claude/docs/sdlc-layers/` and related docs:

- [ ] `sam-definition.md` — exists at `.claude/skills/work-backlog-item/references/sam-definition.md`
- [ ] `plugins/development-harness/CLAUDE.md` — exists
- [ ] `stateless-agent-methodology/research/arl/PROVENANCE.md` — exists (sibling repo or configured path)
- [ ] Layer 0 docs → `TASK_FILE_FORMAT.md` — exists at `.claude/docs/TASK_FILE_FORMAT.md`
- [ ] Layer 1 → `language-manifest-schema.md`, `role-resolution-protocol.md` — exist in development-harness
- [ ] Layer 2 → `plugins/development-harness/docs/layer-2/` — exists with README, schema, pilot profiles

**Evidence:** List each path checked and result (exists / 404 / wrong content).

---

### 2. Doc Completeness

- [ ] Layer 0: All 9 docs present (README, sam-pipeline, arl-touchpoints, artifact-conventions, rt-ica-gate, verification-protocol, task-file-format, evidence-discipline, orchestrator-discipline)
- [ ] Layer 1: All 6 docs present (README, layer-1-overview, language-manifest-template, linting-discovery-protocol, workflow-pattern-taxonomy, harness-role-mapping)
- [ ] Layer 2: README, layer-2-overview, stack-profile-schema, stack-profile-template; pilot profiles python-fastapi, python-cli
- [ ] ARL: arl-meta-layer.md, arl-human-probing-design.md

**Evidence:** `Glob` or `Read` results for each expected file.

---

### 3. Knowledge-Explorer Layer Filter

- [ ] `uv run research/knowledge-explorer.py list --layer 0` — returns entries with `layer: "0"`
- [ ] `uv run research/knowledge-explorer.py list --layer 1` — returns entries with `layer: "1"`
- [ ] `uv run research/knowledge-explorer.py list --layer 2` — returns entries with `layer: "2"`
- [ ] Entries without layer metadata are excluded when `--layer` is used (expected)

**Evidence:** Paste command output for each.

---

### 4. Research Entry Layer Metadata

- [ ] `evaluation-testing/harness-engineering-openai.md` — has `layer: "0"`
- [ ] `api-frameworks/fastapi.md`, `api-frameworks/tornado.md` — have `layer: "2"`, `language`, `stack`
- [ ] `developer-tools/copier-astral.md` — has `layer: "1"` (or `2` if stack-scaffold)
- [ ] `research/README.md` — has "Layer Mapping" section

**Evidence:** Grep for `layer:` in frontmatter of each.

---

### 5. Integration Points

- [ ] `work-backlog-item` SKILL — documents `--language`, `--stack`; references layer docs
- [ ] `groom-backlog-item` SKILL — documents ARL human-probing integration; references arl-human-probing-design
- [ ] `language-manifest-schema.md` — has "Inherits from Layer 0"; `typecheck: (none)`; Conventions schema
- [ ] `role-resolution-protocol.md` — has "Layer 0 gates apply before role resolution"
- [ ] `plugins/development-harness/CLAUDE.md` — references layer model

**Evidence:** Grep or Read for key phrases.

---

### 6. Consistency with Plan

- [ ] Plan deliverables (from attached plan) — compare File and Directory Changes table to actual files
- [ ] Dependency order — Layer 0 → Layer 1 → Layer 2 → Research → SAM/ARL → ARL probing → work-backlog-item

**Evidence:** List any plan items not yet implemented or diverged.

---

## Output Format

Produce a structured report:

```text
## SDLC Layer Evaluation Report
Date: {YYYY-MM-DD}

### Summary
- Cross-Reference: {PASS|FAIL|PARTIAL} — {brief}
- Doc Completeness: {PASS|FAIL|PARTIAL}
- Knowledge-Explorer: {PASS|FAIL|PARTIAL}
- Research Metadata: {PASS|FAIL|PARTIAL}
- Integration Points: {PASS|FAIL|PARTIAL}
- Plan Consistency: {PASS|FAIL|PARTIAL}

### Findings
1. [Category] {finding} — {suggested fix}
2. ...

### Recommended Actions
- [ ] {action 1}
- [ ] {action 2}
```

---

## Iteration

After evaluation:

1. **If `--fix`**: Apply safe fixes (broken paths, missing frontmatter fields, obvious typos). Report each change.
2. **If no `--fix`**: Present findings; offer to create backlog items or apply fixes.
3. **Re-run**: After fixes, re-run evaluation to confirm improvements.

---

## Experiments

Flow experiments and learnings live in [sam-flow-experiments](https://github.com/Jamie-BitFlight/sam-flow-experiments). Clone via SSH: `git clone git@github.com:Jamie-BitFlight/sam-flow-experiments.git`. When iterating, consider running experiments against concept fixtures to validate changes.

---

## References

- [.claude/docs/sdlc-layers/](../../docs/sdlc-layers/)
- [verify skill](../verify/SKILL.md) — evidence discipline
- [groom-backlog-item](../../../plugins/development-harness/skills/groom-backlog-item/SKILL.md) — orchestration pattern
