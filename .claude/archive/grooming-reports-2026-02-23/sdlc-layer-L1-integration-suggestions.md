# SDLC Layer 1 Integration Suggestions

**Generated**: 2026-02-23
**Plan**: SDLC Layer Separation Architecture
**Layer 1 Scope**: Language manifest schema, abstract roles, quality gates, project detection, language standards
**Source**: Full read of all Layer 1 items from sdlc-layer-candidates-master.md

---

## Plan Reference

The SDLC Layer Separation Architecture defines:
- **Layer 0**: SDLC-agnostic (harness, SAM pipeline, human touchpoints)
- **Layer 1**: Language-specific (manifest schema, abstract roles, quality gates, project detection)
- **Layer 2**: Stack/goal-specific
- **ARL**: Meta-layer (observe, identify, accumulate, improve)

Layer 1 formalization requires: language manifest schema, abstract role mapping, quality gate declarations, project detection rules, and language standards.

---

## 1. language-manifest-template

**Path**: `plugins/development-harness/templates/language-manifest-template.md`

### Extracted Content

- Skeleton with four sections: Role Fulfillment, Quality Gates, Project Detection, Process Flow Override
- Role Fulfillment: architect, test-designer, code-reviewer, design-spec, linting (agents @plugin:agent, skills /plugin:skill)
- Quality Gates: format, lint, typecheck, test, standards (backtick commands, {files} placeholder)
- Project Detection: markers (config files), source-patterns, test-patterns (glob patterns)
- Process Flow Override: optional, (none) uses default harness flow

### Integration Suggestion

**Where in plan**: Layer 1 formalization — "Language Manifest Schema" section

**Amendment**: Add explicit reference to the template as the canonical starting point for new language plugins. Require all Layer 1 language plugins to produce a manifest conforming to this template before they can compose with the harness.

**Nugget**: The template is minimal (28 lines). The full schema with validation rules lives in `language-manifest-schema.md`. Plan should distinguish: template = quick-start skeleton; schema = validation rules and examples.

---

## 2. python3-development

**Path**: `plugins/python3-development/skills/python3-development/SKILL.md`

### Extracted Content

- ROLE_TYPE identification (orchestrator vs sub-agent) with mandatory echo statement
- Linting Discovery Protocol: git hook tool → CI config → tool detection; format-first workflow
- Type Checker Discovery: basedpyright, pyright, mypy from pre-commit or pyproject.toml
- Quality Gates: format (ruff), lint (ruff), typecheck (detected), test (pytest >80%), modernpython, shebangpython
- Standard Project Structure: packages/, tests/, pyproject.toml, hatchling
- Agent orchestration: python-cli-architect, python-pytest-architect, python-code-reviewer, python-cli-design-spec, swarm-task-planner
- Pre-Delegation Checklist: read orchestration guide, identify workflow, plan agent chain, define scope, set success criteria
- Anti-pattern: DO NOT pre-gather data for agents (CoVe bypass)

### Integration Suggestion

**Where in plan**: Layer 1 — "Reference Implementation: Python" subsection

**Amendment**: Add python3-development as the canonical Layer 1 reference. Plan should require other language plugins to provide equivalent: (1) Role Fulfillment mapping to harness abstract roles, (2) Quality Gates with discovery protocol, (3) Project Detection markers (pyproject.toml, setup.py, setup.cfg), (4) Orchestration guide for agent chaining.

**Nugget**: The Linting Discovery Protocol (git hook → CI → fallback) is a reusable pattern. Extract as a Layer 1 standard: "Language plugins MUST implement a discovery sequence before executing quality gates."

---

## 3. python-development-orchestration

**Path**: `plugins/python3-development/skills/python3-development/references/python-development-orchestration.md`

### Extracted Content

- Five workflow patterns: TDD, Feature Addition, Code Review, Refactoring, Debugging
- Agent selection: python-cli-architect (default), stdlib-scripting (last resort), python-pytest-architect, python-code-reviewer, python-cli-design-spec, swarm-task-planner
- Decision tree for scripts: internet access? → python-cli-architect; no uv? → stdlib-scripting
- Quality Gates: holistic-linting, pytest, modernpython, shebangpython
- Anti-patterns: don't write Python as orchestrator; don't skip validation; don't mix agent contexts

### Integration Suggestion

**Where in plan**: Layer 1 — "Workflow Patterns" (new subsection)

**Amendment**: Add workflow pattern taxonomy as a Layer 1 concept. Each language plugin should document: (1) TDD-equivalent, (2) Feature Addition, (3) Code Review, (4) Refactoring, (5) Debugging — with agent chains and quality gates per pattern.

**Nugget**: The "Context to pass: file paths, outcomes, user requirements only. Do not pass file contents" rule is critical for CoVe. Include in Layer 1 standards: "Orchestrators pass paths and outcomes; agents discover and verify."

---

## 4. perl-development

**Path**: `plugins/perl-development/` (SKILL.md, agents: perl-script-developer, perl-script-auditor, perl-cli-architect)

### Extracted Content

- Perl 5.30+ standards: strict, warnings, autodie; feature (say, state, signatures)
- Agents: perl-script-developer, perl-script-auditor, perl-cli-architect
- Skills: perl-development, perl-cpan-ecosystem, perl-environment-setup, perl-testing, perl-lint, perl-validate
- Patterns: Path::Tiny, Try::Tiny, Getopt::Long, POD; security (taint, IPC::Open3 for safe system calls)
- No explicit language manifest file; agents and skills exist but no harness-compatible manifest

### Integration Suggestion

**Where in plan**: Layer 1 — "Language Plugin Inventory" or "Manifest Gap Analysis"

**Amendment**: Add task: "Create `references/language-manifest.md` for perl-development plugin using language-manifest-template." Map: architect → perl-cli-architect; test-designer → perl-testing skill or new agent; code-reviewer → perl-script-auditor; design-spec → perl-cli-architect; linting → perl-lint.

**Nugget**: Perl project detection markers: Makefile.PL, Build.PL, cpanfile, META.json. Quality gates: perl -c (syntax), perlcritic, prove (tests).

---

## 5. bash-development

**Path**: `plugins/bash-development/` (SKILL.md, agents: bash-script-developer, bash-script-auditor)

### Extracted Content

- Bash 5.1+ standards: set -euo pipefail; trap-based error handling
- Agents: bash-script-developer, bash-script-auditor
- Skills: bash-51-features, bash-52-features, bash-53-features, bash-development, bash-lint, bash-logging, bash-portability, bash-testing
- Patterns: pure-bash alternatives, argument parsing template, variable best practices
- No explicit language manifest; version-specific features (5.1, 5.2, 5.3) as separate skills

### Integration Suggestion

**Where in plan**: Layer 1 — "Language Plugin Inventory" or "Manifest Gap Analysis"

**Amendment**: Add task: "Create `references/language-manifest.md` for bash-development plugin." Map: architect → bash-script-developer (or new bash-architect); test-designer → bash-testing; code-reviewer → bash-script-auditor; design-spec → bash-script-developer; linting → bash-lint. Project detection: no standard markers (scripts often standalone); consider: .bashrc, Makefile with bash shebang, or directory with *.sh.

**Nugget**: Bash quality gates differ: format (shfmt if present), lint (shellcheck), typecheck (N/A), test (bats or custom). Plan should allow "typecheck: (none)" for languages without static typing.

---

## 6. agent-creator

**Path**: `.claude/skills/agent-creator/SKILL.md`

### Extracted Content

- Phase 1–7 workflow: Discovery, Requirements, Template Selection, Adaptation, Generation, Validation, Integration
- Role archetypes: Researcher, Planner/Architect, Coder, Creator, Tester, Reviewer, DevOps, Auditor, Context Gatherer, Optimizer, Domain Expert
- Standard vs Role-Based Contract: user-facing (flexible) vs orchestrated (DONE/BLOCKED)
- Template selection via AskUserQuestion; adapt from existing agents or archetypes

### Integration Suggestion

**Where in plan**: Layer 1 — "Abstract Role → Agent Mapping" (cross-reference)

**Amendment**: Add cross-reference: "When creating language-specific agents (e.g., python-cli-architect), use agent-creator skill. Role archetypes (Coder, Reviewer, Architect) align with harness abstract roles (architect, code-reviewer, design-spec)."

**Nugget**: The Domain Expert archetype is the pattern for language-pro agents (javascript-pro, typescript-pro, c-systems-programmer). Plan should state: "Language-pro agents are Domain Expert archetype instances with language-specific skills and quality checklists."

---

## 7. agent-schema

**Path**: `.claude/skills/agent-creator/references/agent-schema.md`

### Extracted Content

- YAML frontmatter spec: name, description, model, tools, skills, permissionMode, hooks, mcpServers, memory, etc.
- Required: name (lowercase, hyphens, max 64), description (action verbs, triggers, keywords, max 1024)
- YAML multiline bug: do NOT use >-, | for descriptions (indexer breaks)
- Validation rules before saving

### Integration Suggestion

**Where in plan**: Layer 1 — "Agent Definition Standards" (new subsection)

**Amendment**: Clarify distinction: (1) **Language manifest** (development-harness) maps abstract roles to agents; (2) **Agent schema** (agent-creator) defines agent frontmatter. Both are Layer 1 concerns. Plan should require language plugin agents to conform to agent-schema (name, description, skills) and be referenced in the language manifest.

**Nugget**: Agent schema does not define "language manifest for agents" — that's the development-harness language manifest. The agent-schema is for individual agent .md files. Avoid conflating the two in plan wording.

---

## 8. agent-templates

**Path**: `.claude/skills/agent-creator/references/agent-templates.md`

### Extracted Content

- Role-Based Contract Archetypes: Researcher, Planner/Architect, Coder, Creator, Tester, Reviewer, DevOps, Auditor, Context Gatherer, Optimizer, Domain Expert
- All use `skills: subagent-contract` for DONE/BLOCKED signaling
- Domain Expert: model: inherit, color, skills: {{domain_skill}}
- Supervisor co-prompt templates per archetype

### Integration Suggestion

**Where in plan**: Layer 1 — "Abstract Roles and Archetype Mapping"

**Amendment**: Add mapping table: harness abstract role → agent-creator archetype. Example: architect → Planner/Architect; test-designer → Tester; code-reviewer → Reviewer; design-spec → Planner/Architect or Coder; linting → (skill, not agent). Plan should state that language manifests resolve harness roles to agents that implement these archetypes.

**Nugget**: The Coder archetype with stack-specific skills (e.g., `skills: subagent-contract, python3-development`) is the pattern for language-specific implementation agents. Plan should document this as the standard for language plugin "coder" role fulfillment.

---

## 9. agent-examples

**Path**: `.claude/skills/agent-creator/references/agent-examples.md`

### Extracted Content

- Real implementations: plugin-assessor, code-review, contextual-ai-documentation-optimizer, doc-drift-auditor, plugin-refactor:refactor-skill, context-gathering
- Role-based examples: Coder (Next.js+Supabase), Coder (Python TUI), Formatter with hooks
- Patterns: description with triggers, permissionMode, color, phased workflow, self-verification

### Integration Suggestion

**Where in plan**: Layer 1 — "Implementation Reference" (nugget only)

**Amendment**: No direct plan amendment. Use as reference when creating language-specific agents.

**Nugget**: The Coder (Python TUI) example shows `skills: subagent-contract, python3-development` — the exact pattern for language manifest code-reviewer/coder fulfillment. Plan should cite this as the reference implementation for stack-specific Coder agents.

---

## 10. skill-research-process

**Path**: `.claude/skills/skill-research-process/SKILL.md`

### Extracted Content

- 3-stage process: Initialize → Research → Integrate
- Quality Gate 1: Category verification (distinct, complete)
- Quality Gate 2: Anti-hallucination checkpoint (every claim cited, no training data)
- Quality Gate 3: Final validation (links, structure)
- Citation format required; MCP tool selection (Ref > exa > WebFetch)

### Integration Suggestion

**Where in plan**: Layer 1 — "Quality Gates for Meta-Artifacts" (skill/agent creation)

**Amendment**: Add that skill-research-process quality gates (especially Gate 2: anti-hallucination) apply when creating language-specific skills. Language standards documented in skills must have cited sources. Plan should reference this for "language standards" documentation quality.

**Nugget**: Gate 2 pattern — "Every factual claim has a cited source" — should extend to language manifest quality gate commands. When a manifest declares `lint: \`ruff check {files}\``, the plan could require that the command be verified against project config (discovery protocol) rather than assumed.

---

## 11. optimize-claude-md

**Path**: `.claude/skills/optimize-claude-md/SKILL.md`

### Extracted Content

- 8 optimization principles: positive framing, motivation, concrete examples, front-loaded priorities, concise language, explicit format control, strategic XML tagging, structural enforcement
- RT-ICA pre-check, CoVe post-check in delegation template
- Phases: Validate → Measure → Delegate → Verify → Measure → Report → Apply
- Applies to CLAUDE.md, SKILL.md, agent definitions

### Integration Suggestion

**Where in plan**: Layer 1 — "Quality Standards for AI-Facing Content" (ARL overlap)

**Amendment**: Add that language plugin documentation (CLAUDE.md, SKILL.md, agent prompts) should meet optimize-claude-md principles. When formalizing Layer 1, run optimize-claude-md on language manifest schema docs and template to ensure clarity for AI consumption.

**Nugget**: The 8 principles apply to language manifest documentation. Plan should require: language manifest schema and template are optimized for AI parsing (front-loaded structure, explicit format, concrete examples per language).

---

## 12. javascript-pro

**Path**: `.claude/agents/javascript-pro.md`

### Extracted Content

- ES2023+, Node.js 20+ specialist
- Quality checklist: ESLint, Prettier, tests >85%, JSDoc, bundle size, async error handling, no var
- Project detection: read package.json, build config, module system
- Operational protocol: read config → analyze patterns → implement → verify

### Integration Suggestion

**Where in plan**: Layer 1 — "Language-Pro Agent Pattern" (new subsection)

**Amendment**: Add javascript-pro as a Layer 1 language-pro agent. It implements the Domain Expert archetype with: (1) quality checklist (ESLint, Prettier, tests), (2) project detection (package.json), (3) language standards (ES2023+). Plan should require a language manifest entry mapping code-reviewer or architect to @javascript-pro when a TypeScript/JavaScript plugin is created.

**Nugget**: javascript-pro has no explicit language manifest. If a "javascript-development" or "typescript-development" plugin is created, it should include a manifest with: markers: package.json; quality gates: eslint, prettier, test; role fulfillment including javascript-pro or typescript-pro.

---

## 13. typescript-pro

**Path**: `.claude/agents/typescript-pro.md`

### Extracted Content

- TypeScript 5.0+ specialist; strict mode always
- Quality checklist: strict mode, no any, 100% type coverage, type-only imports, source maps, declaration files
- Project detection: tsconfig.json, package.json, build configs
- Initialization protocol: read config → assess type patterns → identify framework → check lint config

### Integration Suggestion

**Where in plan**: Layer 1 — "Language-Pro Agent Pattern" (same as javascript-pro)

**Amendment**: typescript-pro extends the pattern with type-specific gates (type coverage, strict mode). Plan should note: TypeScript/JavaScript plugins can share project detection (package.json) but differ on typecheck (tsc for TS, N/A for JS).

**Nugget**: typescript-pro has hardcoded path in memory: `/home/user/repos/claude_skills/.claude/agent-memory/typescript-pro/`. Plan should include backlog item: "Replace hardcoded agent memory paths with {AGENT_MEMORY_DIR} or relative paths" (consistent with development-harness service-docs-maintainer fix).

---

## 14. c-systems-programmer

**Path**: `.claude/agents/c-systems-programmer.md`

### Extracted Content

- C99/C11, POSIX, Valgrind, GDB specialist
- Quality focus: memory management, pointer safety, error handling, thread safety
- Tool recommendations: GCC/Clang -Wall -Wextra, Valgrind, GDB, clang-tidy
- No explicit project detection; no language manifest

### Integration Suggestion

**Where in plan**: Layer 1 — "Language-Pro Agent Pattern"

**Amendment**: c-systems-programmer is a Domain Expert for C. Plan should add: "C development plugin (if created) would use markers: Makefile, CMakeLists.txt, Makefile.am; quality gates: format (clang-format), lint (clang-tidy), typecheck (N/A or -Wall), test (ctest/make test)."

**Nugget**: C projects often lack a single canonical config file. Project detection for C may need: Makefile, CMakeLists.txt, configure.ac, or *.c file presence. Plan should document that some languages have ambiguous detection and allow fallback to "source pattern match only."

---

## Summary: Plan Amendments to Add

| Amendment | Location | Priority |
|-----------|----------|----------|
| Reference language-manifest-template as canonical starting point | Layer 1 Schema | High |
| Add python3-development as reference implementation | Layer 1 | High |
| Extract Linting Discovery Protocol as Layer 1 standard | Layer 1 Standards | High |
| Add workflow pattern taxonomy (TDD, Feature, Review, Refactor, Debug) | Layer 1 | Medium |
| Create manifest for perl-development, bash-development | Backlog/Tasks | Medium |
| Map harness roles ↔ agent-creator archetypes | Layer 1 | Medium |
| Clarify agent-schema vs language-manifest distinction | Layer 1 | Medium |
| Add language-pro agent pattern (Domain Expert + quality checklist + project detection) | Layer 1 | Medium |
| Require skill-research-process Gate 2 for language standards docs | Layer 1 Quality | Low |
| Fix hardcoded paths in typescript-pro, javascript-pro | Backlog | Low |

---

## Cross-References for Plan

- **language-manifest-schema**: `plugins/development-harness/skills/development-harness/references/language-manifest-schema.md`
- **role-resolution-protocol**: `plugins/development-harness/skills/development-harness/references/role-resolution-protocol.md`
- **development-harness CLAUDE.md**: `plugins/development-harness/CLAUDE.md` (composition model, Voltron diagram)
