# DH Plugin Known Entities

Authoritative reference for extraction workers and verifiers. Use this to validate
extracted relationships — agent names, skill names, and MCP tool names must match
entries in this file exactly. An extracted reference to an entity not listed here
is either a short-form alias (resolve to the canonical name) or a hallucination (reject).

Generated from source: `agents/*.md`, `skills/*/`, `backlog_core/server.py`,
`sam_schema/server.py`, `agent_profile/server.py`.

---

## Agents (30)

Canonical names are the filename without `.md`. Referenced in source as
`subagent_type="dh:{name}"` or as a TeamCreate member name.

```
alignment-analyst
backlog-item-groomer
classifier
codebase-analyzer
code-reviewer
context-refinement
contract-verification
dh-context-gathering
doc-drift-auditor
ecosystem-researcher
fact-checker
feature-researcher
feature-verifier
generic-stage-agent
impact-analyst
integration-checker
plan-validator
reviewer-accessibility
reviewer-performance
reviewer-quality
reviewer-security
rtica-assessor
service-docs-maintainer
swarm-task-planner
t0-baseline-capture
task-worker
technical-researcher
tn-verification-gate
workflow-extractor-reducer
workflow-extractor-worker
```

---

## Skills (59)

Canonical names are the directory name under `skills/`. Referenced in source as
`/dh:{name}` or `Skill(skill="dh:{name}")`.

```
add-new-feature
analyze-test-failures
api-state
backlog
backlog-tools-administrator
clear-cove-task-design
codebase-auditor
codemod-runner
code-review-architecture
code-review-claude-skills
code-review-cli
code-review-llm
code-review-nodejs
code-review-python
code-review-typescript
code-review-web
complete-implementation
complete-milestone
comprehensive-test-review
context-integration
create-artifact
create-backlog-item
development-harness
dh-meta-docs
discovery
dispatch
ecosystem-research
evaluate-sdlc-layers
execution
fact-check
file-classification
final-verification
find-cause
forensic-review
gate-push
generate-task
groom-backlog-item
groom-milestone
group-items-to-milestone
impact-measurement
implementation-manager
implement-feature
interop
kage-bunshin
meta-workflow-graph-refresh
multi-perspective-review
planner-rt-ica
planning
research-note
rt-ica
setup-skill-discovery
start-task
subagent-contract
task-decomposition
test-failure-mindset
validation-protocol
verify-done
work-backlog-item
work-milestone
```

### Stub skills (alias only — no execution logic)

These invoke `work-backlog-item` with a mode argument. Do not trace them as
independent execution entry points.

```
create-backlog-item  →  /dh:work-backlog-item create
groom-backlog-item   →  /dh:work-backlog-item groom
```

---

## MCP Tools — Backlog Server (`mcp__plugin_dh_backlog__*`)

42 tools. Short-form aliases used in prose are listed where they differ from the
full tool name. An extracted call to any short-form must be resolved to the full
`mcp__plugin_dh_backlog__` name before entering the graph.

### Artifact tools

The short forms below are graph-normalization labels, not executable signatures.

| Full name | Short forms seen in prose |
|---|---|
| `mcp__plugin_dh_backlog__artifact_get` | `artifact_get()` |
| `mcp__plugin_dh_backlog__artifact_list` | `artifact_list()` |
| `mcp__plugin_dh_backlog__artifact_read` | `artifact_read()` |
| `mcp__plugin_dh_backlog__artifact_register` | `artifact_register()` |

### Backlog item tools

| Full name | Short forms seen in prose |
|---|---|
| `mcp__plugin_dh_backlog__backlog_add` | `backlog_add()` |
| `mcp__plugin_dh_backlog__backlog_close` | `backlog_close()` |
| `mcp__plugin_dh_backlog__backlog_comment_issue` | `backlog_comment_issue()` |
| `mcp__plugin_dh_backlog__backlog_create_milestone` | `backlog_create_milestone()` |
| `mcp__plugin_dh_backlog__backlog_create_project` | `backlog_create_project()` |
| `mcp__plugin_dh_backlog__backlog_create_sam_task` | `backlog_create_sam_task()` |
| `mcp__plugin_dh_backlog__backlog_get_ready_sam_tasks` | `backlog_get_ready_sam_tasks()` |
| `mcp__plugin_dh_backlog__backlog_get_sam_tasks` | `backlog_get_sam_tasks()` |
| `mcp__plugin_dh_backlog__backlog_get_soonest_milestone` | `backlog_get_soonest_milestone()` |
| `mcp__plugin_dh_backlog__backlog_groom` | `backlog_groom()` |
| `mcp__plugin_dh_backlog__backlog_list` | `backlog_list()` |
| `mcp__plugin_dh_backlog__backlog_list_comments` | `backlog_list_comments()` |
| `mcp__plugin_dh_backlog__backlog_list_issues` | `backlog_list_issues()` |
| `mcp__plugin_dh_backlog__backlog_list_labels` | `backlog_list_labels()` |
| `mcp__plugin_dh_backlog__backlog_list_merged_prs` | `backlog_list_merged_prs()` |
| `mcp__plugin_dh_backlog__backlog_list_milestones` | `backlog_list_milestones()` |
| `mcp__plugin_dh_backlog__backlog_list_projects` | `backlog_list_projects()` |
| `mcp__plugin_dh_backlog__backlog_normalize` | `backlog_normalize()` |
| `mcp__plugin_dh_backlog__backlog_pull` | `backlog_pull()` |
| `mcp__plugin_dh_backlog__backlog_read_comment` | `backlog_read_comment()` |
| `mcp__plugin_dh_backlog__backlog_resolve` | `backlog_resolve()` |
| `mcp__plugin_dh_backlog__backlog_strike_entry` | `backlog_strike_entry()` |
| `mcp__plugin_dh_backlog__backlog_sync` | `backlog_sync()` |
| `mcp__plugin_dh_backlog__backlog_update` | `backlog_update()` |
| `mcp__plugin_dh_backlog__backlog_update_sam_task_status` | `backlog_update_sam_task_status()` |
| `mcp__plugin_dh_backlog__backlog_view` | `backlog_view()` |

### Dispatch orchestration tools

| Full name | Short forms seen in prose |
|---|---|
| `mcp__plugin_dh_backlog__dispatch_conflicts` | `dispatch_conflicts()` |
| `mcp__plugin_dh_backlog__dispatch_create_plan` | `dispatch_create_plan()` |
| `mcp__plugin_dh_backlog__dispatch_item_status` | `dispatch_item_status()` |
| `mcp__plugin_dh_backlog__dispatch_read` | `dispatch_read()` |
| `mcp__plugin_dh_backlog__dispatch_spawn` | `dispatch_spawn()` |
| `mcp__plugin_dh_backlog__dispatch_stale_check` | `dispatch_stale_check()` |
| `mcp__plugin_dh_backlog__dispatch_validate` | `dispatch_validate()` |
| `mcp__plugin_dh_backlog__dispatch_wave_start` | `dispatch_wave_start()` |
| `mcp__plugin_dh_backlog__dispatch_wave_status` | `dispatch_wave_status()` |

### Sync tools

| Full name | Short forms seen in prose |
|---|---|
| `mcp__plugin_dh_backlog__sync_now` | `sync_now()` |
| `mcp__plugin_dh_backlog__sync_status` | `sync_status()` |

### Agent profile tools (mounted under backlog server namespace)

| Full name | Short forms seen in prose |
|---|---|
| `mcp__plugin_dh_backlog__profile_list` | `profile_list()` |
| `mcp__plugin_dh_backlog__profile_load` | `profile_load()`, `profile_load(agent_name=...)` |

---

## MCP Tools — SAM Server (`mcp__plugin_dh_sam__*`)

3 tools. Each tool handles multiple actions via an `action` parameter.

| Full name | Short forms | Actions |
|---|---|---|
| `mcp__plugin_dh_sam__sam_plan` | `sam_plan()` | `read`, `create`, `list`, `status`, `ready`, `update`, `append_task`, `finalize` |
| `mcp__plugin_dh_sam__sam_task` | `sam_task()` | `read`, `claim`, `state`, `update` |
| `mcp__plugin_dh_sam__sam_active_task` | `sam_active_task()` | `get`, `set`, `update`, `clear` |

---

## Registered Artifacts (`artifact_register` / `artifact_read`)

Stored via `artifact_register`, retrieved via `artifact_read`. The `artifact_type` value
is the canonical key. Short-form prose references (e.g. "the architect spec", "the T0
baseline") must resolve to one of these keys.

SAM plans are not registered artifacts. Create and read their content through `sam_plan`,
then associate the returned logical plan address with its owner through `backlog_update`.

| artifact_type key | Producer skill/agent | Consumer skill/agent |
|---|---|---|
| `feature-context` | `add-new-feature` (feature-researcher) | `add-new-feature` (architect, swarm-task-planner) |
| `codebase-analysis` | `add-new-feature` (codebase-analyzer), `code-review-architecture` | `add-new-feature` |
| `architect` | `add-new-feature` (swarm-task-planner) | `implement-feature`, `add-new-feature` |
| `T0-baseline` | `implement-feature` (t0-baseline-capture) | `implement-feature` (TN gate comparison) |
| `TN-verification` | `implement-feature` (tn-verification-gate) | `complete-implementation` |
| `code-review` | `complete-implementation` (code-reviewer) | `complete-implementation`, `forensic-review` |
| `audit-report` | `complete-implementation` (doc-drift-auditor) | `complete-implementation` |
| `research` | `add-new-feature` (ecosystem-researcher / technical-researcher) | `add-new-feature` |
| `dispatch-plan` | `groom-milestone` (dispatch_create_plan) | `work-milestone` |

Source: `backlog_core/models.py` ArtifactType enum (L1263–1271), `G2-artifacts.json`,
`add-new-feature/SKILL.md`, `implement-feature/SKILL.md`, `complete-implementation/SKILL.md`.

---

## Backlog Item Sections (`backlog_groom(section=...)`)

Written via `backlog_groom(section="{name}", content=...)`, read via
`backlog_view(selector, section="{name}")`. Section name must match exactly.

### Sections written by groom swarm agents

| Section name | Written by agent | Evidence source |
|---|---|---|
| `Impact Radius` | `impact-analyst` | `agents/impact-analyst.md` |
| `Fact-Check` | `fact-checker` | `agents/fact-checker.md` |
| `RT-ICA` | `rtica-assessor` | `groom/finalize.md` |
| `Issue Classification` | `classifier` | `agents/classifier.md` (via `swarm.md`) |
| `Root-Cause Analysis` | `classifier` | `agents/classifier.md` |
| `Design Intent Alignment` | `alignment-analyst` | `agents/alignment-analyst.md` |
| `Grooming Notes` | groom finalize step | `groom/finalize.md` |

### Body sections defined in item schema

Canonical top-level order from `skills/backlog/references/item-schema.md` / `skills/backlog/templates/item.md`:

```
Description            ← not a `## ` section — creation-time template field, no sections[] key
Acceptance Criteria     ← creation-time template field ("**Acceptance Criteria**:"); `acceptance_criteria`
                           IS also a registered SECTION_HEADING key for `backlog_groom(section=...)` writes
Research First          ← creation-time template field ("**Research first**:"), not a `## ` section
Suggested Location      ← creation-time template field ("**Suggested location**:"); `suggested_location`
                           is separately a registered SECTION_HEADING key
Fact-Check
RT-ICA
Groomed                 ← special-cased in section_display_title(), not a plain SECTION_HEADING entry
Acceptance Criteria Verification   ← documented in item-schema.md/item.md as written by
                                       `work-backlog-item close`, but no current code path implements
                                       this: the close workflow's per-criterion PASS/FAIL text is
                                       generated by a verification agent and used only as a pass/fail
                                       gate, never persisted to the item; `resolve_item()` posts a
                                       GitHub comment (`## Resolved`), not this section. Aspirational
                                       doc prose, not verified behavior — no SECTION_HEADING entry
                                       exists or is needed until a write/read path is implemented.
```

`Fact-Check` and `RT-ICA` ARE registered `SECTION_HEADING` keys (`fact_check`, `rt_ica`) — they are
both top-level `##` sections in the template AND written via `backlog_groom(section=...)`.

Subsections under `## Groomed` (written as one block by `backlog-item-groomer` via `groomed_content`,
parsed into `GroomedData.subsections` — **a separate namespace from `item.sections`/`SECTION_HEADING`**;
looked up as `sections["Groomed"]["subsections"]["{name}"]`, never as a top-level `sections["{name}"]`,
so these do not need — and as of this writing do not have — their own `SECTION_HEADING` entries):
```
Reproducibility
Priority
Impact
Scope
Output / Evidence
Dependencies
Research
Skills
Agents
Prior Work
Files
Decision
Human Input        ← conditional (RT-ICA BLOCKED or domain judgment needed)
Questions for Human ← conditional (targeted missing-information questions)
Blockers            ← conditional (from RT-ICA MISSING items)
```

Optional/context-dependent sections from `docs/backlog-item-groomed-schema.md`, cross-checked
against `backlog_core/rendering.py`'s `SECTION_HEADING`. Most are registered top-level
`SECTION_HEADING` keys. `Human Input`, `Questions for Human`, and `Blockers` are not — but this is
correct, not a gap: `agents/backlog-item-groomer.md` produces all three today as `## Groomed`
subsections (see list above), the same mechanism as `Priority`/`Impact`/`Benefits`. There is no
top-level `section=`/`sections[...]` evidence for these three because they were never meant to be
top-level sections. `Acceptance Criteria Verification` is a separate case (see note above):
```
Benefits
Expected Behavior
Desired Structure
Human Input          ← Groomed subsection, not a top-level SECTION_HEADING key (see above)
Questions for Human   ← same
Resources
Blockers              ← same
Effort
Issue Classification
Root-Cause Analysis
Acceptance Criteria Verification
```

`Scope` and `Desired Structure` were added to `SECTION_HEADING` by #2979 — `discovery/SKILL.md`
reads `sections['Scope']` / `sections['Desired Structure']` (Title Case) but neither key existed in
the registry before. `Output / Evidence` was added to `SECTION_HEADING` by #2979 for the same
reason: `groom/groom-drift.md` reads `sections["Output / Evidence"]` at the top level (distinct
from the `## Groomed` subsection of the same display name) and the un-registered key previously
round-tripped through the generic `unknown__` fallback with an embedded `/` character
(`unknown__output_/_evidence`) instead of a clean canonical key.

**Provenance note — `Story`, `Context`, `Working Register`, `Divergence Notes`:** these four keys
are registered in `SECTION_HEADING` (added by #2964) with no current `section=` write-directive or
`sections[...]` read evidence in `plugins/development-harness/{agents,skills}/**/*.md`. Their
registration is sourced from legacy production data in the live `.dh` backlog cache (see #2953,
#2955, #2956 for the investigation and git blame on `SECTION_HEADING` for exact provenance) — these
display titles exist to give a clean, human-readable heading to sections real historical backlog
items already carry under those raw storage keys, not because any current doc instructs an agent to
write or read them. `Divergence Notes` additionally appears as a live `## Divergence Notes` heading
in **SAM task files** (`skills/start-task/SKILL.md`, `agents/context-refinement.md`) — a different
artifact type from backlog items, parsed independently of `backlog_core`'s section mechanism
entirely. Kept, not removed, per the Living Document Protocol below — flagging provenance is
required before removal, and legacy data may still reference these keys.

Source: `skills/backlog/references/item-schema.md` (L54–73), `skills/backlog/templates/item.md`,
`docs/backlog-item-groomed-schema.md` (L64–81), `agents/impact-analyst.md`,
`agents/fact-checker.md`, `agents/classifier.md`, `agents/backlog-item-groomer.md`, `groom/finalize.md`,
`backlog_core/rendering.py` `SECTION_HEADING` (full grep cross-check across doc `section=`/`sections[...]` usage).

---

## Living Document Protocol

This file is maintained by extraction agents, not by humans. When any extraction
worker or reducer agent encounters an entity that is not listed here but can be
verified from body content evidence, it MUST update this file before continuing.

### When to add a new entity

Add to this file when ALL of the following are true:
1. The entity appears in the body content of the source file (not the description or frontmatter)
2. The verbatim evidence quote can be cited with file path and line number
3. The entity is one of: an agent name, a skill name, an MCP tool name, a registered
   artifact type key, or a named backlog item section

Do NOT add based on description text, inferred relationships, or mentions in other
agents' descriptions of what a target does.

### How to add

Add the entity to its correct section with this annotation on the same line:

```
entry-name   ← [discovered: {source_file}:{line}, {date}]
```

For artifact types and sections, add a full row to the table with producer/consumer
and evidence source.

### How to flag a conflict

If an entity appears in the source with a name that differs from an existing entry
(e.g. a section called "Impact Radius" in one file and "Impact Radius Section" in
another), add both variants with a conflict note:

```
Impact Radius           ← [canonical]
Impact Radius Section   ← [variant, agents/impact-analyst.md:L243 — resolve to canonical]
```

The reducer resolves conflicts by choosing the form that appears most frequently
across corroborated workers, or escalates to a human if tied.

### Staleness

The Agents/Skills/MCP-tool/Registered-Artifacts sections were last generated on 2026-06-11 from
source and have not been re-verified in this pass. The **Backlog Item Sections** section was
reconciled on 2026-08-18 (#2979) against `backlog_core/rendering.py`'s `SECTION_HEADING` registry
and a full `section=`/`sections[...]` grep of `plugins/development-harness/{agents,skills}/**/*.md`
— see the provenance notes inline above. If the plugin has changed since either date, run an
extraction pass — workers will discover and add missing entities as they trace each file.

---

## Validation rules for extraction workers

1. Any agent name extracted from body content must appear in the Agents list above.
2. Any skill invocation extracted from body content must appear in the Skills list above.
3. Any MCP tool call extracted from body content must resolve to a full name in the
   tables above. Short forms are valid evidence — resolve them to full names in the
   output schema.
4. A relationship citing only a stub skill (`create-backlog-item`, `groom-backlog-item`)
   as a target must be re-expressed as a call to `work-backlog-item` with the
   appropriate mode argument.
5. Descriptions and frontmatter fields are NOT valid evidence sources. Evidence quotes
   must come from the body content only.
6. Any `artifact_type` value extracted from body content must match a key in the
   Registered Artifacts table. Prose references like "the architect spec" or "the T0
   baseline" must be resolved to their canonical key (`architect`, `T0-baseline`) before
   entering the graph.
7. Any `section=` value extracted from a `backlog_groom` call must match a name in the
   Backlog Item Sections lists. Unrecognised section names must be flagged as AMBIGUOUS,
   not silently included.
8. When an entity is found in body content that is NOT in this file, add it following
   the Living Document Protocol above before emitting the finding. The finding is then
   EXTRACTED, not AMBIGUOUS. Never discard a real entity just because this file is
   incomplete — update the file and continue.
