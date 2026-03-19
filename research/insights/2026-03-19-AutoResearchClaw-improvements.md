# Improvement Proposals: AutoResearchClaw

**Research entry**: ./research/agent-frameworks/AutoResearchClaw.md
**Generated**: 2026-03-19
**Patterns assessed**: 7
**Backlog items created**: 1 (issues: #845)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 4

---

## Improvement 1: Add automated citation verification to research-curator validate mode

**Source pattern**: "4-Layer Citation Verification: (1) arXiv ID validation -> (2) CrossRef/DataCite DOI lookup -> (3) Semantic Scholar title matching -> (4) LLM relevance scoring; hallucinated references are auto-removed" (Section: Citation Integrity & Literature Management)
**Local system**: `.claude/skills/research-curator/SKILL.md` (validate mode), `.claude/skills/research-curator/scripts/validate_research.py`
**Confidence**: High
**Impact**: Medium
**Backlog**: #845 created

### Current state

The research-curator `--validate` mode checks structural issues (missing required fields, broken links, malformed frontmatter) via `validate_research.py`. It does not verify that cited sources actually exist or are relevant. Citations in research entries (URLs, arXiv IDs, DOI references) are taken at face value. The CLAUDE.md citation requirements (section "Citation Requirements") mandate cited sources for every factual claim, but no automated tool enforces citation validity -- only structure is checked.

### Target state

The `--validate` mode includes a citation verification layer that checks: (1) URL reachability (HTTP HEAD request, report non-2xx status), (2) arXiv ID format validation and optional API lookup, (3) DOI resolution via CrossRef/DataCite API. Hallucinated or dead references are flagged as warning-severity issues in the validator JSON output. A new `--verify-citations` flag enables this layer (off by default to avoid network dependency in CI).

### Measurable signal

Run `uv run .claude/skills/research-curator/scripts/validate_research.py --json --verify-citations ./research/agent-frameworks/AutoResearchClaw.md` -- output includes a `citation_verification` section with per-URL status (reachable/unreachable/invalid-format). At least one research entry with a fabricated URL produces a warning-severity finding.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Formal stage transition events and state machine for SAM pipeline | Medium | The local system implements multi-stage orchestration via skill chaining (`/add-new-feature` -> `/implement-feature` -> `/complete-implementation`) and hook events (`SubagentStop`, `PostToolUse`). AutoResearchClaw uses a 23-stage state machine with explicit `StageStatus` and `TransitionEvent` enums and rollback transitions. The local `sam_schema` package has a `TaskStatus` enum but may already encode equivalent transitions -- a deeper read of `sam_schema/core/models.py` would be needed to confirm the gap is real vs. already covered at a different abstraction level. |
| AI-facing agent manifest for external AI bootstrap | Medium | AutoResearchClaw uses `RESEARCHCLAW_AGENTS.md` as a manifest that external AIs (via OpenClaw) can read to understand and invoke the system. The local repo has `plugin.json` and `marketplace.json` for plugin discovery, but no equivalent "here is how an external AI assistant should invoke this system" document. The gap requires interpretation -- `marketplace.json` may already serve this purpose for Claude Code's marketplace consumption model, making the pattern architecturally redundant. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Self-Healing Experiments (NaN/Inf detection, targeted LLM repair, iterative refinement up to 10 rounds) | Already tracked in backlog as #449 (Retry with exponential backoff for BLOCKED tasks), #448 (Stall detection for subagent tasks), #87 (SAM: Timeout/Stall Detection), #85 (SAM: Error Recovery / Rollback Procedures) |
| Hardware Awareness (GPU/MPS/CPU auto-detection and code generation adaptation) | Incompatible with repo architecture -- this is a Claude Code plugin/skills repository, not an experiment execution environment. Hardware-aware code generation is outside the repo's domain. |
| Quality Gates with automatic rollback on rejection | Already tracked in backlog as #85 (SAM: Error Recovery / Rollback Procedures). The local system has 6-phase quality gates in `/complete-implementation` that block on failure but lack rollback -- this specific gap is within scope of the existing backlog item. |
| Self-Learning from Failures (MetaClaw cross-run knowledge transfer with 30-day time-decay) | Already tracked in backlog as #775 (Persistent structured session metadata for cross-session context recovery) and #317 (Structured session work logs with pre-compact and session-start hooks). The cross-session learning gap is covered by these two items. |
