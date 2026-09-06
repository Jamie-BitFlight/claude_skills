---
name: optimize-claude-md
description: "Optimize existing CLAUDE.md, SKILL.md, agent definitions, and other AI-facing files for Claude comprehension and economy. Scope: optimization of existing content only — not upstream sync, not read-only auditing. Measures baseline metrics, delegates to @ai-doc-optimizer agent with file-type-specific context, runs independent verification via second agent, measures post-optimization metrics, and presents comprehensive before/after report. Supports iterative mode for large targets. Use when improving prompt effectiveness, reducing token waste, or rewriting instructions for LLM consumption. Invoke with /optimize-claude-md <file-or-directory>."
argument-hint: <file-or-directory-path>
user-invocable: true
---
If the user's intent does not match the purpose of this skill, load `plugin-lifecycle` to route to the right skill and process: `Skill(skill="plugin-creator:plugin-lifecycle")`.

# Optimize AI-Facing Files

Orchestrate multi-phase optimization of AI-facing documentation with measurement, delegation, verification, and comprehensive reporting.

## Invocation

```text
/optimize-claude-md <path>
```

Where `<path>` is one of:

- A single file (e.g., `./CLAUDE.md`, `.claude/skills/my-skill/SKILL.md`, `.claude/agents/my-agent.md`)
- A skill directory (e.g., `.claude/skills/my-skill/`) — optimizes SKILL.md and all reference files
- A plugin directory (e.g., `plugins/my-plugin/`) — optimizes CLAUDE.md, all skills, and all agents

## Process

`${CLAUDE_PLUGIN_ROOT}/docs/runtime-environment.md` contains the two audiences, the environment split, and the three-part check; read it before optimizing a plugin's runtime text, because a path that resolves in the authoring repo fails for every installed consumer.

<user_provided_target>$ARGUMENTS</user_provided_target>
<PWD> !`pwd` </PWD>

### Phase 1: Validate Target

If `<user_provided_target>` is empty, ask the user for a target path before proceeding.

If `<user_provided_target>` is not an absolute path, prepend the value of `<PWD>` to produce the absolute path. Use that absolute path for all subsequent operations.

Verify the resolved absolute path exists. Determine scope (single file, skill directory, or plugin directory).

Recognize these file types: `CLAUDE.md`, `AGENTS.md`, `SKILL.md`, agent definition (`.md` in `agents/`), reference file (`.md` in `references/`). Both `CLAUDE.md` and `AGENTS.md` are index files — apply index discipline checks in Phase 2.

### Phase 2: Measure Baseline

**For all files**:

- Determine file type (`CLAUDE.md`, `AGENTS.md`, `SKILL.md`, agent definition, reference file)
- Measure token count: `uvx skilllint@latest check --tokens-only <file>`
- Record baseline token count

**For SKILL.md files only**:

- Run completeness score evaluation (8-category assessment from /plugin-creator:audit-skill-completeness)
- Record baseline completeness score (format: X/24)
- Resolve the skill's goals — use `<target-skill>/SKILL-GOALS.md` if present, otherwise activate the `/plugin-creator:skill-goal-extractor` skill against the skill directory. Record the goals; they are passed into delegation and are the standard every later phase judges changes against.
- Offer a `/plugin-creator:evaluate-and-tighten-skills` pass before optimizing. Tightening decides what content earns its place; optimization decides how the survivors read. Running them in that order avoids polishing prose that a tightening pass would delete. Skip the offer only when the skill was tightened against these same goals already.

**For CLAUDE.md and AGENTS.md files** — run index discipline audit (6 binary checks):

Score = number passing (0–6). Record as `Index: N/6`.

| Check | Pass condition |
|-------|---------------|
| Entry length | All entries ≤ ~150 chars |
| No procedure steps | No entry contains numbered steps or multi-sentence procedures |
| Operative-fact hooks | All hooks state the rule/constraint/value directly; no entry contains "Load when" |
| No inline processes | No substantial process/protocol body appears directly inline |
| No stale routes | All linked `docs/` files exist at the referenced paths |
| No missing routes | All `docs/` files have a corresponding router entry |

**Record all metrics** for reporting.

### Phase 3: Delegate to @ai-doc-optimizer

Spawn the optimization agent via Agent tool with the delegation template below.

The agent owns its own process — RT-ICA, the optimization principles (via its preloaded
`prompt-optimization` skill), file-type strategies, CoVe, token-impact reporting, and its DONE/
BLOCKED contract are all defined in the agent. Pass only what the agent cannot derive on its own:
the target, the measurements taken in Phase 2, and the references this skill owns. Restating the
agent's process here creates a second copy that drifts from the agent's own definition.

<delegation_template>

```text
TARGET: {resolved path(s)}
FILE TYPE: {CLAUDE.md | SKILL.md | agent definition | reference file}
BASELINE TOKEN COUNT: {N tokens}
BASELINE COMPLETENESS SCORE: {X/24} (SKILL.md only)
BASELINE INDEX SCORE: {N/6} (CLAUDE.md/AGENTS.md only)
RESOLVED GOALS: {goals from Phase 2, with their source} (skill targets only)

TASK:
Optimize the target per your defined process. Judge every transformation against the resolved
goals above — a goal must be left as well-supported as it was.

CONSTRAINTS:
- For CLAUDE.md and AGENTS.md: read `${CLAUDE_SKILL_DIR}/references/index-discipline.md` before analyzing — this is the index routing reference; CLAUDE.md/AGENTS.md are indexes, not encyclopedias
- For CLAUDE.md and AGENTS.md: apply the 6-check index audit (entry length ≤150 chars; no procedure steps in entries; operative-fact hooks — no "Load when X", hook states the rule directly; no inline processes/protocols; no stale routes; no missing routes) — each violation is a quality failure at the same level as missing commands or vague instructions
- For CLAUDE.md and AGENTS.md: when an inline process/protocol is found, produce the two-step atomic output: (a) the `docs/<slug>.md` file with `name/description/metadata.type` frontmatter + full content, (b) the replacement one-line router entry stating the operative fact — use the discriminator flowchart in `index-discipline.md` to choose between `docs/` and `.claude/rules/` extraction
- For CLAUDE.md and AGENTS.md: use the baseline Index score (N/6) to prioritize — a score below 4/6 means index discipline is the primary optimization target before any other transformation
- For CLAUDE.md: read `${CLAUDE_SKILL_DIR}/references/claude-rules-extraction.md` before analyzing; perform path-scoped rules extraction phase after optimization analysis, before CoVe — path-scoped content (Python rules, CI yml, TypeScript) goes to `.claude/rules/`, not `docs/`
- For CLAUDE.md: flag any knowledge claim whose only home is a non-versioned artifact (chat, Google Docs, people's heads) — it is invisible to agents; external URLs with `SOURCE:` citations are the correct form and are not flagged
- For CLAUDE.md: flag any cross-links not validated by a linter or CI check — mechanical enforcement (linters, freshness checks, cross-link validation) is the only reliable guard against doc drift

Report in your defined output structure.
```

</delegation_template>

SOURCE (three CLAUDE.md-specific constraints above): OpenAI Harness Engineering, "Harness engineering: leveraging Codex in an agent-first world" (<https://openai.com/index/harness-engineering/>, accessed 2026-06-04) — empirically validated failure modes: P1 map-not-manual, P2 docs-as-system-of-record, P4 versioned-local-auditable, P5 mechanical-enforcement. P3 (progressive disclosure) is already enforced by this skill's iterative passes and SK006 extraction threshold.

Routing by concern:
- Establish what a skill exists to achieve, before judging any of its content → `/plugin-creator:skill-goal-extractor`
- Remove content that does not serve those goals (decides whether text exists) → `/plugin-creator:evaluate-and-tighten-skills` — run before optimizing
- Optimize existing content (decides how surviving text reads — clarity, structure, Anthropic prompt engineering principles) → `plugin-creator:ai-doc-optimizer` (this skill uses this path)
- Audit quality (read-only, no writes, score against completeness categories) → `plugin-creator:skill-auditor`
- Sync content against upstream docs (add NEW/fix STALE from live sources) → `plugin-creator:skill-content-updater`
- Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly

### Phase 4: Handle Agent Response

**If agent signals BLOCKED**:

- Present the blocking reason to the user
- Ask for resolution (missing inputs, clarifications, or constraints)
- Wait for user input
- Re-delegate with additional context once blocker is resolved

**If agent signals DONE**:

- Write the agent's "Optimized Content" output to `.tmp/scratch/optimized-{basename}` (where `{basename}` is the target filename, e.g. `SKILL.md` → `optimized-SKILL.md`). Create `.tmp/scratch/` if absent.
- Proceed to Phase 5 (Independent Verification) — use `.tmp/scratch/optimized-{basename}` as `{path to optimized version}`

### Phase 5: Independent Verification

Spawn a SECOND agent (general-purpose, NOT the same agent that optimized) to verify optimization quality.

**Verification Template**:

```text
ORIGINAL FILE: {path to original}
OPTIMIZED FILE: {path to optimized version}

TASK:
Compare the original and optimized files. Verify:

1. Original intent preserved — no functional behaviors lost
2. Technical terms exact — tool names, file paths, command syntax unchanged
3. Structural conventions maintained — frontmatter format, heading hierarchy intact
4. No regressions introduced — edge cases still handled, constraints still enforced

CONSTRAINTS:
- You have NO context from the optimization process
- Base verification ONLY on comparing the two files
- Report any regressions, ambiguities, or losses of specificity
- Signal PASS if optimization preserves all original intent
- Signal REGRESSION if any functional behavior was lost or technical terms changed incorrectly

OUTPUT:
- Verification Status: PASS or REGRESSION
- Regressions Found (if any) with line number references
- Preserved Behaviors (summary)
```

**Handle verification result**:

- If PASS: proceed to Phase 6
- If REGRESSION: present regression details to user, offer to revise or keep original

### Phase 6: Measure Output

**For all files**:

- Measure post-optimization token count: `uvx skilllint@latest check --tokens-only .tmp/scratch/optimized-{basename}`
- Calculate delta: `(post - baseline) / baseline * 100`

**For SKILL.md files only**:

- Run post-optimization completeness score
- Calculate delta: `post - baseline` (absolute change)

**For CLAUDE.md and AGENTS.md files**:

- Re-run the 6-check index audit on the optimized file
- Record post-optimization Index score (N/6) and delta

**Record all metrics** for reporting.

### Phase 7: Present Comprehensive Report

Report to user with structure:

```text
## Optimization Report: {filename}

### Baseline Metrics
- Token Count: {N tokens}
- Completeness Score: {X/24} (SKILL.md only)
- Index Discipline Score: {N/6} (CLAUDE.md/AGENTS.md only)

### Post-Optimization Metrics
- Token Count: {M tokens} ({+/-Y%})
- Completeness Score: {Z/24} (delta: {+/-D}) (SKILL.md only)
- Index Discipline Score: {N/6} (delta: {+/-D}) (CLAUDE.md/AGENTS.md only)

### Changes Applied
{List of transformations with principle citations from agent report}

### CoVe Verification Results
{Agent's falsifiable verification questions and answers}

### Independent Verification
- Status: {PASS | REGRESSION}
- {Regression details if any}

### Structural Upgrade Candidates
{Sections that could benefit from decision flows, tables, checklists}

### Before/After Diff
{Diff output showing exact changes}

### Recommendation
{Proceed with optimization | Revise based on regressions | Keep original}
```

### Phase 8: Apply on Approval

Write optimized content ONLY after user confirms. Do not auto-apply.

On user approval: overwrite the original target path with the content from `.tmp/scratch/optimized-{basename}`, then delete the temp file.

## Iterative Mode for Large Targets

For files exceeding `TOKEN_WARNING_THRESHOLD` (defined in `skilllint`) or plugin directories, offer iterative optimization:

**Pass 1: Structural Changes**

- Reorganize sections for front-loaded priorities
- Split large sections to references/ subdirectory
- Add decision flow diagrams, tables, checklists
- Measure token count after structural changes

**Pass 2: Content Optimization**

- Apply positive framing (replace prohibitions with directives)
- Add motivations and concrete examples
- Compress verbose explanations without losing clarity
- Measure token count after content changes

**Pass 3: Polish**

- Optimize frontmatter (description compression, argument hints)
- Verify cross-references between files
- Ensure format consistency (code fence language specifiers, markdown links)
- Final measurement

**Convergence**: Terminate when completeness score stops improving between passes (delta <1 point) or token reduction plateaus (delta <2%).

## Scope Expansion Rules

When target is a **skill directory**:

1. Optimize SKILL.md (primary)
2. Optimize each file in `references/` (secondary)
3. Verify cross-references between SKILL.md and reference files remain valid

When target is a **plugin directory**:

1. Optimize CLAUDE.md if present (primary)
2. List all skills and agents — ask user which to include
3. Apply iterative mode: one pass per selected component
4. Verify plugin.json references remain consistent

## Edge Cases

- **File not found**: Report exact path checked, ask user to confirm
- **Binary or non-markdown file**: Skip with explanation
- **Already optimal**: Acknowledge effectiveness, suggest only minor refinements per agent constraint
- **Large file (exceeds `TOKEN_WARNING_THRESHOLD`)**: Offer iterative mode with multi-pass optimization
- **Agent returns BLOCKED**: Present blocking reason to user with specific questions
- **Independent verification finds regression**: Report regression, offer to revise or keep original
- **Token count increases**: Report reason (added examples, motivations, or structure), verify completeness score improved to justify expansion
- **Completeness score decreases**: Signal regression, recommend keeping original or revising optimization strategy
