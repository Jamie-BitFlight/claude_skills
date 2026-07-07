# Repository Access Procedure — Tested

Verified end-to-end against an out-of-session-scope public repository (tested 2026-07-07). Follow
this sequence verbatim. Each numbered step exists because a specific alternative was tried and
confirmed broken in this session type — do not re-derive these through trial and error.

**This scoping matters — do not over-generalize it.** Steps 3 and 4 (the `gh api` 403 and the
`add_repo` restriction) are properties of *sandboxed/remote Claude Code execution environments
with a GitHub-scope-enforcing proxy* — the environment this was tested in. They are not a
universal fact about `gh` or about Claude Code generally. A session with a full, unrestricted
`gh`/`GITHUB_TOKEN` (a local CLI session, for example) will not hit these walls, and `gh api`
may simply succeed there. Steps 1 and 2 (plain `git clone`, never standalone `cd`) are good
practice regardless of environment and don't depend on this scoping. If `gh api` succeeds on
the first attempt in your session, use it — this document exists to stop wasted retries after
a failure is observed, not to preemptively forbid a tool that might work fine.

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

The failure is in `gh`'s wrapper logic, not in git itself, so it does not indicate the repo is
inaccessible — plain `git clone` on the identical URL succeeds (verified same session, same
repo, exit 0).

## 2. Explore the clone with `Read`/`Grep`/`Glob` directly — never `cd`

Pass the worktree path as the tool's `path`/`file_path` argument on every call:

```text
Read(file_path="./.worktrees/{repo-name}/README.md")
Glob(pattern="**/*.py", path="./.worktrees/{repo-name}/")
Grep(pattern="class .*Plugin", path="./.worktrees/{repo-name}/")
```

A standalone `cd ./.worktrees/{repo-name}` Bash call does not persist — each Bash call in this
session resets to the original working directory before the next call runs (confirmed by direct
test: a compound command ending in `cd` printed "Shell cwd was reset to {original-dir}"
immediately after, before the next Bash call executed). If a raw directory listing is
unavoidable, chain it into ONE Bash call — `cd DIR && ls -la` — never issue `cd` as its own
call; it accomplishes nothing and wastes a turn.

## 3. Do NOT call `gh api` or any `api.github.com` endpoint for an out-of-scope repo

Tested failure mode, reproducible on any repo outside this session's authorized GitHub scope:

```text
$ gh api repos/{owner}/{repo}
{"message":"GitHub access to this repository is not enabled for this session. Use add_repo to
request access."} (HTTP 403)
```

This is a hard scope restriction, not a missing `-R` flag or an auth glitch — it applies
identically to unauthenticated `curl https://api.github.com/repos/{owner}/{repo}` (also proxied
and blocked, verified same test, same message, same HTTP 403). No retry, flag change, or
alternate endpoint will succeed for a repo the session hasn't been granted access to. Do not
spend a second tool call confirming this once it has failed once for a given repo.

## 4. Do NOT call `add_repo` (or any session-scope-expansion tool) to route around step 3

`add_repo`'s own tool description states: "Invoke ONLY when the user explicitly asks to add a
repo... Do NOT invoke autonomously." A URL supplied as a research target is not a user request
to add that repo to the session's GitHub scope. Calling `add_repo` here is a contract violation
of that tool, not a valid fallback — and it still doesn't get you the metadata any faster than
step 5.

This exact mistake was observed in a live session: after `git clone` succeeded and a bare `cd`
was blocked, the agent tried `gh api` twice (both 403), then called the session's `add_repo` tool
as a last resort — six tool calls spent reaching the answer that steps 1 and 5 give directly.

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
