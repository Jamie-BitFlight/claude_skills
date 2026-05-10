# Improvement Proposals: Codebase Recon Skill

**Research entry**: ./research/skill-generation-tools/codebase-recon-skill.md
**Generated**: 2026-05-10
**Patterns assessed**: 5
**Backlog items created**: 2 (issues: #2246, #2249)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 2

---

## Improvement 1: Add probe-phase auto-calibration to linear-walkthrough based on repository size

**Source pattern**: "Auto-Scaling Analysis — The skill runs a Probe phase to determine repository size and calibrates analysis parameters: Small repos (<500 commits): analyze entire history, return 10 results. Medium repos (500-10k): analyze last 1 year, return 20 results. Large repos (>10k): analyze last 6 months, return 30 results." — research entry section "Key Features", lines 37-47.
**Local system**: ./.claude/skills/linear-walkthrough/SKILL.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #2246 created

### Current state

`linear-walkthrough/SKILL.md` uses a fixed 50k-token-per-agent read budget regardless of repository size (lines 36, 53, 68, line 40 of references/agent-instructions.md). The Discovery phase (Phase 1) writes a coverage plan, but coverage plan agent assignments are sized only by total file bytes per file (`~4 characters per token` proxy at line 40 of agent-instructions.md). There is no orchestrator-level probe step that inspects repository size signals (commit count, file count, contributor count, age) before spawning the Discovery agent. The number of parallel Tracing agents (N) is determined by the Discovery agent splitting files into 50k-token assignments — small repos still pay the cost of full Discovery + multiple Tracing agents + Validation rotation; large repos receive the same fixed per-agent budget regardless of how much the codebase actually contains.

### Target state

A Phase 0 "Repo Probe" step is added at the top of the linear-walkthrough Mermaid workflow, executed by the orchestrator before Phase 1 Discovery. The probe runs three commands and writes their results to `walkthrough/repo-vitals.md`:

1. `git rev-list --count HEAD` — total commits
2. `find <target-directory> -type f \( -name "*.py" -o -name "*.ts" -o ... \) | wc -l` — source file count
3. `git shortlog -sn --no-merges | wc -l` — total contributors

The probe result classifies the repo as small (<500 commits OR <100 source files), medium (500-10k commits, 100-1000 files), or large (>10k commits, >1000 files), and writes a calibration block at the top of `coverage-plan.md`. The Discovery agent reads this calibration block and adjusts:

- Small: single Tracing agent, no cross-validation rotation, skip synthesis-validation if N=1
- Medium: current behavior (N agents, M validators)
- Large: tighter per-agent token budget (25k instead of 50k), larger N, validation rotation enforced

### Measurable signal

After the change, running `/linear-walkthrough` on a target directory produces `walkthrough/repo-vitals.md` containing the three probe values and a classification line `size_class: small|medium|large`. The string `size_class:` is grep-able. `coverage-plan.md` contains a `## Calibration` section that names which class was selected and how many tracing agents will spawn. On a small synthetic repo (<10 commits, <5 files), exactly 1 tracing agent is spawned; on a medium repo, the default N>=2 spawns; the orchestrator log records the probe was consulted before Phase 1.

---

## Improvement 2: New skill for git-history risk reconnaissance before code review

**Source pattern**: "Cross-Referencing and Risk Identification — High-Risk Files: Intersects code hotspots with bug magnets to identify files that are both frequently changed AND bug-prone. Risk Ownership: For each high-risk file, runs `git shortlog -sn -- <file>` to identify the primary owner. Bus Factor Risk: Flags knowledge concentration if active contributors are less than 30% of total contributors." — research entry section "Key Features", lines 63-70. Also "Seven-Dimension Parallel Analysis" lines 49-61.
**Local system**: ./.claude/skills/ (no existing skill performs git-history risk analysis)
**Confidence**: High
**Impact**: High
**Backlog**: #2249 created

### Current state

Grep of `/home/user/claude_skills/.claude/skills/` and `/home/user/claude_skills/plugins/*/skills/` for `shortlog`, `hotspot`, `bug magnet`, `bus factor`, `firefighting`, `momentum` returns zero matches — no local skill performs git-history-based risk identification. The `linear-walkthrough` skill traces execution paths through code but does not consume git metadata (file change frequency, fix commit clustering, contributor distribution). The `create-merge-request-changelog` skill consumes git history but only for the diff between two refs, not for whole-repo risk profiling. As a result, when the orchestrator spawns code-review agents (e.g., `code-review.md`, `code-reviewer` from various plugins), those agents have no signal indicating which files are highest-risk and should receive priority attention. The orchestrator cannot direct attention to "this file changes the most AND has the most fix commits" without manually constructing the git pipeline each time.

### Target state

A new skill at `./.claude/skills/git-history-recon/SKILL.md` is created. Its workflow:

1. Probe repo size (commit count, contributor count) and select a calibrated time window — small repos analyze all history, medium 1 year, large 6 months
2. Run 7 git pipelines in parallel (orchestrator may dispatch individual Bash calls or use a single helper script):
   - hotspots: `git log --name-only --since=<window> | sort | uniq -c | sort -rn | head -<N>`
   - bug magnets: `git log --grep='fix\|bug\|broken\|hotfix\|revert' --name-only --since=<window> | sort | uniq -c | sort -rn | head -<N>`
   - bus factor: `git shortlog -sn --no-merges`
   - active vs total contributors (last 3 months)
   - momentum: `git log --since=<window> --format='%Y-%m' | sort | uniq -c`
   - firefighting: count of revert/hotfix/rollback commits in window
   - newly added files: `git log --since=<window> --diff-filter=A --name-only`
3. Cross-reference: intersect hotspots with bug magnets → high-risk file list with primary owner per file
4. Output `walkthrough/recon-report.md` with 8 sections matching the codebase-recon report template (vitals, hotspots, bug magnets, high-risk files, bus factor, momentum, firefighting, newly added, recommendations)

The skill is invocable as `/git-history-recon` and produces a markdown report consumable by `linear-walkthrough` (which can reference it during Phase 1 Discovery to prioritize coverage), `code-review` agents (which receive the high-risk file list as priority targets), and onboarding workflows.

### Measurable signal

`./.claude/skills/git-history-recon/SKILL.md` exists with frontmatter `name: git-history-recon`. Running `/git-history-recon` on a git repository writes `walkthrough/recon-report.md` containing literal section headers `## Code Hotspots`, `## Bug Magnets`, `## High-Risk Files`, `## Bus Factor`, `## Team Momentum`, `## Firefighting Frequency`, `## Recently Added Files`, `## Recommendations`. Each section contains at least one entry sourced from the corresponding git command. The High-Risk Files section is computed as the set intersection of hotspots and bug magnets, with each file annotated with its `git shortlog -sn -- <file>` primary owner. The skill validates with `uvx skilllint@latest check ./.claude/skills/git-history-recon/`.

---

## Improvement 3: Linear-walkthrough Discovery agent should consume a recon report when one exists

**Source pattern**: "Codebase Intelligence Before Code Review — Provides structured input for code review agents, architects, and analyzers by identifying hotspots and high-risk files beforehand." — research entry section "Relevance to Claude Code Development", lines 200-203.
**Local system**: ./.claude/skills/linear-walkthrough/references/agent-instructions.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence medium: the Discovery agent's coverage plan logic in `agent-instructions.md` already prioritizes by file size and entry-point clustering. Whether bolting on a recon-report consumer is the cleanest integration point depends on whether Improvement 2 (the git-history-recon skill) lands first and what its output schema looks like. Specifically, the Discovery agent's clustering rule ("Each assignment must... include a rationale for why these files belong together" — agent-instructions.md line 38) could either consume recon-report.md as a prioritization input or not — either path is defensible without further design.

### Current state

`./.claude/skills/linear-walkthrough/references/agent-instructions.md` lines 12-43 instruct the Discovery agent to identify entry points, build assignments by clustering related entry points, estimate token budgets per assignment by file size, and track uncovered areas. The instructions never reference git history, file change frequency, or risk signals. If a recon report exists at a known location, the Discovery agent has no instruction to read it or weight high-risk files higher in coverage prioritization.

### Target state

The Discovery Agent Instructions section gains a step: "If `walkthrough/recon-report.md` exists, read its `## High-Risk Files` and `## Code Hotspots` sections. Files appearing in either list must be assigned to a Tracing agent (no high-risk file may be left in the uncovered areas section unless the entire codebase exceeds Discovery's read budget). Note in each assignment's rationale which files were prioritized due to recon signals." This couples the recon report (Improvement 2) into the walkthrough flow.

### Measurable signal

Discovery agent output `coverage-plan.md` includes a `## Recon-Driven Prioritization` subsection listing files lifted from `recon-report.md`. When `recon-report.md` is absent, the subsection is omitted. Running `/linear-walkthrough` after `/git-history-recon` produces a coverage plan where every High-Risk File from the recon report is assigned to some Tracing agent.

---

## Improvement 4: Optional report export step at end of linear-walkthrough synthesis

**Source pattern**: "Post-Report Markdown Export — After displaying the terminal report, the skill offers to save findings to a markdown file (e.g., `docs/codebase-recon-report.md`) for persistent documentation. No automatic commit — user decides whether to version the report." — research entry section "Key Features", lines 94-98.
**Local system**: ./.claude/skills/linear-walkthrough/SKILL.md (Phase 4 Synthesis)
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence low: linear-walkthrough already writes `walkthrough/unified-walkthrough.md` (or `walkthrough/unified/index.md` for the multi-file split case) as its final artifact. The "offer to export" step from codebase-recon is solving a problem (terminal output is ephemeral) that linear-walkthrough already solves (output is always a file). Any improvement here would be a micro-enhancement (e.g., offer to copy unified-walkthrough.md to a project-root location like `docs/architecture.md`) and the value is marginal. Would need user feedback that current output location is inconvenient before treating this as a real gap.

### Current state

`linear-walkthrough/SKILL.md` Phase 4 always writes `walkthrough/unified-walkthrough.md` to the target directory's `walkthrough/` subdirectory. There is no prompt to relocate the artifact to a more user-visible location like `docs/`.

### Target state

Optional final step prompts the user (via AskUserQuestion or equivalent) whether to copy the unified walkthrough to `docs/architecture.md` or keep it scoped to `walkthrough/`.

### Measurable signal

After Phase 4 completes, the orchestrator either has user input recording the choice or has copied the file. Not actionable until the gap is validated.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Linear-walkthrough Discovery agent consumes recon report (Improvement 3) | medium | Depends on Improvement 2 landing first; coupling design defensible either way without further design work |
| Optional report export step (Improvement 4) | low | Linear-walkthrough already writes file output by default; marginal value without user feedback |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Multi-ecosystem skill packaging via Agent Skills Specification (Claude Code + skills.sh + Codex Plugin System) | Already covered by `./plugins/plugin-creator/skills/agentskills/SKILL.md` and `./plugins/plugin-creator/skills/skill-creator/references/agent-plugin-ecosystem.md` (referenced at line 162 of agent-plugin-ecosystem.md, accessed 2026-05-10). The portable-fields rule and validation gate in those references already capture the cross-ecosystem distribution pattern. |
| Slash-command activation as `/codebase-recon` | Already covered — every skill in this repo is invocable as a slash command via the standard skill activation mechanism documented in `./plugins/plugin-creator/skills/claude-skills-overview-2026/SKILL.md`. The "use slash command for invocation" pattern is the default path for any local skill, including the proposed `/git-history-recon` from Improvement 2. |
