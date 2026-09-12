# Goal Contract Assessment — `.claude/skills/research-curator/`

Produced by `/skill-lapidary:establish-validatable-goals .claude/skills/research-curator/`.
Assess-only pass; the two confirmed discrepancies below were subsequently fixed in a follow-up
commit on this branch (see git log for this file's directory). This document is a record of the
assessment, not a live-updated status page — re-run the skill for a current read.

---

## 1. Target Boundary, Kind, Authority Context, Sources Read

**Kind**: Agent Skill (Claude Code plugin skill directory), invoked as `/research-curator`.

**Boundary examined**: complete `.claude/skills/research-curator/` directory —
`SKILL.md`, `SKILL-GOALS.md`, `references/{batch-mode,duplicate-detection,entry-template,frontmatter-generation,repo-access-procedure,validation-rules}.md`, `scripts/{validate_research.py,fix_research_formatting.py,migrate_to_yaml_frontmatter.py,refresh_github_stats.py,backlink_lib.py}`.

**Independently observed local usage evidence**:
- Paired subagents in `.claude/agents/`: `research-curator.md`, `research-insight-extractor.md`, `research-utilization-assessor.md`, `research-cross-referencer.md`, `research-backlink-detector.md`, and `research-context-agent.md`.
- Real corpus at `./research/` (README.md + ~30 category directories, an `insights/` and `utilization/` directory) — evidence the skill has actual production usage.
- Git history: `SKILL.md` has 26 commits; `SKILL-GOALS.md` has exactly one commit, part of PR #3234 "feat(plugin-creator): add skill-goal-extractor skill".
- Read `validate_research.py` directly to check code against documented behavior.

**Authority context**: No user-supplied goals or acceptance criteria were provided with the original request. `SKILL-GOALS.md` exists, so it is the strongest available source per goal-source precedence, and is treated as `OBSERVED`. Its git history shows it was added in the same commit that introduced the `skill-goal-extractor` tool itself — i.e., it reads as a tool-generated extraction, not a user-reviewed/approved artifact, and no separate approval event was found for its specific content. **All six goals in `SKILL-GOALS.md` remain `OBSERVED`, not `APPROVED`**, pending explicit user approval or independently observed repository governance.

---

## 2. Goals (status + provenance)

Source: `SKILL-GOALS.md` (`OBSERVED`, not `APPROVED`).

| # | Goal | Provenance |
|---|---|---|
| G1 | Quote-grounded research entries with confidence levels per claim | `OBSERVED` (SKILL-GOALS.md L3) |
| G2 | Duplicate/staleness avoidance via URL detection → `--rerun` routing | `OBSERVED` (SKILL-GOALS.md L4) |
| G3 | Parallel batch intake, ≤5 concurrent agents/wave, no lost failure detail, no rate-limit overwhelm | `OBSERVED` (SKILL-GOALS.md L5) |
| G4 | Structural validity — auto-fix error-severity, surface warning/info | `OBSERVED` (SKILL-GOALS.md L6) |
| G5 | Passive research → active follow-through (backlog, utilization, cross-reference graph) | `OBSERVED` (SKILL-GOALS.md L7) |
| G6 | End-to-end fidelity of agent-reported results (no generalization/information loss) | `OBSERVED` (SKILL-GOALS.md L8) |

---

## 3. Invariants, Constraints, Non-Goals

- **Invariant (G3)**: max 5 concurrent `@research-curator` agents per wave; waves are sequential (`batch-mode.md`).
- **Invariant**: backlink-detector agents run strictly sequentially, one entry at a time, to prevent a write race on shared cited entries (`batch-mode.md`).
- **Non-goal** (`research-curator.md` agent, "Fidelity Rule 2a"): stars/forks/contributor counts are never gathered, by any fallback.
- **Constraint** (`entry-template.md`): freshness schedule — 3-month default next-review, 6-month stale threshold, shorter (4–6 week) intervals for high-release-cadence projects; calibration is left to agent judgment, unenforced by any script.
- No explicit "## Non-Goals" section exists centrally; the non-goal above is recovered indirectly from an agent file, not stated centrally.

---

## 4. Per-Goal Assessment (summary)

| Goal | Readiness | Key finding |
|---|---|---|
| G1 — quote-grounded, per-claim confidence | `UNDERDEFINED` | Convention documented (`entry-template.md`) but no validator check enforces confidence-qualifier presence or quote-grounding. |
| G2 — duplicate/staleness avoidance | `EVALUABLE_WITH_HUMAN_JUDGMENT` | Procedure fully specified (`duplicate-detection.md`); no automated test — agent-executed prose, not code. |
| G3 — bounded parallel batch intake | `UNOBSERVABLE_WITHIN_SCOPE` | Design coherent; concurrency cap is a prompt-level instruction, not code-enforced; no run transcript available to confirm compliance. |
| G4 — enforced structural validity | `CONFLICTED` → fixed on this branch | See §5 below — two verified discrepancies between docs and `validate_research.py`, both corrected in this PR. |
| G5 — passive research → active follow-through | `EVALUABLE_WITH_HUMAN_JUDGMENT` | Mechanism well-specified; `research-context-agent.md` exists but is referenced by none of the mode flows in `SKILL.md`/`batch-mode.md` — unresolved scope question, not fixed on this branch (see §6). |
| G6 — end-to-end relay fidelity | `EVALUABLE_WITH_HUMAN_JUDGMENT` | Explicit do/don't relay rubric (`SKILL.md` L60–98); inherently qualitative, correctly left unautomated. Citation to `plugins/summarizer/skills/agent-result-relay/SKILL.md` not independently verified (out of bounded target). |

---

## 5. Confirmed Discrepancies — Fixed on This Branch

1. **`header_fields` severity mismatch.** `validation-rules.md`'s Check Definitions table listed `header_fields` under "Error Severity (must fix)", while the implementation (`validate_research.py`) and the same document's own Validation Gate section both treat it as **warning**-severity. **Fix**: moved `header_fields` to the Warning Severity list in `validation-rules.md`; no code change needed (code was already correct).
2. **`cross_references_absent` documented but not implemented.** `validation-rules.md`, `SKILL.md`, and `batch-mode.md` all described `cross_references_absent` as an existing warning-severity check with a 2026-03-12 date-based exemption — but `validate_research.py` had no such check. **Fix**: implemented `_check_cross_references` (plus `_reference_date_yaml`/`_reference_date_text` helpers and a `_flatten_yaml_items` helper) in `validate_research.py`, wired into both the YAML-frontmatter and text-header branches of `validate_file`. Covered by `tests/research_backlinks/test_cross_references_check.py`.

---

## 6. Open Items Not Addressed on This Branch

- `research-context-agent.md` exists in `.claude/agents/` but is unreferenced by any mode flow in this skill. Needs a maintainer decision: wire it into a mode + document it, or remove/relocate it as orphaned.
- G1's missing confidence/quote-grounding validator check, G3's unverified concurrency-cap compliance, and formal user approval of `SKILL-GOALS.md` itself remain open (see the original assessment's §5 candidate criteria and §7 decisions for detail).

**Target writes for the original assessment pass: NONE.** The fixes in §5 and this report file were written afterward, in a separate follow-up commit, per explicit user request.
