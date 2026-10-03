# Utilization Proposals: gentle-ai

**Research entry**: ./research/agent-frameworks/gentle-ai.md
**Generated**: 2026-10-03
**Integration surfaces found**: 4 (CLI | API | SDK-less | webhook-less) — `gentle-ai` CLI (install/doctor/sync/review/update), GGA pre-commit/PR/CI CLI, Engram localhost HTTP/MCP server (port 7437, `mem_*` tools), Context7 MCP config
**Proposals written**: 2
**Skipped**: 5 — already covered, config-overwrite conflict, documentation-only files, pattern-only (not callable)

Absence check run before proposing: `grep -rIl -i -E "engram|gentle-ai|guardian.angel|mem_save|localhost:7437"` over the repo excluding `.git`, `node_modules`, `.venv`, `research/`, `.worktrees/` returned no files. The only hit under `research/` is the entry itself. No local system already calls Engram or GGA.

---

## Utilization 1: .pre-commit-config.yaml → GGA (Guardian Angel)

**Research entry**: ./research/agent-frameworks/gentle-ai.md
**Caller**: /home/user/claude_skills/.pre-commit-config.yaml
**Integration mechanism**: CLI subprocess
**Replaces or adds**: Adds an AI-judged staged-file review gate. Current hooks are deterministic linters and validators only.
**Setup cost**: Medium (GGA binary install, provider selection in `~/.config/gga/config`, per-commit LLM latency and cost)
**Integration surface**: GGA pre-commit hook, `--pr-mode`, `--ci` modes; install via `gentle-ai install` (research entry, "GGA (Guardian Angel)" and "Installation Pipeline" sections)

### Why this caller

`.pre-commit-config.yaml` (hook ids read: conventional-pre-commit, ruff, biome-check, markdownlint-cli2, skilllint, ty, validate-research-entries, and others) contains only deterministic checks. The one LLM-based reviewer, `.claude/agents/code-review.md` (frontmatter: "Use ONLY when explicitly requested by user... DO NOT use proactively"), is manual. GGA would add a gate that judges staged files against the rules in `AGENTS.md`, with SHA256 caching so only changed files are re-reviewed, and it can use Claude Code as the provider. The entry documents `AGENTS.md` as GGA's rules file, and this repo already has an `AGENTS.md`. Caveat: this repo's `AGENTS.md` is a broad working guide rather than a concise rule list, and prek stashes unstaged changes during hooks (AGENTS.md gotcha 3), so a slow LLM hook lengthens the stash window.

### Integration sketch

The research entry documents GGA only at the level of "pre-commit hook", `--pr-mode`, `--ci`, and provider config at `~/.config/gga/config`. It does not document the exact subcommand or flags a `.pre-commit-config.yaml` `entry:` would use, so none are invented here. Deferred until the upstream GGA README (`Gentleman-Programming/gentleman-guardian-angel`) is read to confirm the invocation. Shape of the change:

```yaml
# .pre-commit-config.yaml (entry command to be confirmed from GGA's own docs)
- repo: local
  hooks:
    - id: gga
      name: Guardian Angel review
      entry: <gga command per upstream README>
      language: system
      pass_filenames: false
```

CI variant: the entry documents a `--ci` mode for `.github/workflows/code-quality.yml`. Per `rules/ci-workflows.md`, read that rule before touching the workflow.

---

## Utilization 2: .mcp.json → Engram memory server

**Research entry**: ./research/agent-frameworks/gentle-ai.md
**Caller**: /home/user/claude_skills/.mcp.json
**Integration mechanism**: API call (MCP tools backed by the Engram server on localhost:7437)
**Replaces or adds**: Adds searchable cross-session project memory (SQLite + FTS5) usable from any agent. Claude Code's auto memory loads only the first 200 lines of `MEMORY.md`.
**Setup cost**: High (Go binary install, local daemon on port 7437 and optional boot autostart, a new store of decisions outside git)
**Integration surface**: Engram tools `mem_session_start`, `mem_search`, `mem_save`, `mem_session_summary`; database `~/.engram/engram.db`; health port 7437 (research entry, "Engram Memory System")

### Why this caller

`.mcp.json` currently registers two servers, `Ref-local` and `context7-local`; neither provides memory. The repo's memory layers are CLAUDE.md files, rules, auto memory (`plugins/plugin-creator/skills/memory-and-rules/SKILL.md`: auto memory loads "first 200 lines of `MEMORY.md`"), and per-agent `memory: project` (for example `plugins/development-harness/agents/classifier.md` line 6). None of these is full-text searchable across sessions or across harnesses. The repo targets claude-code, codex, hermes, opencode and cursor (AGENTS.md "Cross-harness"), and Engram's shared database is the entry's documented mechanism for sharing memory across those agents. Caveat: how the agent should launch Engram's MCP server is not documented in the entry (the installer wires it into `~/.claude.json`). The decision-history use case also overlaps with the SAM pipeline and backlog_core records in `plugins/development-harness`, so scope has to be set before adoption.

### Integration sketch

The entry documents the call flow, not an MCP launch command:

```text
session start -> mem_session_start(project_name)        # returns recent sessions, decisions, bugs
during work   -> mem_search(topic)                      # FTS5 lookup
on decision   -> mem_save(observation, type: decision|bug|pattern)
session end   -> mem_session_summary(goal, discoveries, accomplished, files)
```

Wiring into `.mcp.json` is deferred: the server `command`/`args` is not in the research entry. The only documented way to wire it is `gentle-ai install --agents claude-code --non-interactive`, which writes `~/.claude.json` and `~/.claude/` (user scope) rather than the repo's `.mcp.json`. Trial path: run `gentle-ai install` with a Memory Only preset in a throwaway environment, then read the resulting `~/.claude.json` entry to copy into `.mcp.json`.

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| /home/user/claude_skills/.claude/agents/code-review.md | Read. Manual-only reviewer; GGA would be a pre-commit gate rather than a replacement, so it is folded into Utilization 1 rather than proposed as its own caller. |
| plugins/development-harness (backlog_core, sam_schema, `sam_schema/core/backends/local_context_backend.py`) | Read the context backend (per-session `active-task-{session_id}.json`). Storing decisions in Engram would mean extending backlog_core, which is custom building, not calling a service. The covered use case is in Utilization 2. |
| plugins/plugin-creator/skills/memory-and-rules/SKILL.md and plugins/development-harness/agents/classifier.md | Read (memory-and-rules). Reference documentation and an agent definition, not callers. The research entry's "Integration Opportunities" anchor to them because they contain the terms "persistent memory" and "cross-session". |
| `gentle-ai install` / `sync` as a way to configure this repo's harnesses | Entry states it injects persona, theme, permissions and SDD orchestrator into `~/.claude/CLAUDE.md` and `settings.json`. That conflicts with the repo's plugin-managed, cross-harness configuration. Reconsider only for the Engram trial in Utilization 2. |
| ODD, RDD, SDD skills and the Context7 MCP config | ODD/RDD/SDD are workflow patterns rather than a callable surface (pattern adoption, out of scope here). Context7 is already registered as `context7-local` in `.mcp.json`. |
