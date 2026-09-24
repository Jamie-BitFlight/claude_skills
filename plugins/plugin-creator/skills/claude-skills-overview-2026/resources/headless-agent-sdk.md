# Headless Skill Dispatch

Read this reference when a programmatic Claude Code session must discover or directly invoke a
filesystem skill. For CLI flags, output schemas, streaming events, and environment configuration,
consult the live [CLI reference](https://code.claude.com/docs/en/cli-reference),
[headless reference](https://code.claude.com/docs/en/headless), or SDK documentation instead of a
copied option table.

Without `--bare`, `claude -p` discovers skills from configured filesystem sources. Python and
TypeScript Agent SDK sessions load those sources through `setting_sources` or `settingSources`;
the SDK `skills` option controls which discovered skills the model may invoke automatically.

Dispatch a discovered, user-invocable skill by placing `/<name>` in the prompt:

```bash
claude -p "/my-deploy-skill production"
```

Direct dispatch is independent of the SDK `skills` allowlist. `user-invocable: false` removes the
command surface, while `disable-model-invocation: true` blocks automatic model invocation without
blocking direct dispatch. Inspect `system/init.skills` and `system/init.slash_commands` when the
caller must distinguish a missing command from an ordinary prompt.

The SDK does not register in-memory skill definitions; skills remain filesystem artifacts.
`--bare` skips normal discovery, except documented `.claude/skills/` handling for directories
supplied with `--add-dir`.

Interactive scheduled-task tools and `/loop` are unavailable in print mode. Use an external
scheduler for unattended recurrence.

SOURCE: [Headless mode](https://code.claude.com/docs/en/headless) and
[Agent SDK skills](https://code.claude.com/docs/en/agent-sdk/skills) (accessed 2026-09-24)
