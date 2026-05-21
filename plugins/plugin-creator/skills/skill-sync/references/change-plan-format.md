# Change Plan Format

## Schema

A change plan is a markdown file at `.tmp/scratch/plans/skill-sync-{slug}-YYYYMMDD.md`.

```text
# Change Plan: {skill-name}
# Generated: YYYY-MM-DD
# Skill path: {path to SKILL.md}

## Summary
One sentence describing the overall change intent.
If no changes are needed: "No changes needed — all claims verified, structure valid."

## Changes

### {section-name or frontmatter.field}
- Action: REPLACE | ADD | REMOVE | MOVE_TO_REFERENCES
- Source: {completeness | upstream-drift | structure}
- Current: "{quoted current text or (none)}"
- New: "{proposed replacement text or reference link}"
- Rationale: {one sentence}
- Citation: SOURCE: {URL} (accessed YYYY-MM-DD)

## References Extractions
List sections to extract to references/ (required when addition pushes past SK006):

- Section "{section-name}" -> references/{filename}.md
```

Only include `## References Extractions` when at least one extraction is needed.

## Synthesis Precedence Rules

Apply in this order when reports conflict:

1. **Structural fixes first** — address broken links, frontmatter schema violations, and progressive disclosure before content changes
2. **STALE overrides existing** — a STALE upstream verdict replaces the current text without merging
3. **NEW requires citation** — only include a NEW upstream claim when the drift report contains a SOURCE: URL and access date
4. **SK006 pairs with extraction** — any addition pushing the body past SK006 must include a `## References Extractions` entry for the affected section
5. **UNVERIFIABLE = preserve** — claims with non-200 or DNS-failure verdicts are left unchanged

## No-Change Exit

If all upstream verdicts are VERIFIED and the structure report has no findings: write a change plan containing only:

```text
# Change Plan: {skill-name}
# Generated: YYYY-MM-DD
# Skill path: {path}

## Summary
No changes needed — all claims verified, structure valid.
```

Stages 4–6 are skipped when the change plan has no `## Changes` section.
