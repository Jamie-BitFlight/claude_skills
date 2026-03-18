# Improvement Proposals: Emqutiti

**Research entry**: ./research/developer-tools/emqutiti.md
**Generated**: 2026-03-18
**Patterns assessed**: 7
**Backlog items created**: 0
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 6

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Environment variable override for configuration profiles | Low | The research entry describes `EMQUTITI_<PROFILE>_*` env vars as overrides for TOML-based broker profiles. The local system uses JSON context files (`.claude/context/active-task-*.json`) and YAML frontmatter for task/plan configuration, not TOML profiles. The hook runtime profile controls item (#577) already tracks adding profile-like controls to hooks. To raise confidence, one would need to verify that no existing mechanism in `sam_schema` or skill frontmatter supports env-var overrides for configuration fields, and that such overrides would address an observed failure mode (none documented). |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Component-based UI architecture | Too abstract — describes Go TUI package decomposition (connections, history, topics, traces, importer). This repo's plugin/skill architecture already follows modular decomposition with clear APIs per skill. The pattern is domain-specific to Bubble Tea TUI development, not transferable to Claude Code skill orchestration. |
| Focus management system | Not applicable — this repo has no terminal UI; all interaction is through Claude Code's CLI and agent delegation. Focus traversal, viewport offsets, and keyboard navigation are TUI concerns with no local system to map to. |
| Headless operation (dual-mode interactive + CLI) | Already covered — the SAM workflow already supports both interactive (user-invoked `/implement-feature`, `/start-task`) and programmatic modes (hook-driven `task_status_hook.py`, CLI `sam status/ready/claim`). The `sam` CLI provides JSON output for programmatic consumption. The dual-mode pattern is already implemented. |
| Trace recording for debugging / audit trails | Already in backlog as #109 (SAM: Audit Trail / Observability, P2). Emqutiti's persistent trace storage under `~/.config/emqutiti/data/<profile>/traces` with replay capability is conceptually similar to what #109 proposes. No new gap identified beyond what is already tracked. |
| MQTT message inspection in workflows | Domain-specific to MQTT protocol. This repo has no MQTT broker interaction and no foreseeable need for one. The pattern (agents querying external systems to verify state) is too generic to produce an actionable improvement. |
| Terminal UI patterns (Bubble Tea + Lipgloss) | Not applicable — this repo produces Claude Code plugins (skills, agents, MCP servers), not terminal UI applications. Adopting Bubble Tea patterns would require a fundamentally different output format with no current use case. |
| Configuration management (TOML profiles with defaults) | Already partially tracked as #577 (Add hook runtime profile controls to task_status_hook). The local system uses YAML frontmatter and JSON context files rather than TOML profiles; the specific mechanism (TOML + `default_profile` + env overrides) is architecture-incompatible. The profile concept itself is already being addressed via #577. |
