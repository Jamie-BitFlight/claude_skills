# Utilization Proposals: Jakub Krehel Interface Skills Collection

**Research entry**: ./research/developer-tools/jakubkrehel-skills.md
**Generated**: 2026-10-02
**Integration surfaces found**: 3 (npm CLI | Claude Code plugin | skill orchestration pattern)
**Proposals written**: 2
**Skipped**: 2 — different domain scope (CLI UI design), pattern already adopted (orchestration model)

---

## Utilization 1: dh:code-review-web → jakubkrehel interface design perspectives

**Research entry**: ./research/developer-tools/jakubkrehel-skills.md
**Caller**: /home/user/claude_skills/plugins/development-harness/skills/code-review-web/SKILL.md
**Integration mechanism**: Extend multi-perspective-review verdict schema with design reviewer tasks
**Replaces or adds**: Adds visual/design-level review perspectives (layout, typography, colors, UI polish) to complement existing code-correctness review
**Setup cost**: Medium (extend verdict schema + add new reviewer tasks + integrate jakubkrehel skills as external dependency)
**Integration surface**: npm CLI `npx skills add jakubkrehel/skills` to install domain skills; skill invocation via `/interfaces:better-interface`, `/interfaces:better-layout`, `/interfaces:better-typography`, `/interfaces:better-colors`, `/interfaces:better-ui`

### Why this caller

code-review-web (lines 1-10) currently reviews web code at the code level: accessibility WCAG compliance, XSS prevention, performance metrics (layout thrash, CLS, lazy loading), and CSS semantics. It enforces correctness rules within a codebase. However, the resulting code may be correct but visually/experientially flawed — a button may be accessible per WCAG but poorly styled, typography may be valid CSS but breaking the product's type system, color choices may meet contrast ratios but violate the palette structure.

The jakubkrehel skills address this gap: `better-interface` combines domain skills (layout, typography, colors, UI polish) that review the rendered interface result, not just the code. The research entry's Section "Multi-Domain Review Orchestration" (lines 39-44) consolidates evidence across domains and ranks by user impact with shared severity definitions, a pattern the dh multi-perspective-review skill already implements (dh:review-verdict-contract, Section §2.1, schema_version 1.0).

### Integration sketch

Extend multi-perspective-review (Section "Step 3: Create the Ephemeral Review Plan") to optionally include UI design reviewer tasks alongside existing Security/Performance/Quality/Accessibility perspectives. Each additional task dispatches to a corresponding jakubkrehel skill:

```yaml
# Example: extended 5-perspective review plan
Review Plan (7 tasks):
  Task 1: Security reviewer          → dh:review-security-change (current)
  Task 2: Performance reviewer       → dh:review-performance-change (current)
  Task 3: Quality reviewer           → dh:review-quality-change (current)
  Task 4: Accessibility reviewer     → dh:review-accessibility-change (current)
  Task 5: Layout & Spacing reviewer  → /interfaces:better-layout (new)
  Task 6: Typography reviewer        → /interfaces:better-typography (new)
  Task 7: Color & Palette reviewer   → /interfaces:better-colors (new)
  Task 8: UI Polish reviewer         → /interfaces:better-ui (new)
  [Synthesizer collects all verdicts into one punch list]
```

Each task produces a verdict struct (dh:review-verdict-contract §2.1); synthesizer deduplicates and ranks findings by severity and user impact using jakubkrehel's escalation triggers (research entry, Section "Multi-Domain Review Orchestration", lines 42-43).

**Precondition**: Multi-perspective-review must be invoked with a `--ui-review` flag to activate design reviewers; default remains 4-perspective (current behavior).

**Data flow**: Changed files list from Step 1 (lines 31-47) is already collected and passed to each reviewer task — no new data gathering needed. Each design reviewer reads the changed CSS/component files and the rendered interface (via URL or screenshot in the plan body) and produces a verdict using the jakubkrehel skill's review methodology.

---

## Utilization 2: dh:multi-perspective-review → jakubkrehel better-interface orchestration pattern

**Research entry**: ./research/developer-tools/jakubkrehel-skills.md
**Caller**: /home/user/claude_skills/plugins/development-harness/skills/multi-perspective-review/SKILL.md
**Integration mechanism**: Model multi-perspective-review's reviewer dispatch and verdict consolidation on jakubkrehel's better-interface multi-domain skill routing
**Replaces or adds**: Reinforces existing pattern; documents a reference implementation of multi-domain orchestration with escalation triggers and evidence-first finding ranking
**Setup cost**: Low (documentation + optional: adopt jakubkrehel escalation trigger model into verdict schema)
**Integration surface**: Research entry pattern documentation, specifically Sections "Multi-Domain Review Orchestration" (lines 39-44) and "Key Features: Multi-Domain Review Orchestration" (lines 39-44); escalation trigger list (lines 42-43); shared severity scale (lines 44)

### Why this caller

multi-perspective-review (SKILL.md, Section "Role", lines 10-16) dispatches four parallel reviewers (Security, Performance, Quality, Accessibility) as independent SAM tasks, collects structured verdicts in parallel, and synthesizes them into one deduplicated punch list with a shared severity model.

The jakubkrehel `better-interface` skill (research entry, Section "Key Features: Multi-Domain Review Orchestration", lines 39-44) implements an analogous pattern for UI domains: it "combines all domain skills in order: accessibility → layout → writing → typography → colors → UI polish," consolidates findings across domains, and "ranks by user impact" with a shared severity scale (lines 44: "BLOCKER | MEDIUM | LOW"). Both systems apply the same architectural pattern — many parallel specialized reviewers whose findings are consolidated and ranked by a shared signal.

The research entry's "Escalation triggers" (lines 42-43) define specific rules that immediately rank findings as HIGH severity regardless of which domain found them. This pattern could enhance the dh verdict contract's finding-ranking logic. Currently, dh:review-verdict-contract defines severity per perspective (security/performance/quality/accessibility); jakubkrehel's cross-domain escalation triggers (e.g., "interactive control with no accessible name" ranks HIGH immediately) offer a way to identify system-level failures that require priority regardless of the domain that discovered them.

### Integration sketch

No code change required; this is a reference-pattern reinforcement. However, optionally:

1. **Document the pattern mapping** in dh:multi-perspective-review's "Related Patterns" section:
   - dh:multi-perspective-review :: parallel dispatching + verdict consolidation + shared severity
   - jakubkrehel:better-interface :: multi-domain skill routing + finding consolidation + user-impact ranking
   - Commonality: both use the "many specialized reviewers, one synthesis gate" architecture

2. **Optional enhancement**: Adopt jakubkrehel's escalation trigger model into dh:review-verdict-contract. Add a new field to the verdict schema (Section §2.1):

```json
{
  "schema_version": "1.0",
  "perspective": "...",
  "verdict": "...",
  "findings": [...],
  "escalation_triggers_matched": ["interactive_control_no_name", "keyboard_unreachable"]  // NEW
}
```

The synthesizer then applies cross-domain escalation rules (any finding matching a global escalation trigger immediately ranks HIGH, regardless of the per-perspective severity it was assigned).

---

## Skipped Systems

| Local System | Reason skipped |
|---|---|
| `/home/user/claude_skills/plugins/python-engineering/skills/designing-ui-for-cli/SKILL.md` | Different domain scope. designing-ui-for-cli addresses CLI/TUI output design (Typer, Rich, Textual, Questionary) on a 7-stage discipline grounded in PRODUCT.md and DESIGN.md. jakubkrehel-skills addresses web interface design (accessibility, layout, typography, colors, visual polish). No integration surface overlap; both are UI-focused but serve non-overlapping channels. |
| `/home/user/claude_skills/plugins/development-harness/skills/review-verdict-contract/SKILL.md` | Pattern already adopted. review-verdict-contract already implements the structured verdict schema and consolidation model that jakubkrehel's better-interface uses. No callable integration surface; this skill documents a schema, not a tool to call. Extending the schema (Utilization 2) is a choice, not a requirement. |

---

## Integration Priority

| Proposal | Priority | Reasoning |
|---|---|---|
| Utilization 1 (code-review-web extension) | Medium-High | Closes gap in web code review where correctness is enforced but visual/design quality is not. Benefits: addresses design-level failures that code review alone misses (visual contrast, typography system violations, layout breaks). Cost: requires installing jakubkrehel skills as external dependency and extending multi-perspective-review dispatcher. Blocker: only relevant when reviewing web/UI code changes. |
| Utilization 2 (multi-perspective-review reference pattern) | Low-Medium | Reinforces existing architecture; no code change required. Optional enhancement (escalation triggers) could improve finding prioritization across domains. Benefit: documents reference implementation of multi-domain orchestration. Cost: minimal (documentation). |

