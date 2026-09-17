---
name: dh-cli-usage
description: Use when a development-harness agent or skill needs to run the DH CLI or locate DH server scripts across supported harnesses.
user-invocable: false
---

# DH CLI Usage

Determine this skill's absolute directory with the branch for the current harness:

- Claude Code: use `${CLAUDE_PLUGIN_ROOT}/skills/dh-cli-usage`. Claude Code substitutes
  `${CLAUDE_PLUGIN_ROOT}` in plugin skill content.[1]
- Codex: use the absolute `skill_root` value returned when this skill is read.[2]
- OpenCode: use the `Base directory for this skill` value appended to the loaded skill.[3]
- Kimi: use the substituted `${KIMI_SKILL_DIR}` value.[4]
- Hermes: use the substituted `${HERMES_SKILL_DIR}` value.[5]
- Cursor: do not construct `<skill-root>`; Cursor documents skill-root-relative bundled resources,
  but no source establishes that it exposes the absolute skill root.[6] The
  [Cursor harness measurement](../../docs/work-ledger/measurements/harness-cursor.md#skillmd--loaded)
  records the evidence search. Use the configured `mcp__plugin_dh_*` tools instead. If the operation
  specifically requires the CLI or a server-script path, report that Cursor exposes no verified
  absolute skill root and return `STATUS: BLOCKED`.

For substitution-based branches, use the first line below that became a concrete absolute path and
ignore unresolved lines:

<skill_root>
${CLAUDE_PLUGIN_ROOT}/skills/dh-cli-usage
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

## References

1. [Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference) (accessed 2026-09-16)
2. [Codex skill read implementation](https://github.com/openai/codex/blob/ac192cd7937b0d73edc6dffe009940ae53782dd4/codex-rs/ext/skills/src/tools/read.rs#L66) (accessed 2026-09-16)
3. [OpenCode skill tool implementation](https://github.com/anomalyco/opencode/blob/337fd144d2ba144743368f78d9579a99cce175bd/packages/opencode/src/tool/skill.ts#L34-L60) (accessed 2026-09-16)
4. [Kimi Code agent skills](https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/customization/skills.md#body-placeholders) (accessed 2026-09-16)
5. [Hermes Agent creating skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills#referencing-bundled-scripts-from-skillmd) (accessed 2026-09-16)
6. [Cursor agent skills](https://cursor.com/docs/skills) (accessed 2026-09-16)
