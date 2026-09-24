<!--
Split rule: keep material here only if BOTH hold — (a) it is meaningless to a harness that is
not Claude Code, and (b) Claude Code does not already supply it itself (available-skills/agent
listings, tool descriptions, hook execution). Everything else — every project fact, behaviour,
rule, and index, even when the mechanism it names happens to be Claude-Code-shaped — belongs in
AGENTS.md, which this file imports below. This repo's plugins ship harness manifests beside
`.claude-plugin/` (per-plugin coverage varies — follow AGENTS.md's Repository Overview to generate
and inspect the compatibility view), so "which skill to use when" is a project workflow rule, not a
Claude-Code one, even where a given plugin's non-Claude manifest doesn't exist yet.
-->

@../AGENTS.md

This session's `Setup` hook (`.claude/settings.json`, matcher `init|maintenance`) already runs
`uv self update` and `prek install` for you — skip re-running those two specific commands unless
troubleshooting a setup failure. The hook does not run `uv sync`; still run that yourself per
AGENTS.md's "Environment Setup" before assuming dependencies are installed.
