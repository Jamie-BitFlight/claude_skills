## Context Manifest: Validate orchestrator-discipline plugin

**Groomed**: 2026-02-20
**Source backlog item**: `.claude/BACKLOG.md` lines 23-28

> **NOTE (2026-02-27)**: BACKLOG.md was removed. Backlog items now live in `.claude/backlog/` per-item files; GitHub Issues are the source of truth.

---

### Plugin Structure

Location: `plugins/orchestrator-discipline/`

```text
plugins/orchestrator-discipline/
├── .claude-plugin/
│   └── plugin.json                          (670 bytes)
├── hooks.json                               (597 bytes — at ROOT, not in hooks/)
├── hooks/
│   ├── pre-tool-orchestrator-read-warning.cjs    (2648 bytes, chmod +x)
│   └── pre-tool-diagnostic-command-gate.cjs      (3302 bytes, chmod +x)
├── rules/
│   └── CLAUDE.md                            (6615 bytes)
└── skills/
    └── orchestrator-discipline/
        ├── SKILL.md                         (4082 bytes)
        └── references/
            └── investigation-escalation.md  (13264 bytes)
```

Total files: 7 (including plugin.json). No agents directory. No scripts directory.

**ANOMALY**: `hooks.json` exists at the plugin root AND the plugin references `./hooks.json` from `plugin.json`. A `hooks/` directory contains the JS files, but there is no `hooks/hooks.json`. This is the correct layout — plugin.json `hooks` field points to `./hooks.json` at root, and that file's `command` values reference `${CLAUDE_PLUGIN_ROOT}/hooks/*.js`.

---

### Hook Configuration

File: `plugins/orchestrator-discipline/hooks.json` (at plugin root)

```json
{
  "description": "Orchestrator discipline enforcement hooks — context window protection",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Grep",
        "hooks": [{ "type": "command", "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/pre-tool-orchestrator-read-warning.cjs\"" }]
      },
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/pre-tool-diagnostic-command-gate.cjs\"" }]
      }
    ]
  }
}
```

Event: `PreToolUse`
Matchers: `Read|Grep` (source file read warning) and `Bash` (diagnostic command gate)
Both hooks: `type: command`, invoke Node.js scripts via `${CLAUDE_PLUGIN_ROOT}` variable

---

### Hook Logic Summary

#### pre-tool-orchestrator-read-warning.cjs

**Trigger condition**: `Read` or `Grep` tool call where target path matches:

- Extensions: `.py .toml .yaml .yml .js .ts .jsx .tsx .json .cfg .ini .env .sh .bash .go .rs .rb .java .c .cpp .h .hpp`
- Test directories: paths containing `/test/`, `/tests/`, `/spec/`, `/__tests__/`, or files matching `test_*.py`

**Does NOT fire on**: `.md`, `.txt`, plan files, BACKLOG.md, CLAUDE.md, skill definitions (confirmed by test)

**Action**: Non-blocking. Injects `additionalContext` via `hookSpecificOutput.additionalContext` with an `<orchestrator-read-warning>` XML block asking: "Will you Edit or Write this file this turn?"

**Verified behavior** (live test 2026-02-20):
- `Read` on `BACKLOG.md` → `{}` (no output, does not fire)
- `Read` on `.js` file → fires, `additionalContext` present
- `Read` on `.py` file → fires
- `Read` on `.toml` file → fires
- `Grep` on `.js` file → fires
- `Grep` on directory path (no extension) → `{}` (does not fire)

**Gap identified**: Grep with a directory `path` argument (e.g., `Grep pattern /path/to/src`) does not fire because the directory path has no extension. This is a false negative — the hook only checks the `path` field of Grep, which may be a directory. Broad `Grep` searches across source directories are not caught.

#### pre-tool-diagnostic-command-gate.cjs

**Trigger condition**: `Bash` tool call where `command` matches any of:

- Python: `ty check`, `ruff check`, `mypy`, `pyright`, `basedpyright`, `pylint`, `pytest`
- JS/TS: `eslint`, `tsc.*--noEmit`
- Rust: `cargo check`, `cargo clippy`
- Go: `go vet`
- Meta: `pre-commit run`, `prek run`

**Does NOT fire on**: `git status`, `ls`, `wc`, `uv run` alone, any non-diagnostic Bash (confirmed by test)

**Action**: Non-blocking. Injects `additionalContext` with `<orchestrator-diagnostic-warning>` block showing the matched command and instructing delegation.

**Verified behavior** (live test 2026-02-20):
- `uv run ty check .` → fires
- `uv run pytest tests/` → fires
- `uv run prek run --files foo.py` → fires
- `git status` → does not fire

**Gap identified**: `ruff format` is not in DIAGNOSTIC_PATTERNS but produces large output. Whether it should be gated is a design question. `uv run ruff check` IS caught (because `ruff check` is in patterns). `mypy` with `uv run` prefix is also caught.

---

### Rules Content Summary

File: `plugins/orchestrator-discipline/rules/CLAUDE.md` (6615 bytes)

Sections:

1. **Context Window Read Constraints** — Explicit permitted/prohibited lists. Falsifiable test: "Will I Edit or Write this file in this turn?"
2. **Delegation Constraints** — No exemption categories. Never pre-gather data for agents. Never pre-read task files.
3. **Investigation Escalation Anti-Pattern** — 4-step escalation sequence with mermaid flowchart. Trigger signal: 3+ Read/Grep/Bash on source files without interleaving Edit/Write/Task.
4. **Agent Output Polling Anti-Pattern** — `TaskOutput` with `block=false` on running agents. Prohibition on reading `.output` files directly. Session 77509a5e cited as observed instance.
5. **Diagnostic Commands** — Lists commands that must be delegated. Exception for post-edit single-file verification.
6. **Epistemic Identity Scope** — Scopes the "use tools to verify" imperative: task-routing information only, not source code.

**Format**: Mermaid flowcharts for both anti-patterns. Hard constraints use NEVER/MUST NOT language.

---

### Skill Summary

File: `plugins/orchestrator-discipline/skills/orchestrator-discipline/SKILL.md` (4082 bytes)

**Frontmatter**:

```yaml
---
description: Orchestrator context window discipline enforcement. Prevents the orchestrator from reading source files it will not edit, running diagnostic commands that waste context, and rationalizing delegation bypasses. Use when setting up orchestrator guardrails, reviewing delegation discipline, or diagnosing context window waste in multi-agent workflows. Activates PreToolUse hooks that surface decision points before source file reads and diagnostic command execution.
---
```

No `name` field (correct — avoids Claude Code bug where `name` field prevents slash command registration).
No `user-invocable` field (skill is auto-loaded via plugin hooks/rules, not invoked manually).

**Contents**:
- Explains what the plugin provides (hooks, rules, reference material)
- Hook behavior reference — extensions list, command patterns
- "Does NOT trigger on" section for both hooks
- Correct orchestrator workflow mermaid diagram

**Trigger phrases in description**: "orchestrator guardrails", "delegation discipline", "context window waste", "multi-agent workflows" — usable for semantic activation.

---

### Reference Files

`plugins/orchestrator-discipline/skills/orchestrator-discipline/references/investigation-escalation.md` (13264 bytes)

Contents:
- Pattern description with 4-step escalation sequence
- Root cause analysis (competing instructions, soft phrasing, no structural enforcement, exemption invention)
- Detection signals flowchart (mermaid)
- Correct workflow examples (diagnostic baselining, code investigation, config changes)
- Anti-pattern examples with token cost estimates (~21,000 chars vs ~500 chars)
- Variant: Agent Output Polling (identical root cause, different surface form)

Reference is linked from SKILL.md: `[Investigation Escalation Anti-Pattern](./references/investigation-escalation.md)`

---

### Plugin Manifest Completeness

File: `plugins/orchestrator-discipline/.claude-plugin/plugin.json`

```json
{
  "name": "orchestrator-discipline",
  "description": "Enforces orchestrator context window discipline via PreToolUse hooks and rules. ...",
  "version": "1.3.2",
  "author": { "name": "Jamie Nelson", "url": "https://github.com/bitflight-devops" },
  "skills": ["./skills/orchestrator-discipline"],
  "hooks": "./hooks.json",
  "rules": ["./rules"],
  "commands": ["./skills/orchestrator-discipline"]
}
```

**Declared components**:
- `skills`: points to `./skills/orchestrator-discipline` (directory exists, SKILL.md present)
- `hooks`: points to `./hooks.json` (file exists at root)
- `rules`: points to `["./rules"]` (directory exists, CLAUDE.md present)
- `commands`: points to `["./skills/orchestrator-discipline"]` (duplicates skills — appears intentional to register as slash command)

**CRITICAL ISSUE — validation failure**: `"rules"` is an unrecognized key per `claude plugin validate`. No other plugin in the repo uses `rules` in `plugin.json`. This is a blocking issue for marketplace distribution.

**Marketplace entry**: Present in `.claude-plugin/marketplace.json` as:

```json
{ "name": "orchestrator-discipline", "source": "./plugins/orchestrator-discipline" }
```

Note: Entry lacks `id` field. Other entries in marketplace.json also lack `id` — this appears to be the repo's standard format.

---

### Validation Results

Command run: `claude plugin validate plugins/orchestrator-discipline/`

```text
Validating plugin manifest: /home/user/repos/claude_skills/plugins/orchestrator-discipline/.claude-plugin/plugin.json

✘ Found 1 error:

  ❯ root: Unrecognized key: "rules"

✘ Validation failed
```

**Root cause**: The `"rules"` field in `plugin.json` is not part of the Claude Code plugin.json schema. It is a plugin-specific convention in this repo but not a recognized plugin manifest key.

**Impact**: Plugin cannot be validated with `claude plugin validate`. Marketplace users who run validation will get a failure. Cannot be submitted to marketplace as-is.

**Fix options**:
1. Remove `"rules"` from `plugin.json` — rules may still load if Claude Code loads `rules/` by convention (unverified)
2. Move rules content into SKILL.md or a CLAUDE.md at a different level
3. Investigate whether Claude Code loads a plugin's `rules/` directory automatically without it being declared

---

### Privacy Scan Results

Email search: No matches found in any plugin file.

Personal names found:
- `plugin.json` line 6: `"name": "Jamie Nelson"` — in the `author` field. This is the repo owner's name and appears in other plugin manifests. Not a privacy issue for this repo context.
- `plugin.json` line 7: `"url": "https://github.com/bitflight-devops"` — public GitHub org URL. Not private.

API keys, tokens, passwords: No matches found.

Session ID in rules/CLAUDE.md line 78: `77509a5e` — references a session ID from the source analysis session. This is an internal reference, not a credential. Appears acceptable.

**Conclusion**: No PII or private data issues beyond the author attribution, which is standard for this repo.

---

### Related Skills and Agents

Skills directly relevant to this work:

- `plugins/plugin-creator/skills/hooks-core-reference/SKILL.md` — hook event types, lifecycle
- `plugins/plugin-creator/skills/hooks-io-api/SKILL.md` — hook input/output schema, `hookSpecificOutput` structure
- `plugins/plugin-creator/skills/hooks-patterns/SKILL.md` — hook design patterns
- `plugins/plugin-creator/skills/claude-hooks-reference-2026/SKILL.md` — comprehensive hooks reference
- `plugins/plugin-creator/skills/claude-plugins-reference-2026/SKILL.md` — plugin.json schema (authoritative source for what fields are valid)

For validation testing:
- `plugins/plugin-creator/scripts/plugin_validator.py` — internal validator (separate from `claude plugin validate`)

Agents relevant to this work:
- `@plugin-creator:plugin-assessor` — comprehensive plugin structure analysis
- `@plugin-creator:refactor-validator` — validates refactoring completeness

---

### Prior Work

**Commits**:

```text
03f4342  feat(orchestrator-discipline): add plugin for orchestrator context window discipline
         (2026-02-19, initial creation — added all 7 files)

1cfefd4  refactor(mypy): update mypy configuration for improved type checking
         (touches orchestrator-discipline? — adjacent commit, may be unrelated)

323e23e  feat(dasel): add data transformation and exploration plugin
         (unrelated)

908f73e  style(frontmatter): normalize YAML quoting across all component files
         (touches orchestrator-discipline files — YAML quoting normalization)
```

The `908f73e` commit updated SKILL.md frontmatter quoting. The initial commit `03f4342` created all files. No other commits modify this plugin.

**Commit message (03f4342)** notes:
- "Updates marketplace.json (version 2.13.0) and BACKLOG.md with plugin validation task"
- Confirms the validation task was added to BACKLOG at time of plugin creation

**BACKLOG.md**: Backlog item at lines 23-28 is this exact item — correctly describes what needs to be done.

**Session artifacts**: The `investigation-escalation.md` reference file mentions session `77509a5e` (dasel plugin creation session 2026-02-19) as the observed instance of the agent output polling anti-pattern. This is a narrative reference, not a file artifact.

**Planning docs**: No separate planning documents found for this plugin. Plugin was created directly from anti-pattern analysis.

---

### Gaps and Blockers

**BLOCKER — validation failure**:
`claude plugin validate` fails with: `root: Unrecognized key: "rules"`. This is the primary issue to resolve before the plugin can be considered production-ready or marketplace-distributable.

**Investigation needed**:
- Does Claude Code load a plugin's `rules/` directory automatically (by convention) even without a `rules` key in `plugin.json`?
- If yes: Remove `rules` from `plugin.json` and verify `rules/CLAUDE.md` still loads in sessions.
- If no: Find the correct mechanism to ship rules with a plugin — possibly by moving rules content into the SKILL.md or using a different field.

**Hook gap — Grep on directory paths**:
When the orchestrator calls `Grep` with a directory as the `path` argument (no file extension), `pre-tool-orchestrator-read-warning.cjs` does not fire. The hook checks if `toolInput.path` matches `SOURCE_FILE_EXTENSIONS`, but directories have no extension. This is a false negative for broad codebase searches.

**Unverified — rules loading behavior**:
Whether `rules/CLAUDE.md` actually loads into the session context when the plugin is installed has not been tested. The hook behavior was verified (live tests). The rules loading depends on Claude Code's plugin rules mechanism, which is separate from the hook mechanism.

**Unverified — slash command registration**:
The SKILL.md has no `user-invocable: true` field. Without this, the skill may not register as a `/orchestrator-discipline:orchestrator-discipline` slash command. The SKILL.md description mentions "Manual activation is useful when..." — implying it should be manually invocable. Whether it actually appears as a slash command is not confirmed.

**hooks.json location note**:
`hooks.json` is at the plugin root, not inside `hooks/`. This is intentional (plugin.json `"hooks": "./hooks.json"` references it correctly). No confusion for implementation, but worth noting for reviewers.

---

### Suggested First Steps

Ordered by priority:

1. **Resolve the `rules` key validation failure** (BLOCKER)
   - Read `plugins/plugin-creator/skills/claude-plugins-reference-2026/SKILL.md` to find the canonical plugin.json schema
   - Test whether rules load without being declared: install plugin, open session, check if `rules/CLAUDE.md` content appears in system context
   - If auto-loaded: remove `"rules"` from `plugin.json` and re-run `claude plugin validate` — expect clean pass
   - If not auto-loaded: research correct declaration method or move rules content into SKILL.md

2. **Verify rules load into session context**
   - Install plugin locally: `claude plugin install orchestrator-discipline@jamie-bitflight-skills --scope local`
   - Open a Claude Code session
   - Confirm rules/CLAUDE.md content is active (ask Claude to describe its orchestrator read constraints)
   - OR test with `claude --plugin-dir ./plugins/orchestrator-discipline` session

3. **Verify hooks fire in real Claude Code session**
   - Session test with plugin installed: attempt to `Read` a `.py` file and confirm `<orchestrator-read-warning>` appears in context
   - Session test: attempt `uv run pytest` and confirm `<orchestrator-diagnostic-warning>` appears
   - Session test: `Read` on `BACKLOG.md` and confirm no warning fires

4. **Evaluate Grep-on-directory gap**
   - Assess whether this is a meaningful gap: orchestrators searching broad directories are the high-risk behavior
   - If yes: change hook to fire when tool is `Grep` regardless of `path` extension (fire on all Grep calls, or check if `path` is a directory)
   - Document design decision

5. **Add `user-invocable: true` to SKILL.md if manual activation is intended**
   - SKILL.md says "Manual activation is useful when..." but has no `user-invocable` field
   - If slash command registration is desired, add `user-invocable: true`
   - Run `uv run prek run --files plugins/orchestrator-discipline/skills/orchestrator-discipline/SKILL.md` after

6. **Verify slash command appears after installation**
   - With plugin installed, confirm `/orchestrator-discipline:orchestrator-discipline` appears in autocomplete
   - If not: check for `name` field interference (plugin-creator docs note this is a known bug)

7. **Lint all plugin files**
   - Run `uv run prek run --files plugins/orchestrator-discipline/rules/CLAUDE.md`
   - Run `uv run prek run --files plugins/orchestrator-discipline/skills/orchestrator-discipline/SKILL.md`
   - Run `uv run prek run --files plugins/orchestrator-discipline/skills/orchestrator-discipline/references/investigation-escalation.md`
