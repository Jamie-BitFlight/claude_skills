# Service Docs Maintainer — Agent Memory

## Project: claude_skills

### Documentation Conventions

- **SKILL.md** is AI-facing (concise, imperative). Parameter tables use `| Parameter | Type | Default | Description |` format.
- **README.md** is human-facing (explanatory, contextual). Uses inline code examples with `# Returns:` and `# Progress:` comments.
- Both files live at `.claude/skills/{skill-name}/` alongside `backlog_core/` and `references/`.

### FastMCP `ctx: Context` Parameter Pattern

When FastMCP tools accept `ctx: Context` as first parameter, it is **framework-injected** — callers never pass it.
Do NOT add it to parameter tables. Instead, document the observable behavior:
- In SKILL.md: add a sentence to the tool description, e.g. "Emits progress messages via MCP context during execution."
- In README.md: add a `# Progress:` comment inside the code example block, and add a plain-text note in the section header block explaining which tools emit progress and what callers observe.

### backlog skill — Canonical file paths

- SKILL.md: `/home/ubuntulinuxqa2/repos/claude_skills/.claude/skills/backlog/SKILL.md`
- README.md: `/home/ubuntulinuxqa2/repos/claude_skills/.claude/skills/backlog/README.md`
- ARCHITECTURE.md: `/home/ubuntulinuxqa2/repos/claude_skills/.claude/skills/backlog/backlog_core/ARCHITECTURE.md`
- server.py: `/home/ubuntulinuxqa2/repos/claude_skills/.claude/skills/backlog/backlog_core/server.py`

### backlog_pull — dual return shape

`backlog_pull` has two code paths with different return shapes:
- `selector` provided (single item): returns `{file_path, messages, warnings}`
- `selector` absent (bulk): returns `{pulled, messages, warnings}`

Both shapes must be documented. Split the README.md code example into two blocks with a comment label for each.

### Audit report location

Drift audit reports land at `.claude/reports/DOCUMENTATION_DRIFT_AUDIT_{feature-slug}.md`.
Read this first — it contains file:line citations for every gap. Trust these over memory.
