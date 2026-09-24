# Platform Coverage Registry

Tracks which AI assistant hook systems are covered, their doc URLs, and fetch status.
Update `Last verified` when re-running fetch-and-transform-hooks-docs.sh.

## Covered platforms

| Platform | Hook concept | Doc URL | Reference file | Last verified |
|----------|-------------|---------|----------------|---------------|
| Claude Code | Yes — hooks.json + settings.json | <https://code.claude.com/docs/en/hooks.md> | claude-code.md | 2026-09-24 |
| Claude Code (inline agent) | Yes — agent frontmatter | <https://code.claude.com/docs/en/sub-agents.md> | inline-agent-hooks.md | 2026-09-24 |
| OpenAI Codex plugins | Yes — hooks.json + plugin extension/overlay | <https://learn.chatgpt.com/docs/hooks> | openai-codex.md | 2026-09-24 |
| GitHub Copilot | Yes — .github/hooks/ | <https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/use-hooks.md> | github-copilot.md | 2026-02-27 |

## Fetch-attempted platforms (no hooks doc found at time of last run)

| Platform | URL attempted | Result | Notes |
|----------|--------------|--------|-------|
| Cursor | <https://docs.cursor.com/context/rules> | Pending first run | Rules system, not hooks |
| Windsurf | <https://docs.windsurf.com/windsurf/memories> | Pending first run | Memories system, not hooks |
| Amp | <https://ampcode.com/docs> | Pending first run | Unverified |
| OpenCode | <https://opencode.ai/docs/plugins.md> | Pending first run | Plugin system with async JS/TS hook functions — not a hooks.json system; see agent-plugin-ecosystem references for full coverage |

## Adding a new platform

1. Add row to the table above with URL and "Pending" status
2. Add fetch entry to scripts/fetch-and-transform-hooks-docs.sh
3. Run the script: `bash plugins/plugin-creator/skills/hooks-guide/scripts/fetch-and-transform-hooks-docs.sh`
4. Update Last verified date if reference file was created/updated
