# Claude Variable Compatibility Matrix

Date: 2026-06-08

Goal: identify Claude-specific interpolated variables and environment variables in:

- this repo's plugins
- qualifying dual-target reference repos

Then classify each variable pattern as:

- `portable`
- `portable-with-fallback`
- `rewrite-for-codex`
- `claude-only`

Important distinction:

- some `CLAUDE_*` tokens in `SKILL.md` are harness-side string substitutions
- some `CLAUDE_*` names are true process environment variables visible to hooks, shells, scripts, and MCP servers

These are not interchangeable and must not be analyzed as if they were the same mechanism.

## Evidence Sources

- Official Codex plugin docs: <https://developers.openai.com/codex/plugins/build>
- Qualifying dual-target repo: `obra/superpowers`
- Qualifying dual-target repo: `EveryInc/compound-engineering-plugin`
- Qualifying dual-target repo: `earthtojake/text-to-cad`
- Public Codex issue documenting `${CLAUDE_PLUGIN_ROOT}` MCP handshake failures in practice:
  <https://github.com/openai/codex/issues/19372>

## Search Method

Pattern used:

```text
CLAUDE_[A-Z0-9_]+
${CLAUDE_[A-Z0-9_]+}
$CLAUDE_[A-Z0-9_]+
```

Surfaces classified separately:

- `skills`
- `hooks`
- `mcp`
- `manifest`
- `script`
- `other`

## What The Reference Repos Actually Do

### `compound-engineering-plugin`

This is the strongest explicit cross-harness guidance source.

Observed rules:

- skill directories must be self-contained
- avoid absolute install-cache paths
- avoid platform-specific variables in skills unless a fallback exists
- prefer relative paths in skill content where possible
- where runtime Bash execution needs the skill directory, the repo often uses `${CLAUDE_SKILL_DIR}` in `SKILL.md` command text
- for helper scripts invoked from the skill body, some scripts derive the actual path from `BASH_SOURCE` rather than trusting the environment inside the script
- Codex requires a separate agent-install step because native plugin install does not yet register custom agents

Key implication:

- `CLAUDE_SKILL_DIR` is treated as the least-bad skill-content substitution token for skill-bundled scripts
- `CLAUDE_PLUGIN_ROOT` is not the preferred general skill pattern

### `superpowers`

Observed rules:

- hook commands still use `${CLAUDE_PLUGIN_ROOT}`
- release notes explicitly say some `${CLAUDE_PLUGIN_ROOT}` references were replaced with relative `scripts/` paths
- Windows hook docs spend significant effort on quoting and path conversion around `${CLAUDE_PLUGIN_ROOT}`

Key implication:

- `CLAUDE_PLUGIN_ROOT` persists mainly in hook orchestration and platform-specific launcher cases
- even in a strong dual-target repo, it is not the preferred general-purpose skill pattern

### `text-to-cad`

Observed rules:

- very little direct `CLAUDE_*` usage in plugin skills
- uses `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills` in install scripts, which is installer logic rather than runtime skill logic
- repo guidance emphasizes bundled package code and avoiding sibling-skill imports

Key implication:

- this repo is useful mainly as evidence for self-contained skill/package structure, not for detailed Claude-var translation

## Variable Inventory Summary

### Local repo

Highest-frequency variables:

- `CLAUDE_PLUGIN_ROOT` - dominant across hooks, skills, manifests, MCP, and scripts
- `CLAUDE_PROJECT_DIR`
- `CLAUDE_ENV_FILE`
- `CLAUDE_SKILL_DIR`
- `CLAUDE_CODE_SESSION_ID`

### Reference repos

- `compound-engineering-plugin`
  - mostly `CLAUDE_SKILL_DIR`
  - then `CLAUDE_PLUGIN_ROOT`
- `superpowers`
  - mostly `CLAUDE_PLUGIN_ROOT` in hooks/docs
- `text-to-cad`
  - negligible runtime plugin usage

## Compatibility Matrix

| Variable / Pattern | Where it appears | Reference-repo pattern | Codex portability | Migration rule |
| --- | --- | --- | --- | --- |
| `${CLAUDE_SKILL_DIR}` in `SKILL.md` command text to invoke a co-located script | skills | strongly used by `compound-engineering-plugin` | `portable-with-validation` | treat this as harness substitution, not shell env fallback; keep only where both harnesses are known to substitute it correctly |
| bare relative `bash scripts/x.sh` in skill body | skills | `compound-engineering-plugin` docs discuss this as desirable in theory but not always reliable in Claude runtime | `portable` in principle, but uneven in practice | use only when validated in both harnesses; otherwise keep a harness-substituted skill-local path |
| `${CLAUDE_PLUGIN_ROOT}` in hook commands | hooks | used by `superpowers`; used widely in local repo | `portable` in packaging, runtime still needs validation | keep for hook launch commands when the hook system resolves plugin root; quote carefully for spaces and Windows |
| `${CLAUDE_PLUGIN_ROOT}` in `SKILL.md` to reach plugin-level scripts/assets | skills | discouraged by `compound-engineering-plugin` AGENTS guidance except when pre-resolved/fallback is explicit | `rewrite-for-codex` | move assets/scripts into the skill directory or use a validated skill-content substitution pattern; do not replace it with shell fallback syntax unless that exact surface is proven |
| `${CLAUDE_PLUGIN_ROOT}` inside `.mcp.json` server args | mcp | common in local repo; public Codex issue shows this can fail in Codex practice | `rewrite-for-codex` | do not assume Codex will substitute it correctly; prefer a Codex-specific launcher strategy or mark MCP support unresolved until runtime-proven |
| inline Claude `mcpServers` inside `.claude-plugin/plugin.json` | manifest | present in local repo, not the preferred Codex structure | `portable in packaging` | materialize a root `.mcp.json` and point Codex `mcpServers` at it |
| `CLAUDE_PROJECT_DIR` for project-root paths | hooks, skills, scripts | common in Claude docs/reference material | `portable-with-fallback` at best | prefer current working directory or explicit user/project args; if kept, add fallback behavior and never make it the only path source |
| `CLAUDE_ENV_FILE` | hooks | Claude hook-specific persistence mechanism | `claude-only` unless a Codex hook equivalent is documented and validated | isolate behind Claude-only hook logic; do not build core plugin behavior around it for Codex |
| `CLAUDE_CODE_SESSION_ID` / `${CLAUDE_SESSION_ID}` | hooks, scripts, skills | common for session-correlation logic | `claude-only` unless separately mapped | treat as harness-specific session metadata; add fallback/no-op behavior in Codex |
| `CLAUDE_PLUGIN_DATA` | skills, hooks, MCP docs | Claude plugin persistent-data concept | `rewrite-for-codex` | do not assume the same variable exists; use Codex-documented plugin data surfaces only when explicitly documented |
| `CLAUDE_CODE_*` feature flags (`...EXPERIMENTAL_AGENT_TEAMS`, `...FORK_SUBAGENT`, `...SUBAGENT_MODEL`, etc.) | skills/docs | Claude-only capabilities/config | `claude-only` | document separately; do not claim Codex parity unless there is a Codex-native equivalent |
| `CLAUDE_CODE` presence check for IDE/browser behavior | skills | used in `compound-engineering-plugin` ide-detection docs | `claude-only` | convert to harness-detection logic with Codex-specific branch, not a shared variable |
| `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` in install scripts | installer scripts | used by `text-to-cad` | `claude-only` | keep in harness-specific install tooling, not shared runtime skill logic |

## High-Confidence Migration Rules

### Rule 1: skills should be self-contained

Best evidence:

- `compound-engineering-plugin/AGENTS.md`

Meaning:

- move helper scripts and references into the owning skill directory whenever possible
- remove cross-skill imports and plugin-root lookups from normal skill flows

### Rule 2: distinguish substitution tokens from process env

Best evidence:

- `compound-engineering-plugin` skill and test patterns

Meaning:

- if a skill must execute a bundled script and runtime CWD is not trustworthy, first ask whether the path token is substituted by the harness in `SKILL.md` or expected at shell runtime
- do not introduce shell parameter-expansion fallbacks into `SKILL.md` unless that exact surface is validated
- inside the script itself, prefer self-location via `BASH_SOURCE` or equivalent over assuming the shell exported the same variable

### Rule 3: `${CLAUDE_PLUGIN_ROOT}` is acceptable mainly for hooks, not as a general skill pattern

Best evidence:

- `superpowers` hooks
- `compound-engineering-plugin` AGENTS guidance

Meaning:

- keep it for hook launch paths when necessary
- do not treat it as the default answer for skill content portability

### Rule 4: `.mcp.json` is the weakest portability surface today

Best evidence:

- local runtime validation in this repo
- public Codex issue `#19372`

Meaning:

- even after docs-compliant Codex packaging, MCP runtime parity is not proven
- Claude-style `${CLAUDE_PLUGIN_ROOT}` MCP commands are especially risky in Codex
- MCP support must be runtime-validated plugin-by-plugin

## Local Repo Implications

### Safe first targets

- skill scripts currently using `${CLAUDE_PLUGIN_ROOT}` should usually be refactored toward skill-local `scripts/` plus a validated harness-substituted path pattern
- plugin-level docs lookups like `find ${CLAUDE_PLUGIN_ROOT}/docs` should be treated as harness-specific convenience, not core behavior

### Medium-risk targets

- hook commands using `${CLAUDE_PLUGIN_ROOT}` can likely stay, but must be validated in Codex hook execution

### High-risk targets

- MCP server commands using `${CLAUDE_PLUGIN_ROOT}`
- session/env persistence via `CLAUDE_ENV_FILE`
- task orchestration tied to `CLAUDE_CODE_SESSION_ID`
- Claude-only feature flags for subagent behavior

## Working Definition Of Done

The work is done only when:

1. each plugin has a Codex manifest/marketplace package
2. every `CLAUDE_*` usage is classified
3. every classified usage is either:
   - kept because it is portable,
   - wrapped with a fallback,
   - rewritten to a Codex-safe pattern,
   - or explicitly marked Claude-only
4. skills do not depend on brittle install-path assumptions
5. hooks are both packaged and runtime-validated
6. MCP servers are both packaged and runtime-validated
7. unsupported parity gaps are documented instead of being implied away

That means:

- the target is not just "Codex loads the skills"
- the target is "the same plugin can be distributed to Claude Code and Codex with explicit, validated behavior for each surface"

## Immediate Next Refactors Suggested By This Matrix

1. replace skill-body `${CLAUDE_PLUGIN_ROOT}` script invocations with skill-local `scripts/` only when the replacement path mechanism is validated for that exact skill surface
2. leave hook `${CLAUDE_PLUGIN_ROOT}` paths in place for now, but add Codex hook-execution validation
3. isolate or conditionalize all `CLAUDE_ENV_FILE` / `CLAUDE_CODE_SESSION_ID` behavior
4. treat MCP-heavy plugins as a separate porting lane; do not claim parity until plugin-scoped MCP tools actually surface in Codex sessions

## Incorrect Cleanup Attempt Reverted

I briefly changed some `SKILL.md` examples to use `"${CLAUDE_SKILL_DIR:-.}/..."`.

That was incorrect because it mixed:

- harness-side `SKILL.md` substitution
- shell-side parameter expansion fallback

Those changes were reverted. Future refactors must keep that distinction explicit.

## Remaining `plugin-root -> skill-script` Cases

After the first cleanup pass, the remaining direct `${CLAUDE_PLUGIN_ROOT}/skills/.../scripts/...` `SKILL.md` case is:

- `plugins/development-harness/skills/start-task/SKILL.md`

Why it is deferred:

- it points into a sibling skill (`implementation-manager`) rather than the current skill directory
- the reference-repo guidance favors self-contained skills and warns against cross-skill path coupling
- this needs a structural refactor, not a cosmetic variable swap
