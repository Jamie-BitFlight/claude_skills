# Synthesis Prompt — Merge Bucket Summaries into analysis.json

Use this prompt when all per-bucket Haiku analyses are complete and must be merged
into a single `analysis.json` for the day.

---

## Per-Bucket Analysis Prompt

Use this prompt for each bucket's Haiku subagent. The subagent reads
`buckets/bucket_NNN/content.txt` and produces `summaries/bucket_NNN.json`.

```text
You are analyzing a subset of a day's git changes to produce a structured
changelog entry. This is ONE BUCKET of a larger day — focus only on the
changes in the files provided.

Read the content below (file diffs followed by commit messages):

<content>
{bucket_content}
</content>

For each changed file and its associated commits:

1. Understand the intent from commit messages and diff patterns
2. Categorize each change (bug_fix, enhancement, tech_debt, documentation,
   testing, build_ci, non_functional)
3. Identify affected components (top-level directory or module name)
4. Flag any breaking changes

Return structured JSON matching this schema exactly:

{
  "bucket_summary": "1-2 sentences describing what this group of changes does",
  "change_categories": {
    "bug_fixes": [
      {
        "title": "Clear description of bug fixed",
        "description": "What was broken and how it is now fixed",
        "files_affected": ["path/to/file.py"],
        "commits": ["abc123f"],
        "impact": "Who/what this affects"
      }
    ],
    "enhancements": [
      {
        "title": "Feature added or capability improved",
        "description": "What new functionality was added",
        "benefits": "Value provided",
        "files_affected": ["path/to/file.py"],
        "commits": ["abc123f"]
      }
    ],
    "tech_debt": [
      {
        "title": "Internal improvement made",
        "description": "What was refactored or simplified",
        "files_affected": ["path/to/file.py"],
        "commits": ["abc123f"]
      }
    ],
    "documentation": [
      {
        "title": "Documentation updated",
        "files_affected": ["path/to/file.md"],
        "commits": ["abc123f"]
      }
    ],
    "testing": [
      {
        "title": "Tests added or improved",
        "files_affected": ["tests/test_foo.py"],
        "commits": ["abc123f"]
      }
    ],
    "build_ci": [
      {
        "title": "Build/CI change",
        "files_affected": [".github/workflows/ci.yml"],
        "commits": ["abc123f"]
      }
    ],
    "non_functional": [
      {
        "title": "Formatting, config, or minor cleanup",
        "files_affected": ["path/to/file.py"],
        "commits": ["abc123f"]
      }
    ]
  },
  "components_affected": ["auth", "cli", "scripts"],
  "breaking_changes": []
}

Omit any category array that has no entries. Output only the JSON, no prose.
```

---

## Day Synthesis Prompt

Use this prompt for the synthesis subagent after all bucket summaries are written.
The subagent reads all `summaries/bucket_NNN.json` files and writes `analysis.json`.

```text
You are synthesizing per-bucket changelog summaries into a single day's release
description. Each bucket covered a different set of files; together they cover
the entire day.

Read all bucket summary files listed below (they follow the bucket analysis JSON
schema). Then produce a single merged analysis.json.

Bucket summaries to merge:
{bucket_summary_list}

Merge rules:
1. Combine all arrays in each category (bug_fixes, enhancements, tech_debt, etc.)
2. Deduplicate entries that reference the same commit SHA — keep the most
   descriptive version, merge their files_affected lists
3. Deduplicate components_affected (union, sorted)
4. Deduplicate breaking_changes by description similarity
5. Write a unified summary (2-3 sentences) covering the full day's work across
   all buckets — do NOT just concatenate the bucket_summary strings

Output the merged JSON using this schema:

{
  "summary": "2-3 sentence overview of the entire day's changes",
  "change_categories": {
    "bug_fixes": [...],
    "enhancements": [...],
    "tech_debt": [...],
    "documentation": [...],
    "testing": [...],
    "build_ci": [...],
    "non_functional": [...]
  },
  "components_affected": ["sorted", "unique", "list"],
  "breaking_changes": [],
  "statistics": {
    "commit_count": 0,
    "files_changed": 0,
    "lines_added": 0,
    "lines_deleted": 0
  }
}

Fill statistics from summary.json in the day directory if available; otherwise
omit the statistics block.

Output only the JSON, no prose.
```

---

## Notes

- Bucket summary files follow the per-bucket schema above; `analysis.json` follows
  the full day schema (same as used by `format_mr_description.py`).
- The synthesis agent receives only structured JSON (small payloads) — not raw
  diffs. This keeps synthesis context-safe regardless of how many buckets exist.
- If only one bucket exists for the day, its `change_categories` can be promoted
  directly into `analysis.json` without a synthesis agent call — just add the
  `statistics` block.
