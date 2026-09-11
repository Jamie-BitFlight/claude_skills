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
claude --plugin-dir ./plugins/<name>        # official "Test your plugin" flow
/plugin validate ./plugins/<name>           # or: claude plugin validate ./plugins/<name>
claude plugin validate .                    # from the marketplace root: checks marketplace.json
                                            # schema, duplicate names, source path traversal
claude --debug                              # plugin loading details: manifest errors,
                                            # skill/agent/hook registration, MCP init
```

Mid-session: `/reload-plugins` picks up changes without a restart; the `/plugin`
manager's Errors tab surfaces load failures. Zip/CI artifact testing:
`claude --plugin-url <url>`. Consumer-path test: `/plugin marketplace add
./.claude-plugin/marketplace.json` → `/plugin install <plugin>@jamie-bitflight-skills`.
Official guidance: <https://code.claude.com/docs/en/plugins>.

Substitution behavior: `rules/skill-substitution.md` (repo-local, canary-tested).

## codex

```bash
uv run --script scripts/sync_codex_plugin_manifests.py --check   # .codex-plugin/ manifest current
# per-skill activation evidence (--target and --evidence-file are required):
uv run --script scripts/validate_codex_skill_activation.py \
  --target <plugin-id>:<skill> --evidence-file <evidence.json>
# official discovery checks (no CLI validate command exists in Codex):
codex plugin marketplace add owner/repo        # or ./local-root
codex plugin marketplace list                  # prints each marketplace + resolved root path
```

Post-install: browse `/plugins`, install, then **start a new session** before using
bundled skills/tools. Enablement check: `.codex/config.toml`
`[plugins."<name>@local-repo"] enabled = true`. Skill discovery: `/skills` or
`$`-mention; skill changes are detected automatically — restart if an update doesn't
appear. Official guidance: <https://developers.openai.com/codex/skills> and
<https://developers.openai.com/codex/plugins/build>.

No inline substitution — blocker counts are tracked in `harness_compatibility.json`
(`blockers`) and issue #3445. Codex reads a root `plugin.json` as an Agent Plugins v1
manifest when its `$schema` starts `https://agent-plugins.org/schemas/`, else falls back
to `.codex-plugin/plugin.json` — one portable manifest can serve both codex and hermes.
Substitution exists only in plugin hooks: hook processes get `PLUGIN_ROOT` +
`CLAUDE_PLUGIN_ROOT` (plus `PLUGIN_DATA`/`CLAUDE_PLUGIN_DATA`) env vars and `${KEY}`
replacement in hook command strings.

## hermes

```bash
# official pre-install gates:
hermes plugins validate ./plugins/<name>     # catalog-admission validation (--json for CI)
hermes plugins doctor ./plugins/<name> --ci  # runs real discovery/manifest/register(ctx)/hook/tool
                                             # registry paths; exits non-zero on error
# local test: copy or symlink the plugin dir into ~/.hermes/plugins/<name>, then
hermes plugins enable <name>
# or from a pushed branch:
hermes plugins install <git-url> --ref <40-char-sha> --enable
# in a session: skills_list shows the plugin's skills; skill_view + activate one
HERMES_PLUGINS_DEBUG=1 hermes plugins list   # loading diagnostics
```

There is no `--local` flag; `hermes plugins install` takes a catalog name, Git URL, or
`owner/repo`. Portable `plugin.json` packages install disabled — enable explicitly.
`hermes plugins compat <path>` applies only to native-Python plugins (portable v1
packages import no Python). Official guidance: the developer guide's "Step 6: Test it"
(<https://hermes-agent.nousresearch.com/docs/developer-guide/plugins>).
Substitution and namespacing facts: `harness-hermes.md` (work-ledger measurements).

## kimi

```text
/plugins info <id>     # the ONLY official validation surface: plugin details + diagnostics;
                       # broken manifests / unsafe paths appear here (kimi doctor covers only
                       # config.toml/tui.toml — not plugins)
/reload  (or /new)     # required after install/enable/disable/remove — the current session
                       # does not update; plugin MCP servers start only after this
/skill:<name>          # activate a skill in a NEW session
```

Managed-copy trap: local installs are **copied** to `$KIMI_CODE_HOME/plugins/managed/<id>/`
— editing the source directory after install has no effect; reinstall to test a change.
The smoke test must exercise the managed copy, not the source. Skill frontmatter hard
requirement: `name` AND `description` must both be explicit or parsing fails. No official
testing/validation page exists beyond `/plugins info` (checked all of docs/en). Official
guidance: <https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/customization/plugins.md>.
Discovery roots and substitution facts: `harness-kimi.md` (work-ledger measurements).

## Recording results

Update the plugin's `verification.<harness>` entry in `harness_compatibility.json`:
`status: verified`, the ISO date, and the issue/PR reference in `notes`. Objective fields
are regenerated — run `uv run --script scripts/generate_harness_compatibility.py` after
editing, and never hand-edit `manifests`/`components`/`blockers`.

## Plugin-root resolution strategies

How to author a plugin so the "Common" checks pass on every harness. The spec's
`${PLUGIN_ROOT}` expansion exists only for stdio MCP subprocesses (spec §9.1) — skills-only
plugins (22 of 29 here) cannot use it. Strategies, all audited against upstream source
(this doc's citation table):

| Strategy | claude-code | codex | hermes | kimi | Tradeoff |
|---|---|---|---|---|---|
| **1. Skill-local relative paths** — assets in `skills/<name>/scripts/`, referenced as `scripts/foo.py` | ✅ | ✅ | ✅ | ✅ | Zero machinery; every harness resolves relative to the skill dir. Assets can't be shared between skills without duplication. |
| **2. Self-locating launcher** — tiny script derives plugin root via `Path(__file__).resolve().parents[N]`, execs the real entrypoint | ✅ | ✅ | ✅ | ✅ | The only token-free way to reach plugin-root shared code. `parents[N]` depth must match the installed layout. |
| **3. Hook env vars** — `CLAUDE_PLUGIN_ROOT` / `PLUGIN_ROOT`+`CLAUDE_PLUGIN_ROOT` / `KIMI_PLUGIN_ROOT` | ✅ hooks | ✅ hooks | ✅ hooks | ✅ hooks | Hook processes only, variable name differs per harness — hooks stay per-harness surface. Useless in skill/agent prose. |
| **4. `${CLAUDE_PLUGIN_ROOT}` in SKILL.md text** | ✅ | ❌ literal | ❌ literal | ❌ literal | Claude-only; the failure class tracked in `blockers` and #3445. Retire to generated Claude-only surfaces. |
| **5. Agent discovers the path at runtime** (`find ~/.hermes/plugins …`) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Rejected: hermes namespaces are `agent-plugin-<slug>-<sha8>`, install roots differ per harness — brittle at the layer that must be reliable. |

**Default: strategy 1; strategy 2 where code is genuinely shared at plugin root** (e.g.
`dh`'s `sam_schema/cli.py` behind a skill-local `scripts/sam` launcher). Both are pure
filesystem mechanics — no token, no shell assumption, no per-harness variance.
