---
title: Composio Codebase Migrate
subtitle: Batched multi-file migration skill for large-scale codebase refactors via Composio CLI
category: skill-generation-tools
resource_url: https://github.com/ComposioHQ/awesome-codex-skills/tree/master/codebase-migrate
github_url: https://github.com/ComposioHQ/awesome-codex-skills
date_created: "2026-05-10"
date_last_reviewed: "2026-05-10"
status: published
---

## Overview

**codebase-migrate** is a Codex skill for executing large-scale codebase migrations and multi-file refactors across hundreds of files. It coordinates framework upgrades, API renames, configuration format migrations, and structural refactors using the Composio CLI to manage issue tracking, per-batch pull requests, and CI verification while the agent executes local transforms.

The skill distributes migration work into reviewable batches (~25 files per PR) with automatic checkpoint validation after each batch merges to main, reducing review friction and enabling parallelizable work patterns.

**Identity:**
- **Name:** codebase-migrate
- **Repository:** ComposioHQ/awesome-codex-skills (commit: 500b0c0)
- **License:** Not specified in source
- **Platforms:** Multi-platform (CLI-driven; requires Git, ripgrep, language-specific AST tools)

## Problem Addressed

Large codebase migrations face two competing constraints:

1. **Single massive PR** — technically complete but creates review bottleneck (800-line diffs are rarely reviewed thoroughly).
2. **Manual per-file edits** — reviewable but error-prone and unmaintainable without coordination.

**codebase-migrate** solves this by automating both the transform execution (via codemods) and the coordination ceremony (issue tracking, PR creation, CI polling, merge decision) — enabling teams to ship 200-file migrations as a sequence of reviewable 25-file batches.

## Key Statistics

- **Batch size:** 25 files per PR (configurable, recommended for review throughput)
- **Supported frameworks:** React 17→19, Node 18→22, Django 4→5 (examples; generalizes to any AST-driven transform)
- **Integration depth:** Composio CLI for GitHub PRs, Linear/Jira issue tracking, and CI polling
- **Language flexibility:** Works with `jscodeshift`, `ts-morph`, `comby`, `ast-grep` depending on source language

## Key Features

### 1. Transform Precision Definition
Skill guides definition of exact transforms before execution, with ripgrep scoping to find affected files.

**Example workflow:**
```bash
rg -l 'jest\.(mock|fn|spyOn)' | wc -l    # Find scope
rg -l 'from "jest"' | sort                # Find import patterns
```

### 2. Batched Execution with Tracking
- Pick N files from affected set
- Transform locally via codemod runner (`jscodeshift`, `ts-morph`, `comby`, or `ast-grep`)
- Test locally on batch only (`npm test -- --changed`)
- Create PR with batch metadata
- Poll CI status via Composio API
- Merge when green and loop to next batch

**Key mechanism:** Maintains a `done.list` to avoid re-processing files across batches.

### 3. Composio CLI Integration
Orchestrates GitHub and issue-tracking operations:
- `GITHUB_CREATE_A_PULL_REQUEST` — create PR with batch number and transform metadata
- `LINEAR_CREATE_ISSUE` / `LINEAR_CREATE_COMMENT` — track migration as issue with PR links
- `GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY` — poll CI status and wait for green

**Example:**
```bash
composio execute GITHUB_CREATE_A_PULL_REQUEST -d '{
  "owner":"acme","repo":"app",
  "head":"migrate/vitest-batch-03","base":"main",
  "title":"migrate(test): jest → vitest (batch 3)",
  "body":"Part of LIN-482. 25 files. Codemod: transforms/jest-to-vitest.ts."
}'
```

### 4. Verification Loop After Each Merge
Runs trending metrics to confirm progress:
```bash
rg 'jest\.(mock|fn|spyOn)' | wc -l    # Should trend to 0
npm test                               # Full suite
```

### 5. Workflow Script Support
TypeScript/JavaScript scripts in `scripts/migrate-batch.ts` can be run per-batch to automate:
- PR creation with issue linking
- Comment posting to tracking issue with PR URL
- Conditional merging based on CI status

## Technical Architecture

### Component Flow

1. **Planning Phase** (manual)
   - Define transform precisely
   - Scope blast radius with ripgrep
   - File tracking issue with Composio CLI

2. **Agent Execution Loop** (per batch)
   - Agent reads N files from ripgrep results
   - Runs codemod via `jscodeshift`, `ts-morph`, `comby`, or `ast-grep`
   - Runs local test suite (`npm test -- --changed`)
   - Commits to feature branch

3. **Orchestration via Composio** (automated)
   - Creates PR via `GITHUB_CREATE_A_PULL_REQUEST`
   - Links to tracking issue via `LINEAR_CREATE_COMMENT`
   - Polls CI via `GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY`
   - Merges when status is green

4. **Verification Phase** (post-merge)
   - Runs trending checks (`rg` to count remaining matches)
   - Runs full test suite
   - Moves to next batch

### Data Flow

```
ripgrep scan
    ↓
pick 25 files
    ↓
codemod + test locally
    ↓
git commit + push
    ↓
Composio: GITHUB_CREATE_A_PULL_REQUEST
    ↓
Composio: LINEAR_CREATE_COMMENT (link issue)
    ↓
Composio: GITHUB_LIST_WORKFLOW_RUNS (poll CI)
    ↓
[wait for green]
    ↓
merge via gh CLI
    ↓
verify + loop
```

### Extension Points

1. **Codemod choice:** Skill supports language-specific tooling — `jscodeshift` for Node, `ts-morph` for TypeScript, `comby` for text-based transforms, `ast-grep` for structural queries
2. **Batch size:** Default 25 files; configurable based on review capacity
3. **Test scope:** Can run `--changed` (batch-only) or full suite; full suite required on final batch
4. **Issue tracking:** Works with Linear or Jira via Composio executor

## Installation & Usage

### Prerequisites

```bash
# Install Composio CLI
curl -fsSL https://composio.dev/install | bash

# Authenticate
composio login
composio link github        # for PRs + CI
composio link linear        # for issue tracking (or jira)
```

### Local Tools Required

The agent will invoke these tools directly:
- `git` — branching and commits
- `rg` (ripgrep) — scoping affected files
- `jscodeshift`, `ts-morph`, `comby`, or `ast-grep` — language-specific AST codemods
- Test runner (`npm test`, `pytest`, etc.)

### Basic Workflow

```bash
# 1. Plan phase: find scope
rg -l 'jest\.(mock|fn)' | wc -l

# 2. Create tracking issue
composio execute LINEAR_CREATE_ISSUE -d '{
  "teamId":"TEAM_ID",
  "title":"Migrate test runner: jest → vitest",
  "description":"Batches of ~25 files per PR"
}'

# 3. Pick batch
BATCH=$(rg -l 'jest\.mock' | head -25)
echo "$BATCH" > batch.list

# 4. Agent transforms batch locally, tests, commits

# 5. Create PR (via Composio or gh CLI)
composio execute GITHUB_CREATE_A_PULL_REQUEST -d '{...}'

# 6. Poll CI
composio execute GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY -d '{...}'

# 7. When green, merge and repeat
```

### Example: Jest → Vitest Migration

Transform definition:
```bash
# Find affected files
rg -l 'jest\.(mock|fn|spyOn)' | sort

# Scope
rg -l 'from "jest"' | wc -l
```

Batch workflow script (`scripts/migrate-batch.ts`):
```ts
const batch = process.argv[process.argv.indexOf("--batch") + 1];
const pr = await execute("GITHUB_CREATE_A_PULL_REQUEST", {
  owner: "acme", repo: "app",
  head: `migrate/vitest-batch-${batch}`,
  base: "main",
  title: `migrate(test): jest → vitest (batch ${batch})`,
  body: `Part of LIN-482. See transforms/jest-to-vitest.ts.`
});
await execute("LINEAR_CREATE_COMMENT", {
  issueId: "LIN-482",
  body: `Opened PR #${pr.number}: ${pr.html_url}`
});
```

Run per batch:
```bash
composio run --file scripts/migrate-batch.ts -- --batch 3
```

## Limitations and Caveats

### Documented Limitations

1. **Codemod coverage:** Regex-based codemods may catch unintended patterns. Skill recommends switching to AST-based tooling (`ast-grep`, `ts-morph`) for structural matches.

2. **Batch size trade-off:** 25 files is optimal for human review; larger batches risk abandonment by maintainers (800-line diffs rarely reviewed thoroughly).

3. **Test environment drift:** Tests passing locally but failing in CI indicate Node/Python version mismatch between developer and CI environment; requires pinning `.nvmrc` or `pyproject.toml`.

4. **Batch conflict handling:** When multiple batches are open, rebase the older batch before merging the newer one; never force-push already-merged batches.

5. **Per-batch vs full suite:** Final batch MUST run full test suite; earlier batches can run `--changed` only.

### Undocumented Gaps

- No documented guidance on handling manual edits when codemod misses files (skill mentions "patch manually and note in PR body" but provides no template)
- No guidance on partial-rollback strategy if a batch is discovered to have broken edge cases after merge
- No atomic multi-issue tracking (can create one tracking issue, but linking multiple issues across batches not documented)

## Relevance to Claude Code Development

**Use case alignment:**
- The `codebase-migrate` skill is directly applicable to plugin lifecycle management in Claude Code. When a plugin API changes, the skill enables coordinated migration of all dependent plugins across the marketplace.
- Useful for large refactors across the `/plugins/*/skills/` directory structure, particularly for framework upgrades affecting multiple skill implementations.
- Supports multi-file renames in SAM task tracking systems where issue linking to work progress is critical.

**Integration pattern:**
- Codex skills are loaded by the Codex CLI and Codex API; Claude Code users do not directly invoke Codex skills. However, the orchestration pattern (batched PRs + CI checkpoints) is transferable to Claude Code workflows via custom agents or the Development Harness `/dh:*` suite.
- The Composio CLI integration pattern could be replicated in Claude Code via the `mcp__github__*` tools and SAM task tracking.

## References

- **SKILL.md source:** <https://github.com/ComposioHQ/awesome-codex-skills/blob/master/codebase-migrate/SKILL.md> (accessed 2026-05-10)
- **Composio CLI docs:** <https://docs.composio.dev/docs/cli> (referenced in source; not independently verified for current version)
- **Repository README:** <https://github.com/ComposioHQ/awesome-codex-skills/blob/master/README.md> (accessed 2026-05-10)
- **GitHub API documentation:** Inferred from Composio executor references (`GITHUB_CREATE_A_PULL_REQUEST`, `GITHUB_LIST_WORKFLOW_RUNS_FOR_A_REPOSITORY`) to standard GitHub REST API endpoints

## Freshness Tracking

**Last reviewed:** 2026-05-10
**Next review:** 2026-08-10 (3 months)

**Confidence summary:**
- **Identity/Metadata:** high — sourced from official repository frontmatter and README
- **Problem Addressed:** high — explicitly stated in skill documentation
- **Features:** high — extracted directly from "Execute in Reviewable Batches" and "Workflow Script" sections
- **Architecture:** high — data flow inferred from documented Composio CLI executor calls and bash examples
- **Usage Examples:** high — verbatim extraction from SKILL.md sections "Planning Phase" and "Execute in Reviewable Batches"
- **Limitations:** medium — documented limitations present; undocumented gaps noted but not comprehensive

**Notes:**
- Composio CLI version and exact feature set not independently verified beyond skill documentation
- Full Composio CLI reference link (docs.composio.dev) referenced in source but not independently accessed
- Integration with Claude Code is speculative; skill is designed for Codex ecosystem

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Awesome Codex Skills — Issue Triage](./awesome-codex-skills-issue-triage.md) | skill-generation-tools | Composio CLI orchestration: both use Composio CLI for multi-tool automation and bulk operations |
| [Codebase Recon Skill](./codebase-recon-skill.md) | skill-generation-tools | Pre-migration codebase analysis via git history across multiple dimensions before executing large-scale changes |
| [Agent Skills](./agent-skills.md) | skill-generation-tools | CI/CD and quality gate patterns; deprecation and migration workflows for large refactors |
| [GitHub CLI (gh)](../developer-tools/github-cli.md) | developer-tools | PR creation and CI polling: github-cli is alternative to Composio for GitHub operations |
| [Repomix](../developer-tools/repomix.md) | developer-tools | Codebase understanding before operations: pre-migration understanding of file structure and impact |
| [Vercel Labs Skills](./vercel-labs-skills.md) | skill-generation-tools | Multi-agent skill distribution pattern for large-scale tooling coordination |
| [mattpocock/skills](./mattpocock-skills.md) | skill-generation-tools | Architectural refactoring skill and pre-commit validation patterns for safe large-scale changes |

