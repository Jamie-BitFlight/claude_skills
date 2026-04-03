---
resource: gitagent
category: agent-frameworks
status: current
accessed: 2026-03-29
next_review: 2026-06-29
---

# GitAgent — Framework-Agnostic, Git-Native Agent Standard

## Overview

GitAgent is an open-source framework and specification for defining AI agents as git repositories. It provides a portable, version-controlled, and framework-agnostic standard for AI agent definitions that works across Claude Code, OpenAI, LangChain, CrewAI, AutoGen, and other AI frameworks. The core premise: "Clone a repo, get an agent."

GitAgent is maintained by the open-gitagent organization and published as the npm package `@shreyaskapale/gitagent`. Current version: **v0.1.7** (as of 2026-03-29). Specification version: v0.1.0 (aligned with Spec section in repository).

**Repository**: <https://github.com/open-gitagent/gitagent>
**npm package**: @shreyaskapale/gitagent
**Homepage**: <https://gitagent.sh>
**License**: MIT

## Problem Addressed

Every AI framework (Claude Code, OpenAI Agents SDK, LangChain, CrewAI, AutoGen) implements agent definitions differently — mixing config files, Jinja2 templates, Python code, and YAML. There is no universal, portable way to define an agent that works across frameworks.

GitAgent solves this by extracting the agent identity layer (prompts, rules, roles, tool schemas, compliance policies) into a portable, versionable, git-native format. The identity is decoupled from runtime orchestration: what ports cleanly (system prompts, persona definitions, hard constraints, tool schemas, role/segregation policies, model preferences) stays in the agent definition; what stays in the framework (runtime loops, live tool execution, memory I/O, state machines) remains there.

Key use cases:
1. **Portability**: Define an agent once, export to multiple frameworks without rewriting identity
2. **Version control**: Every change to agent behavior is a git commit with full history, diffs, and rollback
3. **Compliance**: First-class support for FINRA Rule 3110 (supervision), Rule 4511 (recordkeeping), SEC Regulation S-P (privacy), and Federal Reserve SR 11-7 (model risk management)
4. **Composition**: Agents can extend parent agents, declare dependencies, and delegate to sub-agents
5. **Collaboration**: Fork public agents, customize identity, and PR improvements upstream

## Key Statistics

- **GitHub stars**: 2,160 (as of 2026-03-29)
- **GitHub forks**: 240 (as of 2026-03-29)
- **Language**: TypeScript
- **Repository size**: 24.6 MB
- **Open issues**: 14 (as of 2026-03-29)
- **Created**: 2026-02-24
- **Last updated**: 2026-03-29
- **Node version requirement**: >= 18
- **npm downloads**: Available at <https://www.npmjs.com/package/@shreyaskapale/gitagent>

## Key Features

### 1. Git-Native Agent Definitions

Agents are entire git repositories. Required files are minimal:
- **`agent.yaml`** — manifest with name, version, model preferences, compliance configuration
- **`SOUL.md`** — identity, personality, communication style, values

Every change (skill addition, rule refinement, model preference update) is a git commit with full version history, diffs, and rollback capability.

**Mechanism**: Git becomes the version control and collaboration layer for agent definitions. Users use standard git workflows (branches, PRs, tags) for agent governance. `git diff` shows exactly what changed between agent versions; `git blame` traces every line to who wrote it and when.

### 2. Framework-Agnostic Exports

The same agent definition can be exported to multiple frameworks via adapters. Each adapter reads the git-native files and generates output in the target framework's format.

**Supported export targets** (from package.json keywords and docs.md):
- **system-prompt** — Concatenated system prompt (works with any LLM API)
- **claude-code** — CLAUDE.md compatible format for Claude Code
- **openai** — OpenAI Agents SDK Python code
- **crewai** — CrewAI YAML configuration
- **lyzr** — Lyzr Studio agent
- **github** — GitHub Actions agent
- **git** — Git-native execution with auto-detection
- **opencode** — OpenCode instructions + config
- **gemini** — Google Gemini CLI (GEMINI.md + settings.json)
- **openclaw** — OpenClaw format
- **nanobot** — Nanobot format
- **cursor** — Cursor `.cursor/rules/*.mdc` files

**Usage example**:
```bash
gitagent export --format system-prompt     # Outputs concatenated prompt
gitagent export --format claude-code       # Outputs CLAUDE.md
gitagent export --format openai            # Outputs Python agent code
```

### 3. Regulatory Compliance First-Class Support

GitAgent has embedded compliance configuration for financial services and other regulated domains. The `compliance` section in agent.yaml defines:

**Risk Classification & Frameworks**: `risk_tier` (low, standard, high, critical) and applicable frameworks (FINRA, Federal Reserve, SEC, CFPB, OCC, FDIC, BSA/AML, EU AI Act, UK FCA, etc.)

**FINRA Rule 3110 (Supervision)**: Configuration for human-in-the-loop policies, escalation triggers (low confidence, specific action types, detected errors), override capability, and kill switch (immediate halt).

**FINRA Rule 4511 & SEC 17a-4 (Recordkeeping)**: Audit logging (structured JSON or plaintext), retention periods (6 years minimum per 4511), immutable logs, and log contents (prompts/responses, tool calls, decision pathways, model version, timestamps).

**Federal Reserve SR 11-7 (Model Risk Management)**: Model inventory tracking, validation cadence (annual, quarterly, change-based), conceptual soundness documentation, ongoing monitoring, outcomes analysis, drift detection, and parallel testing.

**Data Governance**: PII handling policies (redact, encrypt, prohibit, allow), data classification (public, internal, confidential, restricted), consent requirements, cross-border status, bias testing, and Less Discriminatory Alternative (LDA) search for CFPB.

**Communications Compliance (FINRA Rule 2210)**: Communication type (correspondence, retail, institutional), pre-review requirements, fair/balanced enforcement, no misleading statements, and customer AI disclosures.

**Vendor Management (SR 23-4)**: Due diligence completion, SOC 2 report requirements, vendor AI change notification, and fourth-party risk assessment.

**Segregation of Duties (SOD)**: Define roles (maker, checker, executor, auditor) with permissions, conflict matrix (which role pairs cannot be held by the same agent), handoff workflows (require multi-agent participation), and enforcement level (strict blocks deployment; advisory issues warnings).

Example compliance configuration from spec:
```yaml
compliance:
  risk_tier: high
  frameworks: [finra, federal_reserve, sec]
  supervision:
    human_in_the_loop: always
    kill_switch: true
  recordkeeping:
    audit_logging: true
    retention_period: 7y
    immutable: true
  segregation_of_duties:
    roles:
      - id: analyst
        permissions: [create, submit]
      - id: reviewer
        permissions: [review, approve, reject]
    conflicts: [[analyst, reviewer]]
    enforcement: strict
```

### 4. Skills System

Agents declare reusable capability modules. Skills are stored in a `skills/` directory with:
- **SKILL.md** — Frontmatter metadata + skill instructions
- **scripts/** — Executable helpers (bash, Python, Node.js)
- **references/** — Supporting documentation
- **assets/** — Templates, schemas
- **examples/** — Example inputs and outputs

Skills can be discovered, installed from git repositories, and composed into workflows.

**CLI example**:
```bash
gitagent skills list
gitagent skills search "code-review"
gitagent skills install https://github.com/org/code-review-skill.git
```

### 5. Composable Agent Hierarchies

Agents can extend parent agents and compose with dependencies:

```yaml
extends: https://github.com/org/base-agent.git
dependencies:
  - name: fact-checker
    source: https://github.com/org/fact-checker.git
    version: ^1.0.0
    mount: agents/fact-checker
```

Sub-agents are defined in an `agents/` directory, either as full agent directories (containing agent.yaml, SOUL.md) or lightweight markdown files (agents/{name}.md). This enables hierarchical agent structures where parent agents delegate tasks to specialized sub-agents.

### 6. Deterministic Workflows (SkillsFlow)

Multi-step workflows are defined in a `workflows/` directory as YAML with deterministic execution:

```yaml
name: code-review-flow
triggers: [pull_request]

steps:
  lint:
    skill: static-analysis
    inputs:
      path: ${{ trigger.changed_files }}

  review:
    agent: code-reviewer
    depends_on: [lint]
    prompt: "Focus on security and performance"
    inputs:
      findings: ${{ steps.lint.outputs.issues }}

  test:
    tool: bash
    depends_on: [lint]
    inputs:
      command: "npm test -- --coverage"

  report:
    skill: review-summary
    depends_on: [review, test]
    conditions:
      - ${{ steps.review.outputs.severity != 'none' }}
    inputs:
      review: ${{ steps.review.outputs.comments }}
      coverage: ${{ steps.test.outputs.report }}
```

**Mechanism**: Each step declares `depends_on` ordering and `conditions` for execution. Data flows between steps via template syntax `${{ steps.step-name.outputs.field }}`. No LLM discretion on execution order — the workflow follows the same path every time.

### 7. Live Agent Memory & Knowledge

Agents can maintain persistent cross-session state:

**memory/** directory:
- `MEMORY.md` — Working memory (200 line max) updated at runtime
- `memory.yaml` — Configuration for memory behavior
- `archive/` — Historical snapshots

**knowledge/** directory:
- `index.yaml` — Retrieval hints for knowledge documents
- Markdown, CSV, PDF, or other readable formats
- Organized as a hierarchical tree with embeddings for semantic reasoning

Memory persists across sessions; agents can update and reference their own memory.

### 8. Compliance Auditing & Validation

The CLI includes audit and validation commands:

```bash
gitagent validate                    # Validate agent.yaml against spec, check SOUL.md, verify skills/tools exist
gitagent validate --compliance       # Validate compliance configuration against regulatory frameworks
gitagent audit                       # Generate full compliance audit report with checklist
gitagent info                        # Display agent summary (name, version, skills, tools, compliance)
```

Validation checks:
- **Schema validation** — agent.yaml against strict JSON schema using AJV
- **Reference checking** — Verify that referenced skills, tools, and sub-agents exist
- **Compliance validation** — When `--compliance` flag used, check that compliance configuration is complete for declared frameworks
- **Audit report** — Comprehensive checklist of compliance controls mapped to agent configuration

### 9. Framework Porting Patterns

GitAgent includes patterns for porting agents from existing frameworks (NVIDIA AIQ, LangGraph, CrewAI) without rewriting. The porting extracts the identity layer into git-native format while leaving runtime orchestration in the framework.

**Example**: NVIDIA's AIQ Deep Researcher (a 3-agent hierarchy for cited research reports) was ported to show how identity — system prompts, persona definitions, hard constraints, tool schemas, role/SOD policies, model preferences — translates cleanly to gitagent while framework-specific runtime code (state machines, graph wiring, iterative loops) stays in Python.

### 10. CLI Commands

Main commands from source code and documentation:

| Command | Purpose |
|---------|---------|
| `gitagent init [--template]` | Scaffold new agent (minimal, standard, full templates) |
| `gitagent validate [--compliance]` | Validate against spec and regulatory requirements |
| `gitagent info` | Display agent summary |
| `gitagent export --format <fmt>` | Export to other formats (system-prompt, claude-code, openai, crewai, etc.) |
| `gitagent import --from <fmt> <path>` | Import from existing framework format |
| `gitagent run <source> --adapter <a>` | Run agent from directory or git repo with specified adapter |
| `gitagent install` | Resolve and install git-based dependencies |
| `gitagent audit` | Generate compliance audit report |
| `gitagent skills <cmd>` | Manage skills (search, install, list, info) |
| `gitagent lyzr <cmd>` | Manage Lyzr Studio agents (create, update, info, run) |

## Technical Architecture

### Core Components (from source code structure)

**Loaders** (`src/utils/`):
- `loader.ts` — Parse and load agent.yaml manifest, SOUL.md, RULES.md, and related files
- `skill-loader.ts` — Extract metadata from SKILL.md files (frontmatter parsing)
- `schemas.ts` — Load JSON schemas for validation (agent-yaml, skill-yaml, etc.)
- `git-cache.ts` — Clone and cache git repositories locally

**Commands** (`src/commands/`):
- `init.ts` — Scaffold new agent with template
- `validate.ts` — Schema and reference validation, compliance checks
- `export.ts` — Convert agent to target format via adapters
- `import.ts` — Convert from framework format to gitagent
- `run.ts` — Execute agent with specified runner/adapter
- `audit.ts` — Generate compliance audit report
- `skills.ts` — Manage skills (search registry, install, list)
- `lyzr.ts` — Lyzr Studio integration

**Adapters** (`src/adapters/`):
One adapter per supported framework, each responsible for reading gitagent files and generating framework-specific output:
- `claude-code.ts` — Generate CLAUDE.md from agent.yaml, SOUL.md, RULES.md, skills, compliance
- `openai.ts` — Generate OpenAI Agents SDK Python code
- `crewai.ts` — Generate CrewAI YAML
- `lyzr.ts` — Generate Lyzr Studio agent
- `system-prompt.ts` — Concatenate into system prompt
- `github.ts`, `gemini.ts`, `cursor.ts`, `openclaw.ts`, `nanobot.ts`, `opencode.ts` — Additional frameworks
- `shared.ts` — Shared utilities for adapter implementations

**Runners** (`src/runners/`):
Correspond to adapters but for execution (run command), not export:
- `claude.ts` — Run via Claude Code
- `openai.ts` — Run via OpenAI Agents SDK
- `crewai.ts` — Run via CrewAI
- `lyzr.ts` — Run on Lyzr Studio
- `git.ts` — Auto-detect and run (infer best adapter from repo hints)
- Additional runners for other frameworks

**Validators** (within `validate.ts`):
- Schema validation using AJV (Ajv JSON validator)
- Reference validation (check skill/tool/agent existence)
- Compliance validation (frameworks, supervision, recordkeeping, SOD)
- Manifest loading and error reporting

### Data Flow

**Export flow**:
1. User invokes `gitagent export --format {fmt} -d {path}`
2. `export.ts` loads agent manifest via `loader.ts`
3. Selected adapter (e.g., `claude-code.ts`) reads SOUL.md, RULES.md, skills metadata, compliance config
4. Adapter generates output in target framework format
5. Output written to stdout or file

**Run flow**:
1. User invokes `gitagent run -d {path} --adapter {a}`
2. `run.ts` loads agent via `loader.ts`
3. Selected runner (e.g., `openai.ts`) initializes framework-specific client
4. Runner executes agent with provided prompt/input
5. Results streamed to stdout

**Validation flow**:
1. User invokes `gitagent validate -d {path} [--compliance]`
2. `validate.ts` loads manifest, SOUL.md, skills, tools, sub-agents
3. AJV schema validation on manifest
4. Reference existence checks (skills, tools, agents)
5. If `--compliance` flag: compliance configuration validation against frameworks
6. Report generated with errors and warnings

### Extensibility Points

**Adapters**: Adding a new framework involves:
1. Create `src/adapters/{framework}.ts` exporting `exportTo{Framework}(dir: string): string`
2. Read gitagent files (manifest, SOUL.md, RULES.md, skills, compliance)
3. Generate framework-specific output (Python code, YAML, config files)
4. Add to adapter index in `src/adapters/index.ts`

**Runners**: Adding a new execution runtime involves:
1. Create `src/runners/{framework}.ts` exporting `run(dir: string, input: string): Promise<string>`
2. Initialize framework client with loaded agent manifest
3. Execute agent with input
4. Return result
5. Add to runner index in `src/runners/index.ts`

**Validators**: Compliance validators can be extended by adding new framework entries to the validation logic in `validate.ts`.

## Installation & Usage

### Installation

```bash
npm install -g @shreyaskapale/gitagent
# or
npm install @shreyaskapale/gitagent
```

**Verify**:
```bash
gitagent --version   # v0.1.7
gitagent --help
```

### Quick Start

**Create a new agent**:
```bash
gitagent init --template standard --dir ./my-agent
```

Generated structure:
- `agent.yaml` — Manifest with name, version, description
- `SOUL.md` — Identity and personality
- `RULES.md` — Hard constraints
- `skills/` — Skill directories
- `tools/` — Tool definitions
- `examples/` — Calibration interactions

**Validate**:
```bash
gitagent validate -d ./my-agent
gitagent validate -d ./my-agent --compliance  # If compliance config present
```

**Export to Claude Code**:
```bash
gitagent export --format claude-code -d ./my-agent
# Output: CLAUDE.md with agent identity, SOUL, RULES, skills, compliance
```

**Run with Claude Code adapter**:
```bash
gitagent run -d ./my-agent --adapter claude-code --prompt "Hello"
```

**Run from a git repository**:
```bash
gitagent run -r https://github.com/user/my-agent --prompt "Summarize this project"
```

**Run with auto-detected adapter** (git runner):
```bash
gitagent run -r https://github.com/user/my-agent --adapter git --prompt "Hello"
# Auto-detects best adapter from repo hints (.gitagent_adapter file)
```

## Examples & Patterns

### Human-in-the-Loop for RL Agents
Agents learning new skills or writing to memory open a branch + PR for human review before merging.

### Segregation of Duties
Multi-agent workflows where no single agent controls a critical process end-to-end. Define roles (maker, checker, executor, auditor), conflict matrix (which roles can't be the same agent), and handoff workflows.

Example from README:
```yaml
compliance:
  segregation_of_duties:
    roles:
      - id: maker
        description: Creates proposals
        permissions: [create, submit]
      - id: checker
        description: Reviews and approves
        permissions: [review, approve, reject]
    conflicts: [[maker, checker]]  # maker cannot approve own work
    assignments:
      loan-originator: [maker]
      credit-reviewer: [checker]
    handoffs:
      - action: credit_decision
        required_roles: [maker, checker]
        approval_required: true
    enforcement: strict
```

### Live Agent Memory
`memory/runtime/` holds persistent state (dailylog.md, key-decisions.md, context.md) that agents update across sessions.

### Agent Versioning
Every change (skill addition, rule change, model update) is a git commit. Roll back broken prompts with `git revert`, explore past versions with `git log`.

### Shared Context & Skills via Monorepo
Root-level `context.md`, `skills/`, `tools/` automatically shared across all agents in a monorepo. No duplication.

### Branch-Based Deployment
Use git branches (dev → staging → main) to promote agent changes through environments like software deployments.

### Knowledge Tree
Organize entity relationships hierarchically in `knowledge/` with embeddings for semantic reasoning at runtime.

### Agent Forking & Remixing
Fork any public agent repo, customize `SOUL.md`, add your own skills, PR improvements upstream. Open-source agent collaboration.

### CI/CD for Agents
Run `gitagent validate` on every push via GitHub Actions. Test agent behavior in CI, block bad merges, auto-deploy. Treat agent quality like code quality.

### Agent Diff & Audit Trail
`git diff` shows exactly what changed between agent versions. `git blame` traces every line to who wrote it and when.

### Tagged Releases
Tag stable agent versions like `v1.1.0`. Pin production to a tag, canary new versions on staging, roll back instantly.

### Secret Management via .gitignore
Agent tools needing API keys read from local `.env` file (kept out of version control). Agent config is shareable, secrets stay local.

### Agent Lifecycle with Hooks
Define `bootstrap.md` and `teardown.md` in `hooks/` folder to control agent startup and shutdown behavior.

### SkillsFlow
Deterministic multi-step workflows defined in `workflows/` YAML with `depends_on` ordering, `${{ }}` template data flow, and per-step `prompt:` overrides.

## Limitations and Caveats

**Development stage**: GitAgent is at v0.1.7 (released 2026-03-29). The specification is v0.1.0. The project is actively developed but not yet at 1.0 stable release. Breaking changes in the specification are possible in future versions.

**Adapter completeness**: While 11+ adapters are listed, the maturity of each varies. Primary adapters (claude-code, system-prompt, openai, crewai) are likely more complete than newer ones (openclaw, nanobot). Test coverage in source code shows adapter tests only for cursor and codex; other adapters may have gaps.

**Runtime orchestration not in scope**: GitAgent defines agent identity, not runtime loop behavior. Agents still require framework-specific orchestration (state machines, conversation loops, tool execution). Porting focuses on identity; orchestration logic remains in the framework.

**Compliance configuration vs. enforcement**: The manifest supports compliance configuration (supervision, recordkeeping, SOD), but enforcement is not built into gitagent itself. It is the responsibility of the runner/adapter and the environment to enforce these policies. `gitagent validate --compliance` checks configuration completeness, not actual enforcement.

**Skill discovery and registry**: The `gitagent skills` command mentions registry operations, but registry implementation details are not fully documented in the reviewed sources. The registry appears to be in development.

**Knowledge embedding and retrieval**: The specification mentions "embeddings" for knowledge tree reasoning but does not document the embedding mechanism, storage format, or retrieval algorithm.

**Model constraints enforcement**: The manifest supports model preference and constraints (temperature, max_tokens, etc.), but enforcement is adapter/runner-specific. Not all adapters may honor all constraints.

**Cycle detection in dependencies**: While agent dependencies are supported, the sources do not document how circular dependency graphs are detected or handled.

## Relevance to Claude Code Development

GitAgent is directly relevant to Claude Code development in several ways:

1. **Portable agent definitions**: Developers using Claude Code can define agents in gitagent format and export them to other frameworks (OpenAI, CrewAI, etc.) without rewriting identity, rules, or compliance policies.

2. **Compliance and audit support**: For developers building regulated agents (financial services, healthcare), gitagent provides first-class support for FINRA, Federal Reserve, SEC, and CFPB compliance configuration and auditing.

3. **Multi-agent orchestration**: Claude Code agents can be composed hierarchically, extend parent agents, and delegate tasks to sub-agents using gitagent's inheritance and composition model.

4. **Version control and collaboration**: Agent definitions as git repos enable version control, diffing, branching, and open-source collaboration — valuable for teams building agent libraries.

5. **Framework porting**: Agents defined in gitagent can be ported to other frameworks via adapters, useful for cross-framework interoperability.

6. **Skills system**: Reusable capability modules (skills) are portable across agents and frameworks, supporting code reuse and modular agent design.

7. **Skill marketplace**: The skills registry (in development) could enable discovery and sharing of reusable agent capabilities.

## References

- **Main Repository**: <https://github.com/open-gitagent/gitagent>
- **Homepage**: <https://gitagent.sh>
- **npm Package**: <https://www.npmjs.com/package/@shreyaskapale/gitagent>
- **Specification**: <https://github.com/open-gitagent/gitagent/blob/main/spec/SPECIFICATION.md> (accessed 2026-03-29)
- **Documentation**: <https://github.com/open-gitagent/gitagent/blob/main/docs.md> (accessed 2026-03-29)
- **Example Agents**: <https://github.com/open-gitagent/gitagent/tree/main/examples> (accessed 2026-03-29)
- **NVIDIA AIQ Deep Researcher Port**: <https://github.com/open-gitagent/gitagent/tree/main/examples/nvidia-deep-researcher> (accessed 2026-03-29)
- **Source Code**: <https://github.com/open-gitagent/gitagent/tree/main/src> (accessed 2026-03-29)
- **Compliance Reference**: FINRA Rules 3110, 4511, 2210; Federal Reserve SR 11-7, SR 23-4; SEC Regulation S-P, 17a-4; CFPB Circular 2022-03; EU AI Act; UK FCA guidance; MAS Singapore standards
- **Related Projects**: Salient AI (purpose-built agent architecture), FINOS AI Governance Framework

## Freshness Tracking

| Section | Confidence | Last Verified | Notes |
|---------|-----------|--------------|-------|
| **Identity/Metadata** | high | 2026-03-29 | Version, license, homepage, GitHub stats extracted directly from API |
| **Features** | high | 2026-03-29 | Feature descriptions extracted verbatim from README.md and SPECIFICATION.md |
| **Technical Architecture** | high | 2026-03-29 | Source code reviewed; component names and data flow documented from src/ directory listing and file reads |
| **Installation & Usage** | high | 2026-03-29 | Commands and examples extracted from docs.md, README.md, and source code |
| **Examples & Patterns** | high | 2026-03-29 | Patterns documented in README.md with YAML examples verbatim |
| **Limitations** | medium | 2026-03-29 | Based on specification review and source code gaps (missing test coverage for some adapters, incomplete documentation on registry) |
| **Compliance Features** | high | 2026-03-29 | Full compliance configuration documented from SPECIFICATION.md with exact YAML schema structure |

**Next review recommended**: 2026-06-29 (3 months). Recheck for v1.0 release, adapter maturity changes, registry implementation, and new frameworks added.

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Agno](./agno.md) | agent-frameworks | Multi-agent framework with persistent state and knowledge transfer; gitagent can export agent definitions to Agno format |
| [OpenFang](./openfang.md) | agent-frameworks | Rust Agent OS with native SKILL.md support; shares structured agent definition and autonomous hands pattern with gitagent skills system |
| [Micro-Agent](./micro-agent.md) | agent-frameworks | Python ReAct agent framework with MCP multi-server support; both support framework-agnostic tool integration via protocol abstraction |
| [Everything Claude Code](./everything-claude-code.md) | agent-frameworks | Claude Code skills and agents system; gitagent export adapter for claude-code generates CLAUDE.md compatible with this framework |
| [AI Agents Frameworks](./ai-agents-frameworks.md) | agent-frameworks | Comparative benchmarks of 10+ agent frameworks; gitagent enables unified definition and export across these evaluated frameworks |
| [Ruflo](./ruflo.md) | agent-frameworks | Multi-agent orchestration with 100+ agents and 215+ MCP tools; gitagent format enables portable agent definitions for Ruflo's swarm coordination |
| [Pi Monorepo](./pi-mono.md) | agent-frameworks | TypeScript agent framework with unified LLM API and modular architecture; shares agent composition and skill reuse philosophy with gitagent |
