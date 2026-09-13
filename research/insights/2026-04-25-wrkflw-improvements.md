---
title: "Improvement Proposals: wrkflw"
---

<!-- removed-skill-citations -->
> **Removed-skill citations:** `swarm-spawning` were removed in PR #3422 (commit `4e1e73bd6`, 2026-09-06) and **retired in favour of** `plugins/agent-orchestration/skills/parallel-work/`, with what delegation guidance survives in `plugins/agent-orchestration/skills/delegate/`. "Retired in favour of" is that PR's own wording, at `plugins/agent-orchestration/skills/delegate/references/harness-notes/claude-code.md` — not a capability-preserving consolidation: `parallel-work/SKILL.md` § "Persistent teams" argues against the long-lived-team model outright, and the `TeamCreate` call that model relied on no longer exists in Claude Code as of v2.1.178 (`plugins/agent-orchestration/skills/delegate/references/harness-notes/claude-code.md`). The removal replaced roughly 2080 lines with roughly 330; the line numbers, pattern numbers, and named sections cited below have no surviving equivalent, and grep over `plugins/` and `.claude/` returns zero hits for them (`Handling Crashed Teammates`, `permission_request`, and the rest). Any "already covered" conclusion resting on them is therefore **refuted by the current tree, not merely unverified against it**.

## Improvement 1: Add local GitHub Actions schema validation to pre-commit

**Source pattern**: "Workflow Validation with Exit Codes — syntax checks, structural validation, and composite action input cross-checking with CI/CD-friendly exit codes. Enables use in CI pipelines and pre-commit hooks." (research entry, README.md line 101 citation; also "Integration Points: GitHub Actions validation in CI/CD pipelines — Projects using Claude Code could integrate `wrkflw validate` into pre-commit hooks or local CI checks to catch workflow errors before pushing.")
**Local system**: ./.pre-commit-config.yaml and ./rules/ci-workflows.md
**Confidence**: High
**Impact**: High
**Backlog**: #1933 created; closed — implemented by PR #2232 (commit `075491c33`, 2026-05-09)

### Current state

**Implemented — this proposal is closed.** On this entry's date, `./.pre-commit-config.yaml` ran
no GitHub Actions schema validator: the closest checks were `check-yaml`, validating raw YAML
parsability only, and a generic `markdownlint-cli2` for docs. Nothing parsed
`.github/workflows/*.yml` against the Actions schema (jobs, steps, expressions, `uses:`
references, `needs:` DAG validity).

`actionlint` (`rhysd/actionlint` v1.7.12) now sits at `./.pre-commit-config.yaml` lines 123–126,
added by PR #2232 (commit `075491c33`, 2026-05-09), which closed backlog #1933. Confirmed by
execution: `uv run prek run --files .github/workflows/code-quality.yml` reports
`Lint GitHub Actions workflow files......Passed`.

The hook is local, and "the `prek run` step runs actionlint" is true of a local run and false of
CI: `actionlint` is named in the `SKIP` env var of the `file-hygiene` job in
`.github/workflows/code-quality.yml`. #1933's acceptance criterion 6 permits exactly that — the
hook id in `SKIP` **or** the binary verifiably on the runner — so the closure is legitimate and
the gap this entry identified is closed for local pre-push validation, which is what it asked for.

`.claude/rules/ci-workflows.md` Phase 4, as it stood on this entry's date (commit `3bec019b4`),
stated "Validate YAML syntax: `python3 -m yaml <file>` or equivalent" — parsability only, not
structural validation. **That step no longer exists.** The file is now `./rules/ci-workflows.md`
(renamed in PR #3391, commit `bf4dcd876`) and its Phase 4 step 2 reads
"Validate: `uv run prek run --files <file>`" — which, since #2232, runs `actionlint` among the
other hooks. Phase 5 (Verify) still instructs "Push and check workflow run if possible"
(`./rules/ci-workflows.md` line 82), so confirming a workflow actually runs on GitHub still needs
a push; what no longer needs one is catching a structural error before that push.

Search confirmed no existing backlog item references actionlint, wrkflw, or local Actions
validation (`backlog_list search="github actions OR actionlint OR wrkflw"` returned 0 items).

### Target state

A new `actionlint` (or `wrkflw validate`) hook is added to `./.pre-commit-config.yaml`,
scoped to `^\.github/workflows/.*\.ya?ml$`. The hook fails with non-zero exit code when:
- Required keys (`name`, `on`, `jobs`) are missing
- A `needs:` reference points at an undeclared job id
- `uses:` references an action with malformed syntax
- `if:` expressions contain unbalanced `${{ }}` or unknown context refs
- Composite-action inputs are missing required keys

`./rules/ci-workflows.md` Phase 4 step 2 ("Validate: `uv run prek run --files <file>`") gains the
structural check. **Reached**: the YAML-syntax-only step this proposal originally targeted was
replaced by that `prek run` step after this entry was written, and `prek run` now includes
`actionlint`, so the structural check arrived through the step rather than alongside it.

### Measurable signal

**Both signals pass.** `uv run prek run --files .github/workflows/code-quality.yml` outputs
`Lint GitHub Actions workflow files......Passed`, and
`grep -E "actionlint|wrkflw" .pre-commit-config.yaml` matches the `- id: actionlint` line
(`./.pre-commit-config.yaml` line 126). The error-injection half of the signal
(`needs: [does-not-exist]` → exit 1 naming the offending job and line) is #1933's acceptance
criterion 3 and was verified on that item, not re-run here.

---

## Improvement 2: Strict-mode rejection for ambiguous diff filters in research-curator workflow tooling

**Source pattern**: "Strict Filter Mode (v0.8.0 Breaking Change) — `wrkflw run --event <name>` must also pass `--diff` or `--changed-files`. Prevents silent skipping of `paths:`-gated workflows ... Without a change set, all workflows with `paths:` filters are silently rejected, causing confusion. Strict mode (default) requires explicit change set input or `--no-strict-filter` to proceed." (research entry, BREAKING_CHANGES.md citation, lines 317–331)
**Local system**: ./rules/silent-failure-prevention.md (the principle); concrete application target: any local script that accepts filter inputs and currently returns "no items matched" instead of erroring. Specifically `plugins/development-harness/scripts/` glob-filtered tooling and the `dispatch_*` family in `mcp__plugin_dh_backlog__`.
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred — confidence Medium: would need a concrete inventory of which local CLI commands accept ambiguous filter combinations and currently silently no-op. Without that inventory, the proposal is a principle-extension rather than a directly observable gap. Raise to High after running a script-by-script audit for "no-op when filter is empty" patterns.

### Current state

`./rules/silent-failure-prevention.md` covers two cases (write operations must report
what changed; branching on inputs requires explicit fallback) but does not cover the third
wrkflw-shaped case: **ambiguous filter inputs that result in no output should fail loudly,
not silently match zero items**.

The wrkflw v0.8.0 breaking change is a textbook instance: `--event push` without `--diff` or
`--changed-files` was a footgun that silently rejected every `paths:`-gated workflow. The fix
was to error up-front with a precise message naming the three valid resolutions (`--diff`,
`--changed-files`, or `--no-strict-filter`).

This pattern likely applies to several local commands but the specific call sites have not been
enumerated.

### Target state

`./rules/silent-failure-prevention.md` gains a third subsection titled
"Ambiguous Filters Must Reject, Not No-op". Content: when a user supplies a filter expression
that lacks the inputs needed to resolve a non-empty result set, the command exits 2 (usage
error) with a message naming each of the missing inputs and the explicit opt-out flag.
Includes the wrkflw error message verbatim as a Right example.

### Measurable signal

Run `grep -A 5 "Ambiguous Filters Must Reject" rules/silent-failure-prevention.md` —
returns the new subsection. The example block contains the literal phrase
`--no-strict-filter`. After the rule is in place, a follow-up audit task identifies at least
one local command that violates the rule and gets fixed.

---

## Improvement 3: Document multi-runtime execution-mode selection pattern for swarm-spawning skill

**Source pattern**: "Multiple runtime options allow developers to choose the execution model that best suits their environment and security needs: Docker (default), Podman, Emulation (host process), Secure Emulation. Mechanism: Trait-based interface — `Runtime` trait defines container operations." (research entry, README.md lines 216–220, Technical Architecture section "Runtime Abstractions")
**Local system**: `./plugins/development-harness/skills/dispatch/SKILL.md` and `./.claude/skills/swarm-spawning/SKILL.md`
**Confidence**: Low
**Impact**: Medium
**Backlog**: Deferred — confidence Low: the local swarm-spawning skill was not read in detail in this assessment. The "single trait, multiple backends" pattern is generally applicable but the gap is inferred rather than directly observed in the local file. Raise to High after Read of `swarm-spawning/SKILL.md` confirms it has only one execution mode hardcoded with no documented decision branch for security vs speed trade-offs.

### Current state

The repository's swarm-spawning and agent dispatch tooling presumably uses a single execution
strategy (subagent or worktree). wrkflw demonstrates that for execution-style tools, exposing
runtime as an explicit user-selectable mode (Docker / Podman / Emulation / Secure-Emulation)
captures a real trade-off matrix: isolation vs. speed vs. host trust.

### Target state

Documented decision flowchart in the relevant SKILL.md showing when to use each isolation
mode (subagent in-process vs worktree subprocess vs dedicated container) — analogous to
wrkflw's runtime selection table.

### Measurable signal

`grep -E "isolation.*mode|runtime.*select" plugins/development-harness/skills/dispatch/SKILL.md`
returns content describing the decision matrix.

---

## Improvement 4: Add trigger-aware diff filtering to local workflow validation hook

**Source pattern**: "Trigger-Aware Filtering and Diff Integration — Workflows are automatically skipped if their `on:` block doesn't match the simulated event and changed file set. This prevents silent failures when testing workflows with `paths:` or `branches:` filters." (research entry, README.md lines 128–149)
**Local system**: ./.pre-commit-config.yaml; depends on Improvement 1 landing first
**Confidence**: High
**Impact**: Medium
**Backlog**: #1934 created

### Current state

There is no current local mechanism that maps `git diff` against the `paths:` filter on a
workflow's `on:` block to determine whether the workflow would actually fire for the staged
change. Pre-commit hooks today either run on every staged file matching a `files:` pattern
or always run — they do not consult the workflow `on:` block.

This means a developer modifying `src/foo.py` might break `code-quality.yml` (which fires on
`paths: ['src/**']`) but the pre-commit hook validating `code-quality.yml` runs regardless
of whether the staged change would even trigger that workflow on push.

### Target state

A `scripts/validate_relevant_workflows.py` script that:
1. Reads the staged file list from `git diff --cached --name-only`
2. Parses each `.github/workflows/*.yml` `on:` block (`paths`, `branches`, `paths-ignore`)
3. Reports which workflows WOULD fire for the staged change
4. Validates ONLY those workflows (or marks "skipped — no path match" for the rest)

Wired in as a pre-commit hook that runs `actionlint`/`wrkflw validate` on the relevant
subset, with a `--all` flag to validate every workflow regardless of diff.

### Measurable signal

Run `git diff --cached --name-only | uv run scripts/validate_relevant_workflows.py`. Output
contains `WOULD FIRE: code-quality.yml` for an `src/foo.py` change and
`SKIPPED (no paths match): backlog-sync.yml` for the same change. Exit code 0 when all
relevant workflows pass validation; non-zero when any of them fail.

---

## Improvement 5: Multi-provider secrets abstraction reference for credential-handling skills

**Source pattern**: "Secrets Management with Multiple Providers — Multiple backend providers for `${{ secrets.* }}` values: Environment variables, File-based (JSON/YAML/.env), HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, Google Cloud Secret Manager. Configuration: Per-provider configuration in `~/.wrkflw/secrets.yml`. Secrets are masked in logs and stored with AES-256-GCM encryption." (research entry, README.md lines 244–257)
**Local system**: No direct equivalent exists in this repo; closest is the various MCP tools that consume `GITHUB_TOKEN` from env (`./.claude/skills/gh/SKILL.md`, `./plugins/development-harness/scripts/run_backlog_server.py`)
**Confidence**: Low
**Impact**: Low
**Backlog**: Deferred — confidence Low: this repo's threat model is single-developer local execution where env-var secrets are sufficient. Adding a multi-provider abstraction is a speculative product-design improvement rather than a closed gap against current practice. No file in the repo currently struggles with secret-source pluralism.

### Current state

The repository uses `GITHUB_TOKEN` from the environment for all GitHub-API access. There is
no abstraction over secret sources because there is no demonstrated need for one.

### Target state

(Speculative) A `rules/secrets-resolution.md` documenting the multi-provider pattern
for plugins that may need credentials beyond env vars.

### Measurable signal

Not actionable today — no existing file in the repo has the secret-source pluralism problem
this would solve.

---

## Improvement 6: Composite-action input cross-checking pattern for plugin manifests

**Source pattern**: "Workflow Validation with Exit Codes — Syntax checks, structural validation, and **composite action input cross-checking** with CI/CD-friendly exit codes." (research entry, line 70)
**Local system**: `./plugins/plugin-creator/scripts/auto_sync_manifests.py` and `./plugins/plugin-creator/scripts/check_agent_auto_discovery.py`
**Confidence**: High
**Impact**: Low
**Backlog**: #1935 created

### Current state

`./.pre-commit-config.yaml` lines 127–142 runs `auto_sync_manifests.py` and
`check_agent_auto_discovery.py` against plugin manifests. Composite-action-style cross-checking
between a manifest's declared inputs/agents and the files those references resolve to is
partial: `check_agent_auto_discovery.py` exists for agents but no analogous check exists for
the cross-product of `commands:`, `skills:`, `hooks:` references in `plugin.json` vs the
files those entries point at.

A typo in `plugin.json` referencing a skill that does not exist on disk is not caught at
pre-commit; the failure surfaces only when a user tries to invoke the dead reference.

### Target state

A new `scripts/check_plugin_manifest_references.py` hook validates that every entry under
`commands:`, `skills:`, `agents:`, `hooks:` in `plugin.json` resolves to a real file/directory.
The hook exits 1 with the unresolved reference and the manifest line number when any
reference is dangling.

### Measurable signal

Inject `"skills": ["does-not-exist"]` into a plugin's `plugin.json`. Run
`uv run prek run --hook check-plugin-manifest-references --files plugins/<plugin>/.claude-plugin/plugin.json`.
Hook exits non-zero with message naming `does-not-exist` and the JSON path. Remove the bad
reference and re-run — hook exits 0.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Strict-mode rejection for ambiguous filter inputs (Imp 2) | Medium | Need an audit identifying specific local commands that silently no-op on empty filters before this becomes directly observable. |
| Multi-runtime execution-mode selection (Imp 3) | Low | The local swarm-spawning skill file was not read in detail; gap is inferred from the wrkflw pattern, not directly observed in repo files. |
| Multi-provider secrets abstraction (Imp 5) | Low | Repository's current threat model has no demonstrated pluralism need; would be speculative product design rather than closing an observed gap. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Modular crate design (16 focused crates) | Already implemented — this repo is structured as a marketplace with per-plugin and per-skill modular boundaries; no concrete improvement to encode beyond what `./.claude/CLAUDE.md` already mandates. |
| Expression evaluator (`${{ }}` substitution) | Not aligned with this repo's architecture — Claude Code prompt context substitution is the model runtime's concern, not a skill the repo can implement. |
| TUI-driven workflow exploration | Not actionable as an improvement — no existing skill in this repo has TUI requirements; building a TUI from scratch on the wrkflw pattern is product design, not a gap-closing improvement. |
| Watch mode for re-execution on file change | Already covered by `prek` pre-commit + git hooks pipeline; the repo's iteration cycle is staged-file driven, not file-watcher driven. |
| Reusable workflows (`uses: org/repo/.github/workflows/...`) | Not applicable — this repo has no internal reusable workflow pattern to extend. |
| Remote triggering via `wrkflw trigger` | Already covered — `gh` skill (`./.claude/skills/gh/SKILL.md`) and `gh workflow run` provide this functionality. |
| Job dependency DAG resolution | Already covered by SAM plan structure with `needs:` semantics in `mcp__plugin_dh_sam__sam_plan` and `dispatch_validate`. |
