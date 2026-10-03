# Improvement Proposals: coop

**Research entry**: ./research/agent-infrastructure/coop.md
**Generated**: 2026-10-03
**Patterns assessed**: 2
**Backlog items created**: 0 (issues: none)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 1

Backlog duplicate check could not run: `backlog_list` returned a GraphQL-unavailable error in this session, and the backlog server instructions require stopping on a failed call. No backlog item was created; none of the proposals below reached High confidence in any case.

---

## Improvement 1: VM-level isolation option for write-capable dispatched agents

**Source pattern**: Relevance to Claude Code Development > Integration Opportunities, Item 1 ("Isolated agent execution" -> `rules/commit-cadence-and-worktrees.md`). The entry says coop's VM boundary is "a different isolation tier that this file does not mention" and that adding a note "would only be warranted if an orchestrator is written to launch agents through `coop claude`; no such launcher exists in the paths searched".
**Local system**: /home/user/claude_skills/rules/commit-cadence-and-worktrees.md (opened); /home/user/claude_skills/plugins/agent-orchestration/skills/ contains `delegate` and `parallel-work`.
**Absence evidence**: `git grep -il -E "microvm|firecracker|limactl|trailofbits/coop" -- plugins/ .claude/skills/ .claude/agents/ rules/ AGENTS.md ARCHITECTURE.md` -> 0 matches; `git grep -il -E "isolated (vm|virtual machine)|devcontainer|docker sandbox" -- plugins/ .claude/skills/ .claude/agents/ rules/` -> 0 matches.
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence Low: the entry's Item 1 conditions any change on an orchestrator that launches agents through `coop claude`, and none exists in the paths it searched; the local worktree rule solves a different problem.

### Current state

`rules/commit-cadence-and-worktrees.md` uses `Agent(isolation: "worktree")` to remove same-tree stash collisions between concurrent writers. Its stated goal is race-condition avoidance, not a security boundary. No local file references VM isolation.

### Target state

Undetermined. The entry does not say what interface a Claude Code workflow would use to spawn a coop instance, so no observable file-level target can be written without inventing one.

### Measurable signal

Not definable until a concrete spawn/sync interface is identified (for example, whether `coop claude` can be invoked non-interactively with a task prompt and a result retrieved via `coop pull`). That would need a primary-source check of coop's docs.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| VM isolation for write-capable agents | low | Entry conditions the change on a `coop claude` launcher that does not exist; verify coop's non-interactive invocation and result retrieval against its docs before proposing a target state. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Typestate / `boot_preflight` choke point, instance operation lock, secret-never-on-argv, Sigstore update verification | Described in the entry's Technical Architecture and Key Features sections (the entry's sections are Overview, Problem Addressed, Key Features, Technical Architecture, Installation & Usage, Relevance to Claude Code Development, Limitations and Caveats, References, Cross-References), not in Relevance to Claude Code Development. They are Rust-CLI internals with no concrete mapped local system; same reasoning as the HolyClaude entry's skipped infrastructure patterns (`research/insights/2026-03-28-holyclaude-improvements.md`). |
