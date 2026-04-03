# Repository Inference Patterns

Patterns for wizard Step 1: infer the project's technology stack from repository marker files.
Used by `setup-skill-discovery/SKILL.md` to determine candidate skill categories before
building the `.dh/skill_discovery.yaml` draft.

This file documents file presence → stack → skill category mappings. For the canonical
language manifest schema (role fulfillment, quality gates, project detection rules), see
`development-harness/references/language-manifest-schema.md` — do not duplicate that content here.

---

## Scan Order and Priority

The wizard scans in two passes:

### Pass 1 — Specific markers (highest priority)

Scan for language and framework-specific files first. These are unambiguous signals.
When multiple specific markers are found, all matching stacks are collected (multi-stack project).

Priority within specific markers: **most specific wins** when two markers point to the same
language. Example: `pyproject.toml` is more informative than `requirements.txt` alone —
if `pyproject.toml` exists, treat it as the authoritative Python marker even if
`requirements.txt` is also present.

### Pass 2 — General markers (lower priority, always checked)

Scan README.md and CLAUDE.md regardless of what Pass 1 found. These files add context
(frameworks, tooling, purpose) that refines candidates even when stack is already known.
General markers never override specific markers.

### Priority rules summary

```
specific language markers  >  infrastructure/tooling markers  >  general description files
pyproject.toml             >  Dockerfile                       >  README.md
(more specific)            >  (less specific within same tier) >  (always scanned)
```

If no specific marker is found and general markers yield no clear signal, default to
`skill_discovery: suggest` mode in the drafted config rather than guessing.

---

## File-to-Stack Mappings

### Python

| Marker file | Inference |
|---|---|
| `pyproject.toml` | Python project — strong signal; also check for framework keys (fastapi, django, flask, typer, rich, fastmcp) |
| `setup.py` | Python project — legacy packaging; weaker signal than pyproject.toml |
| `requirements.txt` | Python project — minimal signal; consider alongside other markers |
| `uv.lock` | Python project using uv — infer modern Python toolchain |

**Skill categories to consider**: Python testing, Python linting, Python type checking,
Python CLI tooling, Python packaging, async Python (if async frameworks detected in pyproject.toml).

Scan `pyproject.toml` for `[tool.pytest.*]`, `[tool.ruff.*]`, `[tool.mypy.*]`,
`[tool.pyright.*]`, `[tool.ty.*]` — these confirm which quality tooling is already configured.

---

### TypeScript / JavaScript

| Marker file | Inference |
|---|---|
| `package.json` | Node.js/JS/TS project — check `dependencies` for React, Vue, Next.js, etc. |
| `tsconfig.json` | TypeScript project (co-present with package.json typically) |
| `bun.lock` or `bun.lockb` | Bun runtime (TypeScript) |
| `pnpm-lock.yaml` | pnpm-managed Node project |

**Skill categories to consider**: TypeScript/JavaScript testing, frontend UI/UX,
React patterns, component design, frontend state management, CSS and styling.

Scan `package.json` `dependencies` and `devDependencies` for framework names
(react, vue, next, remix, vite, vitest, jest, playwright) to refine categories.

---

### Rust

| Marker file | Inference |
|---|---|
| `Cargo.toml` | Rust project — check `[dependencies]` for async runtime (tokio, async-std), CLI (clap, structopt), or embedded targets |
| `Cargo.lock` | Rust project (co-present with Cargo.toml) |

**Skill categories to consider**: Rust testing, Rust async programming, Rust CLI tooling,
systems programming patterns.

---

### Ruby

| Marker file | Inference |
|---|---|
| `Gemfile` | Ruby project — check for Rails, Sinatra, or CLI gems |
| `*.gemspec` | Ruby gem/library |
| `Gemfile.lock` | Ruby project (co-present with Gemfile) |

**Skill categories to consider**: Ruby testing, Ruby linting, Ruby on Rails patterns
(if Rails detected in Gemfile).

---

### Go

| Marker file | Inference |
|---|---|
| `go.mod` | Go module — check module path for organization and purpose |
| `go.sum` | Go project (co-present with go.mod) |

**Skill categories to consider**: Go testing, Go linting, Go CLI patterns,
Go concurrency patterns.

---

### Java / JVM

| Marker file | Inference |
|---|---|
| `pom.xml` | Maven Java project |
| `build.gradle` or `build.gradle.kts` | Gradle Java/Kotlin/Groovy project |
| `settings.gradle` | Gradle multi-module project |

**Skill categories to consider**: Java/Kotlin testing, JVM build tooling,
Spring Framework patterns (if spring detected in pom.xml/build.gradle).

---

### Infrastructure and Automation

| Marker file | Inference |
|---|---|
| `Vagrantfile` | VM automation project — check provisioning shell/ansible blocks |
| `Dockerfile` | Container-based project |
| `docker-compose.yml` or `docker-compose*.yml` | Multi-service container orchestration |
| `*.tf` (any Terraform file) | Infrastructure as Code with Terraform |
| `ansible.cfg` or `playbook.yml` | Ansible automation |
| `.github/workflows/*.yml` | GitHub Actions CI/CD configuration |

**Skill categories to consider**: container tooling, infrastructure as code,
CI/CD pipeline patterns, VM provisioning and testing.

> **VM automation note**: A `Vagrantfile` alongside a `.claude/CLAUDE.md` referencing
> `vm-blackbox` or `vm-flightsimulator` is a strong signal for VM testing harness skills.

---

### Claude Code Project

| Marker file | Inference |
|---|---|
| `.claude/CLAUDE.md` | Claude Code project — scan for plugin references, skill declarations, MCP server registrations |
| `.claude-plugin/plugin.json` | Claude Code plugin — strong signal for plugin authoring skills |
| `agents/*.md` or `.claude/agents/*.md` | Agent definitions present — infer agent authoring context |
| `skills/*/SKILL.md` or `.claude/skills/*/SKILL.md` | Skill definitions present — infer skill authoring context |

**Skill categories to consider**: Claude Code plugin authoring, skill creation,
agent design, MCP server integration, hook development.

Scan `.claude/CLAUDE.md` for `Skill(skill=...` patterns to discover what domain skills
the project already uses — these are strong candidates for `always_use_skills`.

---

### General Description Files

| Marker file | Inference |
|---|---|
| `README.md` | Scan for technology mentions: framework names, language references, tooling names. Lower confidence than specific markers. |
| `CLAUDE.md` (project root) | Scan for skill invocations and technology stack clues |

Treat README.md findings as corroborating evidence, not primary signals. If README.md
mentions a framework not detected by specific markers, note it as a low-confidence candidate.

---

## Scan Priority Examples

```
Scenario: pyproject.toml + package.json + Vagrantfile + .claude/CLAUDE.md
→ Multi-stack: Python, TypeScript, VM automation, Claude Code project
→ Candidate categories: Python testing+linting, TypeScript testing, VM testing harness,
  plugin authoring, skill creation
→ All four stacks represented in skill_rules

Scenario: Cargo.toml only
→ Single-stack: Rust
→ Candidate categories: Rust testing, Rust linting, Rust async
→ README.md scanned for additional context

Scenario: No specific markers, only README.md
→ No confident inference possible
→ Wizard annotates config with # LOW_CONFIDENCE; defaults skill_discovery to 'suggest'
```

---

## Multi-Stack Projects

When Pass 1 finds markers for more than one stack:

1. **List all detected stacks** — do not discard any confident detection.
2. **Check for primary stack** — if one stack clearly dominates (most marker files,
   largest codebase portion per file count), mark it as primary.
3. **Generate skill_rules per stack** — each stack gets its own `when:` condition
   in the draft config. Do not merge unrelated stacks into a single rule.
4. **Separate always_use_skills from stack-conditional rules** — skills that apply
   regardless of what feature is being worked on (e.g., a shared linting skill) go
   in `always_use_skills`; stack-specific skills go in `skill_rules`.

**Example multi-stack `skill_rules` structure (category names, not identifiers):**

```yaml
skill_rules:
  - when: "involves Python, pytest, type hints, or uv"
    use:
      - # Python testing skill
      - # Python linting skill

  - when: "involves TypeScript, React, or frontend"
    use:
      - # TypeScript/frontend skill

  - when: "involves VM, Vagrant, WinRM, or VirtualBox"
    use:
      - # VM testing skill
```

---

## What NOT to Hardcode

- **Skill identifiers** (`provider:skill-name` form) — the wizard resolves these against
  installed skills at runtime via `npx skills list`. Use category descriptions only in this
  file; the wizard inserts actual skill identifiers after inventory.
- **Version numbers** — do not require specific versions of marker files or tooling.
- **Exact file counts** — "check for any `*.tf` file" not "check for at least 3 Terraform files".
