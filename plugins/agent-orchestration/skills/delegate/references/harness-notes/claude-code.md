# Harness notes — Claude Code

Open this when running in Claude Code. Nothing here changes the rules in `delegate` or `parallel-work`; it maps them onto Claude Code's mechanics.

## Dispatching

- A sub-agent is an `Agent` tool call with `subagent_type` and `prompt`. Several `Agent` calls in one assistant turn run concurrently; that is the fan-out mechanism. [1]
- `subagent_type` is a built-in (`general-purpose`, `Explore`, `Plan`), a project agent from `.claude/agents/`, or `plugin:agent-name` for a marketplace agent. [1]
- Sub-agents inherit CLAUDE.md, rules, and tool descriptions. They do not see the orchestrator's conversation and cannot take follow-up questions after they return (unless resumed). Everything they need is in the prompt. [1]
- Sub-agents do not have the `Agent` tool by default. [1] The ROLE_TYPE opener is this skill's own belt-and-braces convention for harnesses where they might.
- Reference the contract by absolute path: `${CLAUDE_PLUGIN_ROOT}/skills/delegate/references/sub-agent-contract.md` resolves inside plugin hooks; in a prompt, paste the resolved path. [2]

## Isolation

- `isolation: worktree` on an `Agent` call gives that sub-agent its own git worktree, branched from the default branch rather than the parent session's `HEAD`. [1] This skill's own convention: use it for every `write` dispatch in a fan-out, since relative paths in the prompt then resolve inside that worktree.
- Completion notifications arrive automatically; Claude waits for one before reporting a sub-agent's results. [1] This skill's own convention: do not poll a running agent's output or read its transcript. If `orchestrator-discipline` is installed, it documents why.

## Enforcement hooks

- If `orchestrator-discipline` is installed, its `pre-tool-block-explore-for-analysis.cjs` hook rejects `Explore` dispatches whose prompt contains reasoning verbs — read that hook's source for the current behavior.

## Long pipelines → dynamic workflows

With plain sub-agents every result lands in the orchestrator's window. When a request needs many phases, wide fan-out, adversarial verification, or loops over an unknown count, ask Claude Code for a **workflow** (or use the `ultracode` trigger). A dynamic workflow is a generated script that holds the loop, the branching, and the intermediate results, so only the final answer reaches your context. [4] Its patterns are the shapes documented in [parallel-work](../../../parallel-work/SKILL.md)'s section headers. Give it a token budget in the prompt ("use 20k tokens") for bounded runs. Saved workflows live in `.claude/workflows/` (project) or `~/.claude/workflows/` (personal), or in a plugin's `workflows/` directory. [4]

## Repeating and finishing

- `/loop` re-runs a prompt or workflow on an interval — triage, verification, research sweeps.
- `/goal` sets a hard completion requirement the session keeps returning to; pair it with a loop so "done" is checked, not declared.

## Agent teams

`SendMessage`, a shared task list, and teammates spawned by naming an `Agent` call exist here and nowhere else. `TeamCreate` no longer exists: as of Claude Code v2.1.178, naming a teammate on an `Agent` call while `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is enabled spawns it directly, with no separate setup step. [3] The `swarm-*` skills that documented the old `TeamCreate` flow were retired in favour of `parallel-work`. If you need mid-task messaging between agents, this is the mechanism; expect to write explicit communication instructions into every teammate's prompt, and expect them to be followed imperfectly.

## References

1. [Create custom subagents](https://code.claude.com/docs/en/sub-agents) (accessed 2026-09-06)
2. [Plugins reference](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-06)
3. [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams) (accessed 2026-09-06)
4. [Orchestrate subagents at scale with dynamic workflows](https://code.claude.com/docs/en/workflows) (accessed 2026-09-06)
