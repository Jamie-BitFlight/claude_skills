# Improvement Proposals: CodeWiki (Google)

**Research entry**: ./research/ai-research-tools/codewiki-google.md
**Generated**: 2026-03-18
**Patterns assessed**: 5
**Backlog items created**: 0
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: CI-triggered documentation drift detection

**Source pattern**: "CodeWiki scans the full repository, maintains links to every symbol, and regenerates diagrams that reflect the current state of the code" and "regeneration of documentation is a continuous process that effectively eliminates the problem of documentation drift" (Section: Key Features, subsection 1)
**Local system**: plugins/python3-development/agents/doc-drift-auditor.md
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: requires measurement of how often drift occurs outside feature cycles to confirm value

### Current state

The `doc-drift-auditor` agent runs exclusively as Phase 4 of `/complete-implementation` (file: plugins/python3-development/skills/complete-implementation/SKILL.md). It audits documentation accuracy against implementation only after all feature tasks reach COMPLETE status. Between feature completions, documentation drift can accumulate undetected -- for example, when direct hotfixes, dependency updates, or manual edits modify behavior without triggering the full SAM workflow.

### Target state

A CI workflow (GitHub Actions) or pre-commit hook invokes a lightweight documentation drift check on every push or PR that modifies implementation files. The check compares modified source files against their corresponding documentation sections and flags new drift items. This would not replace the full Phase 4 audit but would catch drift incrementally between feature cycles.

### Measurable signal

A GitHub Actions workflow file exists at `.github/workflows/doc-drift-check.yml` that runs on push/PR events touching `plugins/` or `src/` paths. The workflow exits non-zero when new drift is detected. Drift detection frequency moves from "per feature completion" to "per PR."

---

## Improvement 2: Auto-generated architecture diagrams from plugin/skill structure

**Source pattern**: "CodeWiki automatically generates always-current architecture, class, and sequence diagrams, ensuring you can visualize complex relationships that match the exact current state of the code" (Section: Key Features, subsection 3)
**Local system**: Mermaid diagrams in SKILL.md files and .claude/rules/local-workflow.md
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred -- confidence low: the research entry describes auto-generated diagrams from code analysis infrastructure that does not exist in this repo; implementing this would require a new code analysis pipeline, not an extension of existing Mermaid authoring

### Current state

Architecture and workflow diagrams in SKILL.md files and rule documents (e.g., `.claude/rules/local-workflow.md`) are manually authored Mermaid blocks. They accurately describe workflows when first written but can drift from implementation as skills and agents evolve. There is no mechanism to generate diagrams from the actual plugin/skill/agent file structure.

### Target state

A script or skill generates Mermaid diagrams from the plugin directory structure, skill frontmatter dependencies, and agent delegation chains. Generated diagrams are written to a known location and compared against manually authored diagrams to detect structural drift.

### Measurable signal

Running a command like `uv run scripts/generate_architecture_diagrams.py` produces Mermaid diagram files that reflect the current skill/agent/plugin structure. Diff between generated and manual diagrams is non-empty when structural drift exists.

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Documentation as Developer Experience (auto-generated docs) | Architecturally incompatible -- local system uses intentionally manual, AI-optimized SKILL.md authoring. Auto-generating from code would replace the authoring model, not extend it. |
| AI-Powered Code Understanding (always-current wiki as agent context) | Too abstract -- local system already provides per-task context gathering via `context-gathering` agent and Context Manifest in task files. The difference (persistent wiki vs per-task regeneration) is a design philosophy, not a concrete mechanism gap. |
| Hyperlinked Navigation Patterns (symbol-level linking) | Already partially covered -- CLAUDE.md File Reference Standards enforce markdown links with `./` paths, skill activation syntax provides cross-skill navigation, and `@research-cross-referencer` adds cross-references between research entries. Full symbol-level linking would require new code analysis infrastructure beyond extension of existing systems. |

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| CI-triggered documentation drift detection | Medium | The doc-drift-auditor exists and works in Phase 4 of /complete-implementation. Whether running it more frequently provides value depends on measuring how often drift occurs outside feature cycles. A time-boxed experiment tracking drift discovery timing would raise confidence. |
| Auto-generated architecture diagrams from plugin/skill structure | Low | The research entry describes diagrams generated by a full code analysis engine (CodeWiki's ingestion pipeline). The local system has no code analysis infrastructure -- only manually authored Mermaid. Implementing this would require a new pipeline, not an extension. Would need a feasibility spike to determine if lightweight generation from frontmatter metadata alone provides value. |
