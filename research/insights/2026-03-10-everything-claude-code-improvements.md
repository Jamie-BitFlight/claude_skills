# Improvement Proposals: Everything Claude Code

**Research entry**: ./research/agent-frameworks/everything-claude-code.md
**Generated**: 2026-03-10
**Patterns assessed**: 12
**Backlog items created**: 2 (issues: #576, #577)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: SubagentStop hook should capture a structured summary of subagent work

**Source pattern**: "Session Summaries in Hook SubagentStop Phase — Rather than losing context when subagents complete, ECC's hooks capture a summary of what was done, allowing parent agents to make informed routing decisions." (Patterns Worth Adopting, item 4)
**Local system**: plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
**Confidence**: High
**Impact**: Medium
**Backlog**: #576 created

### Current state

`task_status_hook.py` handles `SubagentStop` by marking the task COMPLETE, adding a `completed` timestamp, deleting the context file, and syncing completion to GitHub. It does NOT capture any summary of what the subagent accomplished — no record of files changed, tests written, errors encountered, or decisions made. The parent orchestrator (`implement-feature`) receives only the raw sub-agent output in its context window (which is lost on compaction) and has no structured artifact to reference when making routing decisions for subsequent tasks.

### Target state

`task_status_hook.py` SubagentStop handler writes a `summary` field to the task YAML frontmatter (or a separate `.claude/context/summaries/{session_id}-{task_id}.json` file) containing: files_modified (list), tests_added (count), key_decisions (list of strings), errors_encountered (list), and duration_seconds (int, computed from Started to Completed). The `implement-feature` orchestrator can read these summaries when deciding routing for dependent tasks.

### Measurable signal

After SubagentStop fires for a task, the task file's YAML frontmatter contains a `summary:` block with at least `files_modified` and `duration_seconds` fields populated. Verify by reading the task file after a task completes: `uv run implementation_manager.py status . {slug}` output includes a `summary` key for completed tasks.

---

## Improvement 2: Add hook runtime profile controls (disable/strictness)

**Source pattern**: "Runtime controls: ECC_HOOK_PROFILE — Hook strictness (minimal, standard, strict); ECC_DISABLED_HOOKS — Disable specific hooks by ID" (Hooks System section)
**Local system**: .claude/skills/start-task/SKILL.md (PostToolUse hooks), .claude/skills/implement-feature/SKILL.md (SubagentStop hooks)
**Confidence**: High
**Impact**: Medium
**Backlog**: #577 created

### Current state

All hooks defined in SKILL.md frontmatter (`PostToolUse` matcher for Write|Edit|Bash on `start-task`, `SubagentStop` on `implement-feature`) execute unconditionally. There is no mechanism to disable individual hooks, reduce hook frequency (e.g., skip PostToolUse LastActivity updates during high-throughput edits), or set a profile level. If a hook causes performance issues or interferes with debugging, the only option is to edit the SKILL.md frontmatter directly.

### Target state

`task_status_hook.py` reads environment variables at startup: `CLAUDE_SKILLS_HOOK_PROFILE` (values: `minimal`, `standard`, `strict`; default `standard`) and `CLAUDE_SKILLS_DISABLED_HOOKS` (comma-separated hook IDs like `post:edit:last-activity`). In `minimal` profile, PostToolUse LastActivity updates are skipped (only SubagentStop completion marking runs). In `strict` profile, additional validation checks run (e.g., verify task file exists before writing). Disabled hooks exit immediately with code 0 when their ID matches the environment variable.

### Measurable signal

Set `CLAUDE_SKILLS_HOOK_PROFILE=minimal` and run a task. Verify that `last_activity` is NOT updated on Write/Edit/Bash calls (PostToolUse handler exits early) but SubagentStop still marks the task complete. Set `CLAUDE_SKILLS_DISABLED_HOOKS=post:bash:last-activity` and verify the specific hook is skipped while others run.

---

## Improvement 3: Instinct-based pattern extraction from development sessions

**Source pattern**: "Instinct-Based Pattern Extraction — Instead of storing unstructured session logs, ECC extracts confidence-scored instincts (Action, Evidence, Examples) that can be merged, versioned, and fed back into future agent prompts." (Patterns Worth Adopting, item 6)
**Local system**: .claude/skills/session-historian/SKILL.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: session-historian indexes raw JSONL transcripts and caches summaries, but it is unclear whether the existing summary caching mechanism at `~/.claude/kaizen/session-summaries/` already performs partial pattern extraction. Would need to read the `session_query.py` script to confirm absence of any extraction logic beyond raw indexing.

### Current state

`session-historian` provides `list`, `messages`, `search`, `show`, and `index` commands against raw JSONL transcripts. Summaries are cached at `~/.claude/kaizen/session-summaries/`. No confidence scoring, no structured instinct format (Action/Evidence/Examples), no mechanism to merge extracted patterns across sessions, and no path to feed extracted patterns back into agent prompts or rules.

### Target state

A new command (e.g., `session_query.py extract-instincts <session-id>`) parses a session transcript, identifies repeated patterns (tool sequences, error-recovery strategies, decision points), and outputs structured instinct records: `{action: str, evidence: str[], examples: str[], confidence: float, source_sessions: str[]}`. Instincts are stored at `~/.claude/kaizen/instincts/` and can be merged across sessions. A companion command `session_query.py inject-instincts` emits markdown suitable for inclusion in CLAUDE.md rules or agent prompts.

### Measurable signal

Run `session_query.py extract-instincts <session-id>` on a completed session. Output is a JSON array of instinct records, each with `action`, `evidence`, `confidence` fields. At least one instinct file exists at `~/.claude/kaizen/instincts/`.

---

## Improvement 4: Verification loop taxonomy in complete-implementation

**Source pattern**: "Verification Loop Taxonomy — ECC distinguishes checkpoint (gate at end) vs. continuous (monitor throughout) evaluation, with grader types (unit, integration, E2E) and pass@k metrics. This provides a language for discussing evaluation strategy." (Patterns Worth Adopting, item 5)
**Local system**: .claude/skills/complete-implementation/SKILL.md
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: complete-implementation runs 6 sequential phases which function as checkpoint-style gates, but whether adding explicit taxonomy labels (checkpoint vs continuous, grader types) would change observable behavior is unclear. The improvement is primarily vocabulary/documentation rather than mechanism.

### Current state

`complete-implementation/SKILL.md` defines 6 phases (code-review, feature-verifier, integration-checker, doc-drift-auditor, service-docs-maintainer, context-refinement) executed sequentially. Each phase is implicitly a checkpoint gate. There is no explicit classification of verification type (checkpoint vs continuous), no grader type taxonomy, and no pass@k metrics.

### Target state

Each phase in `complete-implementation/SKILL.md` includes a `Verification type:` annotation (checkpoint or continuous) and a `Grader:` annotation (unit, integration, E2E, or documentation). The `implementation_manager.py status` output includes verification metadata showing which phases passed and their grader types.

### Measurable signal

Read `complete-implementation/SKILL.md` — each phase section contains `Verification type:` and `Grader:` annotations. Run `implementation_manager.py status . {slug}` — output includes a `verification` key with phase results.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Instinct-based pattern extraction | Medium | Need to read `session_query.py` to confirm no existing extraction logic beyond raw indexing; `~/.claude/kaizen/session-summaries/` cache may already perform partial extraction |
| Verification loop taxonomy | Low | Improvement is primarily vocabulary/documentation; unclear if adding taxonomy labels changes observable behavior or prevents failures |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Skill Activation Instructions in Agent Prompts | Already covered in implement-feature/SKILL.md (lines 78-86) and start-task/SKILL.md (lines 72-79) — skills loaded from ready-tasks JSON |
| Agent Delegation Template (chief-of-staff) | Already covered — implement-feature skill acts as orchestrator with delegation to named agents per task |
| Modular Command Namespacing | Claude Code plugin system handles namespacing natively; no local gap |
| Skill Library Expansion | Too abstract — no concrete mechanism to implement; purely aspirational |
| GitHub App Marketplace Model | Business/monetization model — not a code or skill gap |
| Language-Specific Rule Stratification | Assessed but deferred inline: our rules/ directory is flat (14 files) with no language-specific content requiring stratification; all rules are Python/general — no multi-language user base to serve |
| Research Entry Automation from sessions | Architecture mismatch: ECC `/learn` extracts patterns inline; our research-curator takes URLs and spawns agents. Integration would require a new input mode, not a gap fix |
| Hook Reuse (SessionStart, PreToolUse) | Our hooks serve different purposes (task status tracking vs ECC's session initialization); adapting ECC patterns would mean replacing, not extending, our hook system |
