---
name: project-manifest-sync-ci-staged-diff-noop
description: manifest-sync CI job ran a staged-git-diff detector on a plain checkout, so it always passed trivially — root cause of issue #3021, fixed via check_plugin_version_bump.py
metadata:
  type: project
---

`plugins/plugin-creator/scripts/auto_sync_manifests.py`'s default (pre-commit-hook) mode detects
changes via `git diff --cached` (the staged index). The `manifest-sync` CI job
(`.github/workflows/code-quality.yml`) ran this exact mode via `prek run auto-sync-manifests
--all-files` on a plain, nothing-staged CI checkout — so `git diff --cached` was always empty and
the step always printed "No manifest updates needed" and exited 0, regardless of what the PR
actually changed. Combined with GitHub squash-merge never running the local pre-commit hook, this
let PR #3005 land a `development-harness` plugin content change with zero `plugin.json` version
bump; the marketplace cache (keyed on version) kept serving stale content indefinitely with no
CI signal.

**Fix (PR #3022, fixes #3021):** new `plugins/plugin-creator/scripts/check_plugin_version_bump.py`
sibling script (kept separate from `auto_sync_manifests.py` — that file is already ~1780 LOC,
well over this repo's 500-LOC file-size policy, so new responsibilities go in a new module, not
grown further into the existing one):
- `--check --base-ref <ref>`: diffs *base_ref* against HEAD directly (`git diff --name-only
  base...head`), not the staged index — works correctly on a plain CI checkout of a squash-merged
  PR. Wired into `manifest-sync` as a new required step using this repo's existing
  `file-hygiene`-job pattern (`fetch-depth: 0` + `git merge-base "origin/$GITHUB_HEAD_REF"
  "origin/$GITHUB_BASE_REF"`).
- `--audit`: retroactive, report-only mode — walks each plugin's `plugin.json` git history to find
  its last version-bump commit, then flags any file changed under that plugin since with no
  further bump. Running it against this repo's real history (2026-08-19) found **16 plugins**
  with the same undetected drift, including `development-harness` itself with 13+ unbumped
  commits since its last bump — proof this wasn't a one-off, it was actively recurring on every
  GitHub-merged PR because no CI check could ever catch it.

**Gotcha found via a real-git-repo integration test (not caught by mocked unit tests):**
`git show ref:path` — used internally by `read_ref_json()` (promoted from `_read_ref_json`,
now a public cross-module helper in `auto_sync_manifests.py`) — requires a repo-root-relative
path. Unlike `git log -- path` / `git diff -- path` (which resolve pathspecs relative to CWD and
accept absolute paths fine), `git show ref:path` looks up the tree entry literally and silently
returns nothing for a filesystem-absolute path. `audit_version_drift()` originally built its path
from `plugins_root.iterdir()` Path objects, which are absolute when the caller passes an absolute
`plugins_root` (e.g. a pytest `tmp_path` fixture) — this made every plugin look falsely
never-bumped in that test scenario, while the real CLI path (`Path("plugins")`, relative) worked
fine. Fixed by always rebuilding a `f"plugins/{name}/..."` string explicitly rather than reusing
the iterated Path's `.as_posix()`. Lesson: when writing git-ref-comparison code, don't trust that
"the pathspec worked for `git log`/`git diff`" implies it'll also work for `git show ref:path` —
test both, ideally with a real subprocess-backed integration test using a `tmp_path`-derived
(absolute) repo root, which is exactly what surfaced this.

See also [[project_ruff_fix_true_autofix]] (this repo's ruff has fix=true).
