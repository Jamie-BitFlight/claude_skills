# Improvement Proposals: Claude Brain

**Research entry**: ./research/context-management/claude-brain.md
**Generated**: 2026-05-02
**Patterns assessed**: 10
**Backlog items created**: 2 (issues: #2095, #2096)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 7

---

## Improvement 1: Project-portable session memory file committable to git

**Source pattern**: "Memory is stored in one file (`.claude/mind.mv2`) at the project root under `.claude/`. ... Versionable: Commit to git, preserving memory in project history; Portable: Transfer via scp, email, or git clone for instant teammate onboarding" (Key Features → Single-File Memory Storage)
**Local system**: `/home/user/claude_skills/.claude/skills/session-historian/SKILL.md` (and `scripts/session_query.py`)
**Confidence**: High
**Impact**: High
**Backlog**: #2095 created

### Current state

Session knowledge in this repo lives in two non-portable locations:

1. Raw transcripts at `~/.claude/projects/<slug>/<session-id>.jsonl` — per-user home directory, never committed, lost on machine change.
2. Cached AI summaries at `~/.claude/kaizen/session-summaries/<session-id>.md` and DuckDB index at `~/.claude/kaizen/session-index.duckdb` — also per-user, also outside the repo.

`.claude/skills/session-historian/SKILL.md` line 3 documents that summaries are "cached at `~/.claude/kaizen/session-summaries/`". Lines 121-122 confirm both the index and summaries live under `~/.claude/kaizen/`. Grep of the repo for any `.claude/sessions/` or project-relative session store returns no results — there is no in-tree, git-trackable session memory artifact a teammate could pull on `git clone`.

Result: a new contributor cloning this repo cannot read what previous sessions decided, debugged, or attempted. Memory is bound to the original developer's home directory.

### Target state

A new optional session-summary writer (extension of session-historian or a Stop hook) can persist a structured summary into `.claude/sessions/<YYYY-MM-DD>-<session-id-prefix>.md` inside the repo, where it is:

- Tracked by git (or explicitly gitignored per project preference, but the location supports tracking)
- Discoverable by other team members on clone
- Indexable by session-historian on any machine that clones the repo

Add a `session_query.py export <session-id> --to-repo` subcommand that writes the same summary structure currently used in `~/.claude/kaizen/session-summaries/` to `<repo>/.claude/sessions/`. Update SKILL.md to document the optional in-repo location alongside the user-home location.

### Measurable signal

Run from a clean clone of the repo on a different machine:

```bash
.claude/skills/session-historian/scripts/session_query.py list --source repo
```

Output lists session summaries committed under `.claude/sessions/` without touching `~/.claude/kaizen/`. File at `.claude/sessions/<date>-<session>.md` contains the same frontmatter schema documented in SKILL.md lines 56-68 (`source_type`, `session_id`, `project`, `date_range`, etc.).

---

## Improvement 2: PostToolUse observation classification and capture beyond LastActivity timestamp

**Source pattern**: "PostToolUse hook captures observations from tool outputs without explicit user action. Observations are classified into 10 types: discovery, decision, problem, solution, pattern, warning, success, refactor, bugfix, feature... Captured tools include: Read, Edit, Write, Update, Bash, Grep, Glob, WebFetch, WebSearch, Task, NotebookEdit. ... Deduplicates observations (1-minute window to avoid re-capturing same tool call)" (Key Features → Automatic Observation Capture; Technical Architecture → PostToolUse Hook)
**Local system**: `/home/user/claude_skills/plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py` (PostToolUse handler at line 854 and 929-933)
**Confidence**: High
**Impact**: Medium
**Backlog**: #2096 created

### Current state

`plugins/development-harness/hooks/hooks.json` lines 58-67 register `task_status_hook.py` as the only PostToolUse handler, scoped to `Write|Edit|Bash`. Lines 854 and 929-933 of that script show the handler's sole responsibility on PostToolUse is to update a `LastActivity` timestamp on the active task file. Grep for `classify`, `observation`, `confidence`, `dedup`, or `categorize` against `task_status_hook.py` returns matches only inside the LastActivity-write logic — the hook does not classify the tool output, does not record what kind of work was done, and does not store an observation record.

Consequences:

- The orchestrator and downstream tooling have no record of which tool calls produced a `discovery` (e.g., a Grep that found a file), a `solution` (an Edit that resolved an error), or a `bugfix` (a commit that fixed a failing test). The signal exists in the JSONL transcript but is not extracted, classified, or made queryable.
- Periodic knowledge auto-save (#1678) and PreCompact context preservation (#1677) — when those land — will save raw snapshots, but without per-tool-call observation classification they cannot deliver the "search past decisions/bugs/solutions by type" capability claude-brain provides.
- Repeated tool calls within a tight loop are written to LastActivity verbatim with no dedup window, so a Bash command run 5 times in 30 seconds creates 5 timestamp updates instead of one observation with `count: 5`.

### Target state

Extend `task_status_hook.py` (or add a sibling `observation_capture_hook.py` registered alongside it) to classify each `PostToolUse` event into one of 10 observation types using rule-based heuristics and persist a structured observation record to `~/.dh/projects/{slug}/observations/<session-id>.jsonl`. Each record contains:

- `id`, `timestamp`, `tool`, `type` (one of the 10 enum values), `summary`, `confidence` (0.0-1.0), `metadata.session_id`
- A 1-minute in-memory dedup window keyed by `(tool_name, hash(input))` so identical successive calls produce one record with `count` incremented

Add a `min_confidence` threshold (default 0.6) below which observations are dropped — matches claude-brain's `minConfidence: 0.6` default in src/types.ts lines 78-84.

### Measurable signal

After implementing the change, run a Claude Code session that performs a `Grep` and an `Edit`. Then run:

```bash
ls ~/.dh/projects/-home-user-claude_skills/observations/
# Expect: <session-id>.jsonl exists

cat ~/.dh/projects/-home-user-claude_skills/observations/<session-id>.jsonl | jq -r '.type' | sort -u
# Expect output includes at least one of: discovery, solution, bugfix
```

Field `confidence` present in every record. Identical tool calls within 60 seconds collapse to one record with `count: N` instead of N records.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Native `/mind` style chat-invocable memory query commands (`/mind stats`, `/mind search "query"`, `/mind ask "question"`) | Medium | session-historian already provides equivalent CLI subcommands (list, messages, search, show, errors, tools, irritation). To raise confidence to High the gap would need to be observed as a friction point — e.g., a session where the user expected to type `/mind search auth` in chat and could not. Without that evidence, a new slash-command surface duplicates capability that is already accessible via the script. Re-evaluate after Improvements 1 and 2 land — if the new in-repo session store and per-tool-call observation index need quick chat-time access, a `/dh:mind` or `/sh:search` command becomes more clearly justified. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| SessionStart context injection (`additionalContext`) | Already tracked: #1677 PreCompact hook for emergency context preservation, #317 Structured session work logs with pre-compact and session-start hooks, #1069 fix: Orchestrator loses active team state across context compaction. Together these cover the inject-prior-context-at-session-start surface. |
| Periodic auto-save every N tool calls | Already tracked: #1678 Periodic session knowledge auto-save hook for crash recovery — explicitly extends `task_status_hook.py` with a counter that fires every N PostToolUse events. |
| Stop hook session summary | Partially covered by #317 (Structured session work logs) — the @logging agent already knows how to read transcripts and produce structured Completed/Decisions/Discovered/Next-Steps logs. Adding a separate Stop-hook summary writer would duplicate that intent. |
| Hook timeout discipline (5s SessionStart, 10s PostToolUse, 30s Stop) | Already implemented: `plugins/development-harness/hooks/hooks.json` lines 10, 65, 76 use 5000ms SessionStart, 10s PostToolUse, 30s SubagentStop — identical to claude-brain's timeouts. No gap. |
| Backup pruning (keeps 3 most recent) | Subsumed by improvements 1 and 2 — pruning policy is meaningful only after the in-repo session store and observation log exist. Premature without the storage layer. |
| Compression of captured observations ("ENDLESS MODE 20x") | Cannot evaluate without first having an observation store to compress. Tied to improvement 2; no independent action. |
| 100% local / no API keys / sub-millisecond search | Already aligned with repo posture — session-historian uses local DuckDB, no API calls. No gap. |
