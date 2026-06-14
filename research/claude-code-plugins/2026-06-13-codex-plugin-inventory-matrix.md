# Codex Plugin Inventory Matrix

Date: 2026-06-13

Scope: all 30 directories under `plugins/`, inventoried by subagents against the Codex distribution contract in `2026-06-13-codex-plugin-usability-orchestration.md`.

## Global Findings

- Codex documentation establishes `.codex-plugin/plugin.json`, bundled `skills`, plugin MCP servers, hooks, apps, and marketplace metadata as plugin surfaces.
- No official Codex manifest support was found for Claude-style `commands/` or `agents/` as first-class plugin fields.
- No official Codex `SKILL.md` command pre-resolution or Claude-style `!`` / `${CLAUDE_*}` interpolation equivalent was found.
- Hook packaging and hook execution are separate validation problems. Packaging a hook file does not prove Codex trusts or fires it.
- MCP packaging and MCP runtime availability are separate validation problems. A manifest `mcpServers` path does not prove plugin-scoped MCP tools appear in-session.
- Standalone distribution means repo-relative cross-plugin paths, sibling plugin references, and root-level scripts are risks unless the plugin remains useful without them.

## Plugin Matrix

| Plugin | Class | Distribution Risk | Main Codex Gap | Codex-Native Remediation | Minimal Isolated Validation |
| --- | --- | --- | --- | --- | --- |
| `agent-orchestration` | `static-skill` | Low-medium | Claude `Agent`, `TeamCreate`, `$ARGUMENTS`, and external agent ecosystem references are prose-only in Codex. | Keep behavior-centric skill text; label Claude-only ecosystem assumptions; avoid implying agent runtime parity. | Ask it to delegate a two-part bug fix and verify WHERE/WHAT/WHY plus parallel subtasks. |
| `agentskill-kaizen` | `mcp-dependent` | High | MCP config, commands, and agents depend on Claude session layout and unregistered command/agent semantics. | Make transcript and DB roots configurable; replace harness-only paths; add a portable CLI or Codex-visible entry skill. | Run analysis on a tiny JSONL corpus and verify report output without `${CLAUDE_PLUGIN_ROOT}`. |
| `bash-development` | `static-skill` | Low-medium | Agent names and slash command examples are not Codex-registered surfaces. | Keep as pure reference skill or document agents as Claude-only. | Review a short Bash script and cite bundled portability references. |
| `brainstorming-skill` | `dynamic-skill` | Low-medium | Approval gate is policy-only, not mechanically enforced. | Add a concise Codex checklist for approval-before-implementation. | Ask for constrained feature ideas and verify it asks one clarifying question before ideation. |
| `clang-format` | `static-skill` | Medium | External `clang-format` binary required; asset/index naming drift. | Keep as pure skill; add setup/validate note; fix stale asset reference. | Request a `.clang-format` for a C++ snippet and verify template plus dry-run diff guidance. |
| `commitlint` | `static-skill` | Low-medium | Cross-skill references may be stale or unavailable. | Keep as knowledge skill; inline generic pre-commit advice where needed. | Extract allowed `type-enum` values from sample commitlint configs. |
| `conventional-commits` | `static-skill` | Low | External skill references are not bundled. | Inline minimal commitlint/pre-commit advice or mark references optional. | Generate a breaking-change commit header/footer. |
| `dasel` | `command-dependent` | High | Docs mix v2 and v3 syntax; installer hook/script depends on external binary/network and `${CLAUDE_PLUGIN_ROOT}`. | Fix v3 syntax drift first; expose install/check as explicit Codex workflow; separate docs from install side effects. | Ask for YAML top-level-key inspection and verify stdin-based v3 `dasel` syntax, not `-f`. |
| `development-harness` | `hook-dependent` | Very high | MCP, hooks, agents, child Claude sessions, and `CLAUDE_*` session/env behavior are core workflow pieces. | Create a Codex-native orchestration entrypoint; replace Claude root/session/env assumptions; degrade unsupported child-agent behavior explicitly. | Ask which fallback agent runs when no language manifest exists and verify artifact discovery paths. |
| `dot-dash` | `hook-dependent` | Very high | Core dashboard behavior is hook-driven and tied to Claude home/session transcripts. | Add Codex launcher or standalone server mode; remove Claude-home hardcoding; validate hook firing separately. | Start dashboard and verify token gate plus active session registration. |
| `fastmcp-creator` | `command-dependent` | High | `!` load-time probes and external skill refs are not Codex-portable; runtime packages are external. | Move probes into optional scripts/docs; add graceful missing-package path; replace stale external refs. | Build a minimal `@mcp.tool` server using FastMCP v3 patterns. |
| `frustration-analyzer` | `mcp-dependent` | High | MCP server and agent pipeline assume Claude transcript layout and `${CLAUDE_PLUGIN_ROOT}`. | Register MCP/agent roles only where Codex supports them; make session/output roots configurable; add a portable wrapper. | Run RTFP against a tiny transcript and verify PNG/output artifacts. |
| `gitlab-skill` | `command-dependent` | High | Claude `!`` pre-resolution around `gitlab_context.py`; command docs not surfaced as Codex actions. | Replace pre-resolution with explicit Codex instructions or a portable helper workflow; validate scripts independently. | Validate a GLFM admonition and verify token setup fails gracefully without `GITLAB_TOKEN`. |
| `holistic-linting` | `agent-dependent` | High | Workflow depends on agents, command docs, and report conventions not registered in Codex. | Collapse core flow to a portable lint/review CLI or document agent-dependent degradation. | Run on a scratch Python file and verify resolver/reviewer reports without suppression hacks. |
| `litellm` | `static-skill` | Medium | External skill references and local server assumptions may not be bundled. | Replace cross-skill links with Codex-native guidance; add small local example. | Produce `litellm.completion()` for llamafile preserving `llamafile/...` and `/v1` base. |
| `llamafile` | `command-dependent` | High | External downloads, binary launch, model path, and fixed port assumptions. | Parameterize version/port/model path; add launch/health-check workflow. | Explain default OpenAI-compatible base URL and port. |
| `orchestrator-discipline` | `hook-dependent` | High | Core enforcement is Claude `PreToolUse` hooks/rules; `${CLAUDE_PLUGIN_ROOT}` in hook commands. | Translate guardrails to Codex-supported hooks/policy where possible; vendor rule text into Codex skill docs. | Attempt a diagnostic grep and verify redirect/block behavior if hooks are trusted. |
| `perl-development` | `command-dependent` | Medium | External Perl toolchain commands are assumed; agents are not Codex-registered. | Add preflight/validation checklist or wrapper for `perl -c`, `perlcritic`, and `prove`; label agents optional. | Write a Perl script header and list exact validation commands. |
| `plugin-creator` | `dynamic-skill` | High | Deep helper-agent graph, MCP bootstrap, `${CLAUDE_*}` docs, scratch-path conventions, and repo-relative scripts. | Keep top-level router skills; add required-runtime reference; normalize repo-relative examples or label workspace-only. | Create a new skill and verify valid frontmatter plus `skilllint` route. |
| `process-siren` | `mcp-dependent` | Medium-high | Mermaid MCP uses live `npx ...@latest`; delegator skill references Claude-style subagent dispatch. | Pin or vendor validator path; document Codex skill-only fallback when MCP or agent dispatch is absent. | Convert a 3-step conditional workflow to Mermaid and report quality triage. |
| `python-engineering` | `agent-dependent` | High | Many workflows rely on agents, external skill namespaces, `!` probes, and SAM/development-harness assumptions. | Add a Codex dispatcher or degrade agent routing explicitly; vendor/remove external namespaces; move probes to scripts/docs. | Plan a Python CLI feature and verify router selects CLI/testing guidance. |
| `python3-development` | `mcp-dependent` | Medium-high | Semantic search hard-depends on plugin MCP tool names and network-installed MCP bootstrap. | Add MCP-required preflight and graceful BLOCKED path when tools are absent. | Ask for semantic implementation search and verify tool-backed file/line/snippet output. |
| `rtfp` | `agent-dependent` | High | Real pipeline lives in agents/scripts and Claude transcript layout. | Collapse agent split into script entrypoints; make session root configurable. | Feed fake transcript and verify strongest reaction plus PNG output. |
| `scientific-method` | `mcp-dependent` | High | MCP, hook, agent, slash-command behavior not fully represented in Codex; version drift exists. | Sync metadata; collapse hook/agent roles into skills or mark unavailable; validate MCP separately. | Start synthetic investigation and expose experiment registry tools. |
| `summarizer` | `hook-dependent` | High | Validation hook and subagent/team orchestration use Claude-specific runtime constructs and `$SKILL_DIR`. | Replace hook enforcement with Codex-native validator/test harness; make templates discoverable without env-token paths. | Summarize one Markdown file and verify required structured sections and sources. |
| `the-rewrite-room` | `command-dependent` | High | Slash commands, agents, hooks, external plugin dependencies, and GitLab validator path are not Codex-native. | Add top-level router skill or explicit Codex command equivalent; document required external plugins and tokens. | Run authoring workflow on GitLab README draft and verify STATUS block plus GLFM validation. |
| `twelve-factor-app` | `static-skill` | Low | Placeholder references/scripts reduce usefulness, but core skill is portable. | Replace placeholders with concrete checklists/examples when desired. | Ask for Factor III review of hardcoded config and verify tool-free env-var guidance. |
| `uv` | `static-skill` | Low-medium | README references repo-root update script and sibling `python3-development` standards file. | Vendor shared standards or label repo-maintenance script as repo-only. | Create and run a PEP 723 script without sibling plugin dependencies. |
| `verification-gate` | `static-skill` | Low-medium | Claude tool names and missing reference file reduce Codex fit; enforcement is prose-only. | Rewrite terminology to Codex action model and fix/remove broken reference. | Diagnose missing PEP 723 dependency and verify it does not jump to `uv sync`. |
| `xdg-base-directory` | `static-skill` | Low | No major runtime gap; pure guidance skill. | No immediate remediation beyond optional prompt tests. | Resolve unset/relative XDG env var cases correctly. |

## Remediation Order

1. **Safe static fixes:** `xdg-base-directory`, `conventional-commits`, `twelve-factor-app`, `commitlint`, `uv`, `verification-gate`, `clang-format`, `litellm`, `bash-development`, `agent-orchestration`.
2. **Command-dependent fixes:** `gitlab-skill`, `dasel`, `fastmcp-creator`, `llamafile`, `perl-development`, `holistic-linting`, `the-rewrite-room`.
3. **MCP-dependent fixes:** `process-siren`, `frustration-analyzer`, `scientific-method`, `python3-development`, `agentskill-kaizen`.
4. **Hook/agent-heavy fixes:** `orchestrator-discipline`, `summarizer`, `dot-dash`, `development-harness`, `python-engineering`, `rtfp`, `plugin-creator`.

## Acceptance Notes

- Static skills can become `works` after isolated install plus natural skill-selection validation.
- Command-dependent plugins should become `works-with-degradation` unless Codex-native command entrypoints are added and validated.
- MCP-dependent plugins remain `packaged-only` or `works-with-degradation` until plugin-scoped MCP tools are visible in a Codex session.
- Hook-dependent plugins remain `packaged-only` or `works-with-degradation` until hook trust and firing are proven in an isolated install.
