---
title: "Improvement Proposals: mex"
---

## Backlog Creation Status

Backlog items could not be created during this run for two independent reasons, both observable:

1. `mcp__plugin_dh_backlog__backlog_add` requires a `gate_token` that is injected only when the `/dh:work-backlog-item` (or `/dh:create-backlog-item`) skill is loaded. This extractor agent has no mechanism to obtain that token.
2. The backlog backend is offline: `backlog_list` returned `"GitHub unavailable: GITHUB_TOKEN not set or token is invalid. Cannot refresh local cache."` — writes would fail or desync against a stale cache (last sync 2026-06-18).

The two high-confidence proposals below are written in full backlog-ready form (title, current state, target state, measurable signal). The orchestrator should create them via `/dh:work-backlog-item create` once the backend is reachable. Recommended priority is recorded per proposal.

---

## Improvement 1: Zero-token drift checker for the CLAUDE.md / .claude/rules instruction-file ecosystem

**Source pattern**: "Zero-Token Drift Detection" — `mex check` runs 11 mechanical checkers (path, edges, index-sync, staleness, command, dependency, cross-file, script-coverage, tool-config-sync, todo-fixme, broken-link) "without spending AI tokens" (Key Features §2; Relevance §2 "Drift Detection for Instruction Files").
**Local system**: `.claude/skills/research-curator/scripts/validate_research.py` (the only mechanical validator in the repo); `.claude/agents/doc-drift-auditor.md` (AI-token-driven code-vs-docs auditor).
**Confidence**: High
**Impact**: High
**Backlog**: Not created — backend offline + no gate token. Recommended: P1 (High confidence x High impact). Suggested type: Feature.

### Current state

The repo has no zero-token mechanical drift checker for its own instruction-file ecosystem (`CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md`, skill/agent markdown). The one mechanical validator, `validate_research.py`, is scoped exclusively to `./research/` entry structure — its checks (section_completeness, header_fields, access_dates, freshness_tracking) are defined in `.claude/skills/research-curator/references/validation-rules.md` and target research entries only. The only drift detection covering instruction files is `.claude/agents/doc-drift-auditor.md`, which is an AI agent (consumes tokens, requires spawning, non-deterministic) and audits code-vs-docs drift, not the four mex mechanical classes below. As a result, a broken markdown link to a moved `.claude/rules/*.md` file, a `uv run` command pointing at a renamed script, or a CLAUDE.md section referencing a deleted rule file is caught only incidentally during review.

### Target state

A new mechanical checker script (e.g. `.claude/skills/<skill>/scripts/check_instruction_drift.py`) runs without spawning an agent and emits the same JSON schema shape used by `validate_research.py` (summary + per-file issues with check/severity/message/line). It implements at minimum the mex checkers that map cleanly to this repo:

- **broken-link** — markdown links of the form `[text](./path)` in CLAUDE.md / .claude/rules / SKILL.md whose target does not exist on disk.
- **command** — `uv run <script>` / `uvx <tool>` references in instruction files pointing at scripts that do not exist at the cited path.
- **staleness** — instruction files not modified in N commits or N days (mex deducts on 30+ days or 50+ commits; thresholds configurable).
- **tool-config-sync** — divergence between `CLAUDE.md` and `.claude/CLAUDE.md` (and any other AI-config files) on shared, duplicated guidance.

### Measurable signal

Run: `uv run .claude/skills/<skill>/scripts/check_instruction_drift.py --json .claude/` — output is valid JSON with a `summary` object containing `errors`/`warnings`/`info` counts and an `entries` array; introducing a known broken `[text](./does-not-exist.md)` link into a rules file produces exactly one `broken-link` error entry citing that file and line; the command exits non-zero when any error-severity issue is present and zero when clean.

---

## Improvement 2: Staleness-by-commit-count signal added to research freshness detection

**Source pattern**: "staleness" checker — "Scaffold files not updated in 30+ days or 50+ commits" with configurable thresholds (`warnDays`/`errorDays`/`warnCommits`/`errorCommits` in `.mex/config.json`) (Key Features §2; Configuration §).
**Local system**: `.claude/skills/refresh-research/SKILL.md` Step 1 (Inventory and Staleness Detection); `.claude/skills/research-curator/references/validation-rules.md` (`statistics_currency`, `freshness_tracking`).
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created — backend offline + no gate token. Recommended: P1 (High confidence x Medium impact). Suggested type: Feature.

### Current state

`refresh-research` Step 1 determines staleness purely from calendar dates: it parses the Freshness Tracking section, computes `Days Old = today - Last Verified`, and marks STALE on three conditions only — no tracking section, `Next Review < today`, or `Last Verified > 6 months ago` (SKILL.md lines 33-49). There is no commit-activity signal. An entry whose upstream repo has churned heavily (many commits) but whose calendar date is still within the review window is reported FRESH and skipped, even though the documented data is likely outdated. mex pairs a time threshold with a commit-count threshold precisely to catch this case.

### Target state

`refresh-research` Step 1 staleness detection adds a commit-based condition alongside the existing date conditions: an entry is marked STALE when commits to its tracked upstream (or, as a proxy, commits touching the entry file's category since Last Verified) exceed a configurable threshold (mex default: 50 for warning, 200 for error). The threshold is documented in the SKILL and overridable, mirroring mex's `warnCommits`/`errorCommits`. The inventory table gains a `Commits Since` column so the STALE decision is auditable.

### Measurable signal

Read `.claude/skills/refresh-research/SKILL.md` Step 1: the staleness flowchart contains a commit-count decision node in addition to the three date-based nodes, and the inventory table header includes a commits-since column. Running `/refresh-research --dry-run` on a corpus where one entry's upstream has >50 commits since Last Verified but is within the date window reports that entry as STALE with the reason attributed to commit count.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason / what would raise confidence |
|---|---|---|
| Append-only event log for decision capture (`.mex/events/decisions.jsonl`, `mex log` with `source`/`status` lifecycle fields — Relevance §4) | Medium | The repo already captures decisions via two mechanisms: the backlog MCP (per-item files synced to GitHub) and `bd remember` (per CLAUDE.md, "Use `bd remember` for persistent knowledge"). Whether mex's lightweight session-scoped JSONL adds value over these is a design judgment, not a directly observable gap. Confidence would rise to High only after reading the `bd remember` implementation to confirm it lacks the `source`/`status` provenance fields and lacks a per-session append log — not examined in this pass. |
| Lightweight `mex heartbeat` vs full `mex check` two-tier health check (cheap metadata read returning `HEARTBEAT_OK` vs full scan — Relevance §5, Key Features §5) | Low | This is valuable only if Improvement 1 (the full mechanical checker) is built first; a "heartbeat" tier is a refinement of a checker that does not yet exist. The gap is inferred, contingent, and has no observable target state in any current file. Revisit after Improvement 1 ships. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-tool config integration (Claude Code / Cursor / Windsurf / Copilot / OpenCode / Codex config files — Relevance §3) | Out of architecture scope. This repo is a Claude Code marketplace plugin; the only relevant local equivalent (preserving the OpenCode `mcp:` frontmatter field) is already handled by `.claude/rules/frontmatter-requirements.md` ("Multi-Ecosystem Frontmatter Preservation"). The remaining tools (Cursor/Windsurf/Copilot config files) are not produced or maintained here, so a `tool-config-sync` across all six tools has no local surface. The CLAUDE.md-vs-.claude/CLAUDE.md slice of this pattern is captured inside Improvement 1, so the actionable part is not lost. |
