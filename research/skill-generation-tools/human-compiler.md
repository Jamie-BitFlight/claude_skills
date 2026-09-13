---
name: HumanCompiler
description: HumanCompiler is a Claude Code plugin that "compiles" a human into an installable AI agent plugin by conducting an 8-phase deep behavioral interview combined with MCP-powered analysis of real work...
license: MIT
metadata:
  topic: human-compiler
  category: skill-generation-tools
  source_url: https://github.com/Gerstep/HumanCompiler
  github: Gerstep/HumanCompiler
  version: "v0.1.0"
  verified: "2026-02-19"
  next_review: "2026-05-19"
---

## Overview

HumanCompiler is a Claude Code plugin that "compiles" a human into an installable AI agent plugin by conducting an 8-phase deep behavioral interview combined with MCP-powered analysis of real work artifacts (Notion docs, Asana tasks, local files). It generates a complete Claude Code plugin package with autonomous and advisory agent variants that authentically embody the interviewed person's communication style, decision-making framework, and domain expertise. The tool targets knowledge workers and teams who want AI agents that replicate a specific person's judgment rather than a generic AI persona.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| Generic AI agents lack individual voice and judgment style | 8-phase interview captures decision frameworks, communication patterns, and vocabulary specific to one person |
| Interview answers may not reflect actual behavior | MCP artifact analysis cross-references interview data against real Notion docs, Asana tasks, and transcripts |
| Agent generation from scratch is technically complex | Handlebars-templated plugin generator produces a complete Claude Code plugin structure (manifest, agents, skills, CLAUDE.md) from a YAML behavioral profile |
| Long interviews risk data loss if interrupted | Progressive phase-by-phase saving with resume capability via `bun run scripts/profile-manager-cli.ts` |
| One agent mode does not fit all use cases | Generates both autonomous mode (full `acceptEdits`) and advisory mode (read-only `plan`) agents from the same profile |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 6 | 2026-02-19 |
| Forks | 1 | 2026-02-19 |
| Contributors | 1 | 2026-02-19 |
| Open Issues | 0 | 2026-02-19 |
| Latest Release | No releases — v0.1.0 in package.json | 2026-02-19 |
| Repository Created | 2026-02-16 | 2026-02-19 |
| Last Push | 2026-02-17 | 2026-02-19 |
| Primary Language | TypeScript | 2026-02-19 |

---

## Key Features

### Structured 8-Phase Behavioral Interview

- Phase 1 — Identity: role, org context, responsibilities, goals
- Phase 2 — Communication: writing style, tone spectrum, characteristic vocabulary
- Phase 3 — Decision-Making: frameworks, prioritization logic, uncertainty handling, tradeoff patterns
- Phase 4 — Domain Expertise: depth map across technical and industry knowledge areas
- Phase 5 — Work Patterns: daily routine, tooling, collaboration style, meeting behavior
- Phase 6 — Edge Cases: conflict resolution, ambiguity handling, failure response, pressure behavior
- Phase 7 — Artifact Analysis: deep reading of 5-10 real work products via MCP tools
- Phase 8 — Calibration: full profile review, corrections, confidence scoring

### MCP-Powered Work Artifact Integration

- Searches Notion for documents, meeting notes, and strategy docs to inform questions
- Queries Asana tasks and projects for work pattern evidence
- Cross-references artifact findings with interview answers to detect gaps or contradictions
- Graceful fallback to direct questions when MCP tools are unavailable

### Resumable Interview State

- Saves structured YAML profile data and raw transcripts after every phase
- `profile-manager-cli.ts` provides `init`, `list`, `status`, `save-transcript`, `update-phase`, `mark-complete` operations
- Profile stored at `~/.human-compiler/<name>/profile.yaml` with per-phase `phases/` subdirectory

### Handlebars-Templated Plugin Generation

- Six template files: `plugin.json.hbs`, `agent-autonomous.hbs`, `agent-advisory.hbs`, `skill-ask.hbs`, `skill-task.hbs`, `claude-md.hbs`
- `generate-plugin.ts` renders all templates from the YAML profile into a complete plugin directory
- Output installs directly via `claude --plugin-dir` or Claude Code plugin marketplace

### Dual Autonomy Mode Output

- `<name>-autonomous.md` agent: full `acceptEdits` permission, acts and decides as the person
- `<name>-advisory.md` agent: `plan` mode, recommends in the person's style without executing
- `/ask-<name>` skill: lightweight consultation command for point queries

---

## Technical Architecture

<eg>
Interview Input (human + MCP artifacts)
        │
        ▼
 SKILL.md orchestrator (/compile-human command)
        │ spawns
        ▼
 interviewer.md agent (maxTurns: 50, model: opus)
        │ per-phase execution
        ▼
 phase-instructions/0N-*.md question banks
        │ structured extraction
        ▼
 profile-manager-cli.ts → profile.yaml (YAML)
  ~/.human-compiler/<name>/
  ├── profile.yaml        (behavioral schema)
  ├── phases/             (per-phase transcripts)
  └── artifacts/          (MCP-sourced documents)
        │
        ▼
 generate-plugin.ts + Handlebars templates
        │
        ▼
 output-plugin/<name>-agent/
  ├── .claude-plugin/plugin.json
  ├── agents/<name>-autonomous.md
  ├── agents/<name>-advisory.md
  ├── skills/ask-<name>/SKILL.md
  ├── skills/<domain>-advice-<name>/SKILL.md
  └── CLAUDE.md
</eg>

The orchestrator skill (`disable-model-invocation: true`) routes commands via `$ARGUMENTS` parsing and delegates interview phases to the `interviewer.md` sub-agent. Profile persistence is handled entirely through CLI invocations of `profile-manager-cli.ts` using `bun run`. The generator is a standalone TypeScript script that takes a profile YAML path and writes a complete plugin directory.

---

## Installation & Usage

```bash
# Install plugin for active Claude Code session
claude --plugin-dir /path/to/HumanCompiler

# Install dependencies (requires bun)
bun install
```

```bash
# Start a new interview
/compile-human

# Resume an interrupted interview
/compile-human resume

# Check status of all profiles
/compile-human status

# Force-generate plugin from existing profile
/compile-human generate
```

```bash
# Install the generated agent plugin
claude /plugin install --from ~/.human-compiler/<name>/output-plugin/

# Or test locally
claude --plugin-dir ~/.human-compiler/<name>/output-plugin/

# Run tests
bun test

# Generate plugin from profile directly
bun run scripts/generate-plugin.ts ~/.human-compiler/<name>/profile.yaml
```

---

## Relevance to Claude Code Development

### Applications

- Direct template for building `skill-generation-tools` that produce Claude Code plugins as output rather than consuming them
- Demonstrates `disable-model-invocation: true` pattern in SKILL.md frontmatter for pure orchestrator skills that route to sub-agents
- Validates the pattern of spawning a dedicated interviewer sub-agent (maxTurns: 50) to handle long structured conversations requiring state
- Shows how to pair a skill orchestrator with a TypeScript CLI backend for profile CRUD, keeping skill logic clean and stateless

### Patterns Worth Adopting

- Per-phase instruction file decomposition (`phase-instructions/0N-*.md`) avoids monolithic skill prompts while giving the agent focused context per step
- Profile schema with explicit `calibration` phase (phase 8) as a final review-and-correct loop is applicable to any multi-phase data gathering workflow
- Handlebars templates for code generation decouple template authoring from TypeScript generation logic — directly transferable to any Claude Code plugin generator
- Progressive save-after-every-phase pattern with CLI-managed state prevents data loss in long-running multi-turn tasks
- Dual autonomy output (autonomous + advisory variants) from the same profile is a reusable pattern for any agent that needs different permission modes

### Integration Opportunities

- Could serve as a model for a `/compile-agent` skill that interviews Claude Code users about their workflow to generate personalized skill sets
- The behavioral profile YAML schema could be adapted to capture team conventions and generate project-specific CLAUDE.md files
- The MCP artifact analysis phase (Phase 7) pattern could be extracted as a reusable sub-agent for any skill that needs to synthesize information from connected MCP sources before asking questions
- Handlebars template approach is directly applicable to the `plugin-creator` skill's code generation pipeline

---

## References

- [HumanCompiler GitHub Repository](https://github.com/Gerstep/HumanCompiler) (accessed 2026-02-19)
- [GitHub API: repos/Gerstep/HumanCompiler](https://api.github.com/repos/Gerstep/HumanCompiler) (accessed 2026-02-19)
- [HumanCompiler README.md](https://github.com/Gerstep/HumanCompiler/blob/master/README.md) (accessed 2026-02-19)
- [HumanCompiler SKILL.md](https://github.com/Gerstep/HumanCompiler/blob/master/skills/compile-human/SKILL.md) (accessed 2026-02-19)
- [HumanCompiler interviewer.md agent](https://github.com/Gerstep/HumanCompiler/blob/master/agents/interviewer.md) (accessed 2026-02-19)
- [HumanCompiler plugin.json manifest](https://github.com/Gerstep/HumanCompiler/blob/master/.claude-plugin/plugin.json) (accessed 2026-02-19)
- [HumanCompiler package.json](https://github.com/Gerstep/HumanCompiler/blob/master/package.json) (accessed 2026-02-19)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [raincast](../coding-agents/raincast.md) | coding-agents | referenced by raincast (coding-agents) |
