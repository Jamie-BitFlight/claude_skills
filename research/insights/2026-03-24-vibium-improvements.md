# Improvement Proposals: Vibium

**Research entry**: ./research/agent-infrastructure/vibium.md
**Generated**: 2026-03-24
**Patterns assessed**: 4
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 3

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| MCP Server Pattern for browser automation | Low | The `agent-browser` skill uses CLI via `allowed-tools: Bash(npx agent-browser:*)` which provides equivalent structured access. An MCP server would be an alternative delivery mechanism, not a functional improvement. Would need evidence that MCP delivery outperforms CLI-based tool access for browser automation before this becomes actionable. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Agent Browser Integration (semantic finding, form filling, screenshots, recording) | Already covered in `.claude/skills/agent-browser/SKILL.md` — skill provides `find text`, `find label`, `find role` semantic locators, `fill`, `click`, `screenshot`, `record`, `pdf`, and more. Coverage equals or exceeds Vibium's described capabilities. |
| Skill-Based Architecture (distributing browser automation as a Claude Code skill) | Already covered — `agent-browser` is already a Claude Code skill with full SKILL.md, frontmatter, allowed-tools, references, and templates. |
| Standards-Based Protocol (WebDriver BiDi over CDP/Playwright) | Too abstract for local system improvement. This is a protocol choice internal to the browser automation tool. The `agent-browser` skill wraps `agent-browser` (Playwright-based); switching to WebDriver BiDi would mean replacing the underlying tool, not extending the local system. No observable gap in agent-facing functionality — both protocols achieve the same browser control capabilities. |
