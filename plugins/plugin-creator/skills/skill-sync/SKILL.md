---
name: skill-sync
description: "Sync a skill's content against the upstream library it covers — check whether the API descriptions, version references, and SOURCE: citations inside SKILL.md and its reference files still reflect what the library actually does today. Use when a library has released updates that may have changed the APIs the skill covers, when a skill references an old library version, when asked to sync, refresh, update, or check a skill against upstream docs, when the skill's content may have drifted from current library behavior, or when SOURCE: citations are stale. Accepts a SKILL.md path, skill directory, or plugin directory."
argument-hint: <skill-path-or-plugin-directory>
model: sonnet
user-invocable: true
---

<sync_target>$1</sync_target>
<invocation_args>$ARGUMENTS</invocation_args>

## Argument Contract

| Input | Resolution |
|---|---|
| Path to a `SKILL.md` file | One pipeline for that skill |
| Path to a skill directory containing `SKILL.md` | One pipeline for that skill |
| Path to a plugin directory containing `skills/` | Glob `skills/*/SKILL.md` → one pipeline per skill |
| Anything else or empty | STOP — report ambiguity, ask for a skill path |

## Pipeline

```mermaid
flowchart TD
    S1["Stage 1 — Token Profile<br>uvx skilllint@latest check SKILL.md<br>wc -w on references/ for size map"] --> S1Q
    S1Q{"Existing file<br>already over SK007?"}
    S1Q -->|"Yes"| S1R["Apply /refactor-skill<br>progressive-disclosure extraction<br>Restart pipeline after"]
    S1Q -->|"No"| S2
    S2["Stage 2 — Parallel Read Agents<br>3 Agent() calls in ONE turn"] --> S3
    S3["Stage 3 — Synthesis<br>Fetch docs index, validate NEW URLs<br>Write change plan to .tmp/scratch/plans/"] --> S3Q
    S3Q{"Change plan has<br>changes?"}
    S3Q -->|"No — all VERIFIED"| Done1(["No changes needed — exit"])
    S3Q -->|"Yes"| S4
    S4["Stage 4 — Clean-Tree Gate<br>git status --porcelain"] --> S4Q
    S4Q{"Output empty?"}
    S4Q -->|"Not empty"| S4Stop(["STOP — dirty working tree<br>List uncommitted files"])
    S4Q -->|"Empty"| S45
    S45["Stage 4.5 — Orchestrator Pre-Fetch<br>Fetch all SOURCE URLs from change plan<br>Write verified content to source-material file<br>URLs that 404 → UNVERIFIABLE, skip"] --> S5
    S5["Stage 5 — Write Agent<br>Agent(skill-content-updater)<br>Receives change plan + source-material path"] --> S5Q
    S5Q{"Post-write skilllint<br>exit code?"}
    S5Q -->|"0"| S6
    S5Q -->|"non-zero"| S5R["Extract over-budget sections<br>to references/<br>Update change plan"]
    S5R --> S5
    S6["Stage 6 — Completion Gate<br>skilllint on ALL modified files"] --> S6Q
    S6Q{"All pass?"}
    S6Q -->|"Yes"| Done2(["Pipeline complete"])
    S6Q -->|"No"| S5
```

## Stage Definitions

**Stage 1 — Token Profile**

Run `uvx skilllint@latest check <skill-path>/SKILL.md` (target the file, not the directory — passing a directory silently reports "Total files: 0" and exits 0 without validating anything). Note whether it passes or fails SK007.

To identify the largest reference files before adding content, run `wc -w <skill-path>/references/*.md | sort -rn | head -5` and surface the top 3 by word count. This indicates where budget pressure is highest.

Pre-write SK007 branch: if the existing SKILL.md is already over SK007, apply `/plugin-creator:refactor-skill` (progressive-disclosure extraction) before making content changes. Restart the pipeline after the refactor completes.

**Stage 2 — Parallel Read Agents**

Dispatch exactly 3 `Agent()` calls in ONE turn so they run concurrently:

1. `Agent(subagent_type="plugin-creator:skill-auditor")` — input: `<skill-path>`; output: `.tmp/scratch/reports/skill-sync-{slug}-completeness-YYYYMMDD.md` (read-only)
2. `plugin-creator:skill-content-updater` (read role) — upstream drift scan; output: drift report with NEW/STALE/VERIFIED/UNVERIFIABLE verdicts per claim
3. `general-purpose` — structure validation; checks progressive disclosure, frontmatter schema, broken reference links; output: structure report

Each agent writes its report to `.tmp/scratch/reports/`. Report formats: [./references/report-formats.md](./references/report-formats.md)

**Note on drift scanner URL fetching:** The `skill-content-updater` agent fetches the SOURCE: citation URLs already present in the skill, as defined in [./references/url-fetch-spec.md](./references/url-fetch-spec.md). Do not instruct it to fetch an external docs index — that is the `skill-sync-source-validator` agent's responsibility in Stage 4.5.

**Stage 3 — Synthesis**

Orchestrator reads all three reports and writes the change plan to `.tmp/scratch/plans/skill-sync-{slug}-YYYYMMDD.md`.

If all verdicts are VERIFIED and no structural issues found: write a "no changes needed" change plan and skip Stages 4–6.

Change plan format and synthesis precedence rules: [./references/change-plan-format.md](./references/change-plan-format.md)

**Stage 4 — Clean-Tree Gate**

```bash
git status --porcelain
```

If output is not empty: STOP. List the uncommitted files. Report to the user. Do not proceed until the tree is clean.

**Stage 4.5 — Source Validation Agent**

Dispatch `Agent(subagent_type="plugin-creator:skill-sync-source-validator")`. Pass the change plan path.

The agent validates and pre-fetches all source content before the write agent runs, keeping URL fetching out of the write agent's context and providing a structured fallback chain when primary fetch methods fail. It handles:
- Validating all NEW URLs against the docs index (`llms.txt` / sitemap) — downgrades fabricated URLs to UNVERIFIABLE directly in the change plan file
- Pre-fetching content for every SOURCE URL using the priority fetch chain defined in [./references/url-fetch-spec.md](./references/url-fetch-spec.md)
- Writing `.tmp/scratch/fetched/source-material-YYYYMMDD.md` with verified content per change plan entry
- Updating the change plan header with the source-material file path

**Stage 5 — Schema-Aware Write Agent**

Dispatch one `Agent(subagent_type="plugin-creator:skill-content-updater")` in write role. Pass the change plan path. The change plan header now contains the source-material file path — the write agent reads from that file and does not need to fetch any URLs.

After the agent returns, run `uvx skilllint@latest check <modified-skill-path>/SKILL.md`. If non-zero: extract the over-budget sections to `references/`, update the change plan with the extraction directive, and re-dispatch the write agent.

**Stage 6 — Completion Gate**

Run `uvx skilllint@latest check` on every file modified in Stage 5. All must exit 0. If any fail: return to Stage 5 with a targeted remediation change plan.
