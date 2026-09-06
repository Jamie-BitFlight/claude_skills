# Harness notes — Claude Code

Open this when running in Claude Code. Nothing here changes the rules in `delegate` or `parallel-work`; it maps them onto Claude Code's mechanics.

## Dispatching

- A sub-agent is an `Agent` tool call with `subagent_type` and `prompt`. Several `Agent` calls in one assistant turn run concurrently; that is the fan-out mechanism.
- `subagent_type` is a built-in (`general-purpose`, `Explore`, `Plan`), a project agent from `.claude/agents/`, or `plugin:agent-name` for a marketplace agent.
- Sub-agents inherit CLAUDE.md, rules, and tool descriptions. They do not see the orchestrator's conversation and cannot take follow-up questions after they return (unless resumed). Everything they need is in the prompt.
- Sub-agents do not have the `Agent` tool; the ROLE_TYPE opener is belt-and-braces for harnesses where they might.
- Reference the contract by absolute path: `${CLAUDE_PLUGIN_ROOT}/skills/delegate/references/sub-agent-contract.md` resolves inside plugin hooks; in a prompt, paste the resolved path.

## Isolation

- `isolation: worktree` on an `Agent` call gives that sub-agent its own git worktree. Use it for every `write` dispatch in a fan-out. Relative paths in the prompt then resolve inside that worktree, which is what you want.
- Completion notifications arrive automatically. Do not poll a running agent's output or read its transcript; `orchestrator-discipline` documents why.

## Enforcement hooks

- `pre-tool-block-explore-for-analysis.cjs` (orchestrator-discipline) rejects `Explore` dispatches whose prompt contains reasoning verbs.

## Long pipelines → dynamic workflows

With plain sub-agents every result lands in the orchestrator's window. When a request needs many phases, wide fan-out, adversarial verification, or loops over an unknown count, ask Claude Code for a **workflow** (or use the `ultracode` trigger). A dynamic workflow is a generated script that holds the loop, the branching, and the intermediate results, so only the final answer reaches your context. Its patterns are the shapes documented in [parallel-work](../../../parallel-work/SKILL.md)'s section headers. Give it a token budget in the prompt ("use 20k tokens") for bounded runs. Saved workflows live in `~/.claude/workflows` or inside a skill.

Reference: <https://code.claude.com/docs/en/workflows>

## Repeating and finishing

- `/loop` re-runs a prompt or workflow on an interval — triage, verification, research sweeps.
- `/goal` sets a hard completion requirement the session keeps returning to; pair it with a loop so "done" is checked, not declared.

## Agent teams

`TeamCreate`, `SendMessage`, and the shared task list exist here and nowhere else. The `swarm-*` skills that documented them were retired in favour of `parallel-work`. If you need mid-task messaging between agents, this is the mechanism; expect to write explicit communication instructions into every teammate's prompt, and expect them to be followed imperfectly.
