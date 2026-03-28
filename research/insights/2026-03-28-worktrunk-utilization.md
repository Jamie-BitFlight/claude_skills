# Utilization Proposals: Worktrunk

**Research entry**: ./research/developer-tools/worktrunk.md
**Generated**: 2026-03-28
**Integration surfaces found**: 2 (CLI tool, configuration system)
**Proposals written**: 1
**Skipped**: 1 — existing implementation handles scope well

---

## Utilization 1: /work-milestone → Worktrunk worktree management

**Research entry**: ./research/developer-tools/worktrunk.md
**Caller**: .claude/skills/work-milestone/SKILL.md
**Integration mechanism**: CLI subprocess (`wt` commands)
**Replaces or adds**: Replaces manual `git worktree add/remove` operations with branch-aware worktree CLI
**Setup cost**: Low (single binary install via package manager)
**Integration surface**: `wt switch`, `wt merge`, `wt remove` — documented in research entry section "Key Features: Core Worktree Commands"

### Why this caller

The `/work-milestone` skill (lines 44-48 of SKILL.md) implements wave-based parallel agent execution across isolated worktrees. It currently uses raw `git worktree add` commands within the kage-bunshin spawn loop. Worktrunk's core design is built for exactly this use case: it manages worktrees by branch name rather than filesystem paths, provides a unified `wt list` status view across all worktrees (line 46: shows staged changes, commits, CI status), and automates merge/cleanup sequencing via `wt merge`.

The research entry identifies that Worktrunk is "particularly valuable in AI-driven development workflows where multiple agents need isolated working directories" and that its `-x` flag for command execution aligns naturally with Claude Code's model of launching agents in specific branches. Currently, `/work-milestone` manually constructs paths and cleans up worktrees. Worktrunk provides branch-centric thinking (research entry line 202) that would reduce context switching and error handling overhead for the orchestrator managing N parallel agent sessions.

### Integration sketch

**Before (current `git worktree` pattern in work-milestone, lines 44-45):**

```bash
# Current approach
for ISSUE in "${WAVE_ISSUES[@]}"; do
  git worktree add "worktrees/work-${ISSUE}" "${INTEGRATION_BRANCH}"
  # ... spawn session in worktree ...
  git worktree remove "worktrees/work-${ISSUE}"
done
```

**After (with Worktrunk):**

```bash
# Worktrunk approach
for ISSUE in "${WAVE_ISSUES[@]}"; do
  # Create or switch to worktree, named by branch
  wt switch --create "wave-item-${ISSUE}" \
    --from "${INTEGRATION_BRANCH}"

  # Spawn session in current worktree (already active)
  cd "$(wt list --format=json | jq -r '.[] | select(.branch == "wave-item-'${ISSUE}'") | .path')"
  # ... spawn kage-bunshin session ...

  # Merge back to integration branch with automatic cleanup
  wt merge "${INTEGRATION_BRANCH}"
done
```

**Key benefits from research entry:**

- **Branch-centric API**: Worktrunk addresses worktrees by branch name (research entry line 45), eliminating path construction errors
- **Unified status**: `wt list --full` (research entry line 46) shows CI status and staged changes across all worktrees, reducing orchestrator queries
- **One-shot merge**: `wt merge` (research entry lines 47-48) performs squash, rebase, fast-forward, and cleanup in sequence—the current skill handles this in multiple manual steps
- **Hook integration**: Post-merge hooks (research entry lines 52, 54) could automate dependency installation or build cache sharing, reducing per-worktree setup time

**Note**: The concrete API surface (subcommand signatures, output format) is documented in the research entry. The sketch above uses patterns from the research entry's "Quick Start" section (lines 142-172). Worktrunk's interactive picker (research entry line 55) could also enhance the wave dispatch UI if future versions expose that capability.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `.claude/skills/swarm-operations/SKILL.md` | Worktrunk targets git/filesystem state (worktrees, branches, merges); swarm-operations manages inter-agent communication (TeamCreate, SendMessage). No integration surface overlap — swarm-operations does not manage worktrees or branches. |

---

## Notes

**Worktrunk integration with `/work-milestone` is additive, not breaking.** The skill's current `git worktree` implementation works correctly. Worktrunk would improve operational clarity and reduce manual error handling. Migration can be incremental: adopt Worktrunk for wave dispatch, keep existing error recovery paths until new paths are validated.

**Hook system potential**: The research entry documents Worktrunk's post-start, post-merge hooks (lines 52, 54) configured in `wt.toml`. These could be leveraged for automated wave-level workflows (e.g., running quality gates after each wave merge, or syncing shared caches between worktrees). This is a future opportunity beyond the initial integration surface identified here.
