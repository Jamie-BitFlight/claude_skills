# Daily Releases Pipeline Map

Extracted from primary sources with file:line citations. No paraphrasing.

## Source Files Read

- `.claude/skills/daily-releases/SKILL.md` (lines 1–138)
- `.claude/skills/daily-releases/scripts/list_daily_ranges.py` (lines 1–256)
- `.claude/skills/daily-releases/scripts/publish_daily_release.py` (lines 1–206)
- `.claude/skills/create-merge-request-changelog/SKILL.md` (lines 1–547)
- `.claude/skills/create-merge-request-changelog/references/analysis_prompts.md` (lines 1–303)

---

## Pipeline Steps in Order

### Step 1: List days to process

**Trigger:** Manual invocation of `/daily-releases` skill. Arguments parsed from `$ARGUMENTS`.

**Script:**

```bash
uv run .claude/skills/daily-releases/scripts/list_daily_ranges.py \
  [--branch BRANCH] [--start-date ...] [--end-date ...] [-R OWNER/REPO]
```

**Source:** `SKILL.md` lines 29–31.

**Script reads:** Git repository commit history via GitPython (`repo.iter_commits(branch, no_merges=True)`). GitHub releases via PyGithub (`gh_repo.get_release(tag)`).

**Script writes:** JSON array to stdout only. No files written.

**Output schema** (`SKILL.md` lines 35–44):

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

**Skip logic** (`SKILL.md` line 47): "Skip entries where `release_exists: true` and `needs_update: false` — those are up to date."

**Dry-run behavior** (`SKILL.md` line 49): "For `--dry-run`, print the list and stop."

**Idempotency logic** (`list_daily_ranges.py` lines 176–190): `_check_day_release_status` checks tag existence, whether tag commit matches `newest_commit`, and whether `GENERATOR_VERSION` in the existing release body matches the current script constant (`GENERATOR_VERSION = "1.0"`, line 48). Returns `(release_exists, needs_update)`.

---

### Step 2: For each day that needs a release

**Ordering** (`SKILL.md` line 53): "Work through days chronologically."

---

#### Step 2a: Extract git data

**Script:**

```bash
uv run .claude/skills/create-merge-request-changelog/scripts/analyze_git_changes.py \
  <base_ref> <head_ref> ./daily-releases/<date>/
```

**Source:** `SKILL.md` lines 57–70.

**Script reads:** Git repository data between `base_ref` and `head_ref`.

**Script writes** to `./daily-releases/<date>/` (`SKILL.md` lines 62–70):

- `commits_oneline.txt` — one-line commit list
- `commits_detailed.txt` — full commit messages with metadata
- `changes.diff` — unified diff
- `changes_stat.txt` — diffstat summary
- `changed_files.txt` — file list with A/M/D status
- `changes_numstat.txt` — per-file line counts
- `summary.json` — machine-readable stats

**Note:** The script path is from `create-merge-request-changelog`, not `daily-releases`. See "How create-merge-request-changelog feeds in" section below.

---

#### Step 2b: AI analysis

**Verbatim quote of `SKILL.md` lines 72–95:**

```text
#### 2b. AI analysis

Read the extracted data and apply the primary analysis prompt from:

```text
.claude/skills/create-merge-request-changelog/references/analysis_prompts.md
```

Use the **Primary Analysis Prompt** section with the day's data substituted in:

- `{commit_details}` → contents of `commits_detailed.txt`
- `{changes_diff}` → contents of `changes.diff` (truncate to ~4000 chars if very large; use `changes_stat.txt` summary instead)
- `{changed_files}` → contents of `changed_files.txt`
- `{commit_count}`, `{files_changed}`, `{lines_added}`, `{lines_deleted}` → from `summary.json`

Produce the structured JSON analysis output defined in the prompt's `<output_format>` section.

Also generate a title using the **Title Generation Prompt**:

```text
Daily Release - <date>
```

Save the complete analysis JSON to `./daily-releases/<date>/analysis.json`.
```

**What this step does (not a script):** The AI model itself (the agent executing the skill) reads the five output files from Step 2a, applies the Primary Analysis Prompt from `analysis_prompts.md`, and writes the resulting structured JSON to `./daily-releases/<date>/analysis.json`.

**No script is called for Step 2b.** It is an inline AI inference step.

**Inputs consumed:**

| Variable | Source file |
|---|---|
| `{commit_details}` | `./daily-releases/<date>/commits_detailed.txt` |
| `{changes_diff}` | `./daily-releases/<date>/changes.diff` (truncated to ~4000 chars if large; fall back to `changes_stat.txt`) |
| `{changed_files}` | `./daily-releases/<date>/changed_files.txt` |
| `{commit_count}`, `{files_changed}`, `{lines_added}`, `{lines_deleted}` | `./daily-releases/<date>/summary.json` |

**Output written:** `./daily-releases/<date>/analysis.json`

**Prompt source:** Primary Analysis Prompt from `analysis_prompts.md` lines 6–181. Template variables: `{commit_details}`, `{changes_diff}`, `{changed_files}`, `{commit_count}`, `{files_changed}`, `{lines_added}`, `{lines_deleted}`.

**Output format** (`analysis_prompts.md` lines 79–169): Structured JSON with keys: `summary`, `change_categories` (containing `bug_fixes`, `enhancements`, `tech_debt`, `documentation`, `testing`, `build_ci`, `non_functional`), `components_affected`, `breaking_changes`, `statistics`.

**Title instruction** (`SKILL.md` line 89–93): "Also generate a title using the **Title Generation Prompt**: `Daily Release - <date>`". The Title Generation Prompt is at `analysis_prompts.md` lines 280–302. For daily releases the title is fixed as `Daily Release - <date>` rather than AI-generated from the analysis.

---

#### Step 2c: Format into release notes

**Script:**

```bash
uv run .claude/skills/create-merge-request-changelog/scripts/format_mr_description.py \
  ./daily-releases/<date>/analysis.json \
  --no-preview \
  --output ./daily-releases/<date>/description.md
```

**Source:** `SKILL.md` lines 99–104.

**Script reads:** `./daily-releases/<date>/analysis.json`

**Script writes:** `./daily-releases/<date>/description.md`

**Script also reads** (from `create-merge-request-changelog/SKILL.md` line 135): `references/output_template.md` — the MR description template structure.

---

#### Step 2d: Publish the release

**Script:**

```bash
uv run .claude/skills/daily-releases/scripts/publish_daily_release.py \
  --date <date> \
  --tag <tag> \
  --head-ref <head_ref> \
  --notes-file ./daily-releases/<date>/description.md
```

**Source:** `SKILL.md` lines 109–114.

**Optional flag** (`SKILL.md` line 116): "Add `--keep-existing-tag=false` if updating a release that already has the correct tag commit."

**Script reads:** `./daily-releases/<date>/description.md` (`publish_daily_release.py` line 150: `notes_file.read_text(encoding="utf-8")`)

**Script writes/creates:**

- Git tag (`<tag>`, e.g. `v2026.02.21`) at `head_ref` — pushed to `origin` (`publish_daily_release.py` lines 191–192)
- GitHub release via PyGithub API — title `Daily Release - <date>`, body = `description.md` content + `GENERATOR_MARKER` comment appended (`publish_daily_release.py` lines 150, 196–201)

**Tag collision handling** (`publish_daily_release.py` lines 169–188): If tag exists and `keep_existing_tag=True` and the existing commit differs from `head_ref`: deletes existing GitHub release, renames the local tag to `<tag>-r2` (or higher revision), pushes revision tag, deletes original tag from remote, then creates new tag at `head_ref`.

**Generator marker** (`publish_daily_release.py` lines 50–51): `GENERATOR_MARKER = f"<!-- created-by-release-generator: v{GENERATOR_VERSION} -->"` — appended to every release body. Used by `list_daily_ranges.py` to detect version-outdated releases during Step 1.

---

### Step 3: Report

**Source:** `SKILL.md` lines 120–127.

Output printed to terminal:

```text
Processed N days:
  - Created: X new releases
  - Updated: Y existing releases
  - Skipped: Z already up to date
```

No script. AI model prints this summary after the loop.

---

## How create-merge-request-changelog Feeds into daily-releases

**Relationship:** `daily-releases` borrows three artifacts from `create-merge-request-changelog` directly — it does not call it as a subskill, does not import it, and does not copy its files. The `daily-releases` SKILL.md references scripts and prompts by their repository-root paths.

**Three borrowed artifacts** (`SKILL.md` lines 131–135):

1. `../create-merge-request-changelog/scripts/analyze_git_changes.py` — used in Step 2a
2. `../create-merge-request-changelog/references/analysis_prompts.md` — consumed inline in Step 2b
3. `../create-merge-request-changelog/scripts/format_mr_description.py` — used in Step 2c

**Confirmation in `create-merge-request-changelog/SKILL.md` line 546:** "Use the `/daily-releases` skill to create AI-analyzed GitHub Releases for every day with commits. It uses this skill's `analyze_git_changes.py`, `analysis_prompts.md`, and `format_mr_description.py` as the rendering pipeline."

**Step 2b specifically is NOT a script call.** The AI agent reads `analysis_prompts.md` and applies the Primary Analysis Prompt itself — inline inference, not a subprocess.

---

## Where analysis.json is Consumed

`analysis.json` is written at the end of Step 2b by the AI model. It is consumed in Step 2c:

```bash
uv run .claude/skills/create-merge-request-changelog/scripts/format_mr_description.py \
  ./daily-releases/<date>/analysis.json \
  --no-preview \
  --output ./daily-releases/<date>/description.md
```

`format_mr_description.py` reads the JSON, applies templates from `references/output_template.md`, and writes `description.md`. The JSON is not consumed again after Step 2c.

---

## Complete File Graph

### Inputs to the pipeline

- Git repository commit history (GitPython, `repo.iter_commits`)
- GitHub releases API (PyGithub, `gh_repo.get_release`)
- `$GITHUB_TOKEN` environment variable
- `$ARGUMENTS` (parsed for `--start-date`, `--end-date`, `--branch`, `--dry-run`)
- `.claude/skills/create-merge-request-changelog/references/analysis_prompts.md` (Primary Analysis Prompt template, Title Generation Prompt)
- `.claude/skills/create-merge-request-changelog/references/output_template.md` (MR description template, read by `format_mr_description.py`)

### Per-day intermediate files (written then consumed within same day's loop iteration)

```text
./daily-releases/<date>/commits_oneline.txt       ← written by analyze_git_changes.py  (Step 2a)
./daily-releases/<date>/commits_detailed.txt      ← written by analyze_git_changes.py  (Step 2a)
                                                  ← read by AI in Step 2b ({commit_details})
./daily-releases/<date>/changes.diff              ← written by analyze_git_changes.py  (Step 2a)
                                                  ← read by AI in Step 2b ({changes_diff})
./daily-releases/<date>/changes_stat.txt          ← written by analyze_git_changes.py  (Step 2a)
                                                  ← read by AI in Step 2b (fallback for large diffs)
./daily-releases/<date>/changed_files.txt         ← written by analyze_git_changes.py  (Step 2a)
                                                  ← read by AI in Step 2b ({changed_files})
./daily-releases/<date>/changes_numstat.txt       ← written by analyze_git_changes.py  (Step 2a)
                                                  ← not explicitly consumed downstream (informational)
./daily-releases/<date>/summary.json              ← written by analyze_git_changes.py  (Step 2a)
                                                  ← read by AI in Step 2b ({commit_count}, {files_changed},
                                                     {lines_added}, {lines_deleted})
./daily-releases/<date>/analysis.json             ← written by AI model               (Step 2b)
                                                  ← read by format_mr_description.py   (Step 2c)
./daily-releases/<date>/description.md            ← written by format_mr_description.py (Step 2c)
                                                  ← read by publish_daily_release.py   (Step 2d)
```

### External outputs (persist after pipeline)

```text
Git tag <tag> at <head_ref>    ← created/moved by publish_daily_release.py (Step 2d), pushed to origin
GitHub release for <tag>       ← created/updated by publish_daily_release.py (Step 2d) via PyGithub API
```

### Script-to-file mapping

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | `list_daily_ranges.py` | git history, GitHub releases API | stdout (JSON array) |
| 2a | `analyze_git_changes.py` | git commits between `base_ref`..`head_ref` | 7 files in `./daily-releases/<date>/` |
| 2b | _(AI inline inference)_ | `commits_detailed.txt`, `changes.diff`, `changes_stat.txt`, `changed_files.txt`, `summary.json`, `analysis_prompts.md` | `./daily-releases/<date>/analysis.json` |
| 2c | `format_mr_description.py` | `analysis.json`, `output_template.md` | `./daily-releases/<date>/description.md` |
| 2d | `publish_daily_release.py` | `description.md` | git tag (remote), GitHub release |

---

## Script Ownership

| Script | Belongs to |
|---|---|
| `list_daily_ranges.py` | `daily-releases` skill |
| `publish_daily_release.py` | `daily-releases` skill |
| `analyze_git_changes.py` | `create-merge-request-changelog` skill |
| `format_mr_description.py` | `create-merge-request-changelog` skill |
| `analysis_prompts.md` | `create-merge-request-changelog` skill (references/) |
| `output_template.md` | `create-merge-request-changelog` skill (references/) |
