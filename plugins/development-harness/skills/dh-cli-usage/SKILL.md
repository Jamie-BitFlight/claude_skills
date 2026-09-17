---
name: dh-cli-usage
description: "Gives the dh CLI command and the directory of dh's scripts, both resolved from this skill's own directory. Use before running a dh plan, backlog, artifact or dispatch command, or a script from dh's scripts directory, and when an mcp__plugin_dh_* server failed to connect."
user-invocable: false
---

# dh CLI usage

<sam_cli>
uv run "${CLAUDE_SKILL_DIR}/../../sam_schema/cli.py"
uv run "${KIMI_SKILL_DIR}/../../sam_schema/cli.py"
uv run "${HERMES_SKILL_DIR}/../../sam_schema/cli.py"
</sam_cli>

<dh_scripts>
${CLAUDE_SKILL_DIR}/../../scripts
${KIMI_SKILL_DIR}/../../scripts
${HERMES_SKILL_DIR}/../../scripts
</dh_scripts>

Use the line whose path is absolute. A line still reading `${…}` names a variable this harness does
not fill in; pass over it.

When no line is absolute, take the directory your harness stated above this body on a
`Base directory for this skill:` line. Then `<sam_cli/>` is
`uv run "<that directory>/../../sam_schema/cli.py"`, and `<dh_scripts/>` is
`<that directory>/../../scripts`.

When no line is absolute and no such directory is stated, report `STATUS: BLOCKED` naming this
skill, and run no `<sam_cli/>` command. Use the `mcp__plugin_dh_*` tools for any operation that has
one.

Wherever a dh skill, agent or reference writes `<sam_cli/> plan read …`, run your `<sam_cli>` line
followed by the words written after `<sam_cli/>`. The path in the line is complete; run it as
written. A path written `<dh_scripts/>/name.py` is your `<dh_scripts>` line followed by `/name.py`.
A dh command written without `<sam_cli/>`, such as `plan read --address …`, runs the same way: your
`<sam_cli>` line followed by the command.

When a `<sam_cli/>` command fails, run `<sam_cli/> plan --help`. When that also exits non-zero,
report the exact command and its stderr as `STATUS: BLOCKED`, and run no other `<sam_cli/>` command.

For the grouped commands and their options, read [command reference](./references/command-reference.md).

When an `mcp__plugin_dh_*` server failed to connect, read [MCP connection check](./references/mcp-connection-check.md).
