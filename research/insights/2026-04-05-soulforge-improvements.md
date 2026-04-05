# Improvement Proposals: SoulForge

**Research entry**: ./research/coding-agents/soulforge.md
**Generated**: 2026-04-05
**Patterns assessed**: 12
**Backlog items created**: 0
**Deferred (low confidence)**: 3
**Skipped (already covered or tracked)**: 9

---

## Improvement 1: File-level edit coordination for parallel swarm agents

**Source pattern**: "AgentBus: in-process coordination layer for parallel subagents. Handles file caching (deduplicated reads across agents), tool result caching (persists across dispatches), edit coordination (serialized writes per file with ownership tracking)" (from research entry, Technical Architecture section, line 56)
**Local system**: .claude/skills/swarm-operations/SKILL.md, .claude/skills/swarm-patterns/SKILL.md
**Confidence**: Medium
**Impact**: High
**Backlog**: Deferred -- confidence medium: the swarm-operations skill documents Claude Code's built-in TeamCreate/SendMessage/TaskCreate/TaskUpdate tools, which are platform APIs not extensible by this repo. File-level edit coordination would need to be a platform feature or an MCP-based coordination layer. The gap is real but the implementation path requires either a new MCP server or changes to Claude Code's swarm runtime, neither of which can be confirmed as feasible from reading the local skill files alone.

### Current state

The swarm-operations SKILL.md documents Agent dispatch with `team_name`, `name`, `prompt`, and `run_in_background` parameters. The swarm-patterns SKILL.md shows Pattern 6 (Coordinated Multi-File Refactoring) where file boundaries are established by convention in the prompt text ("Claim task #1, refactor the User model"). There is no mechanism for file ownership tracking, serialized writes per file, or deduplication of reads across agents. Two agents dispatched to overlapping files will both read and write independently, risking conflicts.

### Target state

Swarm dispatch includes a file claim mechanism: each agent declares which files it intends to edit (either in TaskCreate metadata or via an MCP tool). Other agents querying the same file see a warning or are blocked from writing until ownership is released. Reads of the same file by multiple agents are served from a shared cache rather than each agent reading independently.

### Measurable signal

Swarm-patterns SKILL.md includes a pattern demonstrating file ownership claims. An MCP tool or convention exists where agents can query "which files are claimed by other agents" before editing. Running a parallel swarm where two agents target the same file produces a coordination warning rather than silent conflict.

---

## Improvement 2: Dispatch validation requiring explicit file paths

**Source pattern**: "Schema enforcement for dispatch: Require explicit targetFiles with real paths on subagent dispatch. Prevents hallucinated file paths." (from research entry, Patterns Worth Adopting section, line 290)
**Local system**: .claude/skills/swarm-operations/SKILL.md, .claude/skills/swarm-patterns/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the swarm-patterns SKILL.md shows dispatch prompts containing file references as free text strings within the `prompt` parameter. Whether Claude Code's Agent tool supports structured `targetFiles` parameters is not confirmed from reading the local files. The SKILL.md documents the tool API as it exists in Claude Code v2.1.45, and the Agent tool schema does not include a `targetFiles` field. Implementing this would require either extending the Agent tool (platform change) or adding a pre-dispatch validation step as a convention in the skill documentation.

### Current state

Swarm-patterns SKILL.md Pattern 6 (line 229-275) shows agent dispatch with file references embedded in free-text prompts: `"Claim task #1, refactor the User model"`. There is no structured field for target files, no validation that referenced files exist, and no prevention of hallucinated file paths in dispatch prompts.

### Target state

Agent dispatch prompts in swarm-patterns include a convention or structured pattern where target files are validated before dispatch. Either: (a) a pre-dispatch step using Glob/Read to confirm file existence before including paths in prompts, or (b) a TaskCreate convention where `description` includes validated file paths in a parseable format.

### Measurable signal

Swarm-patterns SKILL.md includes guidance that file paths in dispatch prompts must be verified with Glob or Read before dispatch. At least one pattern demonstrates this pre-validation step explicitly.

---

## Improvement 3: Git co-change analysis for context gathering

**Source pattern**: "Cochange analysis: Parse git log to find files always edited together. Captures implicit coupling that import graphs miss." (from research entry, Patterns Worth Adopting section, line 288)
**Local system**: .claude/agents/research-context-agent.md (context management), CLAUDE.md (no codebase indexing)
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred -- confidence low: the research entry describes a concrete mechanism (parse git log --name-only for last 300 commits, record pairwise file combinations in commits with 2-20 files). However, the local system that would benefit -- context-gathering agents -- was not fully examined. The context-gathering agent may already use git log as part of its process, and the co-change data would need a consumer (a skill or agent that acts on coupling data). The gap is inferred rather than directly observed in a specific local file.

### Current state

No local skill, agent, or script parses git commit history to identify files that are frequently co-edited. Context-gathering relies on explicit file reads and grep-based discovery. Implicit coupling (files that change together but do not import each other) is invisible to the current system.

### Target state

A skill or MCP tool accepts a file path and returns its top co-change partners from git history. Context-gathering agents use this data to include related files when building context for a task involving a specific file.

### Measurable signal

Running a command like `uv run cochange.py src/core/agents/forge.ts` returns a ranked list of files most frequently co-edited with the input file, based on git log analysis.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| File-level edit coordination for parallel swarm agents | medium | Need to confirm whether Claude Code's swarm runtime supports custom coordination layers or whether an MCP-based approach is feasible within the platform constraints |
| Dispatch validation requiring explicit file paths | medium | Need to confirm whether the Agent tool schema can be extended or whether validation must be convention-only in skill documentation |
| Git co-change analysis for context gathering | low | Need to examine context-gathering agent fully and confirm no equivalent exists; need to identify a concrete consumer for co-change data |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Live repo graphs with incremental updates | Requires building new infrastructure (SQLite-backed graph, tree-sitter parsing, PageRank). Not an extension of any existing local system -- would be a new system entirely. Too large for a skill improvement. |
| Budget scaling (token budget inversely with conversation length) | Runtime behavior of the LLM client, not extensible via skills or plugins in this repo |
| Semantic summaries cached by mtime | Requires runtime codebase indexing infrastructure that does not exist locally |
| Dual-backend architecture for LSP | This repo does not run LSP servers; pattern is not applicable |
| Task routing per-task model assignment | Already covered by .claude/rules/model-selection.md which maps cognitive task type to model tier (haiku/sonnet/opus). SoulForge uses named slots (spark/ember) but the underlying principle is equivalent. |
| MCP server extraction (@soulforge/mcp) | Integration opportunity for consuming SoulForge's tools, not an improvement to existing local systems. Already covered in the utilization file at research/insights/2026-04-05-soulforge-utilization.md |
| Prompt caching strategy | Runtime concern for the LLM provider layer, not extensible via this repo's skills or plugins |
| Real-time project detection | No existing local system to extend; would be a new capability rather than an improvement |
| Thinking mode configuration | Runtime concern for Claude Code client, not extensible via skills or plugins |
