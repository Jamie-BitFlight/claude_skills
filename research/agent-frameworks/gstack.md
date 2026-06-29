---
title: "gstack — Claude Code Workflow Skills"
---

## Identity & Metadata

| Field | Value |
|-------|-------|
| **Name** | gstack |
| **Full Name** | gstack — Garry Tan's Stack |
| **Creator** | Garry Tan (President & CEO, Y Combinator) |
| **Repository** | <https://github.com/garrytan/gstack> |
| **License** | MIT (source: GitHub API + CHANGELOG) |
| **Current Version** | 0.3.1 (released 2026-03-12) |
| **Primary Language** | TypeScript |
| **Runtime Requirement** | Bun v1.0+ (source: package.json engines) |
| **GitHub Stats** | 6,058 stars, 710 forks, 23 open issues (as of 2026-03-13) |
| **Repository Type** | Skill/framework collection — not a standalone application |
| **Status** | Active (last commit 2026-03-14) |

---

## Purpose & Design Philosophy

gstack addresses a core limitation in AI-assisted development: **generic assistants lack role-specific cognition**. Instead of a single model asking "how do I implement this?", gstack lets developers summon eight different specialized agents, each optimized for a different phase of the development lifecycle.

From README: "Planning is not review. Review is not shipping. Founder taste is not engineering rigor. If you blur all of that together, you usually get a mediocre blend of all four. I want explicit gears." (source: README.md line 147-151)

The design philosophy is **cognitive switching** — consciously select which mental model to apply to each task. A feature request starts in "founder mode" (/plan-ceo-review) to discover the real problem, shifts to "engineering rigor mode" (/plan-eng-review) for architecture, then to "paranoid reviewer mode" (/review) to find production bugs, and finally "release machine mode" (/ship) to close the loop without friction.

---

## Eight Workflow Skills

Each skill is implemented as a Markdown-based Claude Code skill file (prompts + instructions). They are discovered and loaded by Claude Code's skill loader.

### 1. `/plan-ceo-review` — Founder Mode

**What it does**: Pressure-tests product direction by asking "what is the 10-star product hiding inside this request?" (source: README.md line 196)

**Mechanism**: Shifts Claude's role to founder/CEO perspective. Instead of taking the request literally, it rethinks the problem from the user's point of view and finds the version that feels inevitable and delightful.

**Example from README**: When user says "Let sellers upload a photo for their item," `/plan-ceo-review` reframes this as helping someone create a listing that actually sells, then proposes: auto-identify the product from photo, pull specs and pricing comps from web, draft title and description, suggest best hero image.

**Confidence**: High — purpose and mechanism clearly documented in README with concrete examples.

### 2. `/plan-eng-review` — Engineering Manager Mode

**What it does**: Locks in architecture, data flow, system boundaries, failure modes, edge cases, and test coverage. Forces assumptions into diagrams.

**Mechanism**: Transitions from product ideation to technical planning. Enforces system design discipline by requiring diagrams (sequence, state, component, data-flow) to expose hidden assumptions.

**Key Innovation**: "LLMs get way more complete when you force them to draw the system." (source: README.md line 220-221) Diagrams make hand-wavy planning harder and expose edge cases earlier.

**Example from README**: For the smart listing flow, `/plan-eng-review` answers: architecture for upload/classification/enrichment, synchronous vs background jobs, failure handling, race condition prevention, persistence strategy.

**Confidence**: High — documented with explicit example and rationale for diagram forcing.

### 3. `/review` — Paranoid Staff Engineer Mode

**What it does**: Structural code audit focused on production failure modes, not style nitpicks.

**Mechanism**: Asks "what can still break?" rather than "is the code clean?" Looks for N+1 queries, race conditions, stale reads, bad trust boundaries, escaping bugs, broken invariants, bad retry logic, and tests that pass while missing real failure modes.

**Scope**: This is not linting or formatting — it is about discovering bugs that pass CI but blow up in production.

**Example from README**: For the listing implementation, asks about N+1 queries, trust boundaries (client-provided file metadata), race conditions on cover-photo selection, orphaned files from failed uploads, "exactly one hero image" invariant under concurrency, prompt injection from pulling web data.

**Confidence**: High — clear distinction from CI checks, concrete examples, explicit about what mode NOT to apply.

### 4. `/ship` — Release Machine Mode

**What it does**: Automates the final mile for a ready branch: sync with main, run tests, update changelog/versioning, push, open/update PR.

**Mechanism**: Eliminates friction from the "interesting work done, boring release work left" phase where humans often procrastinate. Treats shipping as a mechanical process requiring discipline, not ideation.

**Scope**: For ready branches only, not for deciding what to build. Stops brainstorming and starts disciplined release execution.

**Tools**: Sync main, rerun tests, check branch state, version/changelog update, git push, PR creation/update.

**Confidence**: High — clear scope boundaries and mechanical nature of tasks.

### 5. `/browse` — QA Engineer Mode (Headless Browser)

**What it does**: Gives Claude eyes. Logs in to apps, clicks through UI, takes screenshots, checks console errors, verifies end-to-end flows.

**Architecture**: Compiled CLI binary (written in TypeScript, compiled with Bun --compile) that talks to a persistent Chromium daemon via HTTP. Built on Playwright.

**Key metrics from BROWSER.md**:
- First call: ~3 seconds (launches Chromium daemon)
- Subsequent calls: ~100-200ms round trip
- Context overhead: 0 tokens (plain text output, not MCP protocol)
- Lifecycle: 30-minute idle timeout, auto-restart on crash
- Reference system: accessibility tree (via Playwright's `aria-snapshot`) → @e refs → Locator map

**Command categories** (source: BROWSER.md lines 6-20):
- Navigate (goto, back, forward, reload, url)
- Read (text, html, links, forms, accessibility)
- Snapshot (with diff, annotate, cursor-interactive scan)
- Interact (click, fill, select, hover, type, press, scroll, wait, viewport, upload)
- Inspect (js, eval, css, attrs, is, console, network, dialog, cookies, storage, perf)
- Visual (screenshot, pdf, responsive)
- Compare (diff across environments)
- Tabs & Cookies (tab management, cookie import)

**Multi-workspace support**: When running under Conductor (parallel execution platform), each workspace gets its own isolated browser instance derived from `CONDUCTOR_PORT - 45600`.

**Performance comparison** (source: BROWSER.md lines 143-149):

| Tool | First call | Subsequent | Context overhead |
|------|-----------|-----------|-----------------|
| Chrome MCP | ~5s | ~2-5s | ~2000 tokens |
| Playwright MCP | ~3s | ~1-3s | ~1500 tokens |
| **gstack browse** | **~3s** | **~100-200ms** | **0 tokens** |

"In a 20-command browser session, MCP tools burn 30,000-40,000 tokens on protocol framing alone. gstack burns zero." (source: BROWSER.md line 149)

**Authentication**: Bearer token generated per session, written to state file (chmod 600), required on every HTTP request to prevent other processes from controlling the browser.

**Confidence**: High — technical architecture fully documented, implementation details verified from BROWSER.md, performance comparison explicit.

### 6. `/qa` — QA Lead Mode

**What it does**: Systematic test pass with structured reporting, health scoring, screenshot evidence, and regression tracking.

**Mechanism**: Explores every reachable page, fills forms, clicks buttons, checks console errors, tests responsive layouts. Produces structured report with health score (0-100), ranked issues with repro steps, screenshots.

**Three modes** (source: README.md line 410-414):
- **Full** (default): Systematic exploration, 5-15 minutes, documents 5-10 well-evidenced issues
- **Quick** (`--quick`): 30-second smoke test — homepage + top 5 nav targets
- **Regression** (`--regression baseline.json`): Run full mode, diff against previous baseline

**Report artifacts**: Saved to `.gstack/qa-reports/` for trend tracking and comparison.

**Example from README**: `/qa https://staging.myapp.com` explores 12 pages, fills 3 forms, tests 2 flows, produces health score 72/100 with top 3 ranked issues (critical, high, medium) and full report with screenshots.

**Confidence**: High — three modes documented with scope and duration expectations, report structure specified.

### 7. `/setup-browser-cookies` — Session Manager Mode

**What it does**: Imports cookies from the user's real browser (Chrome, Arc, Brave, Edge, Comet) directly into the headless session.

**Mechanism**: Auto-detects installed Chromium browsers, decrypts cookies via macOS Keychain (with fallback for locked databases), loads them into Playwright session. Interactive picker UI lets user choose exactly which domains to import — no cookie values are displayed.

**Lifecycle** (source: CHANGELOG 0.3.1, lines 5-14):
- First import per browser triggers macOS Keychain prompt ("Allow" or "Always Allow")
- Per-browser AES key caching (one Keychain prompt per browser per session)
- Async 10s Keychain timeout (no event loop blocking)
- DB lock fallback: copies locked cookie DB to /tmp for safe reads
- Supports interactive UI or CLI with `--domain` flag

**Example from README**: `setup-browser-cookies github.com` imports 12 cookies without UI. Or use interactive picker to select multiple domains visually.

**Use case**: Test authenticated pages without logging in manually through headless browser. Session carries over between `/browse` and `/qa` commands.

**Confidence**: High — mechanism documented, macOS-specific security details specified, CLI alternatives provided.

### 8. `/retro` — Engineering Manager Mode

**What it does**: Analyzes commit history, work patterns, and shipping velocity. Writes candid retrospective with per-person feedback.

**Mechanism**: Parses commit history (timestamps, authors, files, LOC), computes metrics (commits, LOC, test ratio, PR sizes, fix ratio), detects coding sessions, finds hotspot files, tracks shipping streaks. Team-aware: deep treatment on requestor's work, then breakdown for every contributor with specific praise and growth opportunities.

**Output** (source: README.md lines 481-500):
- Week-level summary: commits, LOC, test ratio, PRs, peak hours, shipping streak
- Per-contributor breakdown with praise and growth opportunities
- Top 3 team wins, 3 things to improve, 3 habits for next week
- Saved JSON snapshot to `.context/retros/` for trend tracking

**Comparison mode**: `retro compare` shows this week vs last week side by side.

**Example from README**: 47 commits (3 contributors), 3.2k LOC, 38% tests, 12 PRs, 47-day shipping streak. Per-person: discipline on small PRs, low test ratios, shipping volume.

**Confidence**: High — output structure specified with metrics and example.

---

## Installation & Setup

**Requirements** (source: README.md line 100):
- Claude Code (any recent version)
- Git
- Bun v1.0+
- For `/browse` native binary: macOS or Linux (x64 or arm64)

**Global Install**:

```bash
git clone https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack
./setup
```

The `setup` script:
1. Runs `bun install` to fetch dependencies
2. Compiles the browse binary with `bun build --compile`
3. Creates symlinks at `~/.claude/skills/` for each skill (browse, qa, review, etc.)

**Project-Local Install** (optional, for team sharing):

```bash
cp -Rf ~/.claude/skills/gstack .claude/skills/gstack
rm -rf .claude/skills/gstack/.git
cd .claude/skills/gstack
./setup
```

**What gets installed** (source: README.md lines 115-122):
- Skill files (Markdown prompts) in `~/.claude/skills/gstack/`
- Symlinks at `~/.claude/skills/browse`, `~/.claude/skills/qa`, `~/.claude/skills/review`, etc.
- Compiled browser binary at `browse/dist/browse` (~58MB, gitignored)
- `node_modules/` (gitignored)
- Retro snapshots to `.context/retros/` for trend tracking

Everything lives in `.claude/` — nothing touches PATH or runs in background.

**Upgrade**:

```bash
cd ~/.claude/skills/gstack && git fetch origin && git reset --hard origin/main && ./setup
```

---

## Architecture & Implementation

### Repository Structure (source: CLAUDE.md)

```
gstack/
├── browse/          # Headless browser CLI (Playwright)
│   ├── src/
│   │   ├── cli.ts              # Thin client
│   │   ├── server.ts           # HTTP server + command routing
│   │   ├── browser-manager.ts  # Chromium lifecycle
│   │   ├── snapshot.ts         # Accessibility tree → refs
│   │   ├── read-commands.ts    # Non-mutating commands
│   │   ├── write-commands.ts   # Mutating commands (click, fill, etc.)
│   │   ├── meta-commands.ts    # Server management, chain, diff
│   │   ├── cookie-import-browser.ts  # macOS Keychain decryption
│   │   ├── cookie-picker-routes.ts   # Cookie picker UI HTTP routes
│   │   ├── cookie-picker-ui.ts       # Self-contained HTML/CSS/JS
│   │   └── buffers.ts          # CircularBuffer for logs
│   ├── test/        # Integration tests + fixtures
│   └── dist/        # Compiled binary
├── plan-ceo-review/ # /plan-ceo-review skill
├── plan-eng-review/ # /plan-eng-review skill
├── review/          # /review skill
├── ship/            # /ship skill
├── qa/              # /qa skill (with templates, issue taxonomy)
├── setup-browser-cookies/  # /setup-browser-cookies skill
├── retro/           # /retro skill
├── setup            # Build + symlink script
├── package.json     # Dependencies + build scripts
└── README.md
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Implementation language | TypeScript |
| Runtime | Bun v1.0+ (source: package.json) |
| Browser automation | Playwright 1.58.2 (source: package.json dependencies) |
| Build tool | Bun --compile (generates ~58MB single binary) |
| HTTP server | Bun.serve |
| IPC mechanism | HTTP over localhost with bearer token auth |
| Security | macOS Keychain for cookie decryption; chmod 600 state file |
| Testing | Bun test integration tests (166 tests as of 0.3.0) |

### Browser Daemon Architecture (source: BROWSER.md)

```
Claude Code
    │
    ▼
browse CLI (thin client, ~1ms startup)
    │ HTTP POST localhost:9400 (Bearer token)
    ▼
Bun HTTP server (persistent daemon)
    │
    ├─ browser-manager.ts (Chromium lifecycle)
    ├─ snapshot.ts (accessibility tree → ref map)
    ├─ read/write/meta commands
    └─ Playwright API calls
           │
           ▼
         Headless Chromium (auto-starts on first call, auto-stops after 30 min idle)
```

**Isolation model**: Thin CLI client reads state file, sends command, prints response. No state stored in CLI. All state managed by persistent daemon. Multi-workspace support via `CONDUCTOR_PORT` or `BROWSE_PORT` env vars.

**Error handling**: Crash recovery (no self-healing — expose failure), actionable Playwright error wrapping for agents.

---

## Features Deep Dive

### Accessibility-Based Element Selection

Most sophisticated feature of the browse tool. Instead of brittle CSS selectors or XPath, gstack uses Playwright's accessibility tree API:

1. `page.locator(scope).ariaSnapshot()` returns YAML-like tree
2. Parser assigns sequential refs (`@e1`, `@e2`, ...) to each element
3. For each ref, builds a Playwright `Locator` using `getByRole` + nth-child
4. Ref-to-Locator map stored on `BrowserManager`
5. Commands like `click @e3` look up Locator and execute

**Extended features** (source: BROWSER.md lines 92-93):
- `--diff` (`-D`): Baseline snapshot, next `-D` call returns unified diff of changes
- `--annotate` (`-a`): Overlay ref labels on screenshot, then remove
- `--cursor-interactive` (`-C`): Scan for non-ARIA clickables (divs with cursor:pointer, onclick, tabindex>=0), assign `@c1`, `@c2`... refs

**Benefit**: No DOM injection. No scripts. Just native Playwright accessibility API. Works across frameworks because ARIA is standardized.

### Snapshot Diffing

`snapshot -D` stores baseline. Next `snapshot -D` call compares current against baseline, returns unified diff showing what changed. Verification that actions actually worked.

### Multi-Tab & Cookie Management

Commands: `tabs`, `tab`, `newtab`, `closetab` for multi-page workflows.

Cookie import: `cookie-import <json-file>` with auto-fill domain, or `cookie-import-browser` for macOS Keychain decryption with interactive picker.

### Console, Network, Dialog Capture

Hooked into Playwright events, kept in O(1) circular buffers (50,000 capacity each), flushed asynchronously to disk. Accessible via commands: `console`, `network`, `dialog`. Dialogs auto-accepted by default (configurable).

### The `chain` Command

Multi-step commands in one call (JSON from stdin). Executes sequentially, returns results.

---

## Limitations & Caveats

### Browser Scope Limitations

1. **Authentication complexity**: While `/setup-browser-cookies` handles import from real browsers, multi-factor authentication flows still require manual intervention if MFA is required.

   _Confidence_: Medium — documented in README that interactive login is needed, but edge cases around MFA not explicitly covered.

2. **JavaScript-heavy apps**: While Playwright waits for network idle by default, highly dynamic apps with continuous polling or WebSocket connections may be challenging. Snapshot refs are based on accessibility tree, which only captures currently-rendered elements (not shadow DOM or iframes without accessible labels).

   _Confidence_: Medium — inferred from Playwright capabilities; not explicitly documented in gstack docs.

3. **No built-in visual regression testing**: Screenshots are for manual verification. No perceptual diffs or pixel-level regression detection.

   _Confidence_: High — scope is explicit in `/qa` documentation: screenshots for evidence, not automated visual regression.

### Skill Limitations

4. **`/plan-ceo-review` can ideate beyond feasibility**: No real-time product constraint checking. Plans may explore ideas that are technically infeasible or outside current project scope.

   _Confidence_: Low — limitation not documented; inferred from nature of founder-mode brainstorming.

5. **`/review` requires production context**: Code review is structural (race conditions, invariants) but not context-aware. Can miss domain-specific bugs (e.g., business logic errors). Requires reviewer to be familiar with the problem domain.

   _Confidence_: Medium — README explicitly says "paranoid staff engineer mode" for structural bugs, implicitly scoped to things CI misses, not domain logic.

6. **`/retro` metrics are git-based only**: Does not track actual deployed-hours, feature flag rollouts, on-call incidents, or runtime performance degradation. Metrics are commit history and file changes only.

   _Confidence_: High — `/retro` output documented with specific metrics (commits, LOC, test ratio, per-file analysis), all derived from git history.

### Conductor Requirement for 10-Parallel Setup

From README: "How to fly: 10 sessions at once — Conductor runs multiple Claude Code sessions in parallel." (line 88-96)

Conductor is a separate platform (conductor.build) — gstack is just "Conductor-aware," meaning it auto-detects `CONDUCTOR_PORT` and isolates browser instances. Conductor is required for true parallel execution at scale.

_Confidence_: High — explicitly stated as separate tool with Conductor-aware setup.

---

## Relevance to Claude Code Development

**Primary use case**: gstack is a workflow automation framework FOR Claude Code development, not a framework FOR building Claude Code plugins or agents.

**Relevance to this repo (claude_skills)**:
- **Pattern reference**: gstack demonstrates the "role-specific agent" pattern that could be adapted for other skill domains (e.g., testing skills, deployment skills, documentation skills)
- **Browser automation integration**: `/browse` is a proven alternative to MCP-based browser tools with lower context overhead
- **Parallel execution integration**: Multi-workspace support via environment variables could inform how claude_skills handles concurrent agent execution
- **Skill organization**: Eight separate skills in one repo with a shared binary (browse) is a scalable pattern for feature-rich tool suites

**Not relevant**:
- Doesn't help with agent scaffolding, skill validation, plugin architecture, or marketplace mechanics
- Doesn't contribute to claude_skills' own implementation (though it demonstrates mature Claude Code skill design)

---

## Usage Patterns & Workflows

### Single-Session Workflow

From README demo (lines 33-80):
1. Describe feature in plan mode
2. `/plan-ceo-review` pressure-tests product direction
3. `/plan-eng-review` locks in architecture
4. Exit plan mode, implement
5. `/review` finds structural bugs
6. `/ship` lands the branch
7. `/setup-browser-cookies` imports test auth
8. `/qa https://staging.myapp.com --quick` smoke test
9. `/browse staging.myapp.com/feature` detailed QA

### Parallel Workflow (with Conductor)

From README (lines 88-96): One person, ten parallel Claude Code sessions:
- Session 1: `/qa` on staging
- Session 2: `/review` on PR
- Session 3: implementing feature
- Sessions 4-10: other branches/tasks

Each workspace gets isolated browser instance (separate Chromium process, cookies, tabs, logs).

### Retrospective Workflow

From README (lines 502): `/retro compare` for weekly trends. JSON snapshots saved to `.context/retros/` for baseline tracking.

---

## References

- [GitHub Repository](https://github.com/garrytan/gstack) — accessed 2026-03-13
- [README.md](https://github.com/garrytan/gstack/blob/main/README.md) — accessed 2026-03-13
- [BROWSER.md](https://github.com/garrytan/gstack/blob/main/BROWSER.md) — technical internals, command reference, performance comparison
- [CHANGELOG.md](https://github.com/garrytan/gstack/blob/main/CHANGELOG.md) — version history, 0.3.1 features
- [package.json](https://github.com/garrytan/gstack/blob/main/package.json) — dependencies (Playwright 1.58.2), runtime requirements (Bun 1.0+)
- [CLAUDE.md](https://github.com/garrytan/gstack/blob/main/CLAUDE.md) — repository structure, development guide
- GitHub API `/repos/garrytan/gstack` — stars (6,058), forks (710), license (MIT), language (TypeScript), last pushed (2026-03-14)

---

## Next Review Date

2026-06-13 (3 months from initial research)

Monitor for:
- Major version updates to gstack (currently 0.3.1 — pre-1.0)
- Conductor integration changes
- New skills or substantial refactors to existing skills
- Breaking changes to browse command API

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Browser MCP](../mcp-ecosystem/browsermcp-mcp.md) | mcp-ecosystem | Alternative browser automation approach: Browser MCP preserves real browser profiles via extension bridge, while gstack's /browse spawns isolated headless sessions |
| [Kernel](../agent-infrastructure/kernel-sh.md) | agent-infrastructure | Cloud-hosted browsers-as-a-service platform providing similar VPC isolation and session persistence features to gstack's /browse infrastructure |
| [PinchTab](../agent-infrastructure/pinchtab.md) | agent-infrastructure | Accessibility-tree-based element refs (~800 tokens/page) complement gstack's snapshot-with-refs approach; both prioritize token efficiency over screenshots |
| [git-cliff](../developer-tools/git-cliff.md) | developer-tools | Changelog automation foundation for gstack's /ship skill's version and release documentation workflow |
| [Superpowers](../agent-frameworks/superpowers.md) | agent-frameworks | Parallel multi-skill orchestration pattern: Superpowers uses composable skills for TDD/debugging; gstack uses skills for role-specific cognitive modes (founder/engineer/reviewer/release) |
| [Everything Claude Code](../developer-tools/everything-claude-code.md) | developer-tools | Large-scale skill ecosystem architecture similar to gstack's modular skill design; both provide specialized agents for distinct development lifecycle phases |
| [Get Shit Done](../agent-frameworks/get-shit-done.md) | agent-frameworks | Spec-driven multi-agent orchestration with context rotation between tasks, paralleling gstack's cognitive mode switching across /plan-ceo-review → /plan-eng-review → /review → /ship workflow |
| [Claude Quickstarts](../developer-tools/claude-quickstarts.md) | developer-tools | Official reference for multi-session agents and browser automation (Playwright) patterns underlying gstack's /browse and /qa infrastructure |
| [Niteni](../developer-tools/niteni.md) | developer-tools | Automated code review with severity classification and inline suggestions, analogous to gstack's /review skill structural audit approach |
| [Harness Engineering (OpenAI)](../evaluation-testing/harness-engineering-openai.md) | evaluation-testing | Production engineering discipline for AI agents: gstack's philosophy of role-specific cognitive modes echoes the harness approach of building scaffolding before expecting complex agent output |
