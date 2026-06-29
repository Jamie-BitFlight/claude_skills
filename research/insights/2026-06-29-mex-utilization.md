# Utilization Proposals: mex

**Research entry**: ./research/context-management/mex.md
**Generated**: 2026-06-29
**Integration surfaces found**: 3 (CLI | npm package | TypeScript SDK)
**Proposals written**: 2
**Skipped**: 2 — doc-drift-auditor already covers code-docs drift; session-historian is session capture, not project state monitoring

---

## Utilization 1: doc-drift-auditor → mex drift detection

**Research entry**: ./research/context-management/mex.md
**Caller**: ./.claude/agents/doc-drift-auditor.md
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Extends existing documentation drift detection with zero-token automated checkers for project instruction files (CLAUDE.md, .cursorrules, rule files)
**Setup cost**: Low (npm install mex-agent, mex setup --mode agent-memory)
**Integration surface**: `mex check --json` (11 automated checkers: path, edges, index-sync, staleness, command, dependency, cross-file, script-coverage, tool-config-sync, todo-fixme, broken-link)

### Why this caller

The doc-drift-auditor agent (./claude/agents/doc-drift-auditor.md) detects divergence between documented features and actual implementation through git forensics and code analysis. Its current scope focuses on README ↔ code drift. However, the agent does not currently detect drift in AI-facing instruction files (.claude/CLAUDE.md, .claude/rules/*.md, .cursorrules) — files that guide agent behavior directly and deteriorate silently when unfollowed by code changes.

The mex tool provides 11 zero-token drift checkers that are directly applicable to this repo's instruction ecosystem:
- **tool-config-sync**: Flags when CLAUDE.md, .cursorrules, and other AI tool configs get out of sync with each other
- **broken-link**: Detects markdown links in CLAUDE.md and rules files that point to non-existent files
- **staleness**: Flags files (CLAUDE.md, rules) not updated in 30+ days or 50+ commits
- **todo-fixme**: Catches unresolved TODO/FIXME markers left in instruction files
- **path** and **script-coverage**: Detect missing files and uncovered scripts referenced in CLAUDE.md

Integrating mex's checkers into the doc-drift-auditor workflow would extend its scope from code-docs drift to instruction-file drift, catching gaps that cause agent confusion and session-to-session inconsistency without spending tokens.

### Integration sketch

In doc-drift-auditor.md (./claude/agents/doc-drift-auditor.md), add a new section after "Analysis Techniques" to call mex:

```bash
# Before: Audit documentation drift (current workflow)
git log --follow --oneline -- path/to/file
grep -n "^##\|^###" README.md

# After: Also audit instruction file drift via mex (NEW)
mex check --json --quiet
# mex outputs:
# {
#   "score": 92,
#   "errors": [{checker: "tool-config-sync", files: [".cursorrules", "CLAUDE.md"], message: "..."}],
#   "warnings": [{checker: "staleness", files: [".claude/rules/*.md"], message: "..."}]
# }

# Parse mex output and fold into drift report:
# - Instruction files out of sync with each other
# - Broken links in CLAUDE.md or rule files
# - Unresolved TODOs in agent instructions
```

**Execution flow**: doc-drift-auditor invokes `mex check --json` (setup prerequisite: `npx mex-agent setup --dry-run` to verify .mex/ scaffold exists), parses the structured output, cross-references instruction file drift with code-docs drift findings, and includes both in the final DOCUMENTATION_DRIFT_AUDIT.md report.

---

## Utilization 2: refresh-research → mex event log for research decisions

**Research entry**: ./research/context-management/mex.md
**Caller**: ./.claude/skills/refresh-research/SKILL.md
**Integration mechanism**: npm package / CLI subprocess
**Replaces or adds**: Adds persistent, timestamped decision logging for research refresh operations (which entries were updated, why, version changes detected)
**Setup cost**: Medium (npm install mex-agent, initial .mex setup with ROUTER.md configuration for research workflow context)
**Integration surface**: `mex log --source research --status implemented` (append-only JSONL event log at .mex/events/decisions.jsonl)

### Why this caller

The refresh-research skill (./skills/refresh-research/SKILL.md) orchestrates parallel research-curator agents to bulk-refresh stale research entries. After each wave completes, the skill produces a summary report (Step 6) that lists updated, unchanged, and failed entries. However, these summaries are transient — they exist in the current session's output and are not persisted for future reference.

The mex event log (`.mex/events/decisions.jsonl` + `mex log` command) provides a lightweight, append-only persistent record. Each refresh operation could log:
- What entries were refreshed and why (staleness threshold passed, --all flag, --category filter)
- Which entries succeeded, which failed, which had no changes
- Version bumps detected (v0.3 → v0.5 in agno.md)
- Stars/metrics changes noted during refresh

The benefit is that across multiple sessions, future research-refresh invocations can query the event log to understand historical refresh patterns, detect recurring failures in specific entries, and make better decisions about wave sizing and retry strategies.

### Integration sketch

In the refresh-research workflow (Step 4: Spawn Agents in Waves), after each wave completes, add a call to `mex log`:

```bash
# Step 4 (after each wave completes)
mex log "Research refresh: Wave {N} complete ({M}/{total} succeeded)" \
  --source research \
  --status implemented

# Example real output:
# $ mex log "Refreshed 5 entries: agno (v0.3→v0.5), narsil (unchanged), orbstack (failed)" \
#     --source research --status implemented
# $ Appended to .mex/events/decisions.jsonl:
# {"ts":"2026-06-29T15:30Z","message":"Refreshed 5 entries: agno (v0.3→v0.5), narsil (unchanged), orbstack (failed)","source":"research","status":"implemented"}

# Later sessions can query:
# $ mex timeline --json | jq '.[] | select(.source=="research")'
# → retrieves all research refresh events across sessions
```

**Execution flow**: After Step 6 (Summary Report) in refresh-research, add a new Step 6a that invokes `mex log` with the wave summary. This creates a searchable, persistent decision trail without requiring changes to external backlog systems. Future research refresh runs can optionally query the event log via `mex timeline --json` to understand prior refresh success/failure patterns.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| ./.claude/skills/session-historian/SKILL.md | Session historian captures session transcripts and user messages (past work), not project state monitoring. mex's agent-memory mode is designed for persistent agent loops maintaining operational memory, not session history retrieval. Different purpose; no integration surface overlap. |
| ./.claude/skills/refresh-research/SKILL.md (alternative approach) | While refresh-research is a strong candidate (Utilization 2 above), mex's primary value for this caller is event logging, not orchestration replacement. The research curator workflow is already well-structured; mex adds value at the logging tier, not the orchestration tier. |

---

## Integration Summary

mex provides three integration surfaces for this codebase:

1. **Zero-token drift detection** via `mex check` — directly applicable to doc-drift-auditor for instruction-file compliance
2. **Persistent event logging** via `mex log` — directly applicable to research refresh operations for decision persistence
3. **Multi-tool instruction synchronization** — not utilized in current proposals, but available if CLAUDE.md synchronization with other AI tool configs becomes a pain point

The strongest fits are doc-drift-auditor (catch instruction file decay automatically) and refresh-research (persist research refresh decisions across sessions). Both integrate at the CLI level with no API dependencies; setup cost is npm installation + one-time mex setup.

