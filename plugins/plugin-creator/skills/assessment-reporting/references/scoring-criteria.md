# Plugin Assessment Scoring Criteria

## Description Quality (0–10)

| Score | Criteria |
|-------|----------|
| 9–10 | Action verbs, trigger phrases, clear scope, specific use cases |
| 7–8 | Clear purpose, some keywords, could use more triggers |
| 5–6 | Basic description, missing keywords or context |
| 3–4 | Vague, unclear when to use |
| 0–2 | Missing or single word |

Normalization for overall scoring: convert Description Quality to a 0–100 component by multiplying the 0–10 raw score by 10 before applying the 15% overall weight in the Overall Plugin Score calculation.

## Reference Organization (0–100)

| Score | Criteria |
|-------|----------|
| 100 | All refs linked, bidirectional nav, no orphans, index if needed |
| 80 | All refs linked, minor nav gaps, no orphans |
| 60 | Some orphans exist but most content properly linked |
| 40 | Multiple orphans, navigation unclear |
| 20 | Many orphans, structure unclear |
| 0 | References exist but not integrated |

## Documentation Quality (0–100)

Start from 100 and deduct for citation findings:

All deduction values below are positive magnitudes that are subtracted from 100 via `100 - total_deductions`.

| Finding type | Deduction magnitude (each) | Max deduction magnitude (cap) |
|--------------|----------------------------|-------------------------------|
| Persistent broken citation (`SOURCE:` URL returns 404/410 after retry policy) | 20 | 60 |
| Unreachable citation (timeout, DNS, 5xx, 401/403/429) | 10 | 30 |
| Drift suspected (URL reachable but claim phrase absent) | 15 | 45 |

Rules:
- Apply deductions only when `SOURCE:` citations exist.
- Reachable citation with phrase present has no deduction.
- Apply the assessor retry policy before classifying a citation as persistently broken.
- Reachable citation with insufficient claim context (no sentence available; link title fallback used) has no deduction and should be reported in the Citation Drift section notes/findings as informational manual-review context.
- Apply each cap per finding type independently, then sum all deduction magnitudes (total deductions may exceed 100).
- Final score formula: `max(0, 100 - total_deductions)` where `total_deductions` is the summed deduction magnitude.
- Use this 0–100 result as the Documentation Quality component score before weighting it at 10% in the overall plugin score.

## Overall Plugin Score (0–100)

| Component | Weight | Criteria |
|-----------|--------|----------|
| Structural validity | 20% | Correct directory structure, all required files |
| Manifest completeness | 15% | Required fields present, recommended fields |
| Frontmatter correctness | 20% | Valid YAML, required fields, correct types |
| Description quality | 15% | Trigger keywords, clarity, actionability |
| Reference organization | 15% | No orphans, proper linking, navigation |
| Documentation quality | 10% | Citation reliability and evidence support quality |
| Enhancement potential | 5% | Growth opportunities identified |

## Orphan Classification

| Classification | Criteria | Recommendation |
|----------------|----------|----------------|
| Linked | Referenced from SKILL.md | Verify link works |
| Orphaned — New Content | Not linked, unique information | Add link to SKILL.md or create index |
| Orphaned — Duplicate | Not linked, duplicates SKILL.md | Merge into main file or delete |
| Orphaned — Notes | Not linked, appears to be drafts | Move or delete |
| Orphaned — Examples | Not linked, contains examples/templates | Link from appropriate section |
| Index File | Named index.md, links to other files | Verify all links, link from SKILL.md |
