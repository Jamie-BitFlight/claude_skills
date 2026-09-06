# Delegation

Substantive work is delegated to sub-agents — see `agent-orchestration:delegate`.

- How: the `agent-orchestration:delegate` skill. See its Pointers section for what dispatched agents follow, fan-out shapes, and what the orchestrator may read or run itself.
- Bug fixes: `fix-delegation-discipline.md` (reproduce first).
- Agent output goes to `.tmp/scratch/` per `scratch-directory.md`; the STATUS block carries the path.
