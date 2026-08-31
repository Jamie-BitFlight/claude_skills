---
name: pre-commit
description: Configures and runs git hooks with prek (or the pre-commit it replaces — same `.pre-commit-config.yaml`). Use when adding or troubleshooting git hooks, writing a `prepare-commit-msg` or `commit-msg` stage hook, or authoring `.pre-commit-hooks.yaml` for hook distribution.
---

# Git Hooks (prek)

prek is a Rust rewrite of pre-commit: same `.pre-commit-config.yaml`, same `.pre-commit-hooks.yaml`, no Python runtime required. Default to prek for new setups. A repo already on pre-commit keeps working — most commands below carry over unchanged, but not all; see "prek vs pre-commit CLI" before assuming a 1:1 mapping.

## Detect the installed tool

Read line 2 of `.git/hooks/pre-commit`:

- `github.com/j178/prek` → prek
- `pre-commit.com` → pre-commit

## Install

```bash
uv tool install prek   # or: pip install prek / cargo install prek
prek --version

prek install                                     # pre-commit stage only
prek install --hook-type prepare-commit-msg      # add prepare-commit-msg
prek install -t pre-commit -t prepare-commit-msg # multiple stages
prek install --prepare-hooks                     # also build hook envs now
prek install --overwrite                         # replace an existing shim
```

Install more stages by default without repeating `--hook-type`:

```yaml
# .pre-commit-config.yaml
default_install_hook_types: [pre-commit, prepare-commit-msg]
```

## Hook stages

Stage names match git hook names directly:

| Stage                | Fires                        | Use for                           |
| --------------------- | ---------------------------- | ---------------------------------- |
| `pre-commit`          | Before commit creation       | Formatting, linting, tests         |
| `prepare-commit-msg`  | Before the message editor    | **Rewriting the commit message**   |
| `commit-msg`          | After the message is written | Validating the commit message      |
| `pre-push`            | Before push to remote        | Integration tests, security scans  |
| `pre-merge-commit`    | Before a merge commit        | Merge validation                   |
| `post-checkout`       | After checkout                | Environment setup                  |
| `post-commit`         | After commit created          | Notifications, logging             |
| `post-merge`          | After merge completes          | Dependency updates                |
| `manual`              | Explicit invocation only      | On-demand tasks                    |

### prepare-commit-msg vs commit-msg

| | prepare-commit-msg | commit-msg |
| --- | --- | --- |
| Can modify the message | Yes | No — validation only |
| Runs | Before the editor opens | After the message is written |
| Env vars | `PRE_COMMIT_COMMIT_MSG_SOURCE`, `PRE_COMMIT_COMMIT_OBJECT_NAME` | none |
| Use for | Rewriting, formatting | Validation, rejection |

For message validation, load `Skill(skill: "commitlint:commitlint")` or `Skill(skill: "conventional-commits:conventional-commits")` instead of building a hook.

## Configuration files

### `.pre-commit-config.yaml` — user repository

| Property | Type | Default | Purpose |
| --- | --- | --- | --- |
| `repos` | list | required | Repository mappings |
| `default_install_hook_types` | list | `[pre-commit]` | Hook types installed by default |
| `default_stages` | list | all stages | Default stages for hooks |
| `fail_fast` | bool | `false` | Stop on first hook failure |

```yaml
repos:
  - repo: https://github.com/org/tool
    rev: v1.0.0 # immutable ref — tag or SHA, never a branch name
    hooks:
      - id: hook-name
        stages: [prepare-commit-msg]
        args: [--option, value]
```

Hook-level properties: `id` (required), `stages`, `args`, `files`/`exclude` (regex), `types` (AND logic), `always_run`, `pass_filenames`, `verbose`, `require_serial`.

### `.pre-commit-hooks.yaml` — hook repository

Defines hooks for distribution. Required: `id`, `name`, `entry`, `language`. Optional: `stages`, `pass_filenames` (default `true`), `always_run` (default `false`), `files`/`exclude`, `types`, `description`, `minimum_pre_commit_version`.

```yaml
- id: commit-polish
  name: Polish Commit Message
  description: Rewrites commit messages to conventional format using LLM
  entry: commit-polish
  language: python
  stages: [prepare-commit-msg]
  pass_filenames: false # hook receives the message file path, not staged files
  always_run: true # run even without staged file changes
  minimum_pre_commit_version: "3.2.0"
```

## Implementing a prepare-commit-msg hook

Receives the commit message file path as `sys.argv[1]`, plus `PRE_COMMIT_COMMIT_MSG_SOURCE` (`message`/`template`/`merge`/`squash`/`commit`) and `PRE_COMMIT_COMMIT_OBJECT_NAME` (commit SHA, for amends) as env vars.

```python
#!/usr/bin/env python3
"""Hook entry point for prepare-commit-msg stage."""

import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("Error: No commit message file provided", file=sys.stderr)
        return 1

    commit_msg_file = sys.argv[1]
    source = os.environ.get("PRE_COMMIT_COMMIT_MSG_SOURCE", "")
    commit_sha = os.environ.get("PRE_COMMIT_COMMIT_OBJECT_NAME", "")

    with open(commit_msg_file, encoding="utf-8") as f:
        original_message = f.read()

    if not original_message.strip():
        return 0  # nothing to rewrite

    new_message = process_commit_message(original_message)

    with open(commit_msg_file, "w", encoding="utf-8") as f:
        f.write(new_message)

    return 0


def process_commit_message(message: str) -> str:
    return message


if __name__ == "__main__":
    sys.exit(main())
```

Register the entry point in `pyproject.toml`:

```toml
[project.scripts]
commit-polish = "commit_polish.hook:main"
```

```yaml
# .pre-commit-hooks.yaml
- id: commit-polish
  name: Polish Commit Message
  entry: commit-polish
  language: python
  stages: [prepare-commit-msg]
  pass_filenames: false # critical: hook needs the message file path
  always_run: true # critical: run even without staged files
```

## Running hooks

```bash
git commit -m "message"  # auto: pre-commit + prepare-commit-msg hooks
git push                 # auto: pre-push hooks

prek run                              # staged files only — default, preferred
prek run --files path/to/file.py      # scoped to specific files
prek run commit-polish                # one hook
prek run --stage prepare-commit-msg   # one stage
prek run commit-polish --verbose
prek run --all-files                  # whole repo — only when the user asks for it
```

`--all-files` formats the entire repository: it pollutes diffs with unrelated changes, creates merge conflicts on files others are editing, and breaks `git blame`. Scope to staged files (no args) or `--files <paths>` unless the user explicitly requests a repository-wide cleanup.

## Testing a hook before distributing it

```bash
prek try-repo /path/to/hook-repo hook-id --all-files
prek try-repo /path/to/hook-repo hook-id --files a.py
```

For a message-mutating hook, skip the framework and run the entry point directly against a scratch file:

```bash
echo "test message" > /tmp/test-msg
python -m commit_polish.hook /tmp/test-msg
cat /tmp/test-msg
```

## Skipping hooks

```bash
SKIP=hook-id git commit -m "message"   # skip one hook during a real commit
prek run --skip hook-id                # skip one hook for a manual run
git commit --no-verify                 # bypass all hooks (git-level, works with either tool)
```

`--skip` only applies to `prek run`; git's automatic invocation never sees it. Use `SKIP=hook-id` for that instead — prek honors it exactly like pre-commit (verified against 0.4.11: it errors out if `SKIP` filters out every hook in the config, so never use it to skip an entire single-hook setup).

## Cache

```bash
prek cache dir      # show cache location
prek cache size      # show cache size
prek cache gc        # remove unused cached repos/envs
prek cache clean     # remove all cached data
```

Override the cache directory with `PREK_HOME`.

## prek vs pre-commit CLI

Most subcommands carry over unchanged (`run`, `install`, `uninstall`, `list`, `try-repo`, `validate-config`, `validate-manifest`, `sample-config`). These do not:

| Task | pre-commit | prek |
| --- | --- | --- |
| Update hook revisions | `pre-commit autoupdate` | `prek update` |
| Restrict a run to one stage | `run --hook-stage X` | `run --stage X` |
| Clear the cache | `pre-commit clean` / `pre-commit gc` | `prek cache clean` / `prek cache gc` |

## Common patterns

```yaml
# Commit message rewriting
- repo: https://github.com/your-org/commit-polish
  rev: v1.0.0
  hooks:
    - id: commit-polish
      stages: [prepare-commit-msg]
      pass_filenames: false
      always_run: true

# Commit message validation
- repo: https://github.com/alessandrojcm/commitlint-pre-commit-hook
  rev: v9.5.0
  hooks:
    - id: commitlint
      stages: [commit-msg]
      additional_dependencies: ["@commitlint/config-conventional"]
```

```yaml
# Run formatting on pre-commit, integration tests on pre-push
- repo: local
  hooks:
    - id: python-tests
      name: Run Python Tests
      entry: uv run pytest
      language: system
      stages: [pre-commit]
      types: [python]
      pass_filenames: false

    - id: integration-tests
      name: Run Integration Tests
      entry: uv run pytest tests/integration
      language: system
      stages: [pre-push]
      pass_filenames: false
      always_run: true
```

## Common issues

**Hook not running** — verify the shim exists (`ls -la .git/hooks/prepare-commit-msg`), install the missing stage (`prek install --hook-type prepare-commit-msg`), and check `default_install_hook_types` in `.pre-commit-config.yaml`.

**Message hook receives filenames instead of the message path** — set `pass_filenames: false` for `prepare-commit-msg` and `commit-msg` stage hooks.

**Hook skipped when no files match** — set `always_run: true`.

**Repo updates not reflected after `prek update`** — the config used a mutable ref. Use a tag or SHA (`rev: v1.0.0` or `rev: a1b2c3d4`), never a branch name (`rev: main`).

**Hooks run in an unexpected order** — hooks run in the order listed in `.pre-commit-config.yaml` within a repository entry; hooks from different repository entries may run in parallel. Group dependent hooks in one repository entry, or set `require_serial: true` on the later one.

## Complete example: commit message workflow

```
commit-polish/
├── .pre-commit-hooks.yaml
├── pyproject.toml
└── src/
    └── commit_polish/
        ├── __init__.py
        └── hook.py
```

```yaml
# .pre-commit-hooks.yaml
- id: commit-polish
  name: Polish Commit Message
  description: Rewrites commit messages to conventional commits format
  entry: commit-polish
  language: python
  stages: [prepare-commit-msg]
  pass_filenames: false
  always_run: true
  minimum_pre_commit_version: "3.2.0"
```

```yaml
# consumer's .pre-commit-config.yaml
default_install_hook_types: [pre-commit, prepare-commit-msg]

repos:
  - repo: https://github.com/your-org/commit-polish
    rev: v1.0.0
    hooks:
      - id: commit-polish
        stages: [prepare-commit-msg]
```

```bash
cd /path/to/consumer-repo
prek install                  # installs pre-commit + prepare-commit-msg shims
git add .
git commit -m "fix bug"       # hook rewrites the message before the editor opens
```

## Version requirements

| Component | Minimum | Notes |
| --- | --- | --- |
| prek | 0.4 | CLI surface in this skill verified against 0.4.11 |
| pre-commit | 3.2.0 | Stage names match git hook names — needed for the stage table above |
| Git | 2.24+ | Required for the `pre-merge-commit` stage |

## References

`references/pre-commit-official-docs.md` has the full link set. Config schema, hook stages, and `.pre-commit-hooks.yaml` are pre-commit's format and pre-commit.com's docs describe them accurately for prek too — only the CLI differs, per the table above.

- [prek docs](https://prek.j178.dev/)
- [prek GitHub repository](https://github.com/j178/prek)
- [Pre-commit official site](https://pre-commit.com/)
- [Git prepare-commit-msg documentation](https://git-scm.com/docs/githooks#_prepare_commit_msg)
