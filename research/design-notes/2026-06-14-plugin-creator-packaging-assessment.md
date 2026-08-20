# Plugin-Creator Packaging Assessment

Date: 2026-06-14

Basis: OpenAI system skill `plugin-creator` and its bundled references:

- `/Users/jamienelson/.codex/skills/.system/plugin-creator/SKILL.md`
- `/Users/jamienelson/.codex/skills/.system/plugin-creator/references/plugin-json-spec.md`
- `/Users/jamienelson/.codex/skills/.system/plugin-creator/references/installing-and-updating.md`
- `/Users/jamienelson/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py`

Scope: packaging and marketplace compliance only. This report does not treat runtime skill loading, automatic skill routing, or chained skill execution as proven.

## Summary

Observed plugin count: `30`

Observed strengths:

- All 30 plugin directories have `.codex-plugin/plugin.json`.
- All 30 plugin manifests include `name`, `version`, `description`, `author`, `interface`, and `skills`.
- All manifest `version` values matched the strict semver pattern enforced by `validate_plugin.py`.
- All manifest `skills` paths are `./skills/` and those paths exist.
- Every discovered skill directory under `plugins/*/skills/*/` had a `SKILL.md`.
- No plugin in this repo currently ships `agents/openai.yaml`.
- Every manifest `mcpServers` path that is present points to `./.mcp.json`, and those files exist.

Current packaging state:

- The full repo now passes the OpenAI `plugin-creator` validator: `TOTAL_FAILING_PLUGINS 0`.
- Packaging compliance was reached by:
  - seeding `interface.defaultPrompt` from existing plugin prose
  - wrapping the seven failing `.mcp.json` files in top-level `mcpServers`
  - removing `disable-model-invocation: true` from the seven rejected skill frontmatters
  - removing the rejected top-level `hooks` field from `orchestrator-discipline/.codex-plugin/plugin.json`

## Validator Execution

The OpenAI `plugin-creator` validator was run successfully after fixing two local execution issues:

1. `uv` needed a writable cache directory under `/private/tmp`
2. `PyYAML` needed to be provided via `uv run --with pyyaml`

Working validation pattern:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache \
PATH=/Users/jamienelson/.local/bin:/Users/jamienelson/.volta/bin:$PATH \
uv run --with pyyaml python3 \
  /Users/jamienelson/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  <plugin-path>
```

Initial repo-wide result:

- `30` plugins checked
- `30` plugins failed validation

Observed failure classes from the real validator:

1. Every plugin failed `interface.defaultPrompt` / `interface.default_prompt` requirement.

2. MCP manifest shape failures:

   - `agentskill-kaizen`
   - `development-harness`
   - `frustration-analyzer`
   - `plugin-creator`
   - `process-siren`
   - `python3-development`
   - `scientific-method`

   The validator expects `.mcp.json` to contain a top-level `mcpServers` object. Current plugin files instead expose server names at top level.

3. Skill frontmatter `disable-model-invocation` failures:

   - `frustration-analyzer` skill `rtfp`
   - `plugin-creator` skill `optimize-claude-md`
   - `process-siren` skill `woo-sailor`
   - `python-engineering` skills `cleanup`, `debug`, `lint`, `review`

4. Unsupported top-level plugin manifest field:

   - `orchestrator-discipline` uses `hooks`, which the current validator rejects.

Final repo-wide result after remediation:

- `30` plugins checked
- `0` plugins failed validation

## Runtime Findings Outside Packaging

Packaging validity did not translate directly into Codex runtime usability.

Verified runtime findings:

1. Plugin-bundled hooks are still not proven usable in Codex CLI `exec`.

   Isolated test:

   - Temp `CODEX_HOME`: `/private/tmp/codex-hook-test-home`
   - Plugin: `orchestrator-discipline@jamie-bitflight-skills`
   - Trace: `/private/tmp/codex-hook-test.jsonl`
   - Prompt forced a direct Bash `ls` call, which should have been blocked by the plugin hook `prevent-bash-tool-misuse.cjs`.

   Observed result:

   - Codex executed `/usr/local/bin/zsh -lc ls`
   - trace showed only command execution items
   - no hook lifecycle items appeared
   - repeating with `--enable plugin_hooks` produced the same result

   Upstream evidence:

   - OpenAI docs say plugin-bundled hooks should load from plugin manifests or default `hooks/hooks.json`:
     [Hooks – Codex](https://developers.openai.com/codex/hooks)
   - OpenAI source/issues still show an active contract mismatch:
     - [openai/codex feature flag notes: `PluginHooks` retained as a removed compatibility flag](https://github.com/openai/codex/blob/main/codex-rs/features/src/lib.rs)
     - [Plugin manifests define `hooks`, but plugin hooks are not loaded into the Codex hooks runtime #17331](https://github.com/openai/codex/issues/17331)
     - [Plugin docs/examples imply plugin-local hooks, but runtime only executes global hooks.json #16430](https://github.com/openai/codex/issues/16430)
     - [validator rejects supported plugin hooks manifest field #27141](https://github.com/openai/codex/issues/27141)

2. Plugin-provided MCP servers that rely on `${CLAUDE_PLUGIN_ROOT}` are currently broken in Codex.

   Isolated test:

   - Plugin: `frustration-analyzer@jamie-bitflight-skills`
   - `codex mcp list` showed the effective registered command as:

     ```text
     uv run --script ${CLAUDE_PLUGIN_ROOT}/mcp/server.py
     ```

   - That placeholder remained literal in Codex's effective MCP config.

   Additional direct probe:

   - In the disposable installed cache, `.mcp.json` was temporarily replaced with a shell probe that wrote selected env vars to temp files before exiting.
   - Probe outputs:
     - `/private/tmp/plugin-mcp-env.txt` contained blank lines for both `PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT`
     - `/private/tmp/plugin-mcp-codex-home.txt` contained a blank line for `CODEX_HOME`

   Conclusion:

   - current plugin-provided MCP subprocesses in this Codex CLI path did not receive usable plugin-root environment variables
   - `${CLAUDE_PLUGIN_ROOT}` was not interpolated before launch

4. A portable repo-side MCP rewrite path is locally supported by Codex runtime behavior.

   Verified local pattern:

   - Installed plugin comparison:
     `/Users/jamienelson/.codex/plugins/cache/sisyphuslabs/omo/4.9.2/components/lsp/.mcp.json`
   - That file uses:
     - relative `args`
     - `cwd: "."`

   Disposable install experiment:

   - temp plugin cache:
     `/private/tmp/codex-hook-test-home/plugins/cache/jamie-bitflight-skills/frustration-analyzer/0.2.27/.mcp.json`
   - rewritten test payload:

     ```json
     {
       "mcpServers": {
         "frustration-analyzer": {
           "command": "uv",
           "args": ["run", "--script", "mcp/server.py"],
           "cwd": "."
         }
       }
     }
     ```

   Observed result:

   - `codex mcp list` rendered:
     - `Command`: `uv`
     - `Args`: `run --script mcp/server.py`
     - `Cwd`: absolute installed cache directory for the plugin
   - direct launcher test from that installed cache directory:

     ```bash
     UV_CACHE_DIR=/private/tmp/uv-cache uv run --script mcp/server.py
     ```

     reached dependency resolution and then failed on blocked PyPI access for `tiktoken`.

   Interpretation:

   - Codex accepted and normalized `cwd: "."` relative to the installed plugin root
   - relative script paths removed the plugin-root interpolation failure
   - remaining failure in this environment was dependency/network related, not path resolution

   Upstream evidence:

   - [Codex CLI does not interpolate `${CLAUDE_PLUGIN_ROOT}` in plugin `.mcp.json` args #19582](https://github.com/openai/codex/issues/19582)
   - [Clarify/support plugin-root relative paths in plugin-provided `.mcp.json` #22842](https://github.com/openai/codex/issues/22842)
   - [Codex auto-mirrors Claude Code marketplaces, breaking MCP handshake for Claude-only plugins #19372](https://github.com/openai/codex/issues/19372)

3. Named-skill validation must still reject manual-file fallback behavior.

   Isolated `frustration-analyzer:rtfp` test:

   - Trace: `/private/tmp/codex-rtfp-test.jsonl`
   - Last message: `/private/tmp/codex-rtfp-test-last.txt`

   Observed result:

   - Codex telemetry emitted `codex.skill.injected` for `frustration-analyzer:rtfp`
   - the named MCP tool was not exposed
   - the agent then manually read cached `SKILL.md` and plugin files and attempted a fallback implementation

   Under the repo's stricter QA standard, that is a failure, not a pass.

## Runtime Naming Observation

Codex runtime was directly observed to treat marketplace entry `name` and `source.path` as independent fields.

Observed behavior:

- `codex plugin list` showed:
  - `rwr@jamie-bitflight-skills`
  - `PATH .../plugins/the-rewrite-room`
- Installing with:

```bash
codex plugin add rwr@jamie-bitflight-skills
```

produced:

```text
Added plugin `rwr` from marketplace `jamie-bitflight-skills`.
Installed plugin root: /Users/jamienelson/.codex/plugins/cache/jamie-bitflight-skills/rwr/2.6.11
```

For this repo, plugin short names such as `rwr` and `dh` are therefore being preserved intentionally. The OpenAI `plugin-creator` expectation that marketplace entry name, manifest name, and folder basename all match is not being adopted as a repo requirement here.

## Plugin-Creator Rules Applied

These rules were taken directly from the OpenAI `plugin-creator` skill and validator:

- Plugin manifests and marketplace entries require `name` fields.
- `skills`, `apps`, and `mcpServers` must use the contract paths expected by validation.
- `interface.displayName`, `shortDescription`, `longDescription`, `developerName`, `category`, and `defaultPrompt`/`default_prompt` are required by `validate_plugin.py`.
- Unsupported manifest fields are rejected by validation. The current validator's allowed top-level keys do not include `hooks`.

## Implications For Next Work

Packaging work is no longer the blocker.

Next work should separate into two runtime tracks:

1. Skill-only and skill+agent plugins
   - validate named-skill usability without manual `SKILL.md` fallback

2. Hook-heavy and MCP-heavy plugins
   - treat current Codex runtime behavior as a first-class constraint
   - do not assume plugin-bundled hooks or `${CLAUDE_PLUGIN_ROOT}`-based MCP commands are presently usable
   - prefer only officially supported Codex packaging/runtime conventions when attempting remediation
   - for plugin-local Python MCP servers, prefer relative script paths plus `cwd: "."` over `${CLAUDE_PLUGIN_ROOT}`

## Not Proven By This Assessment

This assessment does not prove:

- that skills load without manual `SKILL.md` reads
- that named skills can be activated natively in Codex
- that chained skill loads complete
- that hooks or MCP servers actually execute at runtime

Those are separate runtime validation concerns.
