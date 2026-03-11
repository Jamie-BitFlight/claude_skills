# Plugin Assessment Scoring Criteria

## Description Quality (0–10)

| Score | Criteria |
|-------|----------|
| 9–10 | Action verbs, trigger phrases, clear scope, specific use cases |
| 7–8 | Clear purpose, some keywords, could use more triggers |
| 5–6 | Basic description, missing keywords or context |
| 3–4 | Vague, unclear when to use |
| 0–2 | Missing or single word |

## Reference Organization (0–100)

| Score | Criteria |
|-------|----------|
| 100 | All refs linked, bidirectional nav, no orphans, index if needed |
| 80 | All refs linked, minor nav gaps, no orphans |
| 60 | Some orphans exist but most content properly linked |
| 40 | Multiple orphans, navigation unclear |
| 20 | Many orphans, structure unclear |
| 0 | References exist but not integrated |

## Overall Plugin Score (0–100)

| Component | Weight | Criteria |
|-----------|--------|----------|
| Structural validity | 20% | Correct directory structure, all required files |
| Manifest completeness | 15% | Required fields present, recommended fields |
| Frontmatter correctness | 20% | Valid YAML, required fields, correct types |
| Description quality | 15% | Trigger keywords, clarity, actionability |
| Reference organization | 15% | No orphans, proper linking, navigation |
| Documentation quality | 10% | Examples, instructions, completeness |
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
