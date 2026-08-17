# Memory Index

- [project_coverage_sysmon_core.md](./project_coverage_sysmon_core.md) — pytest coverage core is set to sysmon (PEP 669); how to verify it's active, why it was safe here
- [project_dh_conftest_lazy_import_cost.md](./project_dh_conftest_lazy_import_cost.md) — plugins/development-harness/conftest.py must keep heavy imports lazy inside fixtures, not module-level — breaks nested pytest subprocess timeouts
- [project_dh_multi_agent_worktree_contention.md](./project_dh_multi_agent_worktree_contention.md) — this machine runs many concurrent claude_skills agent worktrees; isolate timing/regression verification against a throwaway `git worktree add <path> HEAD` baseline, not git stash
