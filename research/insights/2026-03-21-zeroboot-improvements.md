# Improvement Proposals: Zeroboot

**Research entry**: ./research/agent-infrastructure/zeroboot.md
**Generated**: 2026-03-21
**Patterns assessed**: 5
**Backlog items created**: 0 (issues: none)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 4

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Zeroboot as MCP server backend for sandboxed code execution | Low | The fastmcp-creator skill documents `CodeMode` (experimental) for sandboxed Python execution via transforms. A Zeroboot-backed MCP tool would provide hardware-enforced VM isolation instead of Python-level sandboxing, but: (1) CodeMode already exists as the local sandboxing mechanism, (2) integrating Zeroboot requires external infrastructure (Linux + KVM host) that is outside this repo's control, (3) the research entry's "Relevance" section describes integration at the Claude Code platform level, not at the plugin/skill level this repo manages. To raise confidence: verify whether CodeMode's Python-level sandbox has documented escape vectors that Zeroboot's KVM isolation would close, and confirm that a FastMCP tool wrapping Zeroboot's REST API would be consumed by existing workflows. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Sub-millisecond VM isolation for agent code execution | Architecture incompatible: this repo creates Claude Code plugins (skills, agents, workflows). Code execution sandboxing is a platform-level concern controlled by the Claude Code runtime, not by plugins. No local skill, agent, or workflow file controls which sandbox backend is used for code execution. |
| Batch parallel execution (1000+ concurrent forks) | Domain mismatch: Zeroboot's batch execution runs code snippets in parallel VMs. The local swarm-operations skill (`./plugins/swarm-operations/SKILL.md` -- does not exist; `.claude/skills/swarm-operations/SKILL.md` covers multi-agent orchestration via TeamCreate/SendMessage). These are different abstractions -- agent orchestration vs. code snippet parallelism. No gap exists because the local system does not need VM-level code parallelism. |
| Zero-dependency SDK design pattern | Too abstract: the pattern "use only stdlib for SDK clients" is a design philosophy, not a concrete mechanism. The fastmcp-creator skill already documents SDK/client patterns including transport configuration. No observable gap in a local file. |
| Template customization for pre-loaded libraries | Zeroboot-specific mechanism: Firecracker snapshot templates with pre-loaded Python modules are specific to Zeroboot's architecture. No local system has an analogous concept to extend. This would only be relevant if Zeroboot were adopted as infrastructure, which is itself a deferred proposal. |
| Tool testing in isolated VMs before deployment | Already covered: the fastmcp-python-tests skill (`plugins/fastmcp-creator/skills/fastmcp-python-tests/SKILL.md`) provides pytest-based testing patterns for MCP tools. VM-based isolation for tool testing would require Zeroboot as external infrastructure -- an infrastructure adoption decision, not a skill gap. Additionally, the existing git worktree isolation backlog item (#453 -- `p2-systematic-git-worktree-isolation-for-concurrent-task-agents`) addresses the file-level isolation concern for concurrent agents. |
