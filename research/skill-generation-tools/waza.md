# Waza

**Research Date**: 2026-05-04
**Source URL**: <https://github.com/tw93/Waza>
**GitHub Repository**: <https://github.com/tw93/Waza>
**Version at Research**: v3.12.2 (GitHub release tag); per-skill SKILL.md versions: check: 3.20.0, think: 3.17.0, design: 3.19.0, hunt: 3.19.0, read: 3.14.0, write: 3.18.0, learn: 3.15.0, health: 3.17.0
**License**: MIT License

---

## Overview

Waza is a skill collection for Claude Code and Codex that packages eight specialized engineering workflows based on actual professional practices refined across 300+ sessions and 500 hours of real-world use. The name derives from the Japanese martial arts term for technique (技, わざ)—a move practiced until it becomes instinct. Each skill channels AI capability into precision by setting clear goals and constraints, then allowing the model to execute without generic defaults.

The project is part of an intentional trilogy: Kaku (書く) writes code, Waza (技) drills habits, Kami (紙) ships documents.

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI output lacks structure and drifts into generic, imprecise work | Eight narrowly-scoped skills set clear trigger, goal, and constraints for each engineering habit |
| Debugging requires multiple blind passes without systematic root-cause analysis | `/hunt` implements systematic debugging: root cause confirmed before any fix is applied |
| Code review is either skipped or surface-level, missing project-specific constraints | `/check` reviews diffs, extracts project constraints from public repository context, auto-fixes safe issues, and drives release follow-through |
| Planning ideas produces documents but no decision-ready implementation plans | `/think` challenges requirements, pressure-tests design, and produces decision-complete plans with validated structure |
| UI design defaults to generic instead of distinctive | `/design` produces production-grade interfaces with screenshot-driven aesthetic iteration |
| Prose writing carries AI patterns and stiff formulation | `/write` rewrites to sound natural in Chinese and English |
| Research requires manual synthesis across unstructured sources | `/learn` implements six-phase research workflow: collect, digest, outline, fill, refine, self-review, publish |
| Fetching web content for reading or citation is platform-dependent | `/read` fetches any URL or PDF as clean Markdown with platform-specific routing (GitHub, PDFs, WeChat, Feishu, paywalls, JS-heavy pages) |
| Auditing Claude Code setup is manual and incomplete | `/health` performs budget-aware audit of CLAUDE.md, rules, skills, hooks, MCP, and behavior with severity flagging |

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | 4,369 | 2026-05-04 |
| Forks | 265 | 2026-05-04 |
| Contributors | 6 | 2026-05-04 |
| Latest Release | v3.12.2 | 2026-05-04 |
| Created | 2026-03-12 | 2026-05-04 |
| Last Pushed | 2026-05-04 | 2026-05-04 |

---

## Key Features

### Eight Specialized Skills

Each skill has a clear trigger, single responsibility, and explicit scope boundaries.

- **`/think`** (v3.17.0) — Turns rough ideas into approved, decision-complete plans with validated structure before code writing. Covers new features, architecture decisions, value judgments. Not for bug fixes or small edits. Activates on triggers: `出方案, 给方案, 深入分析, 怎么设计, 用什么方案, 判断一下, 有没有必要, 值不值得, what's the best approach, plan this, how should I, should we keep this`

- **`/check`** (v3.20.0) — Reviews code diffs and release-ready changes, extracts project-specific constraints from repository context (README, CI workflows, package manifests, Makefiles), auto-fixes safe issues, drives approved release/publish/push/reaction follow-through, triages issues and PRs. Not for exploring ideas or debugging.

- **`/hunt`** (v3.19.0) — Systematic debugging: finds root cause of errors, crashes, regressions, screenshot-reported defects, unexpected behavior, failing tests. Root cause confirmed before any fix applied. Not for code review or new features.

- **`/design`** (v3.19.0) — Produces distinctive, production-grade UI for any component, page, or visual interface. Handles screenshot-driven iteration when user sends image with visual complaint. Not for backend logic or data pipelines.

- **`/read`** (v3.14.0) — Fetches any URL or PDF as clean Markdown for reading, quoting, citation, downstream work. Handles paywalls, JS-heavy pages, X/Twitter, Chinese platforms via proxy cascade. Not for local text files already in repo.

- **`/write`** (v3.18.0) — Strips AI writing patterns and rewrites prose to sound natural in Chinese or English. Only activates on explicit writing/editing requests. Not for code comments, commit messages, or inline docs.

- **`/learn`** (v3.15.0) — Six-phase research workflow: collect, digest, outline, fill in, refine, self-review, publish. Turns unfamiliar domains or collected sources into publish-ready output. Not for quick lookups or single-file reads.

- **`/health`** (v3.17.0) — Budget-aware audit of Claude Code setup: checks CLAUDE.md, rules, skills, hooks, MCP servers, behavior. Flags issues by severity. Default summary audit avoids burning quota; deep/full audit available on request. Claude Code only.

### Technical Architecture

**Skill Organization** (Source: `.claude-plugin/marketplace.json`, `AGENTS.md`):

- Individual skills stored at `skills/{name}/SKILL.md` with YAML frontmatter metadata (name, description, when_to_use triggers, version)
- Specialized reviewer/inspector agents under `skills/*/agents/`
- Supporting references, scripts, and helper utilities under `skills/*/references/` and `skills/*/scripts/`
- Shared routing and skill resolution via `skills/RESOLVER.md`
- Distribution via marketplace manifest (`.claude-plugin/marketplace.json`), plugin installer, or Claude Desktop ZIP

**Project-Aware Code Review** (`skills/check/references/project-context.md`):

- `/check` extracts project constraints at runtime from public repository context: README, CI workflows, package manifests, lockfiles, build configs, test configs, release notes
- Identifies changed languages, frameworks, generated outputs, protected files
- Compresses findings into review context: verification commands, release artifacts, domain risks, public reply rules
- Applies stricter project rules when they override generic Waza rules

**Skill Composition and Chaining**:

- Skills are designed to chain but transitions are manual
- Common workflows: Design: `/think` → approve → say "implement X" → `/check` → merge; Fix: `/hunt` → fix → `/check` → release/publish/push; Research and write: `/read` → `/learn` → `/write`; Debug and verify: `/hunt` → fix → `/check`

**Distribution Mechanisms**:

1. Claude Code direct slash commands: `npx skills add tw93/Waza -a claude-code -g -y`
2. Codex: `npx skills add tw93/Waza -a codex -g -y`
3. Claude Code plugin marketplace: `/plugin marketplace add tw93/Waza`
4. Claude Desktop: ZIP file from releases (`waza.zip`)

**Script Helpers** (Source: `scripts/`, `Makefile`):

- Statusline setup: `scripts/setup-statusline.sh` — minimal statusline for Claude Code showing context window and quota thresholds (color-coded: green <70%, yellow 70-85%, red >85%)
- English coaching: `scripts/setup-english-coaching.sh` — optional rule appending short corrections to English errors in prompts
- Packaging: `scripts/package-skill.sh` — builds Claude Desktop dispatcher ZIP with inlined skill bodies
- Verification: `scripts/verify-skills.sh` — validates skill descriptions, routing, versions match across marketplace.json, RESOLVER.md, SKILL.md files

---

## Installation & Usage

### Claude Code (Global Installation)

```bash
# Install all eight skills globally
npx skills add tw93/Waza -a claude-code -g -y

# Update to latest version
npx skills update -g -y
```

Once installed, invoke skills using slash commands:

```text
🥷 /think about building a new authentication system
🥷 /check the changes before merge
🥷 /hunt down the race condition in this test
🥷 /design a distinctive login flow
🥷 /read https://docs.example.com/architecture
🥷 /write "The system processes events with asynchronous..." (rewrite this)
🥷 /learn about WebAssembly by researching and writing a guide
🥷 /health run a setup audit
```

### Codex

```bash
npx skills add tw93/Waza -a codex -g -y
```

### Claude Desktop

Download `waza.zip` from [releases](https://github.com/tw93/Waza/releases/latest/download/waza.zip), open Customize > Skills > "+" > Create skill, upload the ZIP.

### Optional Extras

**Statusline** — minimal context window and quota display:

```bash
curl -sL https://raw.githubusercontent.com/tw93/Waza/main/scripts/setup-statusline.sh | bash
```

Color coding: green <70%, yellow 70-85%, red >85% for context window; blue, magenta, red for quota thresholds.

**English Coaching** — optional rule for English practice (appends 😇 correction on English mistakes in prompts):

```bash
# Claude Code
curl -sL https://raw.githubusercontent.com/tw93/Waza/main/scripts/setup-english-coaching.sh | bash -s -- claude-code

# Codex
curl -sL https://raw.githubusercontent.com/tw93/Waza/main/scripts/setup-english-coaching.sh | bash -s -- codex
```

### Uninstall

```bash
# Remove all skills
npx skills remove tw93/Waza -g

# Remove Claude Desktop skill: Customize > Skills, find Waza, click "..." > Delete
# Remove statusline: rm -f ~/.claude/statusline.sh, then remove statusLine from ~/.claude/settings.json
# Remove English coaching: rm -f ~/.claude/rules/english.md (or remove Waza block from ~/.codex/AGENTS.md for Codex)
```

---

## Relevance to Claude Code Development

### Applications

1. **Foundational Pattern for Skill Design** — Waza demonstrates narrowly-scoped, trigger-driven skill architecture that prevents over-generalization. Each skill has explicit "Not for..." exclusions, clear entry points, and avoids feature creep. This pattern is directly applicable to any new skill development in Claude Code's ecosystem.

2. **Project-Aware Agent Capability** — The `/check` skill shows how to extract project context at runtime from public repository files without depending on machine-specific paths or unpublished instructions. This approach enables skills to adapt to project conventions without hardcoding domain-specific rules.

3. **Multi-Skill Workflows** — Waza implements intentional manual chaining (not automatic triggering) between skills. This pattern respects user agency while supporting common multi-step workflows like research-and-write or hunt-and-verify.

4. **Real-World Refinement** — Documented on README: "Built from patterns across real projects, refined through actual use. Every gotcha traces to a real failure: a wrong code path that took four rounds to find, a release posted before artifacts were uploaded, a server restarted eight times without reading the error. 30 days, 300+ sessions, 7 projects, 500 hours." This data-driven refinement approach ensures skills solve actual problems, not theoretical ones.

### Patterns Worth Adopting

1. **Skill Descriptions as Routing Signals** — Each skill's description is concrete and triggerable, written to guide both human intent and potential automatic routing. This contrasts with vague descriptions like "helps with code" or "assists with debugging."

2. **Explicit Scope Boundaries** — Every skill includes "Not for..." clauses that prevent it from being misapplied. Examples: `/think` is "Not for bug fixes or small edits"; `/check` is "Not for exploring ideas or debugging"; `/design` is "Not for backend logic or data pipelines." These boundaries prevent bloat and confusion.

3. **Confidence-Building Through Simplicity** — Rather than attempting universal AI assistance, Waza succeeds by being deliberately narrow. Eight skills for eight habits. Users learn when to reach for each one and what to expect.

4. **Bilingual Trigger Documentation** — Skill descriptions and when_to_use triggers are explicitly documented in both Chinese and English. This enables Waza to serve global teams without losing specificity.

### Integration Opportunities

1. **Skill Repository Contribution** — Waza's eight skills and patterns could be integrated into a central Claude Code skill repository. The Waza approach to narrowness and trigger-driven design could influence how new skills are created and evaluated.

2. **MCP-Native Skills** — While Waza is skill-based, some of its capabilities (especially `/read` with platform-specific routing, `/health` with configuration auditing) could become MCP servers available to any Claude Code extension or agent.

3. **Marketplace Template** — Waza's marketplace manifest structure and naming conventions provide a template for future skill collections. The three-file consistency rule (marketplace.json, RESOLVER.md, SKILL.md) ensures versioning and discoverability alignment.

4. **English/Chinese Dual Documentation Model** — The bilingual structure in README, release notes, and skill descriptions provides a replicable model for AI tools serving non-English-speaking teams.

---

## References

- [Waza GitHub Repository](https://github.com/tw93/Waza) (accessed 2026-05-04)
- [Waza README.md](https://github.com/tw93/Waza/blob/main/README.md) (accessed 2026-05-04)
- [Waza AGENTS.md](https://github.com/tw93/Waza/blob/main/AGENTS.md) (accessed 2026-05-04)
- [Waza marketplace.json](https://github.com/tw93/Waza/blob/main/.claude-plugin/marketplace.json) (accessed 2026-05-04)
- [Waza /think skill](https://github.com/tw93/Waza/blob/main/skills/think/SKILL.md) (accessed 2026-05-04)
- [Waza /check skill](https://github.com/tw93/Waza/blob/main/skills/check/SKILL.md) (accessed 2026-05-04)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| None at this time | — | — |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-05-04 |
| Version at Verification | v3.12.2 (GitHub release tag); per-skill: check: 3.20.0, think: 3.17.0, design: 3.19.0, hunt: 3.19.0, read: 3.14.0, write: 3.18.0, learn: 3.15.0, health: 3.17.0 |
| Next Review Recommended | 2026-08-04 |
| Confidence Map | Overview: high, Problem Addressed: high, Key Statistics: high, Key Features: high (doc-read), Technical Architecture: high (doc-read), Installation & Usage: high (verified), Relevance to Claude Code: high, References: high |
