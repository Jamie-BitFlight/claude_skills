---
name: dh-cli-usage
description: Use when a development-harness agent or skill needs to run the DH CLI or locate DH server scripts across supported harnesses.
user-invocable: false
---

# DH CLI Usage

Determine this skill's absolute directory from the skill metadata supplied by the current harness:

- Codex exposes `skill_root` when the skill is read.
- OpenCode appends `Base directory for this skill` to the loaded skill.
- Cursor resolves paths relative to the skill root.
- Claude Code, Kimi, and Hermes substitute one of these skill-directory values. Use the first line
  that became a concrete absolute path; ignore unresolved lines:

<skill_root>
${CLAUDE_SKILL_DIR}
${KIMI_SKILL_DIR}
${HERMES_SKILL_DIR}
</skill_root>

Call that absolute directory `<skill-root>`. Replace `<skill-root>` with its resolved value before
running any command; it is an instruction token, not a shell or harness substitution variable.

<sam_cli>
uv run "<skill-root>/../../sam_schema/cli.py"
</sam_cli>

Resolve the server script directory from the same root:

<dh_scripts>
<skill-root>/../../scripts
</dh_scripts>

Use `<sam_cli/>` in commands after resolving it above. Run `<sam_cli/> plan --help` to verify the
path before acting. If no form resolves or the probe fails, report the exact error and return
`STATUS: BLOCKED` rather than guessing another path.

Read the [grouped command reference](./references/command-reference.md) for grouped commands. Read
the [MCP connection check](./references/mcp-connection-check.md) when an MCP server cannot be reached.
