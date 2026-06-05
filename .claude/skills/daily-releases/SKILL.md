---
name: daily-releases
description: 'Create GitHub Releases with AI-analyzed changelogs for every calendar day with commits on origin/main. Use when creating daily release notes, backfilling releases, or generating AI-categorized changelogs per day. Uses collect → bucket → analyze → synthesize → publish pipeline via Haiku subagents. Idempotent — skips up-to-date days, updates releases where new commits were added. Accepts optional --start-date, --end-date, --branch, and --dry-run arguments.'
argument-hint: '[--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--branch BRANCH] [--dry-run]'
---

<release_args>$ARGUMENTS</release_args>

# Daily Releases

Create GitHub Releases with AI-categorized changelogs for every day that had commits. Uses the same pipeline as `/create-merge-request-changelog` — real AI analysis, not template substitution.

## Automatic Invocation

When this skill is activated, immediately begin processing without asking the user. Parse any arguments from `<release_args/>`:

```text
--start-date YYYY-MM-DD   Only process days on or after this date
--end-date YYYY-MM-DD     Only process days on or before this date (default: today)
--branch BRANCH           Git branch (default: origin/main)
--dry-run                 Preview without creating releases
```

## Process

Requires `GITHUB_TOKEN` for release status checks (list) and publishing.

**Working directory:** Run all commands from the repository root. Paths below assume cwd is the repo root.

### Step 1: List days to process

```bash
uv run .claude/skills/daily-releases/scripts/list_daily_ranges.py [--branch BRANCH] [--start-date ...] [--end-date ...] [-R OWNER/REPO]
```

This outputs a JSON array. Each entry has:

```json
{
  "date": "2026-02-21",
  "tag": "v2026.02.21",
  "base_ref": "<parent-commit-hash>",
  "head_ref": "<last-commit-hash-of-day>",
  "commit_count": 12,
  "release_exists": true,
  "needs_update": false
}
```

Skip entries where `release_exists: true` and `needs_update: false` — those are up to date.

For `--dry-run`, print the list and stop.

### Step 2: For each day that needs a release

Work through days chronologically. For each day, the pipeline collects data,
buckets it by token budget, analyses each bucket with a Haiku subagent, synthesises
the results, then formats and publishes. Days with few commits pass through a single
bucket with no synthesis overhead.

#### 2a. Collect dataset

```bash
uv run .claude/skills/daily-releases/scripts/collect_day_dataset.py \
  <base_ref> <head_ref> ./daily-releases/<date>/ [-R OWNER/REPO]
```

Writes `./daily-releases/<date>/dataset/`:

- `files.json` — changed source files with status and line counts
- `commits.json` — commits with SHA, message, files touched
- `issues.json` — GitHub issues/PRs referenced or closed (empty if no token)
- `diffs/<sanitized_path>.diff` — per-file unified diff for each source file

Source files: `*.py .js .cjs .mjs .ts .tsx .sh .md .json .yaml .yml`
Excluded: `dist/ build/ node_modules/ vendor/ .venv/` and similar build outputs.

#### 2b. Create token-bounded buckets

```bash
uv run .claude/skills/daily-releases/scripts/bucket_day_data.py \
  ./daily-releases/<date>/ [--token-limit 100000]
```

Token limit defaults to env var `DAILY_RELEASES_TOKEN_LIMIT` or `100000`.

Groups source files by directory module, fills buckets greedily keeping each
under the token limit (measured with tiktoken cl100k_base as a proxy).

Writes `./daily-releases/<date>/buckets/bucket_NNN/`:

- `manifest.json` — `{bucket_id, files, token_count, commit_shas}`
- `content.txt` — file diffs followed by commit messages for this bucket

Prints a summary listing bucket count and token sizes.

#### 2c. Analyse each bucket (delegate — do NOT read bucket files yourself)

For each `bucket_NNN/` directory found under `./daily-releases/<date>/buckets/`:

```python
Agent(
  subagent_type="general-purpose",
  model="claude-haiku-4-5-20251001",
  prompt="""
Read: ./daily-releases/<date>/buckets/bucket_NNN/content.txt

Apply the Per-Bucket Analysis Prompt from:
  .claude/skills/daily-releases/references/synthesis_prompt.md

Write the structured JSON output to:
  ./daily-releases/<date>/summaries/bucket_NNN.json

Report "bucket_NNN.json written" when done.
"""
)
```

Replace `<date>` and `NNN` with actual values before emitting each Agent() call.
Buckets may be processed in parallel — each writes to its own summary file.

After all agents return, verify each `summaries/bucket_NNN.json` exists. Stop with
an error if any is missing.

#### 2d. Synthesise summaries into analysis.json

**If exactly one bucket exists:** promote its JSON directly — copy
`summaries/bucket_001.json` to `analysis.json`, adding a `statistics` block from
`dataset/files.json` counts (commit_count, files_changed, lines_added,
lines_deleted). No synthesis agent needed.

**If two or more buckets exist:**

```python
Agent(
  subagent_type="general-purpose",
  model="claude-haiku-4-5-20251001",
  prompt="""
Apply the Day Synthesis Prompt from:
  .claude/skills/daily-releases/references/synthesis_prompt.md

Read all bucket summary files:
  ./daily-releases/<date>/summaries/bucket_001.json
  ./daily-releases/<date>/summaries/bucket_002.json
  ... (list all that exist)

Also read ./daily-releases/<date>/dataset/files.json for statistics counts.

Write the merged analysis JSON to: ./daily-releases/<date>/analysis.json

Report "analysis.json written" when done.
"""
)
```

After the agent returns, verify `./daily-releases/<date>/analysis.json` exists.
Stop with an error if missing.

#### 2e. Format into release notes

```bash
uv run .claude/skills/create-merge-request-changelog/scripts/format_mr_description.py \
  ./daily-releases/<date>/analysis.json \
  --no-preview \
  --output ./daily-releases/<date>/description.md
```

#### 2f. Publish the release

```bash
uv run .claude/skills/daily-releases/scripts/publish_daily_release.py \
  --date <date> \
  --tag <tag> \
  --head-ref <head_ref> \
  --notes-file ./daily-releases/<date>/description.md
```

Add `--keep-existing-tag=false` if updating a release that already has the correct
tag commit.

### Step 3: Report

After processing all days, print a summary:

```text
Processed N days:
  - Created: X new releases
  - Updated: Y existing releases
  - Skipped: Z already up to date
```

## Reference files

- [./scripts/list_daily_ranges.py](./scripts/list_daily_ranges.py) — list days + commit ranges
- [./scripts/collect_day_dataset.py](./scripts/collect_day_dataset.py) — per-file diff + commit + issues extraction into `dataset/`
- [./scripts/bucket_day_data.py](./scripts/bucket_day_data.py) — token-bounded semantic bucketing into `buckets/`
- [./scripts/publish_daily_release.py](./scripts/publish_daily_release.py) — create/update git tag + GitHub release
- [./references/synthesis_prompt.md](./references/synthesis_prompt.md) — per-bucket analysis prompt + day synthesis prompt
- [../create-merge-request-changelog/scripts/format_mr_description.py](../create-merge-request-changelog/scripts/format_mr_description.py) — render analysis.json to markdown

Reference paths above are relative to this skill directory; CLI commands use repo-root paths.
