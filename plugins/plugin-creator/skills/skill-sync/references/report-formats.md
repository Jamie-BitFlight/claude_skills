# Report Formats

Each Stage 2 read agent writes its report to `.tmp/scratch/reports/` before returning.

## Agent 1: skill-auditor — Completeness Report

Output file: `.tmp/scratch/reports/skill-sync-{slug}-completeness-YYYYMMDD.md`

```text
# Skill Audit: {skill-name}
# Agent: skill-auditor
# Date: YYYYMMDD
# Skill path: {path}

## skilllint Status

Exit code: {0 | non-zero}
SK006/SK007: UNDER | AT | OVER — Body tokens: {N}
Findings: {list of SK006/SK007 violations, or "none"}

## Completeness Score: X/24 (Y%)

| Category | Score | Label | Key Findings |
|----------|-------|-------|--------------|
| Preparation | N | {label} | ... |
| Progression | N | {label} | ... |
| Verification | N | {label} | ... |
| Scripts | N | {label} | ... |
| Examples | N | {label} | ... |
| Anti-Patterns | N | {label} | ... |
| References | N | {label} | ... |
| Assets | N | {label} | ... |

## Progressive-Disclosure Structure

COMPLIANT | VIOLATION: {describe the over-budget section and token count}

## Completeness Gaps

- {gap description} — Category: {category}, Priority: HIGH | MEDIUM | LOW

## Recommendations

1. {High priority recommendation}
2. {Medium priority recommendation}
```

## Agent 2: skill-content-updater — Upstream Drift Report

Output file: `.tmp/scratch/reports/skill-sync-{slug}-drift-YYYYMMDD.md`

```text
# Upstream Drift Report: {skill-name}
# Agent: skill-content-updater (read role)
# Date: YYYY-MM-DD

## Claims Assessed

### {claim text or section name}
- Verdict: NEW | STALE | VERIFIED | UNVERIFIABLE
- Source URL: {url}
- HTTP status: {200 | 301 | 404 | timeout | dns-failure}
- Current text: "{quoted current text in skill}"
- Upstream text: "{quoted upstream text}"  # omit when UNVERIFIABLE
- Recommendation: REPLACE | ADD | PRESERVE
```

## Agent 3: general-purpose — Structure Report

Output file: `.tmp/scratch/reports/skill-sync-{slug}-structure-YYYYMMDD.md`

```text
# Structure Report: {skill-name}
# Agent: general-purpose
# Date: YYYY-MM-DD

## Frontmatter
- name: VALID | INVALID — {reason}
- description: VALID | INVALID — {reason}
- Other fields: {assessment}

## Progressive Disclosure
- Body token estimate: {N} tokens
- SK006 status: UNDER | AT | OVER
- Sections over-budget: {list or none}

## Reference Links
- {link text} -> {path}: EXISTS | BROKEN

## Findings
{list of structural issues to fix, one per line, or "None"}
```

## Verdict Taxonomy

| Verdict | Meaning | Stage 3 action |
|---|---|---|
| `NEW` | Upstream has relevant claim not in skill | Add with SOURCE: citation |
| `STALE` | Skill text diverges from current upstream | Replace with upstream text |
| `VERIFIED` | Skill text matches upstream | Preserve; update access date |
| `UNVERIFIABLE` | Non-200 response or DNS failure | Preserve current text |
