---
name: Research curator code-analysis phase for repository targets
description: "The research-curator agent produces entries based on README files, which are the public relations layer of a repository — they tell you what the author wants you to know, not what you need to know. When the target is a repository without comprehensive technical documentation, the entry misses implementation details that matter: schemas, API layers, internal structures, extension system mechanics, code patterns, and real constraints.\n\nProblem: research entries for open-source repos stop at README depth. Questions about how things actually work (e.g., 'what does a Pi Package manifest look like?', 'how are skills loaded?') cannot be answered from the entry because the agent never examined source code.\n\nSuccess looks like: the research-curator agent has a second stage that traces code from entrypoints through the system — interfaces, schemas, extension points, internal patterns. If comprehensive technical docs exist, this stage can be skipped. If they don't, the code is examined. The resulting entry answers engineering questions, not just marketing questions.\n\nHow to verify: pick a research entry for a repo with thin docs. Ask a question about its internal structure or extension system. The entry should answer it with source-level evidence, not README paraphrases.\n\nResearch first:\n? What is the current agent workflow and where would a code-analysis phase fit?\n? How should the agent decide whether docs are 'comprehensive enough' to skip code analysis?\n? What heuristics determine which source files to examine (entrypoints, exports, config schemas)?"
metadata:
  topic: research-curator-code-analysis-phase-for-repository-targets
  source: User request — session observation that pi-mono research entry couldn't answer implementation-level questions about the extension system
  added: '2026-03-15'
  priority: completed
  type: Feature
  status: done
  issue: '#717'
  last_synced: '2026-03-15T04:46:01Z'
  groomed: '2026-03-15'
  plan: plan/P698-research-curator-code-analysis.yaml
---

## Fact-Check

<div><sub>2026-03-15T04:40:38Z</sub>

Claims checked: 2
VERIFIED: 2 | REFUTED: 0 | INCONCLUSIVE: 0

[VERIFIED] "research entries stop at README depth" — observed in this session: pi-mono research-curator agent (26 tool calls, ~110s) read 11 README/doc files from a shallow clone and zero source files. The resulting entry could not answer questions about Pi Package manifest structure or skill loading mechanics.
Evidence: session transcript 2026-03-15, agent ID a22ad5bea8489bde3

[VERIFIED] "the agent never examined source code" — confirmed by reviewing agent output: all file reads were README.md, AGENTS.md, CONTRIBUTING.md, LICENSE, and package.json files. No files from packages/*/src/ were accessed.
Evidence: session transcript 2026-03-15, agent tool call log
</div>

## RT-ICA

<div><sub>2026-03-15T04:40:52Z</sub>

Goal: Research entries for open-source repos answer engineering questions with source-level evidence, not just README paraphrases.

Conditions:
1. Current research-curator agent workflow is documented | Status: AVAILABLE | File: .claude/skills/research-curator/SKILL.md and .claude/agents/research-curator.md
2. Entry template structure is documented | Status: AVAILABLE | File: .claude/skills/research-curator/references/entry-template.md
3. Heuristic for "docs comprehensive enough to skip code analysis" | Status: MISSING | Not defined anywhere — needs design decision
4. Heuristic for which source files to examine (entrypoints, exports, schemas) | Status: MISSING | Not defined — needs design decision on file selection strategy
5. Agent has access to cloned repo during research | Status: AVAILABLE | Agent already does shallow clone — source files are on disk but not read
6. Entry template has sections for code-level findings | Status: DERIVABLE | Current template has Architecture and Features sections that could hold code-level detail; may need explicit subsections
7. Token/time budget for code analysis phase | Status: MISSING | No guidance on how deep the code analysis should go or when to stop

Decision: APPROVED (with 3 MISSING conditions to resolve during planning)
Missing: doc-sufficiency heuristic, file-selection heuristic, depth/budget constraints
</div>

## Groomed (2026-03-15)


### Issue Classification

<div><sub>2026-03-15T04:41:02Z</sub>

Type: missing-guardrail
Scenario-target: research-curator agent completes an entry for a repo with thin documentation without examining source code, producing an entry that cannot answer engineering-level questions about the system's internals.
Analysis method: none (missing-guardrail does not require RCA)
Guardrail needed: doc-sufficiency check after README pass; if insufficient, trigger code-analysis phase before finalizing entry.
</div>

<div><sub>2026-03-15T04:46:01Z</sub>


**Type**: missing-guardrail
**Rationale**: The agent already has the capability (shallow clone, Read/Glob/Grep tools, depth requirements defined) but no gate that checks whether doc-depth requirements are satisfied before skipping source code. Adding the gate is the entire fix.
**Analysis Method**: none
**Scenario Target**: Research a repo with thin docs -> entry answers implementation-level questions with source-level evidence

</div>

### Reproducibility

<div><sub>2026-03-15T04:43:44Z</sub>


1. Invoke `/research-curator https://github.com/{owner}/{repo}` where the repo has thin or absent technical docs (e.g., no `docs/architecture.md`, no API spec, README covers only installation and high-level features).
2. Wait for the agent to complete and write the entry to `./research/{category}/{name}.md`.
3. Open the entry and attempt to answer: "What does a manifest for this tool look like?", "How does the extension system load plugins?", "What fields are required in a config schema?"
4. Observe that the Architecture section contains only paraphrased README content with no component names, data flow description, or extension point detail sourced from code.

Evidence from verified session (2026-03-15): pi-mono research — agent made 26 tool calls, read 11 files (README.md, AGENTS.md, CONTRIBUTING.md, LICENSE, package.json variants), zero files from `packages/*/src/`. Resulting entry could not answer questions about Pi Package manifest structure or skill loading mechanics.

</div>

### Priority

<div><sub>2026-03-15T04:43:54Z</sub>


8/10 — Research entries for repos with thin docs are permanently shallow. The agent already clones the repo (source is on disk), making the fix a workflow change rather than a new capability. Without this, engineering questions about any underdocumented tool produce README paraphrases regardless of how many times the entry is refreshed.

</div>

### Impact

<div><sub>2026-03-15T04:44:02Z</sub>


- Blocks: Research entries for underdocumented repos cannot answer implementation-level questions; the `@research-insight-extractor` and `@research-utilization-assessor` agents downstream receive shallow entries and produce shallow proposals.
- Bottleneck: Any repo where README is the primary documentation (early-stage projects, internal tools, domain-specific tools) produces entries that can only answer marketing questions, not engineering questions.

</div>

### Benefits

<div><sub>2026-03-15T04:44:11Z</sub>


- Research entries for repos with thin docs become engineering-quality references with source-level evidence.
- Downstream agents (`@research-insight-extractor`, `@research-utilization-assessor`) receive entries that expose extension points, schemas, and internal patterns — enabling concrete integration proposals.
- The agent's existing Depth Requirements for the Architecture section become satisfiable even when README does not cover internals.
- No new tooling required — the shallow clone is already on disk during every repo research session.

</div>

### Expected Behavior

<div><sub>2026-03-15T04:44:22Z</sub>


After completing Phase 1 (Extract from README/docs), the agent evaluates whether the Architecture depth requirements are satisfied from the extracted passages. These requirements are already defined in `@research-curator`'s `## Depth Requirements` section: core component names and relationships, data flow or execution model, extension or integration points.

If the extracted passages satisfy all three criteria, the agent proceeds directly to Phase 2 (Organize).

If any criterion is unsatisfied, the agent performs a code-analysis pass on the cloned worktree before Phase 2. The code-analysis pass reads entrypoint files, type/schema declarations, and index/barrel files from `.worktrees/{repo-name}/`. Findings are added to the extracted passages pool with their file-path sources, then Phase 2 proceeds with the augmented pool.

The resulting entry's Architecture section contains component names, data flow descriptions, and extension point details sourced from actual code — not README paraphrase.

</div>

### Desired Structure

<div><sub>2026-03-15T04:44:35Z</sub>


The `@research-curator` agent workflow gains a decision gate between Phase 1 and Phase 2:

- **Doc-sufficiency check** (observable): after Phase 1 extraction, the agent tests whether the extracted passages cover the three Architecture depth criteria. The check result is logged as an internal working note and determines whether code analysis runs.

- **File selection heuristics** (observable): when code analysis runs, the agent uses three file-pattern tiers against the `.worktrees/{repo-name}/` directory:
  - Entrypoints: `package.json` `main`/`exports`/`bin` fields; `pyproject.toml` `entry_points`; `Cargo.toml` `[[bin]]`
  - Type/schema files: `*.schema.*`, `*.types.*`, `*.d.ts`, `schema.py`, `types.py`
  - Index/barrel files: `src/index.ts`, `src/index.js`, `__init__.py`, `mod.rs`, `lib.rs`

- **Depth budget** (observable): code analysis reads at most N source files per pass (N to be decided in planning; RT-ICA identified this as a MISSING condition). The agent stops after N files and notes how many remain unread.

- **Entry output** (observable): the resulting Architecture section cites `{file-path}:{function-or-type-name}` for each component it names. Entries produced without code analysis continue to cite only README/docs sources.

</div>

### Acceptance Criteria

<div><sub>2026-03-15T04:44:46Z</sub>


1. For a repo where README does not cover architecture internals, the resulting entry's Architecture section contains at least one source reference with a file path from the cloned worktree (e.g., `packages/core/src/index.ts — PluginLoader interface`).
2. For a repo with comprehensive technical docs (e.g., full API spec, architecture guide), the code-analysis phase is skipped and the entry's sources list contains only README/docs URLs — no worktree file paths.
3. The agent's working notes (internal to the session) contain a doc-sufficiency check result: either "Architecture depth requirements satisfied from docs" or "Architecture depth requirements unsatisfied — triggering code analysis".
4. When code analysis runs, the number of source files read does not exceed the configured depth budget (value to be set in planning).
5. Running `--validate` on an entry produced with code analysis passes all existing error-severity checks (no new validation schema required).
6. Running `--rerun` on an entry previously produced without code analysis re-evaluates doc sufficiency and, if still insufficient, applies the code-analysis phase to update the Architecture section.

</div>

### Research

<div><sub>2026-03-15T04:45:05Z</sub>


**Q1 — Where does code-analysis fit in the current workflow?**

The `@research-curator` agent (`/.claude/agents/research-curator.md`) runs a 5-phase workflow: Extract → Organize → Write → Confidence → Validate. Before Phase 1, the agent already performs a shallow clone of the target repo to `.worktrees/{repo-name}/`. Phase 1 reads README, AGENTS.md, CONTRIBUTING.md, LICENSE, and `package.json` — all docs-layer files. Source files in `packages/*/src/`, `src/`, `lib/` are never read.

The code-analysis phase inserts as **Phase 1b**, triggered conditionally between Phase 1 and Phase 2, when the doc-sufficiency check fails.

**Q2 — How to decide whether docs are sufficient?**

The agent's `## Depth Requirements` section already defines what "sufficient" means for the Architecture section:
- Core components and their relationships (with exact names from source)
- Data flow or execution model
- Extension or integration points

A doc-sufficiency check after Phase 1 evaluates whether any of these three criteria cannot be satisfied from the extracted passages. If all three are satisfiable from docs, code analysis is skipped. If any criterion is unsatisfied, code analysis runs.

This is an observable, deterministic gate — not a subjective judgment. The agent checks: "Do my extracted passages contain component names from source? Do they describe a data flow? Do they name extension points?" If any answer is no, the gate opens.

**Q3 — Which source files to examine?**

No heuristic exists in any current file. Three file-pattern tiers derivable from standard repo structures:

1. **Entrypoints** (define what the tool exposes): `package.json` → `main`, `exports`, `bin` fields; `pyproject.toml` → `[project.scripts]`, `[project.entry-points]`; `Cargo.toml` → `[[bin]]`, `[lib]`
2. **Type/schema declarations** (define data structures): `*.schema.json`, `*.schema.ts`, `*.types.ts`, `*.d.ts`, `schema.py`, `types.py`, `models.py`
3. **Index/barrel files** (expose public API): `src/index.ts`, `src/index.js`, `src/__init__.py`, `src/lib.rs`, `src/mod.rs`

**Model constraint observed**: The agent runs on Haiku. Code analysis adds 10–30 additional `Read`/`Glob`/`Grep` tool calls. The planning phase must set a file-count ceiling (e.g., max 10 source files per analysis pass) to avoid context exhaustion on Haiku.

</div>

### Resources

<div><sub>2026-03-15T04:45:18Z</sub>


| Type | Item |
|------|------|
| Agent | @research-curator — `.claude/agents/research-curator.md` — the agent being modified |
| Skill | /research-curator — `.claude/skills/research-curator/SKILL.md` — orchestrator |
| Reference | `.claude/skills/research-curator/references/entry-template.md` — entry schema |
| Reference | `.claude/skills/research-curator/references/validation-rules.md` — validation schema |
| Script | `.claude/skills/research-curator/scripts/validate_research.py` — entry validator |
| Agent | @research-insight-extractor — `.claude/agents/research-insight-extractor.md` — downstream consumer of entries |
| Agent | @research-utilization-assessor — `.claude/agents/research-utilization-assessor.md` — downstream consumer |
| Prior work | `.claude/skills/skill-research-process/references/gaps-analysis.md` — identified "Clone + Read for code analysis" as tool #3 in the research toolkit |
| Prior issue | #197 (Enhance skill-research-process for CLI tool skills) — related but distinct; that item covers skill creation, this covers research entries |

</div>

### Dependencies

<div><sub>2026-03-15T04:45:29Z</sub>


- Depends on: None — the shallow clone mechanism is already in place; source files are physically available on disk during every repo research session. No new tooling, infrastructure, or prior item completion required.
- Blocks: Research entries for underdocumented repos; downstream quality of `@research-insight-extractor` and `@research-utilization-assessor` outputs for those entries.
- Related (not blocking): #197 (Enhance skill-research-process for CLI tool skills) — shares the "Clone + Read for code analysis" insight but applies to a different workflow (skill creation vs. research entry creation). Can proceed independently.
- Related (not blocking): #436 (Create NotebookLM MCP server in research-curator skill) — adds research sources but is independent of the doc-sufficiency gate.

</div>

### Blockers

<div><sub>2026-03-15T04:45:42Z</sub>


RT-ICA status: APPROVED — no external blockers.

The three MISSING conditions from RT-ICA are design decisions for the planning phase, not external prerequisites:

1. **Doc-sufficiency heuristic** — the decision gate criteria are derivable from the existing Architecture depth requirements in the agent. The planning phase formalizes these into an explicit checklist.
2. **File-selection heuristic** — the three-tier file pattern approach (entrypoints, schema files, index files) is derivable from standard repo conventions. The planning phase selects which tiers to use and in what order.
3. **Token/time budget for code analysis** — the planning phase sets the ceiling (e.g., max N source files). The Haiku model constraint makes this decision important but does not block grooming.

No external systems, approvals, or prior backlog items need to complete before planning can begin.

</div>

### Effort

<div><sub>2026-03-15T04:45:52Z</sub>


Medium — Changes are confined to one file: `.claude/agents/research-curator.md`. The workflow diagram gains one decision node and one new phase block. The three heuristics (doc-sufficiency check, file-selection tier, depth budget) must be designed and written into the agent instructions. No new scripts, no new validators, no schema changes required. The existing `validate_research.py` and entry template remain unchanged.

Key complexity: the doc-sufficiency check must be expressed as an unambiguous, self-applicable instruction for a Haiku model — the check itself must not require reasoning beyond "do my extracted passages contain X, Y, Z?".

</div>