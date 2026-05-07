---
name: gate-push
description: "Single-verb branch-to-PR quality gate pipeline. Use when the user wants to gate, push, and open a PR for a branch in one command."
argument-hint: <branch-name>
user-invocable: true
---

# Gate Push

Run `/dh:gate-push <branch-name>` to execute the same quality-gate pipeline as `/dh:complete-implementation`, then complete push + PR creation.

This mirrors the `git push no-mistakes <branch>` intent from `research/developer-tools/no-mistakes.md`: one verb, full gate pipeline, automatic PR on success.

## Required input

- `branch_name = $ARGUMENTS` (must be non-empty)

If empty: stop and ask for `<branch-name>`.

## Branch → backlog lookup algorithm

1. Normalize `branch_name` into a lookup slug:
   - Strip leading branch type prefix when present (`feature/`, `fix/`, `chore/`, etc.) by removing only the prefix up to and including the first `/` character
   - Then replace any remaining `/`, `_`, and `-` with spaces (for example `feature/auth/login-fix` → `auth/login-fix` → `auth login fix`)
   - Trim whitespace
   - Store the result as `normalized_slug`
   - Expected pattern is `type/slug` (e.g., `feature/foo-bar`); multi-segment branches still normalize using the same rule
2. Strategy 1 (title match):
   - `mcp__plugin_dh_backlog__backlog_list(title="<normalized_slug>")`
3. Strategy 2 (topic match fallback, only if Strategy 1 has zero results):
   - `mcp__plugin_dh_backlog__backlog_list(topic="<normalized_slug>")`
4. If exactly one item is returned, use it as `match`.
5. If multiple items are returned, do not guess — prompt the developer for an explicit issue number or plan path and use fallback mode.

## Resolve complete-implementation input

From `match`, resolve in this order:

1. If `match.issue` exists (issue number field from backlog output) → `target = #<match.issue>`
2. Else if `match.plan` exists and non-empty → `target = <match.plan>` (use the backlog item's plan field directly)
3. Else no resolvable target

## Execute gate pipeline

If `target` is resolved:

```text
Skill(skill: "dh:complete-implementation", args: "<target>")
```

`/dh:complete-implementation` is the source of truth for the quality-gate phases and final push/PR behavior. Do not duplicate its gate logic here.

## No-match / unresolved fallback

If no backlog match is found, or a match exists but has neither `issue` nor `plan`:

1. Prompt the developer for an explicit issue number (`#N`) or plan path.
2. Invoke:

```text
Skill(skill: "dh:complete-implementation", args: "<developer_supplied_target>")
```

## Success check

After successful completion, verify PR visibility for the branch:

```bash
REPO_SLUG="$(git remote get-url origin | sed -E 's#.*github.com[:/]([^/]+/[^/.]+)(\.git)?#\1#')"
if [ -z "$REPO_SLUG" ]; then
  echo "Unable to resolve GitHub repo slug from origin remote."
  exit 1
fi
gh pr list -R "$REPO_SLUG" --head <branch-name>
```

Use the original input branch (`branch_name`), not `normalized_slug`, for `--head`.
