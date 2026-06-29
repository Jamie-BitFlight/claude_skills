---
title: Ponytail — Lazy Senior Developer Mode for AI Agents
resource_name: ponytail
author: Dietrich Gebert
repository_url: https://github.com/DietrichGebert/ponytail
latest_version: "4.7.0"
release_date: "2026-06-17"
license: MIT
---

## Overview

Ponytail is an agent-portable plugin that injects a "lazy senior developer" instruction set into AI agents, enforcing a structured decision ladder that prioritizes simplicity over complexity. Rather than building custom solutions, agents following ponytail first ask whether a feature is needed (YAGNI), reach for the standard library, check for native platform features, reuse installed dependencies, and only then write minimal custom code if nothing else works.

**Core philosophy**: "Ponytail puts him inside your AI agent." The plugin channels a senior developer who has seen every over-engineered codebase and replies to over-building with minimal, correct solutions—not out of laziness, but efficiency.

## Problem Addressed

AI agents without explicit constraints tend toward over-engineering: adding frameworks for single features, creating abstractions no one requested, importing dependencies when stdlib would suffice, writing boilerplate, and generating verbose code. This increases cost, latency, token consumption, and maintenance burden. Ponytail solves this by enforcing a refusal ladder that stops at the first working solution, eliminating speculative code before it starts.

## Key Statistics

**Benchmark Results (Haiku, Sonnet, Opus; 10 runs median per model; 5 everyday tasks)**:

- **Code reduction**: Ponytail writes 80-94% fewer lines than baseline (no skill). Median LOC: Haiku 39 vs. 518 baseline, Sonnet 44 vs. 693, Opus 51 vs. 256. Caveman (a competing simplification skill) produces Haiku 116, Sonnet 120, Opus 67—ponytail beats it on all models.
- **Cost reduction**: 42-75% cheaper than baseline (cost re-verified at 30 runs on 2026-06-17). Median 5-task cost: Haiku $0.011 vs. $0.030, Sonnet $0.035 vs. $0.137, Opus $0.079 vs. $0.137.
- **Latency reduction**: 3-6× faster than baseline. Median 5-task latency: Haiku 9.9s vs. 37.7s, Sonnet 20.1s vs. 124.1s, Opus 18.0s vs. 58.7s.

Benchmarks are single-shot completions (one prompt, one answer), not multi-turn sessions. Production codebases show larger over-engineering margins than the 5-task benchmark set. Source: [benchmarks/README.md](https://github.com/DietrichGebert/ponytail/tree/main/benchmarks).

**Platform support**: Installs to 13 agents: Claude Code, Codex, OpenCode, pi agent harness, Gemini CLI, Antigravity CLI, OpenClaw, plus instruction-only modes for Cursor, Windsurf, Cline, GitHub Copilot, GitHub Copilot CLI, Kiro, and VS Code Codex extension.

## Key Features

### The Decision Ladder

Before writing any code, agents follow a six-rung ladder; they stop at the first rung that holds:

1. **Does this need to exist?** (YAGNI): If speculative, skip it and say so in one line. No "future-proofing."
2. **Standard library does it?** Use stdlib.
3. **Native platform feature?** `<input type="date">` instead of a date picker library. CSS instead of JavaScript. Database constraints instead of app-layer checks.
4. **Installed dependency?** Use it. Never add a new dependency for what a few lines can do.
5. **One line?** Make it one line.
6. **Only then**: The minimum code that actually works.

This is a reflex, not a research project: two rungs work → take the higher one and move on.

### Three Intensity Levels

- **lite**: Build what's asked, name the lazier alternative in one line for the user to choose.
- **full** (default): Ladder enforced. Stdlib and native first. Shortest diff, shortest explanation.
- **ultra**: YAGNI extremist. Deletion before addition. Ship the one-liner and challenge the rest of the requirement in the same breath.

### Code Shortcuts and Debt Tracking

Intentional simplifications are marked with a `ponytail:` comment. If a shortcut has a known ceiling (global lock, O(n²) scan, naive heuristic), the comment names the ceiling and the upgrade path, e.g., `# ponytail: global lock, per-account locks if throughput matters`. This turns deferred work into visible, searchable debt rather than silent over-simplification.

### Companion Skills

- **ponytail-review**: Analyzes the current diff for over-engineering and returns a delete-list.
- **ponytail-audit**: Scans the whole repo for over-engineering, not just recent changes.
- **ponytail-debt**: Harvests all `ponytail:` comments into a tracked ledger, surfacing deferred work.
- **ponytail-help**: Quick reference card for commands and modes.

### Protective Rules

Laziness is enforced only where it is safe. Never simplifies away:
- Input validation at trust boundaries.
- Error handling that prevents data loss.
- Security measures.
- Accessibility basics.
- Anything explicitly requested by the user (if the user insists on the full version, build it).

Hardware calibration is preserved: a real clock drifts, a real sensor reads off. Minimal code leaves room for tuning.

Non-trivial logic requires one runnable check behind: an `assert`-based `demo()` or one small test file, not frameworks or fixtures. Trivial one-liners need no test.

## Technical Architecture

### Multi-Agent Portability

Ponytail is distributed as a set of adapters, each tailored to a host agent:

| Host | Mechanism |
|------|-----------|
| Claude Code | Plugin with session activation hooks, mode tracking, commands, and statusline integration. |
| Codex | Plugin with lifecycle hooks and shared skill directory. |
| OpenCode | Server plugin injecting ruleset via `experimental.chat.system.transform`; persists `/ponytail` mode switches. |
| pi | Package extension injecting ruleset and registering `/ponytail` commands. |
| Gemini/Antigravity | Extension pointing `contextFileName` at `AGENTS.md` for always-on rules. |
| Cursor/Windsurf/Cline | Project rules (`.cursor/rules/`, `.windsurf/rules/`, `.clinerules/`). |
| GitHub Copilot (CLI and editor) | Instruction files (`.github/copilot-instructions.md`) and plugin support. |
| Kiro | Project or global steering rules (`.kiro/steering/`). |
| Generic/fallback | Raw `AGENTS.md` or direct skill files (`skills/*/SKILL.md`) for any agent. |

**Core files**:
- `AGENTS.md`: 26-line compact ruleset for always-on injection (instruction-tier hosts).
- `skills/ponytail/SKILL.md`: Full 100+ line skill definition with examples and edge cases.
- `hooks/ponytail-activate.js` and `hooks/ponytail-mode-tracker.js`: Node.js lifecycle hooks for Claude Code and Codex.
- `skills/{ponytail-review,ponytail-audit,ponytail-debt,ponytail-help}/SKILL.md`: Companion skill definitions.

The architecture reuses adapters rather than duplicating rules: when a host supports skills or hooks, the adapter points at the shared `skills/` and `hooks/` directories. When a host only supports project rules, the adapter copies the text from `AGENTS.md` (kept in sync via `scripts/check-rule-copies.js`).

### Behavioral Injection Patterns

**Always-on activation** (Session/Startup hook):
- Claude Code and Codex: Node.js hooks run at SessionStart, load the current mode from persistent storage, and inject it into the next turn.
- OpenCode/pi: Ruleset is injected each turn via shared instruction builder.
- Instruction-only hosts: Rules are present in the project file (`.cursorrules`, `AGENTS.md`, etc.) and read by the host at startup.

**Mode persistence**:
- Stores current level (`lite`/`full`/`ultra`/`off`) in `~/.config/ponytail/config.json` (or env var `PONYTAIL_DEFAULT_MODE`).
- UserPromptSubmit hook (Claude Code/Codex) re-injects the mode at each turn.
- Commands (`/ponytail lite|full|ultra|off`) switch modes and persist the choice.

### Cost Scaling and Model Dependence

The benchmark results vary by model class:
- **Instruction-following models** (Claude, Gemini): Follow the ladder reliably. The ladder is a deliberation step (think before writing), but savings in output tokens outweigh thinking tokens, especially on longer tasks.
- **Terse reasoning models** (e.g., GPT-4o): May spend thinking tokens working through the ladder, offsetting output savings. On some models, per-session cost can go either way depending on prompt length and model behavior.

The "80-94% less code" figure is from single-shot completions on Claude and is not guaranteed to hold across all models or multi-turn sessions. Real agent sessions re-inject the ruleset and run the ladder every turn, which compounds the cost-per-token but also compounds the code-reduction effect.

## Installation & Usage

### Claude Code

```bash
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

Node.js must be on PATH for lifecycle hooks to run (they fail silently if node is absent).

### Other Agents

See README.md lines 78–174 for Codex, OpenCode, pi, Gemini/Antigravity CLI, OpenClaw, and instruction-only adapters (Cursor, Windsurf, Cline, GitHub Copilot, Kiro).

### Configuration

Set default level via env var or config file (default: `full`):

```bash
export PONYTAIL_DEFAULT_MODE=lite
# or
echo '{"defaultMode": "ultra"}' > ~/.config/ponytail/config.json
```

### Commands

Requires a skill-capable host:

| Command | Behavior |
|---------|----------|
| `/ponytail [lite\|full\|ultra\|off]` | Switch intensity or report current level. |
| `/ponytail-review` | Review diff for over-engineering. |
| `/ponytail-audit` | Scan entire repo for over-engineering. |
| `/ponytail-debt` | List all `ponytail:` comments as a ledger. |
| `/ponytail-help` | Quick reference card. |

## Relevance to Claude Code Development

Ponytail is directly applicable to Claude Code plugins and agents:

1. **Embedded agent instruction**: The `AGENTS.md` and skill definitions can be imported into Claude Code agent files or CLAUDE.md rules files to enforce simplicity on downstream agents spawned within the development harness.

2. **Code quality in generated implementations**: When using Claude Code agents to implement features or generate skill files, applying ponytail principles reduces boilerplate and unnecessary abstractions in generated code.

3. **Plugin minimalism**: The ponytail repository itself demonstrates minimal-surface plugin design: 5 skills, reused across 13 hosts, 80 source files total, 4.7.0 version after months of iteration. This pattern applies to new Claude Code plugins.

4. **Multi-agent orchestration debt tracking**: The `ponytail-debt` skill's approach to surfacing deferred work via inline comments can be adapted into orchestration workflows where teams track intentional technical debt across parallel AI implementations.

5. **Cost-aware agent design**: For cost-sensitive agent deployments (especially at scale with multi-turn interactions), embedding ponytail principles reduces per-turn token consumption and latency, improving throughput and lowering total cost of ownership.

## Limitations and Caveats

**Model-dependent performance**: Benchmark results are validated on Claude (Haiku, Sonnet, Opus) under single-shot conditions (one prompt, one answer). Results on reasoning models, local models, or multi-turn sessions may differ. OpenAI GPT-5.5 testing showed cost could increase due to thinking-token overhead outweighing output savings.

**No test framework**: The ruleset generates at most one small test file (`test_*.py`) or assert-based self-check for non-trivial logic; it provides no framework or fixture set. This trades test elegance for code brevity and is suitable for scripts and CLI tools but may be insufficient for large library projects requiring comprehensive test suites.

**Node.js requirement for Claude Code/Codex**: Lifecycle hooks require Node.js on PATH. Without it, activation succeeds silently (no error), but the ruleset is not loaded.

**Manual mode tracking**: Users must remember to switch intensity levels; no auto-detection of codebase complexity or task type. The default (full) is conservative, but if a task genuinely needs the 120-line cache class and the user forgets to switch off ponytail, they will get a one-liner instead.

**Shallow platform feature detection**: The ladder assumes agents know which native features exist (e.g., `<input type="date">`, CSS grid, database constraints). On unfamiliar platforms or APIs, the ladder cannot help.

**Deferred work accumulation**: The `ponytail:` comment system surfaces deferred work but does not enforce it. A codebase can accumulate unbounded debt in comments if reviews do not check the ledger periodically.

## References

- **Repository**: <https://github.com/DietrichGebert/ponytail> (accessed 2026-06-18)
- **Latest Release**: v4.7.0 (released 2026-06-17)
- **License**: MIT
- **Benchmarks**: [benchmarks/README.md](https://github.com/DietrichGebert/ponytail/tree/main/benchmarks) — reproduce with `npx promptfoo eval -c promptfooconfig.yaml`
- **Examples**: [examples/](https://github.com/DietrichGebert/ponytail/tree/main/examples) — real model output from benchmark runs
- **Agent Portability**: [docs/agent-portability.md](https://github.com/DietrichGebert/ponytail/blob/main/docs/agent-portability.md) — adapter matrix
- **Core Ruleset**: [AGENTS.md](https://github.com/DietrichGebert/ponytail/blob/main/AGENTS.md) — 26-line compact form
- **Development**: Tests via `npm test`, rule-copy verification via `node scripts/check-rule-copies.js`, OpenClaw skill build via `node scripts/build-openclaw-skills.js`

## Freshness Tracking

**Last verified**: 2026-06-18
**Next review**: 2026-09-18 (3 months)

### Confidence by Section

- **Identity/Metadata**: high — plugin.json and LICENSE directly consulted
- **Problem Addressed**: high — README.md and AGENTS.md are authoritative
- **Key Statistics**: high — all numbers extracted from benchmark report (README.md and benchmarks/README.md); cost verified at 30 runs on 2026-06-17 per README
- **Key Features**: high — extracted from AGENTS.md (26 lines) and skills/ponytail/SKILL.md (100 lines); feature set stable across all 13 agent implementations
- **Technical Architecture**: high — plugin.json, docs/agent-portability.md, and hooks/hooks.json consulted; architecture verified against source
- **Installation & Usage**: high — direct quotes from README.md installation section and commands table
- **Limitations and Caveats**: medium — derived from README.md discussion of model dependence, benchmark conditions, and AGENTS.md rules. The "no test framework" limitation is inferred from the stated "no fixtures, no per-function suites unless asked" rule; not a bug report or explicit documented limitation
- **Relevance to Claude Code Development**: medium — extrapolated from ponytail's multi-agent portability and design philosophy; not a documented use case but a reasoned projection based on plugin architecture and the development-harness use patterns

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Claude Code Harness](./claude-code-harness.md) | agent-frameworks | shared guardrail instruction model; both enforce agent behavior via pluggable rulesets |
| [Orchestra](./orchestra.md) | agent-frameworks | complements task decomposition with token-budget enforcement; orchestrates work that ponytail minimizes |
| [Get Shit Done](./get-shit-done.md) | agent-frameworks | parallel context-engineering system; ponytail is lazy execution while GSD is meta-prompting strategy |
| [Gstack](./gstack.md) | agent-frameworks | role-specific skill routing; ponytail applies universal simplification, gstack applies role-specific cognition |
| [Everything Claude Code](../developer-tools/everything-claude-code.md) | developer-tools | shared optimization goal: token reduction and cost minimization; complementary at different scales |
| [Composure](./composure.md) | agent-frameworks | overlapping anti-pattern detection; composure blocks patterns, ponytail prevents them upstream |
| [Liteagents](./liteagents.md) | agent-frameworks | shared token-budget constraint; both address latency and cost via instruction-first design |
| [Superpowers](./superpowers.md) | agent-frameworks | paired skill approach: superpowers teach agents to do things well; ponytail teaches them to do less |
| [GitAgent](./gitagent.md) | agent-frameworks | framework-agnostic agent portability; ponytail's 13-platform support mirrors gitagent's "clone a repo, get an agent" philosophy |
