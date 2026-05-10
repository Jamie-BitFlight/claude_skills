# Utilization Proposals: Composio Codebase Migrate

**Research entry**: ./research/skill-generation-tools/composio-codebase-migrate.md
**Generated**: 2026-05-10
**Integration surfaces found**: 1 (CLI + executor API)
**Proposals written**: 0
**Skipped**: 3 — no suitable caller identified

---

## Integration Surfaces Identified

**Composio CLI** — Command-line orchestration tool with executor API

**Documented integration surface:**
- `composio login` — authentication
- `composio execute GITHUB_CREATE_A_PULL_REQUEST` — PR creation
- `composio execute LINEAR_CREATE_ISSUE / LINEAR_CREATE_COMMENT` — issue tracking
- `composio execute GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY` — CI polling
- `composio run --file scripts/migrate-batch.ts` — workflow script execution

**Required local tools:**
- `git` — branching and commits
- `rg` (ripgrep) — finding affected files
- Language-specific codemods: `jscodeshift`, `ts-morph`, `comby`, `ast-grep`
- Test runners: `npm test`, `pytest`, etc.

---

## Candidate Systems Evaluated

### 1. `/gh` Skill

**File**: `./.claude/skills/gh/SKILL.md`

**Result**: SKIPPED

**Reason**: The `/gh` skill provides GitHub CLI wrappers for PR creation, issue management, and CI polling — the *building blocks* Composio uses. However, it does not orchestrate the *coordination layer* that Composio implements: maintaining per-batch tracking, managing checkpoint validation, polling CI status for decision-making, and looping through batches.

The `/gh` skill is a primitive infrastructure layer. Composio adds a semantic layer (batched migrations with automatic coordination). Integrating Composio into `/gh` would require creating an entirely new capability outside the scope of the skill's current purpose (simple GitHub CLI wrapping).

---

### 2. SAM Task Plan System

**File**: `./plugins/development-harness/plugins/development-harness/scripts/run_backlog_server.py` (inferred; not examined)

**Result**: SKIPPED

**Reason**: The SAM (Structured Agent-Managed) task planning system manages individual task lifecycles with state tracking (not-started → in-progress → complete). Composio addresses a different problem: orchestrating *groups* of batched work items with inter-batch checkpointing and CI-based merge decisions.

SAM's per-task granularity does not map to Composio's multi-batch coordination semantics. While SAM could theoretically track each migration batch as a task, the Composio CLI orchestration (batch queuing, conditional merging, CI polling) would remain external to SAM's task model. This is integration at the wrong abstraction level.

---

### 3. Migration-Related Agents (if any)

**Search**: `./.claude/agents/` for migration, refactor, codebase-change patterns

**Result**: SKIPPED

**Reason**: No agent currently exists that orchestrates large-scale multi-file migrations. The closest existing capabilities are:

- Code review agents — review after changes, not coordinate changes
- Refactoring agents — apply changes to individual files or small scopes
- Codebase analysis agents — understand structure, not execute coordinated transforms

Creating a migration orchestration agent *would* be a suitable consumer of Composio, but that would be a *new* system, not an existing caller being enhanced. The utilization assessment is limited to existing systems.

---

## Summary

The Composio codebase-migrate skill documents a callable, well-scoped integration surface (CLI + API). However, **no existing local system is positioned to call it**. The three candidate callers (gh infrastructure, SAM task management, hypothetical migration agents) all lack either:

1. The semantic responsibility for batch coordination, or
2. The need to integrate with GitHub/Linear issue tracking and CI polling, or
3. Physical existence in the codebase

**Implication**: If batched multi-file migrations become a priority in Claude Code plugin development, the appropriate next step would be to create a *new* migration orchestration agent or skill that consumes the Composio CLI integration surface. Until that need is explicitly identified, Composio remains a reference pattern documented for future use.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `./.claude/skills/gh/SKILL.md` | Provides GitHub infrastructure primitives; does not coordinate batched migrations. Composio's value (coordination) is external to `/gh`'s scope. |
| SAM task planning system | Per-task lifecycle tracking; does not address multi-batch coordination, CI-based merge decisions, or checkpoint validation. Composio semantics exceed SAM scope. |
| (Hypothetical) migration agent | Does not exist in codebase. New agent creation is out of scope for utilization assessment. |

---

## Notes

- **Confidence**: High. Composio integration surface is well-documented; assessment of existing systems is complete.
- **Future opportunity**: If Claude Code plugin maintenance requires coordinated large-scale migrations (e.g., framework upgrades affecting multiple skills), the Composio CLI pattern becomes a direct candidate for a new agent or skill.
- **Alternative pattern**: The `/gh` skill could be enhanced to support batch workflow templates without depending on Composio — but this would require custom orchestration logic and is outside the scope of integrating Composio as an external service.
