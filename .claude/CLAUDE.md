<!--
Split rule: keep material here only if BOTH hold — (a) it is meaningless to a harness that is
not Claude Code, and (b) Claude Code does not already supply it itself (available-skills/agent
listings, tool descriptions, hook execution). Everything else — every project fact, behaviour,
rule, and index, even when the mechanism it names happens to be Claude-Code-shaped — belongs in
AGENTS.md, which this file imports below. This repo ships skills/commands/agents to Codex and
Cursor too (see the `.codex-plugin/`, `.cursor-plugin/` manifests beside `.claude-plugin/`), so
"which skill to use when" is a project workflow rule, not a Claude-Code one.
-->

@../AGENTS.md

This session's `Setup` hook (`.claude/settings.json`, matcher `init|maintenance`) already runs
`uv self update` and `prek install` for you — AGENTS.md's "Environment Setup" commands exist for
harnesses without that hook. Skip re-running them here unless troubleshooting a setup failure.
