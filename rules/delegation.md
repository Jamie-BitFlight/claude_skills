# Delegation

Substantive work — implementation, investigation, fixes, reviews, and any file change regardless of size — is delegated to sub-agents. The orchestrator decomposes, dispatches, and adjudicates; agents read, run, and write.

- How: the `agent-orchestration:delegate` skill.
- What dispatched agents follow: `plugins/agent-orchestration/skills/delegate/references/sub-agent-contract.md`. Every dispatch prompt names its path.
- Many units at once: `agent-orchestration:parallel-work`.
- What the orchestrator may read or run itself: the `orchestrator-discipline` plugin.
- Bug fixes: `fix-delegation-discipline.md` (reproduce first).
- Agent output goes to `.tmp/scratch/` per `scratch-directory.md`; the STATUS block carries the path.

`Explore` is for exact-match search only; a hook rejects reasoning tasks sent to it.
