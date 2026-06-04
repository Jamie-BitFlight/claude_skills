# Refactoring Design Map: the-rewrite-room (rwr)

## Overview

The plugin has 3 critical load-blocking issues (name mismatch, empty commands array, STATUS vocabulary divergence), 4 high-severity correctness issues, and 2 medium-severity quality issues. All 9 issues have identified root causes and exact fix specifications below. No workarounds are used — every fix resolves the root cause directly.

## Source Assessment

- Plugin: `plugins/the-rewrite-room/`
- Overall Score: 62/100
- Total Refactoring Targets: 9 fixes across 12 files

---

## Critical Fixes (must fix before plugin loads correctly)

### Fix 1: plugin.json name field

**File:** `plugins/the-rewrite-room/.claude-plugin/plugin.json`

**Root cause:** The `name` field identifies the plugin to the marketplace loader. The directory is `the-rewrite-room/` and all command prefixes are `/rwr:*`, but `name` is set to `"rwr"`. The marketplace slug must match the directory name for load resolution.

**Current value:**

```json
"name": "rwr"
```

**New value:**

```json
"name": "the-rewrite-room"
```

**Why:** Directory name is `the-rewrite-room`, which is the canonical plugin identity. The `rwr` prefix belongs in command filenames (`commands/rwr/`), not in the plugin name field.

---

### Fix 2: plugin.json commands array

**File:** `plugins/the-rewrite-room/.claude-plugin/plugin.json`

**Root cause:** `"commands": []` is empty. Claude Code discovers commands from this array — an empty array suppresses all 4 existing command files.

**Existing command files (verified by glob):**

```text
commands/rwr/audit.md
commands/rwr/author.md
commands/rwr/cite.md
commands/rwr/optimize.md
```

**Missing command file (Fix 4 creates it):**

```text
commands/rwr/doc-to-skill.md
```

**New value (after Fix 4 creates the missing file):**

```json
"commands": [
  "./commands/rwr/audit.md",
  "./commands/rwr/author.md",
  "./commands/rwr/cite.md",
  "./commands/rwr/optimize.md",
  "./commands/rwr/doc-to-skill.md"
]
```

**Interim value (before Fix 4, if fixes are applied in separate passes):**

```json
"commands": [
  "./commands/rwr/audit.md",
  "./commands/rwr/author.md",
  "./commands/rwr/cite.md",
  "./commands/rwr/optimize.md"
]
```

**Dependency:** Fix 4 must be completed before the `doc-to-skill.md` entry is added. Fix 2 interim value can be applied immediately in parallel with Fix 4.

---

### Fix 3: STATUS vocabulary standardization

**Root cause:** The hooks validator (`hooks/hooks.json`) was written with `COMPLETE|BLOCKED|PARTIAL` as the accepted STATUS values. All 5 agent output contracts were written with `DONE|BLOCKED|FAILED`. Every agent invocation produces a `STATUS: DONE` or `STATUS: FAILED` block that the validator rejects as a CONTRACT_VIOLATION.

**Canonical vocabulary decision — which is correct:**

`DONE|BLOCKED|FAILED` is correct. Rationale:

- All 5 agents consistently use `DONE|BLOCKED|FAILED` — this is the intentional output contract for this plugin
- `COMPLETE` and `PARTIAL` are not used anywhere in the agent files; they appear only in the hooks validator
- The validator is a single file vs 5 agents + multiple workflow files — the minority outlier is the validator
- `DONE` is semantically cleaner for routing agents that orchestrate rather than produce artifacts (the distinction between `DONE` and `COMPLETE` matters for orchestrators)
- Fix is: update the hooks validator to accept `DONE|BLOCKED|FAILED`

**All locations requiring STATUS vocabulary update:**

The validator is the only file that needs changing. All agent and workflow files already use the correct vocabulary and must NOT be changed.

**File to update:** `plugins/the-rewrite-room/hooks/hooks.json`

**Current validator prompt excerpt (the diverged section):**

```text
1. STATUS field present with one of: COMPLETE, BLOCKED, PARTIAL
```

**And the example format block in the prompt:**

```text
STATUS: [COMPLETE|BLOCKED|PARTIAL]
```

**And the error message in the return:**

```text
STATUS value must be COMPLETE, BLOCKED, or PARTIAL.
```

**Exact replacements in `hooks/hooks.json` prompt string:**

| Old text | New text |
|----------|----------|
| `STATUS: [COMPLETE\|BLOCKED\|PARTIAL]` | `STATUS: [DONE\|BLOCKED\|FAILED]` |
| `1. STATUS field present with one of: COMPLETE, BLOCKED, PARTIAL` | `1. STATUS field present with one of: DONE, BLOCKED, FAILED` |
| `STATUS value must be COMPLETE, BLOCKED, or PARTIAL.` | `STATUS value must be DONE, BLOCKED, or FAILED.` |

**Confirmed correct locations by file (the 8 from assessment — all in hooks.json prompt, confirmed above as 3 distinct text occurrences within the single JSON string):**

The assessment's "8 locations" refers to the combination of:
- 3 text occurrences within hooks.json (the validator)
- 5 agent output contract blocks (already correct — do NOT touch)

No changes to agent files. Only `hooks/hooks.json` changes.

---

## High Severity Fixes

### Fix 4: Create missing doc-to-skill command file

**Root cause:** The SKILL.md command table lists `/rwr:doc-to-skill` with entry agent `rewrite-room-doc-converter`, but no command file exists at `commands/rwr/doc-to-skill.md`. The agent `rewrite-room-doc-converter.md` exists and is registered in plugin.json agents array — it is not reachable without a command file.

**File to create:** `plugins/the-rewrite-room/commands/rwr/doc-to-skill.md`

**Required content — what the command file must contain:**

The command file must route invocations to `rewrite-room-doc-converter` and pass the three arguments the SKILL.md documents: `<docs_path>`, `<output_plugin>`, `<output_skill>`.

Minimum required structure:

```markdown
---
name: doc-to-skill
description: Convert a user-facing docs directory into a Claude Code skill with reference files, workflow diagrams, and quality criteria. Arguments: <docs_path> <output_plugin> <output_skill>
agent: rewrite-room-doc-converter
---
```

The command file frontmatter must specify `agent: rewrite-room-doc-converter` so Claude Code routes invocations to the correct entry agent. No workflow steps belong in the command file — those live in the skill (`skills/user-docs-to-ai-skill/SKILL.md`) which the agent loads.

**After this fix:** Add `"./commands/rwr/doc-to-skill.md"` to the commands array (Fix 2 final value).

---

### Fix 5: Fix broken link to workflows/validate.md

**File:** `plugins/the-rewrite-room/the-rewrite-room/workflows/audit.md`

**Root cause:** Line 78 of audit.md references `plugins/the-rewrite-room/the-rewrite-room/workflows/validate.md`. The glob for `plugins/the-rewrite-room/workflows/*.md` returned no files — the entire `workflows/` directory has no `validate.md`.

**Current broken reference (line 78):**

```text
Chain -->|Yes| Validate[Chain to validate workflow\nLoad: plugins/the-rewrite-room/the-rewrite-room/workflows/validate.md]
```

**Resolution options (decision required — two valid approaches):**

Option A — Remove the branch: If validate was a planned but unimplemented workflow, remove the conditional branch entirely from the audit flowchart. The `Chain -->|Yes| Validate` node becomes dead code since it points nowhere actionable.

Option B — Replace with inline validation step: Replace the reference with a concrete inline action that the audit workflow performs directly (e.g., run `validate_frontmatter.py` directly via Bash). This is consistent with how `rewrite-room-author` handles GLFM validation — it runs the script directly rather than delegating to a workflow file.

**Recommended:** Option B, replacing the Mermaid node with a direct Bash action referencing the existing validation script at `plugins/plugin-creator/scripts/validate_frontmatter.py`. This matches the plugin's established pattern for script-based validation.

**Exact replacement (Option B):**

```text
Chain -->|Yes| Validate["Run: uv run plugins/plugin-creator/scripts/validate_frontmatter.py <file>"]
```

---

### Fix 6: Fix bare agent references without namespace prefix

**Root cause:** Three agents are referenced without namespace prefix. Claude Code resolves agents by `plugin:agent-name` format. Bare names work only if the agent happens to be in the user's global `~/.claude/agents/` — unreliable for plugin users.

**All bare references found:**

**Location 1:** `plugins/the-rewrite-room/agents/rewrite-room-auditor.md` line 36

```text
| doc-freshness-guardian | doc-freshness-guardian | ...
```

**Location 2:** `plugins/the-rewrite-room/skills/the-rewrite-room/SKILL.md` Workflow Index mermaid, node A3

```text
Audit --> A3[doc-freshness-guardian]
```

**Location 3:** `plugins/the-rewrite-room/agents/rewrite-room-author.md` — `gitlab-docs-expert` and `documentation-expert` in specialist table (both have bare `subagent_type` values)

**Resolution per agent:**

| Bare reference | Correct namespace:agent | Source to verify |
|----------------|------------------------|-----------------|
| `doc-freshness-guardian` | Cannot be namespaced — this agent lives at `/home/user/.claude/agents/doc-freshness-guardian.md` (a global user agent, not a plugin agent). See Fix 7 for the path issue. Reference must stay as bare name OR be documented as a global agent dependency. | Fix 7 handles path; Fix 6 documents the dependency explicitly |
| `gitlab-docs-expert` | Verify which plugin owns this agent, then add `plugin-name:gitlab-docs-expert` | Check `plugins/gitlab-skill/agents/` |
| `documentation-expert` | Verify which plugin owns this agent, then add `plugin-name:documentation-expert` | Check across plugin agents directories |

**Action for `doc-freshness-guardian`:** Document it explicitly as a global user agent dependency in the plugin README or plugin.json `dependencies` section — it cannot be namespaced since it is not in any plugin.

**Action for `gitlab-docs-expert` and `documentation-expert`:** The implementing agent (python-cli-architect or equivalent) must verify the owning plugin by globbing `plugins/**/agents/gitlab-docs-expert.md` and `plugins/**/agents/documentation-expert.md`, then apply the correct `plugin:agent` prefix in the `subagent_type` column of `rewrite-room-author.md`.

---

### Fix 7: Remove hardcoded absolute paths

**Root cause:** Three file references use `/home/user/` absolute paths tied to the author's machine. Plugin files must use paths relative to the repo root or reference agents by their plugin namespace.

**All hardcoded path locations (3 occurrences):**

| File | Line content |
|------|-------------|
| `plugins/the-rewrite-room/skills/the-rewrite-room/SKILL.md` line 98 | `/home/user/.claude/agents/doc-freshness-guardian.md` |
| `plugins/the-rewrite-room/the-rewrite-room/workflows/audit.md` line 29 | `/home/user/.claude/agents/doc-freshness-guardian.md` |
| `plugins/the-rewrite-room/agents/rewrite-room-auditor.md` line 44 | `/home/user/.claude/agents/doc-freshness-guardian.md` |

**All three reference the same file:** `doc-freshness-guardian.md` — a global user agent.

**Correct replacement:** Since this is a global user agent (not in any plugin), it cannot be referenced by a portable plugin-relative path. The correct approach is one of:

Option A — Reference by agent name only (bare): Replace the absolute path with the bare agent name `doc-freshness-guardian` in all descriptive text. The subagent_type in delegations already uses the bare name correctly; the absolute path appears only in documentation/reference table rows.

Option B — Document as external dependency: Add a note in each location: `doc-freshness-guardian — global user agent; install separately`.

**Recommended:** Option A for all three locations. Replace the absolute path with `~/.claude/agents/doc-freshness-guardian.md` (tilde form is portable and conventional for user-home references in documentation), or just use the bare agent name `doc-freshness-guardian` in the Path column of reference tables.

**Exact replacements:**

In `rewrite-room-auditor.md` table Path column:

```text
/home/user/.claude/agents/doc-freshness-guardian.md
```

Replace with:

```text
~/.claude/agents/doc-freshness-guardian.md (global user agent — install separately)
```

Apply the same replacement pattern to the identical strings in `SKILL.md` line 98 and `workflows/audit.md` line 29.

---

## Medium Severity Fixes

### Fix 8: Hook timeout

**File:** `plugins/the-rewrite-room/hooks/hooks.json`

**Current value:** `"timeout": 15` (milliseconds)

**Root cause:** The hook type is `"type": "prompt"` — a prompt-type hook invokes Claude to evaluate the output. A 15ms timeout is insufficient for any LLM call; it will always time out, making the validator permanently non-functional.

**Recommended value:** `"timeout": 30000` (30 seconds)

Rationale: Prompt-type hooks are LLM evaluations. Claude Code's own SubagentStop hooks in other plugins (e.g., `task_status_hook.py`) use 30-second windows. The validator prompt is short (the output contract check), so 30 seconds provides adequate margin without excessive blocking.

**This fix is in the same file as Fix 3** — apply both in a single Edit pass on `hooks/hooks.json`.

---

### Fix 9: Document external dependencies

**File:** `plugins/the-rewrite-room/.claude-plugin/plugin.json`

**Root cause:** The plugin delegates to 11+ agents in external plugins (`development-harness`, `plugin-creator`, `summarizer`, `gitlab-skill`, `prompt-optimization-claude-45`) with no declared dependencies. Users who install `the-rewrite-room` without those plugins get silent routing failures.

**Action:** Add a `dependencies` or `notes` field to plugin.json listing required external plugins. Claude Code's plugin schema may not have a formal `dependencies` field — if not, add a `README.md` section titled "Required plugins" listing each dependency.

**External plugin dependencies identified:**

```text
development-harness       (doc-drift-auditor, service-docs-maintainer)
plugin-creator            (contextual-ai-documentation-optimizer, subagent-refactorer)
summarizer                (file-summarizer, url-summarizer, image-summarizer)
gitlab-skill              (validate_glfm.py script, glfm-syntax.md reference)
prompt-optimization-claude-45  (prompt optimization principles)
```

**Global agent dependencies (cannot be namespaced):**

```text
doc-freshness-guardian    (global user agent — install to ~/.claude/agents/)
gitlab-docs-expert        (verify owning plugin — see Fix 6)
documentation-expert      (verify owning plugin — see Fix 6)
```

---

## Dependency Map

```text
Fix 4 (create doc-to-skill.md)
  └─ must complete BEFORE Fix 2 final value (adding doc-to-skill to commands array)

Fix 3 (STATUS vocabulary) + Fix 8 (timeout)
  └─ both edit hooks/hooks.json — combine into single Edit pass

Fix 1 (plugin.json name) + Fix 2 interim (commands array without doc-to-skill)
  └─ both edit plugin.json — combine into single Edit pass
  └─ Fix 2 final value requires Fix 4 to complete first

Fix 6 (namespace bare agents)
  └─ requires glob verification of owning plugins before writing — no other fix dependency

Fix 7 (hardcoded paths)
  └─ independent — no dependency on other fixes

Fix 5 (broken validate.md link)
  └─ independent — no dependency on other fixes

Fix 9 (document dependencies)
  └─ independent — no dependency on other fixes
  └─ benefits from Fix 6 completing first (reveals correct plugin names for gitlab-docs-expert, documentation-expert)
```

---

## Parallelization Opportunities

**Group A — Can run simultaneously (no shared files, no inter-dependencies):**

- Fix 4: Create `commands/rwr/doc-to-skill.md` (new file — no conflicts)
- Fix 5: Fix broken `validate.md` link in `workflows/audit.md`
- Fix 7: Replace hardcoded absolute paths in 3 files (`SKILL.md`, `workflows/audit.md`, `rewrite-room-auditor.md`)

Note: Fix 5 and Fix 7 both touch `workflows/audit.md` — they must be sequential if in the same agent, or coordinated if in parallel agents editing the same file.

**Group B — Can run simultaneously after Group A completes (or independently if file conflicts managed):**

- Fix 1 + Fix 2 interim: Edit `plugin.json` (single pass, two fields)
- Fix 3 + Fix 8: Edit `hooks/hooks.json` (single pass, two changes)
- Fix 6: Verify owning plugins + update `rewrite-room-author.md` subagent_type values

**Group C — Sequential after Group B:**

- Fix 2 final: Add `doc-to-skill.md` to commands array in `plugin.json` (requires Fix 4 done)
- Fix 9: Document external dependencies (benefits from Fix 6 resolving plugin names)

**Recommended execution order:**

```text
Pass 1 (parallel): Fix 4 | Fix 6 verification | Fix 9 research
Pass 2 (parallel): Fix 1+2interim (plugin.json) | Fix 3+8 (hooks.json) | Fix 5+7 (workflow files + agent files)
Pass 3 (sequential): Fix 2 final (add doc-to-skill to commands) | Fix 9 write
```
