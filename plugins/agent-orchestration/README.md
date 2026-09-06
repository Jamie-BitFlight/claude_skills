# agent-orchestration

A small set of skills and a contract for orchestrating sub-agents, portable across harnesses that support plugins, skills, and agents.

| Piece | Purpose |
| --- | --- |
| `delegate` | Decompose → dispatch → adjudicate. Two prompt modes: specialist (no HOW) and generic (prescribed HOW). Phase table, re-dispatch cap, pattern expansion. |
| `delegate/references/sub-agent-contract.md` | What a dispatched agent follows: one phase, STATUS first line (`DONE` / `PARTIAL` / `BLOCKED`), evidence, artifact path. |
| `parallel-work` | Fan-out/fan-in, mechanical fan-out, maker/checker, generate-and-filter, tournament, hypothesis fan-out, loop-until-stop with caps. |
| `delegate/references/harness-notes/claude-code.md` | Claude Code mechanics only. Add siblings per harness. |

If installed, pairs with `orchestrator-discipline` (what the orchestrator may read and run) and `process-siren` (decision points as evaluable Mermaid). Neither is required.

Install: `/plugin install agent-orchestration@jamie-bitflight-skills`
