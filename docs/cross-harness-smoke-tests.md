# Cross-Harness Smoke Tests

The four harnesses installed on the maintainer's host: claude-code, codex, hermes, kimi.
Run these when a plugin's cross-harness configuration changes, and when recording a
`verified` status in `harness_compatibility.json`. Capability facts per harness (what it
substitutes, where it discovers plugins, which env vars it exports) live in
`plugins/development-harness/docs/work-ledger/measurements/harness-*.md` — on PR #3427's
branch until it merges. Read the matching file before interpreting a failure; this doc
deliberately does not restate them. Each measurement file carries per-claim citations to
source files at a pinned HEAD; these URLs are the exact upstream locations behind the
specific facts this doc relies on:

| Fact used here | Exact source |
|---|---|
| `${PLUGIN_ROOT}`/`${PLUGIN_DATA}` expansion in portable `mcp.json` only | Agent Plugins spec §9: <https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.0.0.md#9-environment-variables-and-placeholder-expansion> |
| Claude Code substitution scope (and the two-docs-page disagreement) | <https://code.claude.com/docs/en/skills> and <https://code.claude.com/docs/en/plugins-reference> — see `rules/skill-substitution.md` for the canary result this repo relies on |
| Codex performs no inline substitution | `harness-codex.md` measurements (codex-rs source citations) + issue #3445 |
| Hermes substitution/namespace facts | `harness-hermes.md` measurements, citing <https://github.com/NousResearch/hermes-agent> (`agent/skill_preprocessing.py`, `hermes_cli/agent_plugins.py`) |
| Hermes install forms (no `--local` flag) | live `hermes plugins install --help` — the CLI is the source of truth |
| Kimi discovery roots and `${KIMI_SKILL_DIR}` | `harness-kimi.md` measurements, citing <https://github.com/MoonshotAI/kimi-code/tree/main/docs/en> |

## Common to every harness

1. Install the plugin through that harness's own install mechanism (not the authoring
   checkout — an installed consumer is the point of the test).
2. The plugin's components are discovered: every skill listed, MCP servers (if any)
   connected, no silent skips.
3. Activate one representative skill and confirm it renders and executes: any path,
   script, or command the skill body instructs the agent to run resolves against the
   *installed* location. A literal unresolved substitution token reaching a shell is a
   failure.
4. For plugins with MCP servers: call one read-only tool through the harness's MCP
   client and confirm a well-formed response.

## claude-code

```bash
claude --plugin-dir ./plugins/<name>        # or install from the local marketplace
/plugin validate ./plugins/<name>
```

Substitution behavior: `rules/skill-substitution.md` (repo-local, canary-tested).

## codex

```bash
uv run --script scripts/sync_codex_plugin_manifests.py --check   # .codex-plugin/ manifest current
# per-skill activation evidence (--target and --evidence-file are required):
uv run --script scripts/validate_codex_skill_activation.py \
  --target <plugin-id>:<skill> --evidence-file <evidence.json>
```

No inline substitution — blocker counts are tracked in `harness_compatibility.json`
(`blockers`) and issue #3445. Codex reads a root `plugin.json` as an Agent Plugins v1
manifest when its `$schema` starts `https://agent-plugins.org/schemas/`, else falls back
to `.codex-plugin/plugin.json` — one portable manifest can serve both codex and hermes.
Substitution exists only in plugin hooks: hook processes get `PLUGIN_ROOT` +
`CLAUDE_PLUGIN_ROOT` env vars and `${KEY}` replacement in hook command strings.

## hermes

```bash
# local test: copy or symlink the plugin dir into ~/.hermes/plugins/<name>, then
hermes plugins enable <name>
# or from a pushed branch:
hermes plugins install <git-url> --ref <40-char-sha> --enable
# in a session: skills_list shows the plugin's skills; skill_view + activate one
```

There is no `--local` flag; `hermes plugins install` takes a catalog name, Git URL, or
`owner/repo`. Portable `plugin.json` packages install disabled — enable explicitly.
Substitution and namespacing facts: `harness-hermes.md` (work-ledger measurements).

## kimi

Install the skill directory through Kimi's skill mechanism, activate one skill, confirm
instructed paths resolve. Discovery roots and substitution facts: `harness-kimi.md`
(work-ledger measurements).

## Recording results

Update the plugin's `verification.<harness>` entry in `harness_compatibility.json`:
`status: verified`, the ISO date, and the issue/PR reference in `notes`. Objective fields
are regenerated — run `uv run --script scripts/generate_harness_compatibility.py` after
editing, and never hand-edit `manifests`/`components`/`blockers`.
