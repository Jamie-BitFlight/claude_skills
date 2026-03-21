---
name: 'evaluate-sdlc-layers: Run and fix findings'
description: 'The evaluate-sdlc-layers skill exists with six checks (cross-refs, doc completeness, knowledge-explorer, research metadata, integration points, plan consistency). Run `/evaluate-sdlc-layers` and address any findings. Success: all checks pass with `--fix` applied where applicable.'
metadata:
  topic: evaluate-sdlc-layers-run-and-fix-findings
  source: Session observation — SDLC layer implementation (2026-02-23)
  added: '2026-02-23'
  priority: P2
  type: Bug
  status: needs-grooming
  issue: '#249'
  last_synced: '2026-03-21T08:20:58Z'
  groomed: '2026-03-21'
---

## Story

As a **maintainer of the project infrastructure**, I want to **evaluate-sdlc-layers: run and fix findings** so that **the project infrastructure stays healthy**.

## Description

The evaluate-sdlc-layers skill exists with six checks (cross-refs, doc completeness, knowledge-explorer, research metadata, integration points, plan consistency). Run `/evaluate-sdlc-layers` and address any findings. Success: all checks pass with `--fix` applied where applicable.

## Suggested Location

`.claude/skills/evaluate-sdlc-layers/SKILL.md`; run against `.claude/docs/sdlc-layers/`

## Context

- **Source**: Session observation — SDLC layer implementation (2026-02-23)
- **Priority**: P2
- **Added**: 2026-02-23
- **Research questions**: None

## RT-ICA

<div><sub>2026-03-21T08:20:58Z</sub>

RT-ICA Final: evaluate-sdlc-layers: Run and fix findings
Goal: Run the six-check evaluate-sdlc-layers skill and fix all findings with --fix where applicable.
Conditions:
1. Skill file exists at .claude/skills/evaluate-sdlc-layers/SKILL.md | Snapshot: AVAILABLE → Final: AVAILABLE | Citation: Glob confirmed, Read verified frontmatter name: evaluate-sdlc-layers
2. Six checks match description (cross-refs, doc completeness, knowledge-explorer, research metadata, integration points, plan consistency) | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker read SKILL.md, confirmed exactly 6 numbered sections matching all names
3. Target directory .claude/docs/sdlc-layers/ exists and has content | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker confirmed Layer 0 (9 files), Layer 1 (6 files) present; Layer 2 MISSING (expected gap the skill will flag)
4. --fix flag supported by the skill | Snapshot: DERIVABLE → Final: AVAILABLE | Citation: fact-checker found argument-hint: '[--dry-run | --fix]' at SKILL.md line 4
5. Success criteria: all checks pass | Snapshot: AVAILABLE → Final: AVAILABLE | Citation: description states "Success: all checks pass with --fix applied where applicable"

Changes from snapshot:
- Condition 2: DERIVABLE → AVAILABLE (resolved by fact-checker reading SKILL.md directly)
- Condition 3: DERIVABLE → AVAILABLE (resolved by fact-checker; Layer 2 missing is a known expected finding, not a blocker)
- Condition 4: DERIVABLE → AVAILABLE (resolved by fact-checker finding --fix in argument-hint)

New conditions discovered by swarm:
- Layer 2 directory (.claude/docs/sdlc-layers/layer-2/) is missing — this is the primary finding the skill will report; not a grooming blocker, it IS the work

Decision: APPROVED — all conditions AVAILABLE. Item is ready for planning phase.
</div>

## Fact-Check

<div><sub>2026-03-21T08:15:52Z</sub>

## Fact-Check Summary

| Claim | Status | Evidence |
|-------|--------|----------|
| Skill exists at `.claude/skills/evaluate-sdlc-layers/SKILL.md` | VERIFIED | File read successfully, contains frontmatter with name: evaluate-sdlc-layers |
| Skill has six checks: cross-refs, doc completeness, knowledge-explorer, research metadata, integration points, plan consistency | VERIFIED | SKILL.md contains exactly 6 numbered sections: 1. Cross-Reference Validation, 2. Doc Completeness, 3. Knowledge-Explorer Layer Filter, 4. Research Entry Layer Metadata, 5. Integration Points, 6. Consistency with Plan |
| `--fix` flag exists in skill | VERIFIED | SKILL.md line 4: `argument-hint: '[--dry-run \| --fix]'` and line 15 documents the flag: "After evaluation, apply safe fixes..." |
| Target dir `.claude/docs/sdlc-layers/` exists and has content | PARTIALLY VERIFIED | Directory exists with content; Layer 0 (9 files) and Layer 1 (6 files) complete. Layer 2 directory DOES NOT EXIST (expected by checks but not implemented). ARL layer has 2 files (arl-meta-layer.md, arl-human-probing-design.md). Root README exists. |

**File Count Verification:**
- Layer 0: 9 files present ✓ (README, sam-pipeline, arl-touchpoints, artifact-conventions, rt-ica-gate, verification-protocol, task-file-format, evidence-discipline, orchestrator-discipline)
- Layer 1: 6 files present ✓ (README, layer-1-overview, language-manifest-template, linting-discovery-protocol, workflow-pattern-taxonomy, harness-role-mapping)
- Layer 2: Directory missing ✗ (expected per SKILL.md Check 2 Doc Completeness section)
- ARL: 2 files present ✓ (arl-meta-layer.md, arl-human-probing-design.md)

**VERIFIED: 3, REFUTED: 0, INCONCLUSIVE: 1**

**Inconclusive Item:** Layer 2 implementation status — SKILL.md describes checking for Layer 2 files (README, layer-2-overview, stack-profile-schema, stack-profile-template, pilot profiles), but the layer-2 directory does not exist. This is expected per backlog item intent ("evaluate and fix findings"), not a factual claim error. The skill will correctly identify this gap during execution.

</div>

## Groomed (2026-03-21)


### Reproducibility

<div><sub>2026-03-21T08:15:58Z</sub>

Run the `/evaluate-sdlc-layers` skill to validate SDLC layer architecture across documentation, research metadata, integration points, and cross-references. The skill's 6 checks inspect:

1. Cross-reference validity — verify linked paths exist (e.g., `.claude/docs/TASK_FILE_FORMAT.md`, layer-specific docs)
2. Doc completeness — confirm all 9 Layer 0 docs, 6 Layer 1 docs, Layer 2 docs, and ARL docs are present
3. Knowledge-Explorer layer filtering — test `uv run research/knowledge-explorer.py list --layer {0|1|2}` returns correct layer metadata
4. Research entry layer metadata — verify frontmatter contains `layer:` field in `.md` files under `research/`
5. Integration points — cross-check skill documentation references layer model (work-backlog-item, groom-backlog-item)
6. Consistency with plan — align actual file structure against deliverables from any attached plan

Run the skill with `--dry-run` to see all failing checks without applying fixes. Failures appear as FAIL/PARTIAL results in the structured report with recommended actions.
</div>

<div><sub>2026-03-21T08:17:52Z</sub>

Run `/evaluate-sdlc-layers` against `.claude/docs/sdlc-layers/` to trigger the validation checks. The need for fixes is revealed when any of the six checks produces a FAIL or PARTIAL result:

1. **Cross-Reference Validation FAIL**: A linked path in `.claude/docs/sdlc-layers/` or related docs does not exist or points to wrong content (e.g., `plugins/development-harness/docs/layer-2/` missing, `TASK_FILE_FORMAT.md` at wrong location).
2. **Doc Completeness FAIL**: Expected files missing from Layer 0 (9 docs), Layer 1 (6 docs), Layer 2 (4+ docs), or ARL sections.
3. **Knowledge-Explorer FAIL**: `uv run research/knowledge-explorer.py list --layer {N}` returns entries without matching `layer:` metadata or misses entries that should have it.
4. **Research Metadata FAIL**: Entries like `evaluation-testing/harness-engineering-openai.md` or `api-frameworks/fastapi.md` lack correct `layer:` frontmatter field or related metadata (`language`, `stack`).
5. **Integration Points FAIL**: Skills (`work-backlog-item`, `groom-backlog-item`) or protocol docs fail to reference layer architecture or document layer inheritance.
6. **Plan Consistency FAIL**: Files implemented do not match File and Directory Changes table in attached plan, or dependency order is violated.

Reproduce: Run the skill with no arguments to get a report, then use `--fix` to apply safe corrections.
</div>

### Priority

<div><sub>2026-03-21T08:16:11Z</sub>

**P2 — Should-Have**: SDLC layers document the architecture for orchestrator discipline, role resolution, language stack selection, and research metadata. Without validation:

- Cross-reference rot accumulates; linked docs become outdated or renamed, breaking dependency chains
- Integration gaps obscure which skills/plugins depend on layer model — future changes may miss critical touchpoints
- Missing research metadata prevents layer-aware research filtering, breaking discovery workflows
- Incomplete docs leave implementors guessing at layer semantics — design intent becomes implicit

P2 rather than P1 because the layer system is foundational but already partially functional; blocking issues are manageable. P2 signals: urgent enough to schedule soon, but not critical-path to active development.
</div>

<div><sub>2026-03-21T08:18:05Z</sub>

**P2: Should-Have** — improves documentation consistency and prevents drift without blocking feature development.

**Justification**: The SDLC Layer Separation Architecture is foundational to the development workflow; incomplete or broken cross-references weaken its authority and trustworthiness. Documentation drift creates confusion for new contributors and agents. However, this is not urgent: it improves tooling quality, not core product functionality. P0 work (authentication, core services) and P1 work (critical tooling) take precedence. Once P0/P1 items stabilize, validation ensures the architectural foundation remains sound for scaling.
</div>

### Impact

<div><sub>2026-03-21T08:16:24Z</sub>

If this item is never completed:

- **Broken docs**: Cross-references point to moved, renamed, or deleted files; docs become non-executable guidance
- **Missing layer metadata**: Research entries lack `layer:` frontmatter, breaking the knowledge-explorer layer filtering feature and preventing discovery workflows from scoping properly
- **Integration ambiguity**: Skills like `work-backlog-item` and `groom-backlog-item` remain undocumented in relation to layer model; future maintainers don't know which skill layers to load for which task
- **Silent divergence**: Plan artifacts diverge from implementation without audit trail; layers semantics decay as documentation drifts from code
- **Reduced discoverability**: Without complete layer docs, new developers cannot understand orchestrator discipline, role resolution, or language manifest structure — onboarding friction increases

Resolution: Systematic validation + automated fixes prevent silent doc rot and keep architecture documentation aligned with implementation.
</div>

<div><sub>2026-03-21T08:18:21Z</sub>

**If this work is not done:**

- **Documentation drift**: Layer docs become inconsistent with actual implementation. New docs added without layer metadata; layer metadata gets out of sync with actual file structure. Agents and contributors lose trusted reference point.
- **Broken cross-references**: Skill docs (work-backlog-item, groom-backlog-item) link to layer docs that don't exist or have moved. Links rot; referenced protocols are inaccessible.
- **Research metadata gaps**: Research entries added without `layer:` field or with incorrect `stack` values. Knowledge-Explorer queries fail to filter correctly. SAM task generation cannot route work to correct layer.
- **Integration points unvalidated**: Skills claim to implement layer architecture but actual docs are incomplete or divergent. New agents inherit broken patterns.
- **Plan slippage**: Architectural plan is never verified against implementation. Divergences accumulate; initial investment in layers is wasted because no one confirms it works.
- **Scaled maintenance debt**: Each new entry, link, or cross-reference is a chance to introduce inconsistency. Without validation, debt compounds exponentially as codebase grows.

**Operationally**: Contributors become unsure whether layer docs are current, leading to either ignoring them or working around them. Layer architecture degrades from authoritative to aspirational.
</div>

### Expected Behavior

<div><sub>2026-03-21T08:16:38Z</sub>

Success state: `/evaluate-sdlc-layers --fix` runs to completion with all 6 checks reporting PASS:

1. **Cross-Reference Validation**: PASS — all linked paths in `.claude/docs/sdlc-layers/` exist and contain expected content
2. **Doc Completeness**: PASS — all 9 Layer 0 docs, 6 Layer 1 docs, Layer 2 docs, and ARL docs are present at expected paths
3. **Knowledge-Explorer Layer Filter**: PASS — `uv run research/knowledge-explorer.py list --layer {0|1|2}` returns entries tagged with correct layer; non-tagged entries are excluded
4. **Research Entry Layer Metadata**: PASS — all research `.md` files have frontmatter `layer:` field set correctly (e.g., `layer: "2"` for fastapi.md)
5. **Integration Points**: PASS — work-backlog-item and groom-backlog-item skills document layer model; orchestrator/language-manifest docs reference layer 0 gates
6. **Plan Consistency**: PASS — file and directory structure matches attached plan deliverables (or no plan present)

After `--fix`, no regressions in `.claude/docs/sdlc-layers/`; files contain valid markdown with correct frontmatter and working cross-references.
</div>

<div><sub>2026-03-21T08:18:33Z</sub>

**Success state**: Running `/evaluate-sdlc-layers` produces a report with all six checks returning **PASS**:

```text
### Summary
- Cross-Reference: PASS
- Doc Completeness: PASS
- Knowledge-Explorer: PASS
- Research Metadata: PASS
- Integration Points: PASS
- Plan Consistency: PASS
```

With `--fix` applied, any auto-fixable issues (broken paths, missing frontmatter, obvious typos, missing directory stubs) are corrected, and the report documents each change made.

**Verification**: Re-running `/evaluate-sdlc-layers` after `--fix` should produce all PASS with zero findings reported. No regression in `.claude/docs/sdlc-layers/` or related docs.
</div>

### Acceptance Criteria

<div><sub>2026-03-21T08:16:51Z</sub>

- [ ] Run `/evaluate-sdlc-layers --dry-run` and generate report with all 6 checks clearly listed (Cross-Reference, Doc Completeness, Knowledge-Explorer, Research Metadata, Integration Points, Plan Consistency)
- [ ] Run `/evaluate-sdlc-layers --fix` and apply all safe fixes; report outputs each change (e.g., "Updated research/fastapi.md frontmatter: added layer: 2", "Fixed cross-reference in layer-1/README.md")
- [ ] After `--fix`, re-run `/evaluate-sdlc-layers` and confirm all 6 checks show PASS (no regressions)
- [ ] Verify `.claude/docs/sdlc-layers/` contains all expected files: 9 Layer 0 docs, 6 Layer 1 docs, Layer 2 structure, ARL docs
- [ ] Confirm no markdown syntax errors or missing frontmatter fields in any `.md` file under `.claude/docs/sdlc-layers/`
- [ ] Document any findings in backlog/plan for follow-up (e.g., broken references that require manual review)
</div>

<div><sub>2026-03-21T08:18:49Z</sub>

- [ ] **AC1**: Run `/evaluate-sdlc-layers --dry-run` against `.claude/docs/sdlc-layers/` and review findings report. Document any FAIL or PARTIAL results observed.
- [ ] **AC2**: Run `/evaluate-sdlc-layers --fix` to apply safe corrections. Capture output showing what was changed (paths fixed, metadata added, etc.).
- [ ] **AC3**: Cross-references validation checks all 6+ linked paths in layer docs and confirms they exist with correct content.
- [ ] **AC4**: Doc completeness confirms all 9 Layer 0 docs, 6 Layer 1 docs, 4+ Layer 2 docs, and ARL docs are present at expected locations.
- [ ] **AC5**: Knowledge-Explorer layer filtering returns correctly tagged entries; entries without `layer:` metadata are excluded when `--layer` filter is used.
- [ ] **AC6**: Research metadata audit verifies sample entries (harness-engineering-openai.md, fastapi.md, copier-astral.md) have correct `layer:` frontmatter.
- [ ] **AC7**: Integration points audit confirms `work-backlog-item` SKILL and `groom-backlog-item` SKILL reference layer docs and document `--language`, `--stack` inheritance.
- [ ] **AC8**: Plan consistency check compares attached plan's File and Directory Changes table against actual implementation; no missing or diverged items.
- [ ] **AC9**: Re-run `/evaluate-sdlc-layers --dry-run` after fixes and confirm all six checks return PASS; zero findings reported.
- [ ] **AC10**: Verify no regression in `.claude/docs/sdlc-layers/` — all existing content preserved, new files/metadata are additions only.
</div>

### Files

<div><sub>2026-03-21T08:17:10Z</sub>

Directly modified by `/evaluate-sdlc-layers --fix`:

- `.claude/docs/sdlc-layers/layer-0/` — all 9 docs (README, sam-pipeline, arl-touchpoints, artifact-conventions, rt-ica-gate, verification-protocol, task-file-format, evidence-discipline, orchestrator-discipline)
- `.claude/docs/sdlc-layers/layer-1/` — all 6 docs (README, layer-1-overview, language-manifest-template, linting-discovery-protocol, workflow-pattern-taxonomy, harness-role-mapping)
- `.claude/docs/sdlc-layers/layer-2/` — README, layer-2-overview, stack-profile-schema, stack-profile-template, and pilot profiles (python-fastapi, python-cli)
- `.claude/docs/sdlc-layers/arl-meta-layer.md`, `arl-human-probing-design.md` — ARL layer docs
- `research/` — any `.md` files with missing or incorrect frontmatter `layer:` field
- `.claude/skills/work-backlog-item/SKILL.md` — integration check only (no modification unless documentation update needed)
- `.claude/skills/groom-backlog-item/SKILL.md` — integration check only
- `plugins/development-harness/CLAUDE.md` — integration check only

Indirectly verified (read-only during checks):
- `research/knowledge-explorer.py` — layer filtering logic
- Cross-referenced external docs (e.g., nested in plugins or sibling repos)
</div>

<div><sub>2026-03-21T08:19:05Z</sub>

**Files likely to be read or modified by the skill and fixes**:

**SDLC Layer Documentation** (read and validated):
- `.claude/docs/sdlc-layers/` (all files)
  - Layer 0: `README.md`, `sam-pipeline.md`, `arl-touchpoints.md`, `artifact-conventions.md`, `rt-ica-gate.md`, `verification-protocol.md`, `task-file-format.md`, `evidence-discipline.md`, `orchestrator-discipline.md`
  - Layer 1: `README.md`, `layer-1-overview.md`, `language-manifest-schema.md`, `language-manifest-template.md`, `linting-discovery-protocol.md`, `workflow-pattern-taxonomy.md`, `role-resolution-protocol.md`, `harness-role-mapping.md`
  - Layer 2: `README.md`, `layer-2-overview.md`, `stack-profile-schema.md`, `stack-profile-template.md`, pilot profiles
  - ARL: `arl-meta-layer.md`, `arl-human-probing-design.md`

**Research Entries** (read for metadata, potentially modified with `--fix`):
- `research/knowledge-explorer.py` — tested for layer filtering
- `research/evaluation-testing/harness-engineering-openai.md` — layer metadata checked
- `research/api-frameworks/fastapi.md`, `tornado.md` — layer and stack metadata checked
- `research/developer-tools/copier-astral.md` — layer metadata checked
- `research/README.md` — layer mapping section validated

**Skills** (read for integration point documentation):
- `.claude/skills/work-backlog-item/SKILL.md` — validated for layer integration, `--language`, `--stack` docs
- `.claude/plugins/development-harness/skills/groom-backlog-item/SKILL.md` — validated for ARL human-probing integration
- Protocol docs: `language-manifest-schema.md`, `role-resolution-protocol.md` — inheritance references validated

**Plan and Related** (if attached):
- Feature plan deliverables file (File and Directory Changes table) — validated against actual implementation

**Output Artifact**:
- Evaluation report written to stdout (no permanent file created unless agent saves it)
</div>

### Effort

<div><sub>2026-03-21T08:17:24Z</sub>

**Low — 30–60 minutes**

Justification:

- The `/evaluate-sdlc-layers` skill is already implemented and ready to run — no new code needed
- Most fixes are mechanical: add missing frontmatter fields, repair broken paths, verify file existence
- 6 checks are well-scoped and focused (doc completeness, cross-references, metadata, integration points)
- Safe fixes are automated by the skill's `--fix` flag — no manual intervention required for common issues
- If all checks pass on first run: trivial (< 10 minutes to run and verify)
- If failures found: moderate complexity (< 1 hour to read findings, apply fixes, re-run, and document results)

Risk: Low. The skill runs read-only checks by default (`--dry-run`) and applies only safe, reversible fixes (`--fix`). No breaking changes anticipated.
</div>

<div><sub>2026-03-21T08:19:21Z</sub>

**Estimate: Medium (4–8 hours)**

**Breakdown**:
- **Skill execution and report generation** (1–2 hours): Run the skill, parse findings, document observations for each of the 6 checks. Findings may be scattered across multiple files, requiring careful cross-referencing.
- **Cross-reference and path validation** (1–2 hours): Verify each of 6+ linked paths exists and contains expected content. If paths are broken, research correct locations or file the finding.
- **Metadata fixes** (1–2 hours): Add missing `layer:` frontmatter fields to research entries. Update `language` and `stack` tags where missing or incorrect. Validate syntax.
- **Documentation updates** (1 hour): Update SKILL docs to reference layer architecture if not already done. Ensure cross-links between work-backlog-item, groom-backlog-item, and layer docs are correct.
- **Verification and re-run** (1 hour): Re-run `/evaluate-sdlc-layers --dry-run` to confirm all fixes applied and zero findings remain. Spot-check a few key files for correctness.

**Complexity factors**:
- **Low-Medium risk**: The skill is designed to auto-fix "safe" issues (paths, metadata, typos). Breaking changes are unlikely unless docs are substantially reorganized.
- **Parallelizable**: Cross-reference checking, metadata audits, and skill doc updates can be done in parallel by an agent.
- **Tool-assisted**: The skill already knows what to check; most work is applying the skill's suggestions and verifying results.

**Success criterion**: All 6 checks PASS, zero findings, zero regression in existing docs.
</div>

### Impact Radius

<div><sub>2026-03-21T08:19:03Z</sub>



## Impact Radius

### Code — Producers
- `.claude/skills/evaluate-sdlc-layers/SKILL.md` — Defines six validation checks and `--fix` flag that will modify target files. Check 1 validates cross-references; Check 2 validates doc completeness; Checks 3-6 validate metadata, integration, and plan consistency. Skill is read-only consumer of layer docs; produces validation report and applies fixes via safe operations.
- `research/knowledge-explorer.py` — Contains layer filtering logic (`--layer {0|1|2}` flag). Will be verified for correct filtering of entries with `layer:` frontmatter metadata. No changes expected; read-only during evaluation.

### Code — Consumers
- `research/knowledge-explorer.py` — Executes layer filtering on research entries. Depends on correct `layer:` frontmatter in `.md` files under `research/` directories. Will verify that entries tagged with `layer: "0"`, `layer: "1"`, `layer: "2"` are properly filtered by `--layer` flag.
- `plugins/development-harness/skills/work-backlog-item/SKILL.md` — Documents `--language` and `--stack` parameters that select Layer 1/2 profiles per skill frontmatter line 14. Integration point: must reference `.claude/docs/sdlc-layers/` for layer model documentation. No code change expected; documentation verification only.
- `plugins/development-harness/skills/groom-backlog-item/SKILL.md` — Documents ARL human-probing integration. Integration point: may reference `arl-human-probing-design.md` for ARL design. No code change expected; documentation verification only.
- `plugins/development-harness/CLAUDE.md` — Declares layer model in line 64 ("This harness implements the **SDLC Layer Separation Architecture**..."). References `.claude/docs/sdlc-layers/`. No code change expected; documentation reference only.

### Documentation (will become stale)
- `.claude/docs/sdlc-layers/README.md` — Declares layer model structure, directory layout, and principles. Will be verified for correct cross-references and completeness. May need updates if layer-2 directory structure is incomplete or if any links are broken.
- `.claude/docs/sdlc-layers/layer-0/README.md` — Expected to document all 9 Layer 0 files. Will be verified for completeness and cross-reference accuracy.
- `.claude/docs/sdlc-layers/layer-1/README.md` — Expected to document all 6 Layer 1 files. Will be verified for completeness.
- `.claude/docs/sdlc-layers/layer-0/sam-pipeline.md` — References work-backlog-item and groom-backlog-item skills. Will be verified for working cross-references.
- `.claude/docs/sdlc-layers/arl-human-probing-design.md` — Expected to document human-probing integration for groom-backlog-item. Will be verified for existence and content accuracy.
- `.claude/docs/sdlc-layers/layer-2/` — Expected directory (README, layer-2-overview, stack-profile-schema, stack-profile-template, pilot profiles). **Currently missing** — backlog item grooming notes indicate Layer 2 directory does not exist. Evaluation will identify this gap; fix may require creating Layer 2 scaffolding or documenting that Layer 2 is optional.
- `research/README.md` — Expected to contain "Layer Mapping" section. Will be verified for section presence and content accuracy.

### Configuration / CI
- `.github/workflows/` — No existing CI jobs for evaluate-sdlc-layers found. No changes required; skill is invoked manually or on-demand. If future automation desired, can add workflow trigger (post-commit validation).

### Agent Instructions
- `plugins/development-harness/skills/work-backlog-item/references/sam-definition.md` — Referenced by skill line 18 and `.claude/docs/sdlc-layers/README.md` line 69. Will verify file exists at correct path.
- `plugins/development-harness/skills/development-harness/references/language-manifest-schema.md` — Referenced in SKILL Check 5 (Integration Points). Will verify for "Inherits from Layer 0" statement and Conventions schema presence.
- `plugins/development-harness/skills/development-harness/references/role-resolution-protocol.md` — Referenced in SKILL Check 5. Will verify for "Layer 0 gates apply before role resolution" statement.

### Systems Inventory

**TodoItems Summary (5-question impact checklist per system):**

| System | File/Component | Q1: Break? | Q2: Stale? | Q3: Code Change? | Q4: Content Update? | Q5: Test? |
|--------|---|---|---|---|---|---|
| 1. evaluate-sdlc-layers | `.claude/skills/evaluate-sdlc-layers/SKILL.md` | No | No | No | No | Manual: skill invocation validates itself |
| 2. SDLC Layer Docs | `.claude/docs/sdlc-layers/` (all files) | Likely (if refs broken) | Yes (doc completeness) | No | Yes (fix broken refs, add frontmatter) | Manual: re-run eval after fixes |
| 3. knowledge-explorer | `research/knowledge-explorer.py` | No (reads, doesn't write) | No | No | No | Manual: verify `--layer` filtering works |
| 4. Research metadata | `research/**/*.md` (8 files with `layer:` field) | Likely (if metadata missing) | Yes (if stale metadata) | No | Yes (add/fix layer frontmatter) | Manual: knowledge-explorer filter test |
| 5. work-backlog-item | `plugins/development-harness/skills/work-backlog-item/SKILL.md` | No (reads layer docs) | No | No | No | Manual: verify layer profile routing works |
| 6. groom-backlog-item | `plugins/development-harness/skills/groom-backlog-item/SKILL.md` | No (reads layer docs) | No | No | No | Manual: verify ARL integration reference works |
| 7. development-harness | `plugins/development-harness/CLAUDE.md` | No (reads layer docs) | No | No | No | Manual: verify layer model reference works |
| 8. Cross-referenced files | `plugins/development-harness/skills/*/references/*.md` (3 files) | No (read-only refs) | No | No | No | Manual: verify all references exist and link correctly |

### Ecosystem Completeness Checklist

- [ ] Every code producer updated or verified compatible
  - `.claude/skills/evaluate-sdlc-layers/SKILL.md` — verified as ready; no changes needed
  - `research/knowledge-explorer.py` — verified as read-only; no changes needed
- [ ] Every stale document updated
  - `.claude/docs/sdlc-layers/` — fix broken cross-references, add missing frontmatter, verify all expected files present
  - `research/README.md` — add or verify "Layer Mapping" section
  - `research/**/*.md` (8 files) — add/verify `layer:` frontmatter field for layer-aware filtering
- [ ] Every agent instruction updated
  - `plugins/development-harness/skills/work-backlog-item/SKILL.md` — verify layer reference works (no code change)
  - `plugins/development-harness/skills/groom-backlog-item/SKILL.md` — verify ARL integration reference works (no code change)
  - `plugins/development-harness/CLAUDE.md` — verify layer model reference works (no code change)
  - Cross-referenced files: verify all paths exist and are accurate
- [ ] CI/config files updated and validated
  - No CI changes required for this evaluation; manual skill invocation sufficient

</div>