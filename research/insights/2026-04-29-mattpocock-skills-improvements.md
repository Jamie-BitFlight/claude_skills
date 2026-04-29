# Improvement Proposals: mattpocock/skills

**Research entry**: ./research/skill-generation-tools/mattpocock-skills.md
**Generated**: 2026-04-29
**Patterns assessed**: 5
**Backlog items created**: 4 (to be created via /dh:create-backlog-item)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 0

---

## Improvement 1: Add Anti-Pattern section to skill template and training

**Source pattern**: mattpocock/skills systematically includes Anti-Patterns sections in every skill (tdd/SKILL.md, design-an-interface/SKILL.md, improve-codebase-architecture/SKILL.md). Example: tdd/SKILL.md Anti-Patterns section teaches "do not slice horizontally (all tests first, then all code)"

**Local system**: `./skills/plugin-creator/skill-creator/SKILL.md`

**Confidence**: High

**Impact**: High

**Backlog**: To be created

### Current state

plugin-creator:skill-creator teaches skill structure following philosophy → workflow → checklists pattern. Reading skill-creator/SKILL.md reveals no Anti-Patterns section required or documented in the template. Agents instructed by skill-creator may produce skills lacking explicit warnings about failure modes.

File: `./skills/plugin-creator/skill-creator/SKILL.md` — search for "Anti-Pattern" returns zero results.

### Target state

1. skill-creator/SKILL.md includes Anti-Patterns as a required section in the template structure (after Philosophy, before Workflow)
2. Every skill produced by skill-creator includes a non-empty Anti-Patterns section with explicit warnings about what NOT to do
3. Training in skill-creator emphasizes Anti-Patterns as equivalent in importance to Philosophy

Example: Anti-Patterns section for a new skill should contain "Do NOT [weak pattern that agents commonly apply]" with explicit failure mode consequences.

### Measurable signal

1. Read `./skills/plugin-creator/skill-creator/SKILL.md` — confirms Anti-Patterns section is present and documented as required
2. New skills created with skill-creator include non-empty `## Anti-Patterns` section in SKILL.md
3. Run `grep -r "## Anti-Pattern" ./skills/*/SKILL.md | wc -l` — count rises as existing skills are updated to include Anti-Patterns sections

---

## Improvement 2: Systematize reference file discovery in skill SKILL.md headers

**Source pattern**: mattpocock/skills organizes deep-dive reference materials within skill directories. Example: tdd/SKILL.md contains YAML frontmatter naming the skill; tdd/ directory contains mocking.md, interface-design.md, refactoring.md, tests.md, deep-modules.md as embedded references. Agents discover and load references automatically.

**Local system**: `./skills/` directory structure and SKILL.md frontmatter convention

**Confidence**: High

**Impact**: Medium

**Backlog**: To be created

### Current state

claude_skills has references/ subdirectories in some skills (e.g., `./skills/plugin-creator/skill-creator/references/`) containing thematic guides. However, SKILL.md does not declare available references in frontmatter or body header. Agents must manually Read reference file paths or rely on glob searches to discover references. This creates friction: agents may miss valuable context.

File: `./skills/plugin-creator/skill-creator/SKILL.md` — no References or "See Also" section declaring available references in references/ subdirectory.

### Target state

1. SKILL.md header includes a References section naming and linking each available reference file. Example: `## References\n- [Skill Frontmatter Validation](./references/frontmatter-validation.md)\n- [Anti-Pattern Library](./references/anti-patterns.md)`
2. skill-creator template includes References field in the example skill output
3. Agents are trained to read references/ directory automatically when loading a skill

### Measurable signal

1. Read `./skills/plugin-creator/skill-creator/SKILL.md` — confirms References section is present and lists each file in `./skills/plugin-creator/skill-creator/references/`
2. New skills created with skill-creator include References section in SKILL.md
3. Run `grep -l "## References" ./skills/*/SKILL.md | wc -l` — count of reference-aware skills rises
4. Validate: for each skill with References section, all listed files exist at the declared paths

---

## Improvement 3: Document skill tools: field semantics and discovery rules

**Source pattern**: mattpocock/skills skills declare required tools in frontmatter and descriptions. Example: tdd/SKILL.md requires npm, test framework; to-issues/SKILL.md requires gh CLI; obsidian-vault/SKILL.md requires Obsidian vault access. This enables skill discovery and agent routing: agents can check tool availability before attempting a skill.

**Local system**: `./.claude/rules/frontmatter-requirements.md` and `./.claude-plugin/plugin.json`

**Confidence**: High

**Impact**: Medium

**Backlog**: To be created

### Current state

frontmatter-requirements.md documents the syntax of the `tools:` field (comma-separated string, not YAML array) but provides no guidance on:
1. When `tools:` field is required vs. optional
2. How `tools:` field drives skill discovery and agent routing
3. Relationship between `tools:` field and skill prerequisites or availability checks

Example: Reading frontmatter-requirements.md, the tools field is documented as "Must be comma-separated string" but no section explains "declare tools: when a skill requires external CLI, service integration, or ecosystem-specific commands."

### Target state

1. frontmatter-requirements.md includes `tools:` field semantics section with examples: "Declare tools: field if the skill requires a CLI tool (npm, gh, git), external service (GitHub API, Obsidian vault), or ecosystem-specific command"
2. skill-creator template includes example `tools:` field with explanatory comments
3. Skill discovery logic (agents selecting which skill to load) references `tools:` field for availability checks
4. Training in skill-creator emphasizes: "tools: field is your skill's contract about what must be available"

### Measurable signal

1. Read `./.claude/rules/frontmatter-requirements.md` — confirms `tools:` field semantics section is present with examples
2. Read `./skills/plugin-creator/skill-creator/SKILL.md` — confirms template includes example `tools:` field with comments
3. Run `grep -c "tools:" ./skills/*/SKILL.md` — count of skills declaring tools (audit baseline)
4. Skill discovery system can parse and evaluate `tools:` field to check availability

---

## Improvement 4: Create parallel exploration pattern guide for sub-agent dispatch

**Source pattern**: mattpocock's design-an-interface skill explicitly spawns 3+ parallel sub-agents with different constraints (simplicity, flexibility, efficiency, depth trade-offs) to explore design space rapidly. Skill workflow: "Instead of one agent designing an interface, spawn 3 agents in parallel, each optimizing for a different constraint. Compare designs on simplicity, flexibility, efficiency, depth. Choose the best approach."

**Local system**: `./skills/swarm-operations/SKILL.md` and agent orchestration patterns

**Confidence**: Medium

**Impact**: Medium

**Backlog**: To be created

### Current state

swarm-operations/SKILL.md teaches parallel task execution (multiple independent jobs running simultaneously) but focuses on throughput and completion time, not exploration. Pattern taught: "Run N tasks in parallel to speed up work." Missing pattern: "Spawn N agents with different constraints to explore a solution space and surface multiple viable approaches."

Agents default to sequential analysis (form hypothesis → test → refine) when parallel exploration would surface trade-offs faster. Example: designing a system, agents might converge on one architecture design. With parallel exploration, 3 agents exploring simplicity, performance, extensibility constraints simultaneously would reveal all three as viable, enabling informed trade-off discussion.

### Target state

1. Create reference guide: `./skills/swarm-operations/references/parallel-exploration-pattern.md` documenting when and how to spawn parallel sub-agents for exploration
2. Update `./skills/swarm-operations/SKILL.md` to include Exploration Workflows section alongside Execution Workflows section
3. Provide constraint specification template: "For each sub-agent, define constraint boundaries (e.g., minimize interface size, maximize flexibility, maximize performance)"
4. Teach evaluation across multiple dimensions: "Compare outputs on dimension X, Y, Z; do not force convergence to one solution"

### Measurable signal

1. Read `./skills/swarm-operations/references/parallel-exploration-pattern.md` — confirms file is present with use-case examples (design space, optimization approaches, testing strategies)
2. Read `./skills/swarm-operations/SKILL.md` — confirms Exploration Workflows section is present with at least one worked example
3. New skills and agents document parallel exploration as applicable to their domain (design skills, optimization skills)

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---------|-----------|--------|
| Domain-aware guidance integration (CONTEXT.md, ADR format) | Medium | improve-codebase-architecture in mattpocock/skills integrates CONTEXT.md and docs/adr/. Local system has `.claude/rules/` context files but CONTEXT.md integration not verified in existing skills. Would need to audit specific skills to confirm gap. Recommend: check `/dh:improve-codebase-architecture` agent implementation to determine if CONTEXT.md awareness already exists before creating backlog item. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---------|---|
| Skill distribution via npm package manager | mattpocock/skills distributed via `npx skills@latest add mattpocock/skills/tdd`. claude_skills distributed via GitHub + plugin marketplace. Different distribution models appropriate to each repository's scope and audience. No actionable improvement for this repository. |
| Cross-language skill support (Python, Go, Rust) | mattpocock/skills heavily JavaScript/TypeScript-centric. claude_skills is language-agnostic. No gap identified — repository already supports multi-language skills (python3-development, etc.). |

---

## Summary

Four high-confidence improvements identified, all addressing systematization of skill structure and discovery:

1. **Anti-Patterns as required section** — prevents weak pattern application
2. **Reference file discovery** — enables agents to load deep-dive context without friction
3. **Tools field semantics** — enables skill discovery and prerequisite checking
4. **Parallel exploration pattern** — teaches rapid multi-constraint solution space exploration

Growth context (mattpocock/skills): 82% star growth in 2 days; 2 new skills added (diagnose, grill-with-docs). This research was triggered by identifying a mature, battle-tested skill collection with clear architectural discipline. Proposals are prioritized to address scale: as claude_skills grows beyond 60+ skills, systematization of structure (anti-patterns, references, tools declarations) becomes critical for agent navigation and skill discovery.
