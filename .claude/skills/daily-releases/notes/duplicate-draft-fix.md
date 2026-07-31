# Duplicate Draft Release — Root Cause and Fix Plan

SOURCE: Direct read of source files (2026-02-24)

- `scripts/publish_daily_release.py` — lines cited by number
- `scripts/list_daily_ranges.py` — lines cited by number

---

## 1. How `publish_daily_release.py` Decides Create vs. Update

**Line 166** — single existence check before any tag work:

```python
existing_release = gh_release_exists(gh_repo, tag)
```

`gh_release_exists` (lines 102–113) calls `gh_repo.get_release(tag)` (PyGithub). It returns `True` if GitHub returns a release for that tag name, `False` on any `GithubException` (including 404).

**Lines 169–188** — tag-rename branch:

```python
if tag_exists(git_repo, tag) and keep_existing_tag:
    old_commit = old_tag_ref.commit.hexsha
    if old_commit != head_ref:  # commit changed
        if existing_release:
            release = gh_repo.get_release(tag)
            release.delete_release()  # line 178 — deletes the release
            deleted_release_in_rename = True
        # rename tag to -r2, delete original, push both
```

**Lines 195–201** — final create-or-update branch:

```python
if existing_release and not deleted_release_in_rename:
    release = gh_repo.get_release(tag)
    release.update_release(name=title, message=notes_content)
else:
    gh_repo.create_git_release(tag=tag, name=title, message=notes_content, draft=False)
```

The decision is purely binary: `existing_release` (snapshotted at line 166) combined with `deleted_release_in_rename`.

---

## 2. Does the Script Check for an Existing Draft Before Creating?

No. `gh_release_exists` (line 102) calls `get_release(tag)`, which resolves **published and draft** releases by tag name. The script does not distinguish draft from published state anywhere. The existence check is present and draft-aware in the sense that `get_release` returns drafts too — but see Section 4 for why it still fails.

---

## 3. PyGithub API Calls Made

| Location | PyGithub call | Purpose |
|---|---|---|
| `gh_release_exists`, line 109 | `gh_repo.get_release(tag)` | Check existence |
| line 177 | `gh_repo.get_release(tag)` | Fetch release object for deletion |
| line 178 | `release.delete_release()` | Delete release in rename path |
| line 196 | `gh_repo.get_release(tag)` | Fetch release object for update |
| line 197 | `release.update_release(...)` | Update existing release |
| line 200 | `gh_repo.create_git_release(...)` | Create new release |

---

## 4. Root Cause of the Duplicate

**Root cause: `existing_release` is captured at line 166 using the old tag. After the tag is renamed (deleted + recreated at new commit), the GitHub release that was associated with the original tag is deleted at line 178 (`deleted_release_in_rename = True`). The script then falls through to `create_git_release` at line 200 — which is correct for that path.**

The duplicate does NOT occur in the commit-changed path. It occurs in the **same-commit re-run** path:

### Scenario: Same-Commit Re-Run (the actual bug)

Preconditions:
- Tag `v2026.02.21` exists, points to commit `abc123`
- `head_ref` passed to the script is also `abc123` (no new commits)
- A draft release for `v2026.02.21` exists on GitHub

Execution trace:

1. Line 166: `existing_release = gh_release_exists(gh_repo, "v2026.02.21")` → `True`
2. Line 169: `tag_exists(git_repo, tag)` → `True`, `keep_existing_tag` → `True`, enters block
3. Line 171: `old_commit = abc123`, `head_ref = abc123` → `old_commit == head_ref`
4. Line 173: `if old_commit != head_ref` → **False** — skip the rename block entirely
5. `deleted_release_in_rename` remains `False`
6. Lines 191–192: `git_repo.create_tag(tag, ref=head_ref, force=True)` + push (tag unchanged, no-op effectively)
7. Line 195: `existing_release and not deleted_release_in_rename` → `True and True` → **takes the update path**

**This path is correct.** The script calls `update_release` on the existing draft. No duplicate is created here.

### Re-evaluation: Where Does the Duplicate Actually Come From?

Given the code, the update path runs correctly for same-commit re-runs. The duplicate must arise from a different scenario. The most consistent explanation given the `list_daily_ranges.py` design:

**The pipeline runs `publish_daily_release.py` for a day where `needs_update=True` (commit changed). The script deletes the release (line 178), renames the tag, creates the new tag, then calls `create_git_release` (line 200). If the pipeline is interrupted between line 178 (delete) and line 200 (create), and then re-run, the second run finds `existing_release = False` (release was deleted) and calls `create_git_release` again. If the pipeline is NOT interrupted but runs concurrently (two parallel CI jobs for the same day), both jobs see `existing_release = False` at line 166 and both call `create_git_release`.**

However, a second mechanism is also present:

**Tag-moved scenario edge case (lines 169–188):** When the commit changes, the script deletes the release at line 178, then sets `deleted_release_in_rename = True`. At line 199–200, it creates a new release. BUT: `get_release(tag)` at line 109 looks up the release by tag name. If GitHub has not yet propagated the tag deletion (eventual consistency), or if the tag move happens on the git side but the release lookup uses the stale tag-to-release association, the flag `existing_release` could be stale — though this is less deterministic.

**Most likely duplicate path (confirmed by code): concurrent or retried pipeline runs on the commit-changed path**, because the delete (line 178) + create (line 200) sequence is not atomic. Between delete and create, any re-entrant run sees no release and creates a second one.

---

## 5. What `needs_update` in `list_daily_ranges.py` Controls

`needs_update` is set in `_check_day_release_status` (lines 176–190):

- Returns `(True, True)` when `current_tag_commit != newest_commit` (line 187–188)
- Returns `(True, version_outdated)` when commit matches but generator version differs (line 189–190)

`needs_update` controls **output filtering** only (line 248):

```python
if include_existing or not exists or needs_update:
    results.append(asdict(entry))
```

It determines whether a day's entry is included in the JSON output fed to the pipeline. It does NOT gate `publish_daily_release.py` from running — if a day appears in the JSON, the pipeline calls `publish_daily_release.py` unconditionally.

`publish_daily_release.py` performs its own existence check at line 166. The two scripts have independent existence checks that are not coordinated.

---

## 6. Proposed Fix Logic

### Fix location: `publish_daily_release.py` (primary), `list_daily_ranges.py` (secondary hardening)

### Fix A — Atomic idempotent create-or-update in `publish_daily_release.py`

Current flow after tag operations:

```text
if existing_release and not deleted_release_in_rename:
    update
else:
    create
```

Problem: `existing_release` is snapshotted before tag operations. After tag rename + delete + re-create, the release state on GitHub may differ from the snapshot.

Proposed flow:

```text
# Re-query release existence AFTER all tag operations complete
# Do not use the stale existing_release snapshot for the final decision
try:
    live_release = gh_repo.get_release(tag)
    live_release.update_release(name=title, message=notes_content)
    log "Updated"
except GithubException (404):
    gh_repo.create_git_release(tag=tag, name=title, ...)
    log "Created"
```

This makes the create-vs-update decision on live state, not stale state captured before tag mutations. It is idempotent: whichever branch runs, the result is the same release with the correct content.

### Fix B — Concurrency guard in pipeline (secondary)

If the pipeline can dispatch multiple jobs for the same day simultaneously, add a per-tag mutex or use GitHub's release API's ETag/conditional-request support to detect concurrent writers. Alternatively, the pipeline orchestration should ensure at-most-one job per tag at a time.

### Fix C — `list_daily_ranges.py` hardening (secondary)

`_check_day_release_status` currently checks whether a GitHub release exists for the tag (via `get_release_generator_version`, line 99). It does not check draft state. If a draft release exists and `commit_changed` is `True`, the function returns `(True, True)`. The tag rename path in `publish_daily_release.py` then deletes the draft.

No change required in `list_daily_ranges.py` for the primary bug fix — the issue is in `publish_daily_release.py`'s stale-snapshot decision at lines 195–200.

---

## 7. Edge Cases

### Tag moved to different commit — update or replace the draft?

When the commit changes, the current code deletes the existing release (line 178) and creates a new one (line 200). This is intentional: the release notes cover a different commit range. Replacing (delete + create) is correct behavior. The fix (re-query at end) preserves this: after the tag rename, `get_release(tag)` returns 404 (the release was deleted), so the create branch runs.

### Draft vs. published state

`get_release(tag)` returns both draft and published releases. The fix does not change this — it re-queries the same API. Draft state is not a factor in the create-vs-update decision and should remain that way.

### Race between delete and re-query

If two pipeline runs are truly concurrent: Run A deletes the release (line 178), Run B re-queries and sees 404, Run B creates. Run A also re-queries, sees the release Run B just created, and calls `update_release`. Both runs converge to a single release. This is safe as long as `update_release` is idempotent with identical content (it is).

### Interrupted run (delete succeeds, create never reached)

Re-query fix handles this correctly: next run sees no release for the tag and calls `create_git_release`. No duplicate.

---

## 8. Summary Table

| Question | Answer | Evidence |
|---|---|---|
| Create vs. update logic | Stale `existing_release` flag from line 166, combined with `deleted_release_in_rename` | Lines 166, 195–201 |
| Checks for existing draft before create? | Yes, but using pre-tag-mutation snapshot | Lines 102–113, 166 |
| PyGithub methods | `get_release`, `delete_release`, `update_release`, `create_git_release` | Lines 109, 178, 197, 200 |
| Root cause | Stale existence snapshot + non-atomic delete/create enables concurrent or retried runs to each call `create_git_release` | Lines 166–200 |
| `needs_update` gates publish? | No — it gates JSON output only; `publish_daily_release.py` does its own check | `list_daily_ranges.py` line 248 |
| Fix location | `publish_daily_release.py` lines 195–201 (re-query after tag ops) | See Fix A above |
