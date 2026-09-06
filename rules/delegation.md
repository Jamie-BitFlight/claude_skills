# Delegation

Substantive work is delegated to sub-agents — see `agent-orchestration:delegate`.

- How: the `agent-orchestration:delegate` skill.
- What dispatched agents follow: `plugins/agent-orchestration/skills/delegate/references/sub-agent-contract.md`. Every dispatch prompt names its path.
- Many units at once: `agent-orchestration:parallel-work`.
- What the orchestrator may read or run itself: the `orchestrator-discipline` plugin.
- Bug fixes: `fix-delegation-discipline.md` (reproduce first).
- Agent output goes to `.tmp/scratch/` per `scratch-directory.md`; the STATUS block carries the path.
