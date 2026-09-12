---
resource: DeepSeek Harness
acronym: dsh
description: "Open-source agent harness with everything-is-a-plugin architecture powered by Cordis"
status: developer preview
release_date: 2026
repository: https://github.com/deepseek-ai/deepseek-harness
documentation: https://deepseek-harness.github.io/deepseek-harness/
research_date: 2026-09-11
source_url: https://github.com/deepseek-ai/deepseek-harness
version_at_research: "unversioned (developer preview, no tagged release at research time)"
license: MIT
language: TypeScript (Node.js)
freshness_tracking:
  last_verified: 2026-09-11
  version_at_verification: "unversioned (developer preview, no tagged release at research time)"
  next_review: 2026-12-11
  last_verified_source: "Repository README.md, AGENTS.md, packages/README.md, SAFETY.md"
---

# DeepSeek Harness

## Overview

**DeepSeek Harness** (`dsh`) is "an open-source agent harness developed by [DeepSeek AI](https://deepseek.com)" built on an **"everything-is-a-plugin architecture and powered by [Cordis](https://github.com/cordiverse/cordis)"** (README.md, lines 5-7). The design philosophy is rooted in compositional spatiotemporal patterns as described in "A Programming Paradigm for Spatiotemporal Composability" (arXiv 2608.25512).

The harness orchestrates AI agent execution by composing modular capabilities—LLM access, shell execution, filesystem operations, web access, subagent delegation—through a plugin registry where every feature is contributed as a plugin. The core agent loop coordinates sessions, model requests, and tool invocations through a unified event model.

## Problem Addressed

Existing agent frameworks couple capabilities tightly to the core loop, making it difficult to extend or replace components independently. DeepSeek Harness addresses this by using Cordis (a capability-plugin framework) to define discrete service contracts—capability seams—where each seam specifies a Service Definition (abstract interface), Service Provider (implementation), and Consumer (model-facing integration). This separation enables swapping providers (e.g., local vs. cloud shell execution) and composing capabilities declaratively from configuration without changing core code.

## Key Features

### Everything-Is-a-Plugin Architecture

Every feature—model access, shell execution, filesystem operations, web browsing, skill management, subagent coordination—registers as a plugin through Cordis. "The harness is assembled from npm packages under `packages/`, grouped by capability family: sessions and the agent loop, model-facing tools, shell and filesystem execution, web access, subagents, and the rest" (packages/README.md, line 12). Plugins register through Cordis effects and event listeners; the system discovers and loads them from configuration (cordis.yml) at runtime.

**Source**: README.md line 7; packages/README.md lines 12-80; AGENTS.md capability seam conventions.

### Modular Capability Families

The harness organizes packages into capability families, each owning a Service Definition / Service Provider / Consumer pattern:

- **Core loop** (`core/`): "Product API spine: sessions, prompts, tools, agent services, and the concrete loop" (packages/README.md, line 31)
- **LLM capability** (`llm/`): "LLM capability family: abstract service + provider adapters" (line 38)
- **Shell execution** (`shell/`): "Bash capability family: executor seam, local impl, model-facing tools" (line 41)
- **Filesystem** (`fs/`): "Filesystem capability family: seam, local impl, model-facing file tools, discovery tools" (line 45)
- **Web access** (`web/`): "Web capability family: seam, search/fetch providers, model-facing web tools" (line 55)
- **Subagent delegation** (`subagent/`): "Subagent capability family: provider-registry contract and model-facing delegation tools" (line 50)
- **Workflow execution** (`workflow/`): "Workflow seam, worker-thread engine, and model-facing `workflow`/`ralph` tools" (line 53)
- **Code execution** (`code-runtime/`): "Code-execution capability family: Service Definition + worker-thread provider + PTC mode Consumer" (line 43)

All packages are scoped `@deepseek-ai/dsh-*` (packages/README.md, line 12).

**Source**: packages/README.md lines 29-75; AGENTS.md convention "A capability seam comprises Service Definition / Service Provider / Consumer roles."

### Session-Centric Event Model

The harness persists agent execution as structured session events. "Model-visible ⟺ logged: anything that reaches a model request must be reconstructable from the session log; a new model-visible input requires a session event" (AGENTS.md conventions). Sessions record tool calls, model responses, state transitions, and user actions in a durable log. "Session version/status" maintains compatibility across API changes through a monotonic schema version and migration chains.

**Source**: AGENTS.md sections on session format, log versioning, and model-visible contracts.

### Multi-Engine Runtime Support

DeepSeek Harness coordinates with Claude Code, Codex, OpenCode, and GitHub's coding agents. The `hooks/` package provides "Hook bridges + the shared Claude Code / Codex wire-protocol library" (packages/README.md, line 64). The SDK (`sdk/`) exposes a "JSON-RPC protocol and TypeScript client/server" for out-of-process integration (line 71). The `acp/` package provides "Automation-only Agent Client Protocol server" (line 72).

**Source**: packages/README.md lines 64, 71, 72; AGENTS.md integration conventions.

### Web UI and Headless Execution

The harness provides a Web GUI (browser-based UI in `client/` and server in `host/`) for interactive use and headless execution for automation. Installation launches the Web UI at `http://127.0.0.1:3080` by default (README.md, line 27). Headless mode runs workflows without a UI; snapshot tests replay recorded sessions through the same profiles.

**Source**: README.md lines 19-27; AGENTS.md test conventions.

## Technical Architecture

### Agent Loop and Session Coordination

The agent loop is the core orchestrator:

1. Receive model response containing tool calls or text
2. Execute tools, recording results in the session event log
3. Prepare the next model request with context, tools, and history
4. Loop until model indicates task completion

Each agent has an "initiator" (the caller—human user, webhook, or automation system) that owns the session lifecycle. "Under `ctx.agents.withInitiator()`, recover the Agent at each orchestration entry, derive `agent.session`, and let operation-local helpers close over it" (AGENTS.md package conventions).

**Source**: AGENTS.md sections on initiator scope and agent loop organization; packages/core/README.md.

### Capability Seam Pattern

Each capability is structured as three orthogonal roles:

1. **Service Definition**: Abstract TypeScript interface (e.g., `ShellService`) describing the capability's contract—methods, parameters, return types
2. **Service Provider**: Concrete implementation registered to the Cordis context (e.g., local shell execution, E2B remote sandbox, pwsh on Windows)
3. **Consumer**: Model-facing tool definitions and execution logic that invoke the service (e.g., `shell_execute` tool that calls `shell.run()`)

Plugins depend on Service Definitions, never on concrete providers. The provider is swappable via configuration without changing consumers. This pattern applies to LLM access, shell execution, filesystem operations, subagent delegation, and every other major feature.

"Extension plugins depend on Service Definitions, never concrete providers" (packages/README.md, line 95). "A capability seam comprises Service Definition / Service Provider / Consumer roles. It is complete, never one role; split only when roles evolve independently" (AGENTS.md).

**Source**: AGENTS.md capability seam conventions; packages/README.md line 95; package READMEs (core, llm, shell, fs, etc.).

### Plugin Loading and Composition

Plugins register through Cordis when the harness loads a profile. A profile is a `cordis.yml` file that declares:

- Which plugins to load (by package name or path)
- Plugin configuration (service bindings, credentials, options)
- Conditional composition (JavaScript expressions for feature flags)

The loader discovers plugins from the workspace (local packages), NPM registry, or GitHub (via the `dsh-plugin` topic). "Cordis allows `!!js` (never `!js`) under plugin `config` and entry `disabled`; other metadata stays literal, so conditional composition also uses overlays" (AGENTS.md).

At runtime, plugins call `ctx.plugin(name, PluginClass, config)` to register. "Every contribution goes through `ctx.effect()` / `ctx.on()`; a registry's `register()` returns the disposer" (AGENTS.md).

**Source**: AGENTS.md conventions on plugin registration and Cordis loading; packages/preset/README.md for profile structure.

### Type System and TypeScript at Scale

The harness compiles under strict TypeScript with `strict: true` and `noImplicitAny`. All exports have JSDoc. "Trust TypeScript at typed same-process boundaries. Do not add runtime validation, fallback behavior, or hostile-input tests solely for values the static interface requires" (AGENTS.md).

The `typert/` package "Type graph generation, artifact loading, and runtime registry" (packages/README.md, line 33) handles type artifacts (JSON schemas, Pydantic models) from external tools and makes them available at runtime for validation and tool schema generation.

**Source**: AGENTS.md type safety section; packages/typert/README.md.

## Installation & Usage

### Install from NPM

```bash
npx @deepseek-ai/dsh web
```

"The command starts the Web UI at `http://127.0.0.1:3080` by default and opens it in the default browser for a local launch. An SSH launch only prints the host URL because the SSH client or editor owns the local forwarded address" (README.md, lines 27-28). Pass `--no-open` to run the server without opening a browser.

**Source**: README.md lines 19-27.

### Install from Source

```bash
git clone https://github.com/deepseek-ai/deepseek-harness.git
cd deepseek-harness
pnpm install
pnpm run build
pnpm dsh web
```

"`pnpm run build` prepares the repository artifacts. `pnpm dsh web` uses those built artifacts without rebuilding" (README.md, lines 41-42). The project requires Node.js `^22.19 || >=24` and pnpm as package manager.

**Source**: README.md lines 29-42; AGENTS.md.

### Run Headless Task

```bash
pnpm dsh --profile headless "task"  # requires DEEPSEEK_API_KEY
```

Headless mode executes agent tasks from the CLI without the Web UI, suitable for automation and CI/CD.

**Source**: AGENTS.md commands section.

### Configuration

Behavior is configured in `cordis.yml` (or overlays for conditional composition). "No hardcoded tunables in plugins: deployment-varying choices are validated `Config` fields changeable from cordis.yml; a `DEFAULT_*` constant or test hook is not configurability" (AGENTS.md). The project reads `DEEPSEEK_API_KEY`, optional `DEEPSEEK_BASE_URL`, and a root `.env` file for real-API tests and demos. "Never commit credentials" (AGENTS.md).

**Source**: AGENTS.md conventions on configuration and secrets.

## Relevance to Claude Code Development

DeepSeek Harness is highly relevant to Claude Code development in four dimensions:

1. **Agent orchestration patterns**: The plugin architecture, capability seams, and session event model are directly applicable to extending Claude Code's agent infrastructure. The separation of Service Definition / Provider / Consumer roles enables building new capabilities without modifying the core loop—a pattern used across Cordis-based systems.

2. **Multi-harness interoperability**: The `hooks/` package bridges Claude Code, Codex, OpenCode, and GitHub's coding agents through a shared wire protocol. Understanding this integration helps coordinate agent development across platforms.

3. **Session persistence and replay**: The session log-based architecture enables recording, replaying, and debugging agent execution. This is directly applicable to Claude Code's session storage, recovery, and audit trails.

4. **Skill and plugin ecosystems**: The `dsh-plugin` discovery mechanism and plugin loading patterns inform how Claude Code can support third-party skill development and plugin composition.

5. **Type-driven tool integration**: The Typert type system and tool schema generation provide a model for representing external tool APIs in a type-safe, model-visible way.

## Limitations and Caveats

**Status**: "DeepSeek Harness is in _developer preview_ and iterating rapidly. **THERE WILL BE COMPATIBILITY-BREAKING CHANGES.**" (README.md, lines 11-13). This is not production software.

**Security**: "DeepSeek Harness is experimental developer-preview software. It has not undergone a security audit and must not be treated as secure or production-ready" (SAFETY.md, lines 6-7). "The project can execute model-generated code and commands, load third-party plugins, and access the network, processes, credentials, and files made available to it. Incorrect model output, defects, misconfiguration, malicious input, or untrusted plugins may damage the host computer, modify or delete files, disclose data or credentials, or cause other unintended effects" (SAFETY.md, lines 9-10).

**Sandboxing**: "Sandboxing, approval prompts, and permission controls can reduce risk, but they do not guarantee isolation or prevent damage. Even correctly enforced restrictions cannot protect resources that the project is allowed to access" (SAFETY.md, lines 11-13).

**External contributions**: "DeepSeek Harness is still at an early stage and under active development. We are sorry that we cannot accept external pull requests at the moment" (CONTRIBUTING.md, line 9). The team invites community plugin development and ecosystem contributions instead.

**API stability**: Public APIs are pre-stable; "update every consumer" when APIs change (AGENTS.md). The `experimental/` package group is unreleased and for internal use only.

**Source**: README.md lines 11-15; SAFETY.md; CONTRIBUTING.md lines 9-12; AGENTS.md API stability section.

## References

- **Repository**: <https://github.com/deepseek-ai/deepseek-harness> (accessed 2026-09-11)
- **Official Documentation**: <https://deepseek-harness.github.io/deepseek-harness/> (accessed 2026-09-11)
- **GitHub Discussions**: <https://github.com/deepseek-ai/deepseek-harness/discussions> (accessed 2026-09-11)
- **Discord Community**: <https://discord.gg/Ycq5dCaS4> (accessed 2026-09-11)
- **Plugin Discovery**: GitHub topic [`dsh-plugin`](https://github.com/topics/dsh-plugin) (accessed 2026-09-11)
- **Cordis Framework**: <https://github.com/cordiverse/cordis> (accessed 2026-09-11)
- **Spatial Composability Paper**: <https://arxiv.org/abs/2608.25512> (accessed 2026-09-11)
- **Official Docs Page**: <https://www.deepseek.com/harness/en/> (attempted 2026-09-11 — inaccessible, connection reset; not counted as accessed)

## Freshness Tracking

**Last Verified**: 2026-09-11

**Sources Read**:
- README.md (primary entry point)
- AGENTS.md (comprehensive development conventions)
- SAFETY.md (experimental status and risk disclosure)
- CONTRIBUTING.md (contribution guidelines)
- LICENSE (MIT)
- packages/README.md (package organization and capability families)

**Official Docs Page**: Attempted to fetch <https://www.deepseek.com/harness/en/> but received a connection reset error. Entry relies on repository documentation.

**Confidence by Section**:
- **Identity/Metadata**: high (repository README, LICENSE, AGENTS.md)
- **Key Features**: high (documented in README, packages/README, AGENTS.md)
- **Technical Architecture**: high (AGENTS.md conventions, package READMEs, module structure)
- **Installation & Usage**: high (README.md, AGENTS.md commands)
- **Limitations**: high (SAFETY.md, CONTRIBUTING.md)
- **Relevance to Claude Code**: medium (inferred from architecture documentation and hooks/SDK packages; not explicitly stated in sources)

**Next Review**: 2026-12-11

**Notes**: This entry focuses on the harness architecture and developer-facing contracts. User-facing features (Web UI capabilities, model behavior, specific tool implementations) are documented in the official repository but were not the focus of this entry. The official docs site was inaccessible; entry is grounded entirely in the repository documentation, which is comprehensive and authoritative.

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Flue](./flue.md) | agent-frameworks | TypeScript agent harness with comparable durable execution model and plugin-based capability composition |
| [Pi Mono](./pi-mono.md) | agent-frameworks | TypeScript monorepo demonstrating unified agent runtime with modular capability packages and multi-interface support |
| [Claude Code Harness](./claude-code-harness.md) | agent-frameworks | Complementary Go-native harness with 5-verb orchestration workflow and guardrail infrastructure patterns |
| [Mission Control](./mission-control.md) | agent-frameworks | Autonomous orchestration engine applying similar multi-stage agent composition and decision-routing patterns |
| [OpenFang](./openfang.md) | agent-frameworks | Rust Agent OS sharing SKILL.md native support and service-layered capability architecture with Cordis pattern equivalents |
| [Orchestra](./orchestra.md) | agent-frameworks | DAG-based task orchestrator with comparable context-aware composition and resumable agent state patterns |
| [Superpowers](./superpowers.md) | agent-frameworks | Skills-driven agent framework sharing capability family organization and subagent coordination patterns |
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | Comprehensive multi-agent system with hook-based automation and extensible skill ecosystem architecture |
