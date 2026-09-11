# Cross-Harness Smoke Tests

The four harnesses installed on the maintainer's host: claude-code, codex, hermes, kimi.
Run these when a plugin's cross-harness configuration changes, and when recording a
`verified` status in `harness_compatibility.json`. Harness capability facts (what each
product substitutes, where it discovers plugins, which env vars it exports) are recorded
per-harness in `plugins/development-harness/docs/work-ledger/measurements/harness-*.md` —
introduced on PR #3427 (not yet on `main` at the time of writing); until it merges, read
them on that branch. Consult the matching file before interpreting a failure.

## Common to every harness

1. Install the plugin through that harness's own install mechanism (not the authoring
   checkout — an installed consumer is the point of the test).
2. The plugin's components are discovered: every skill listed, MCP servers (if any)
   connected, no silent skips.
3. Activate one representative skill and confirm it renders and executes: any path,
   script, or command the skill body instructs the agent to run resolves against the
   *installed* location. A literal unresolved `${CLAUDE_PLUGIN_ROOT}` reaching a shell is
   a failure.
4. For plugins with MCP servers: call one read-only tool through the harness's MCP
   client and confirm a well-formed response.

## claude-code

```bash
claude --plugin-dir ./plugins/<name>        # or install from the local marketplace
/plugin validate ./plugins/<name>
# activate a skill, run one instructed command
```

`${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_SKILL_DIR}` substitute at load time here — this is the
only harness where they do (see `rules/skill-substitution.md`).

## codex

```bash
uv run --script scripts/sync_codex_plugin_manifests.py --check   # .codex-plugin/ manifest current
uv run --script scripts/validate_codex_skill_activation.py       # activation matrix
```

Codex performs no inline substitution. Runtime text containing `${CLAUDE_PLUGIN_ROOT}`
reaches the model literal — any such occurrence in a codex-targeted surface is a blocker
(tracked per-plugin in `harness_compatibility.json` and issue #3445).

## hermes

```bash
hermes plugins install --local ./plugins/<name>   # or portable plugin.json discovery
hermes plugins enable <name>
# in a session: skills_list shows the plugin's skills; skill_view + activate one
```

Hermes substitutes only `${HERMES_SKILL_DIR}`/`${HERMES_SESSION_ID}` in skill bodies;
`${PLUGIN_ROOT}`/`${PLUGIN_DATA}` expand only in portable `mcp.json` values. Loaded-skill
output includes `[Skill directory: <abs path>]` — skills should resolve relative paths
against it. Portable packages namespace skills as `agent-plugin-<slug>-<hash>`.

## kimi

Kimi substitutes `${KIMI_SKILL_DIR}`, not the Claude Code variables. Install the skill
directory through Kimi's skill mechanism, activate one skill, and confirm instructed
paths resolve. Consult `harness-kimi.md` in the work-ledger measurements location named
above (PR #3427 branch until merged) for discovery roots and substitution facts.

## Recording results

Update the plugin's `verification.<harness>` entry in `harness_compatibility.json`:
`status: verified`, the ISO date, and the issue/PR reference in `notes`. Objective fields
are regenerated — run `uv run --script scripts/generate_harness_compatibility.py` after
editing, and never hand-edit `manifests`/`components`/`blockers`.
