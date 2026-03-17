# Improvement Proposals: Awesome AI Apps

**Research entry**: ./research/ai-research-tools/awesome-ai-apps.md
**Generated**: 2026-03-17
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Persistent agent memory across sessions

**Source pattern**: "Memory agent examples using GibsonAI Memori demonstrate: Long-term memory fabric for context retention, Preference tracking across conversations, Style consistency in multi-turn interactions, Fact accumulation in research workflows" (Section: Relevance to Claude Code Development, subsection 4)
**Local system**: CLAUDE.md (context management), `.claude/rules/`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence Low: the research entry describes the pattern at a high level ("could adopt similar memory patterns") without naming a concrete mechanism. The local system already has per-project memory via agent `memory: project` frontmatter, and the `claude-mem` MCP search plugin provides observation storage. Whether GibsonAI Memori's "memory fabric" approach offers something materially different from the existing `claude-mem` plugin cannot be determined from the research entry alone.

### Current state

The repo has two memory mechanisms: (1) agent-level `memory: project` frontmatter that persists agent observations within a project scope, and (2) the `claude-mem` MCP plugin providing `get_observations`, `search`, `smart_search`, `smart_outline`, `smart_unfold`, and `timeline` tools. Neither mechanism is documented as providing cross-session preference tracking or style consistency enforcement as described in the GibsonAI Memori examples.

### Target state

A memory layer that explicitly tracks user preferences, coding style patterns, and accumulated facts across sessions -- accessible to all agents during task execution. The specific implementation mechanism is undefined because the research entry does not describe GibsonAI Memori's API or storage model in enough detail to map to a concrete file change.

### Measurable signal

Cannot be defined without a concrete implementation specification. Would require: (1) a preference/style store queryable by agents, (2) evidence that agents use stored preferences to modify output, (3) persistence verified across separate Claude Code sessions.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Persistent agent memory across sessions | Low | Research entry describes GibsonAI Memori at high level only; local system already has `claude-mem` MCP plugin and `memory: project` -- need concrete comparison of capabilities to determine if a gap exists |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-Framework Comparison Reference | Too abstract -- the research entry describes "evaluating which frameworks best fit feature requirements" as a general reference value, not a concrete mechanism to adopt. This repo is Claude Code-specific and does not need framework-agnostic agent abstractions. |
| Production Agent Patterns (Observability) | Already tracked in backlog as #109 "SAM: Audit Trail / Observability" (P2). Guardrails and human-in-the-loop suggestions are philosophical ("these patterns inform the design") with no concrete mechanism named. Temporal durable workflows are architecture-incompatible -- SAM uses file-based state, not a workflow engine. |
| MCP Server Design Inspiration | Already covered in `plugins/fastmcp-creator/skills/fastmcp-creator/SKILL.md` which provides comprehensive MCP server creation guidance including server-core, providers, transforms, auth, testing, deployment, and real-world patterns. The research entry's MCP examples (GitHub, Docker, Couchbase servers) are application instances, not design patterns absent from the skill. |
| Course-Based Learning Structure | Too abstract -- "progressive complexity tutorials" is a pedagogical philosophy applicable to any documentation project, not a concrete mechanism that maps to a specific file or behavior change in this repo. |
