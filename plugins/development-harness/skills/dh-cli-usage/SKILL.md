---
name: dh-cli-usage
description: Use when running development-harness plan, backlog, dispatch, artifact, active-task, or MCP troubleshooting commands; resolves CLI and server-script paths across agent harnesses.
user-invocable: false
---

# DH CLI Usage

Use the line below whose skill-directory variable the active harness substitutes. Append grouped
CLI arguments to that complete command; do not reconstruct the plugin root or CLI path elsewhere.

<sam_cli>
uv run "${CLAUDE_SKILL_DIR}/../../sam_schema/cli.py"
uv run "${KIMI_SKILL_DIR}/../../sam_schema/cli.py"
uv run "${HERMES_SKILL_DIR}/../../sam_schema/cli.py"
uv run "$DH_SKILL_DIR/../../sam_schema/cli.py"
</sam_cli>

Use the corresponding substituted line as the development-harness scripts directory.

<dh_scripts>
${CLAUDE_SKILL_DIR}/../../scripts
${KIMI_SKILL_DIR}/../../scripts
${HERMES_SKILL_DIR}/../../scripts
$DH_SKILL_DIR/../../scripts
</dh_scripts>

Codex, OpenCode, and Cursor do not substitute any line above. Read the absolute base directory the
harness displays for this loaded skill (the directory containing this `SKILL.md`), assign it
verbatim, and derive both tokens from that known directory:

```bash
DH_SKILL_DIR='<absolute base directory displayed for dh:dh-cli-usage>'
```

Use the corresponding `$DH_SKILL_DIR` lines in the token blocks. Do not search for or guess an
installation path.

Read [Command Reference](./references/command-reference.md) for grouped commands and named options.
Read [MCP Connection Check](./references/mcp-connection-check.md) only after an MCP server fails to
connect.

Before the first state-changing command, run `<sam_cli/> plan --help`. If neither a substituted line
nor the displayed base-directory fallback resolves, or that probe fails, report `STATUS: BLOCKED`
with the command and error output instead of guessing a path.
