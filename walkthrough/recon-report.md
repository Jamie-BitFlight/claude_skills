# Codebase Risk Profile

**Generated**: 2026-05-22T10:42:00Z
**Repository**: claude_skills
**Size Class**: small (53 commits, 4 contributors) (shallow clone)
**Analysis Window**: all history
**Bug-Magnet Keywords**: fix, bug, broken, hotfix, revert
**Caveat**: Bug-magnet detection relies on commit-message keyword matching. Repositories
using ticket-ID-only messages, Conventional Commits without fix/bug words, or non-English
commit conventions may have an under-reported High-Risk Files section. Absence of entries
does not mean low risk.

**WARNING**: This repository is a shallow clone. Git history is truncated and results
may be incomplete. Run 'git fetch --unshallow' for accurate analysis.

## Code Hotspots

Files most frequently changed in the analysis window.

| Changes | File |
|---------|------|
| 26 | plugins/development-harness/.claude-plugin/plugin.json |
| 18 | plugins/plugin-creator/.claude-plugin/plugin.json |
| 5 | uv.lock |
| 5 | plugins/plugin-creator/skills/skill-creator/SKILL.md |
| 4 | plugins/plugin-creator/skills/optimize-claude-md/SKILL.md |
| 4 | plugins/plugin-creator/README.md |
| 4 | plugins/development-harness/tests/test_quality_gates.py |
| 4 | plugins/development-harness/skills/complete-implementation/SKILL.md |
| 4 | plugins/development-harness/sam_schema/core/query.py |
| 4 | plugins/development-harness/backlog_core/server.py |
| 3 | tests/test_quality_gate_integration.py |
| 3 | plugins/the-rewrite-room/.claude-plugin/plugin.json |
| 3 | plugins/plugin-creator/skills/plugin-lifecycle/SKILL.md |
| 3 | plugins/plugin-creator/skills/implement-refactor/SKILL.md |
| 3 | plugins/plugin-creator/skills/hooks-guide/SKILL.md |
| 3 | plugins/plugin-creator/skills/hook-creator/SKILL.md |
| 3 | plugins/plugin-creator/skills/assessor/SKILL.md |
| 3 | plugins/plugin-creator/CLAUDE.md |
| 3 | plugins/development-harness/tests/test_live_validation.py |
| 3 | plugins/development-harness/tests/test_backlog_core_server.py |

## Bug Magnets

Files most associated with fix, bug, broken, hotfix, or revert commits.

| Fix Commits | File |
|-------------|------|
| 21 | plugins/development-harness/.claude-plugin/plugin.json |
| 12 | plugins/plugin-creator/.claude-plugin/plugin.json |
| 4 | plugins/plugin-creator/skills/optimize-claude-md/SKILL.md |
| 4 | plugins/development-harness/sam_schema/core/query.py |
| 3 | plugins/the-rewrite-room/.claude-plugin/plugin.json |
| 3 | plugins/plugin-creator/skills/skill-creator/SKILL.md |
| 3 | plugins/plugin-creator/skills/plugin-lifecycle/SKILL.md |
| 3 | plugins/plugin-creator/skills/implement-refactor/SKILL.md |
| 3 | plugins/plugin-creator/skills/hooks-guide/SKILL.md |
| 3 | plugins/plugin-creator/skills/hook-creator/SKILL.md |
| 3 | plugins/plugin-creator/skills/assessor/SKILL.md |
| 3 | plugins/development-harness/tests/test_quality_gates.py |
| 3 | plugins/development-harness/tests/test_live_validation.py |
| 3 | plugins/development-harness/tests/conftest.py |
| 3 | plugins/development-harness/skills/work-backlog-item/references/workflows/work/post-planning.md |
| 3 | plugins/development-harness/skills/work-backlog-item/references/workflows/work/plan.md |
| 3 | plugins/development-harness/skills/work-backlog-item/SKILL.md |
| 3 | plugins/development-harness/skills/complete-implementation/SKILL.md |
| 3 | plugins/development-harness/sam_schema/server.py |
| 3 | plugins/development-harness/sam_schema/core/backends/local_yaml.py |

## High-Risk Files

Files appearing in both Code Hotspots and Bug Magnets — highest review priority.

| File | Changes | Fix Commits | Primary Owner |
|------|---------|-------------|---------------|
| plugins/development-harness/.claude-plugin/plugin.json | 26 | 21 | Jamie McGregor Nelson |
| plugins/plugin-creator/.claude-plugin/plugin.json | 18 | 12 | Jamie McGregor Nelson |
| plugins/plugin-creator/skills/skill-creator/SKILL.md | 5 | 3 | Jamie McGregor Nelson |
| plugins/plugin-creator/skills/optimize-claude-md/SKILL.md | 4 | 4 | Jamie McGregor Nelson |
| plugins/development-harness/tests/test_quality_gates.py | 4 | 3 | Jamie McGregor Nelson |
| plugins/development-harness/skills/complete-implementation/SKILL.md | 4 | 3 | Jamie McGregor Nelson |
| plugins/development-harness/sam_schema/core/query.py | 4 | 4 | Jamie McGregor Nelson |
| plugins/the-rewrite-room/.claude-plugin/plugin.json | 3 | 3 | Jamie McGregor Nelson |
| plugins/plugin-creator/skills/plugin-lifecycle/SKILL.md | 3 | 3 | Jamie McGregor Nelson |
| plugins/plugin-creator/skills/implement-refactor/SKILL.md | 3 | 3 | Jamie McGregor Nelson |
| plugins/plugin-creator/skills/hooks-guide/SKILL.md | 3 | 3 | Jamie McGregor Nelson |
| plugins/plugin-creator/skills/hook-creator/SKILL.md | 3 | 3 | Jamie McGregor Nelson |
| plugins/plugin-creator/skills/assessor/SKILL.md | 3 | 3 | Jamie McGregor Nelson |
| plugins/development-harness/tests/test_live_validation.py | 3 | 3 | Jamie McGregor Nelson |

## Bus Factor

All-time contributor ranking by commit count. Low bus factor = knowledge concentrated
in few contributors.

| Commits | Contributor |
|---------|-------------|
| 37 | Jamie McGregor Nelson |
| 10 | Jamie Nelson |
| 3 | Claude |
| 3 | dependabot[bot] |

**Bus Factor Assessment**: 2 contributors account for 80% of commits (47 of 53 commits).
Note: "Jamie McGregor Nelson" and "Jamie Nelson" are likely the same person committing
under two identities — effective bus factor for this repository is 1.

## Team Momentum

Commit activity by month in the analysis window.

| Month | Commits |
|-------|---------|
| 2026-05 | 53 |

**Active Contributors (last 3 months)**: 4 of 4 total contributors.

## Firefighting Frequency

Count of revert, hotfix, or rollback commits in the analysis window.

**Firefighting commits**: 0 (0% of total commits in window)

**Assessment**: healthy — < 5% = healthy, 5–15% = elevated, > 15% = high

## Recently Added Files

New files introduced in the analysis window. Review for missing tests,
insufficient documentation, or architectural drift.

- .agent/rules/git-commits.md
- .agent/skills/ccc
- .agents/skills/agent-browser/SKILL.md
- .agents/skills/agent-browser/references/authentication.md
- .agents/skills/agent-browser/references/commands.md
- .agents/skills/agent-browser/references/profiling.md
- .agents/skills/agent-browser/references/proxy-support.md
- .agents/skills/agent-browser/references/session-management.md
- .agents/skills/agent-browser/references/snapshot-refs.md
- .agents/skills/agent-browser/references/video-recording.md
- .agents/skills/agent-browser/templates/authenticated-session.sh
- .agents/skills/agent-browser/templates/capture-workflow.sh
- .agents/skills/agent-browser/templates/form-automation.sh
- .agents/skills/ccc/SKILL.md
- .agents/skills/ccc/references/management.md
- .agents/skills/ccc/references/settings.md
- .agents/skills/copy-editing/SKILL.md
- .agents/skills/copy-editing/evals/evals.json
- .agents/skills/copy-editing/references/plain-english-alternatives.md
- .claude-plugin/marketplace.json

## Recommendations

1. **Priority review targets**: The plugin manifest files
   `plugins/development-harness/.claude-plugin/plugin.json` (26 changes, 21 fix commits) and
   `plugins/plugin-creator/.claude-plugin/plugin.json` (18 changes, 12 fix commits) are the
   two highest-risk files — both churn heavily and are fix-commit magnets. Note these are
   auto-bumped by the pre-commit version hook, so the high fix-commit count partly reflects
   automated version bumps riding along on fix commits rather than defects in the files
   themselves (see EC-6 generated-file noise note).
2. **Knowledge transfer**: Jamie McGregor Nelson is the primary owner of every high-risk
   file in this report. Knowledge is highly concentrated. Consider pair programming or
   documentation sessions to spread ownership.
3. **Momentum**: Activity is concentrated entirely in a single month (2026-05) — consistent
   with a shallow clone truncating older history. Momentum trend cannot be assessed from
   truncated history.
4. **Firefighting**: low — 0% of commits are revert/hotfix/rollback. No firefighting signal
   in the analyzed window.
5. **New code review**: 20 new files were added in the analysis window (skill and reference
   files under `.agents/skills/` and `.agent/`); verify documentation completeness and any
   associated tests.
6. **Detection caveat**: Bug-magnet detection relies on commit-message keywords. Repositories
   with ticket-ID-only or non-English commit conventions may show an empty High-Risk Files
   section that does not reflect actual risk. See report header caveat for details.
   Additionally, this repository is a shallow clone — results reflect only truncated history.
