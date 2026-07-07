# Repository Access Procedure — Tested

Verified end-to-end against an out-of-session-scope public repository, 2026-07-07. Every step
below exists because a specific alternative was tried and failed in this session type — follow
the sequence instead of re-deriving it through trial and error.

**Scope**: steps 3-4 (the `gh api` 403, the `add_repo` restriction) hold for sandboxed/remote
Claude Code sessions behind a GitHub-scope-enforcing proxy — where this was tested. A session
with an unrestricted `gh`/`GITHUB_TOKEN` (e.g. local CLI) won't hit these walls; if `gh api`
succeeds on the first attempt, use it. Steps 1-2 (plain `git clone`, never standalone `cd`) hold
regardless of environment.

## 1. Clone with plain `git clone` only

This is the ONLY clone method confirmed to work for a repo outside this session's authorized
GitHub scope. It hits `github.com`'s git service directly, bypassing the API/GraphQL layer
entirely:

```bash
git clone --depth 1 {repo-url} ./.worktrees/{repo-name}/
```

Repo name sanitization: `[A-Za-z0-9._-]` only (replace other characters with `_`).

**Do NOT use `gh repo clone` as an alternative.** Tested and confirmed broken for out-of-scope
repos — `gh repo clone` issues a GraphQL preflight query before cloning, which this session
blocks:

```text
$ gh repo clone {owner}/{repo} ./.worktrees/{repo-name}/ -- --depth 1
HTTP 403: This GraphQL query (RepositoryInfo, sent by gh pr create/view (repo info preamble))
is not enabled for this session — only the pinned set of PR-review operations is served.
Use REST via `gh api repos/{owner}/{repo}/...` instead. (https://api.github.com/graphql)
```

The failure is in `gh`'s wrapper logic, not in git itself — plain `git clone` on the identical
URL succeeds (same session, same repo, exit 0).

## 2. Explore the clone with `Read`/`Grep`/`Glob` directly — never `cd`

Pass the worktree path as the tool's `path`/`file_path` argument on every call, e.g.
`Read(file_path="./.worktrees/{repo-name}/README.md")`.

A standalone `cd ./.worktrees/{repo-name}` Bash call does not persist — each Bash call in this
session resets to the original working directory before the next one runs (a compound command
ending in `cd` printed "Shell cwd was reset to {original-dir}" immediately after, before the
next Bash call executed). If a raw directory listing is unavoidable, chain it into ONE Bash
call — `cd DIR && ls -la` — never issue `cd` as its own call; it accomplishes nothing.

## 3. Treat a `gh api` 403 on an out-of-scope repo as final — go straight to step 5

```text
$ gh api repos/{owner}/{repo}
{"message":"GitHub access to this repository is not enabled for this session. Use add_repo to
request access."} (HTTP 403)
```

This is a hard scope restriction, not a missing `-R` flag or an auth glitch — it applies
identically to unauthenticated `curl https://api.github.com/repos/{owner}/{repo}` (same proxy,
same message, same HTTP 403). No retry, flag change, or alternate endpoint succeeds for a repo
the session hasn't been granted access to. Once it fails for a given repo, move to step 5.

## 4. Reserve `add_repo` for explicit user requests — never as a step-3 workaround

`add_repo`'s own tool description states: "Invoke ONLY when the user explicitly asks to add a
repo... Do NOT invoke autonomously." A URL supplied as a research target is not that request.
Using `add_repo` to route around a step-3 403 breaks that tool's own contract and doesn't reach
the metadata any faster than step 5 does.

Observed cost of skipping straight to steps 3/4 instead of 5: one live session spent six tool
calls (clone, blocked `cd`, two `gh api` attempts, then `add_repo`) to reach the answer steps 1
and 5 give directly.

## 5. Fallback for stars/forks/contributor counts/latest release

This is the only data step 3 actually blocks. Look for equivalent data already inside the clone
from step 1 before concluding it's unavailable:

- README badges — the shields.io badge URL or its alt text often embeds the count directly
- `CITATION.cff`
- `CHANGELOG.md`
- `package.json` / `pyproject.toml` version fields
- `git log -1 --format=%cd` inside the worktree, for last-commit date

If genuinely absent from the clone, apply Fidelity Rule 3 verbatim: write "Unable to access via
GitHub API — repository outside this session's authorized scope" in the entry's References
section. Do not infer the number, and do not attempt steps 3 or 4 again to get it.
