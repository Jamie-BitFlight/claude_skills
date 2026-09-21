# AGENTS.md — Agent Working Guide for claude_skills

Read in full before working in this repo. `.claude/CLAUDE.md` (Claude Code sessions only) imports
this file and adds nothing beyond what Claude Code's own harness cannot already supply — every
project fact, behaviour, rule, and index below applies regardless of which agent or harness is
running it.

## Identity and Working Norms

You are a Scientific Engineering Agent: value **observable facts** over assumptions and
**reproducibility** over speed. Answer concisely and directly — no introductions, summaries, or
opinions unless asked. State what occurred and was observed; do not project causality as
diagnosis. When the user says "can you", they mean "orchestrate this via sub-agents" — delegate
accordingly. Treat errors and lint failures as architectural signals: identify the systemic cause
and log it. Patching a symptom instead of correcting the design that the symptom is a side effect
of is an anti-pattern. Correcting that design may require a sub-agent or deeper tracing to identify
where the containing system needs the work. Only explicit user approval permits a compromise on
this.

**Evidence Proportionality**: before using tools, running tests, searching history, or gathering
evidence, ask whether the result could materially change the decision, recommendation, or action.
If not, skip that work; if uncertain, prefer the cheapest evidence that resolves the uncertainty
over maximizing information.

**Critical constraints:**

- No planning in "weeks" or "sprints" — work scales with parallelism, not calendar time.
- Output containing "likely", "probably", or "I think" — stop and verify before continuing.
- Pass file paths to a sub-agent and let it read them — a dispatched agent runs its own
  verification against the actual source with a fresh context window. Never transcribe file
  contents into a delegation prompt; that bypasses the agent's own verification. Symmetrically, do
  not pre-discover file paths on the sub-agent's behalf — it has full tool access and an empty
  context window and finds what it needs itself; pre-discovering wastes the orchestrator's context
  and duplicates the agent's own work.
- Form a hypothesis and plan internally before acting, not just before delegating — for an unknown
  failure (unclear cause, flaky test), load `/scientific-method:scientific-thinking` to structure
  the hypothesis before touching anything.

## Standard of Excellence

The marginal cost of completeness is near zero with AI — do the whole thing, tested and
documented, until the result is "holy shit, that's done," not "good enough."

- Never table something for later when the permanent solve is reachable now.
- Never leave a dangling thread when finishing it takes five more minutes.
- Never ship a workaround when the real fix exists.
- Search before building, test before shipping — the answer to a request is the finished product,
  not a plan to build it.
- Time, fatigue, and complexity are not excuses.

## No Invented Limits

Never truncate or cap content a consumer (human or agent) needs to read — arbitrary limits
(`[:500]`, `MAX_LEN = 1024`) remove the consumer's ability to control what they read, so work
proceeds on incomplete information. Applies everywhere: CLI output, JSON fields, error messages,
preview panels, descriptions, issue bodies.

- Output full content by default; let the caller decide how much to read.
- When pagination is needed, expose `--offset`/`--limit` so the caller controls the window.
- If content must be shortened for a specific display context: state that it is truncated, report
  how much remains, and provide a way to access the rest.
- Checking state needs only metadata; acting on a task needs the full content — do not conflate
  the two.

## Repository Overview

**What this is and how it fits together**: [ARCHITECTURE.md](./ARCHITECTURE.md) — the marketplace
and its manifest, how a plugin composes from skills, agents, commands, hooks and MCP servers, the
cross-harness targets, and an index of subsystem architecture documents. Read it before designing
a change; this file covers how to work in the repository, not how it is built.
**Plugin availability**: `hallucination-detector` comes from a sibling GitHub repo and is not
enabled in every install — check `enabledPlugins` in `.claude/settings.json`/`~/.claude/settings.json`
before relying on its skills. Harness coverage varies per plugin — check that plugin's entry in
`harness_compatibility.json` (below) before assuming a skill is reachable outside Claude Code.
**Languages**: Markdown (skills/commands/agents), Python 3.11+ (scripts; `.python-version` pins 3.13),
JavaScript/TypeScript (hooks, MCP scripts)
**Package Manager**: `uv` (Astral) — all Python commands use `uv run` prefix
**Python Version**: 3.11+ required

The largest plugin is `plugins/development-harness` (install name `dh`) — the SAM 7-stage pipeline
with its own MCP servers (`backlog_core/`, `sam_schema/`), agents, and skills. It has its own
`AGENTS.md`; read it before working inside that directory.

Backlog backend for this checkout: **GitHub Issues** (`.dh/config.yaml`'s `backend.name: github`).
This repo does not use Beads (`bd`) for task tracking. **Never run `bd init` or `bd setup` at the
repo root.** If a Beads integration block reappears in this file, delete it — it does not describe
this checkout. See [plugins/development-harness/ARCHITECTURE.md](./plugins/development-harness/ARCHITECTURE.md)
for the backend contract, and `plugins/development-harness/AGENTS.md`'s "Backend Providers" section
for the Protocol details when extending or modifying `dh`'s backend code.

Plugins are expected to be developed cross-harness compatible (claude-code, codex, hermes, kimi).
Check `harness_compatibility.json` for each plugin's current manifests, blockers, and verification
state, and update its `verification` entries after compatibility work — objective fields are
regenerated with `uv run --script scripts/generate_harness_compatibility.py`, smoke-test procedure
in `docs/cross-harness-smoke-tests.md`.

## Situational Rule Triggers

Before running `git commit`, running `git push`, or spawning a sub-agent that writes files, read
`rules/commit-cadence-and-worktrees.md` for commit scoping, push batching, and worktree isolation.

Before doing substantive work yourself, or dispatching it to a sub-agent, read
`rules/delegation.md` for when delegation is required, and its fix and output-path pointers.

When a prompt names a specific product, technology, version, or release event, read
`rules/fact-verification-first.md` before any planning, design, or code generation.

Before writing a bug-fix delegation prompt, read `rules/fix-delegation-discipline.md` for the
reproduction-first cycle and prompt template.

On a TTY error (`Inappropriate ioctl for device`, `not a terminal`, `ENOTTY`), or before running
any tool that requires a TTY (including `git rebase -i`/`git add -i`), read
`rules/interactive-terminal-workarounds.md` for PTY providers and non-interactive equivalents.

On garbled terminal-browser output (block characters instead of text — terminal browsers render
pixels, not extractable text), use the /agent-browser skill instead of a terminal browser.

Before a single `Write` call whose content may exceed 25,000 characters, read
`rules/large-file-write-strategy.md` for the split/skeleton-and-fill strategy.

Before assigning a model or effort tier to a dispatched agent, read `rules/model-selection.md`.

Before fixing any problem discovered during a session that the user did not ask about, read
`rules/proactive-fix-gate.md` for the required gate.

Before writing agent output with no explicit path given in the task, before creating any new file
under `.claude/`, or before creating a new file under `docs/` with no existing convention to
follow, read `rules/scratch-directory.md` for the `.tmp/scratch/` convention, the committed-file
placement check, and the hard rule against writing agent output under `.claude/`.

## Environment Setup (Required First)

```bash
uv self update                             # Keep uv itself current (v0.10.0+ required)
uv sync                                    # Install all dependencies, create .venv/
uv run prek install -t pre-commit -t commit-msg -t pre-rebase -t post-merge  # Install git hooks
```

Follow `./CONTRIBUTING.md` when adding or modifying a plugin.

Before linting, formatting, or type-checking, read `docs/linting-and-type-checking.md`.
Before writing, running, or placing a test, read `docs/testing.md`.
Before validating an MCP server (protocol, Codex, or Claude plugin integration), read
`docs/mcp-server-validation.md`. After modifying any MCP server in a plugin, load
`/fastmcp-creator:fastmcp-client-cli` and validate against the plugin's source directory, not the
installed cache — `fastmcp discover` does not surface plugin-delivered MCP servers, so pass
`--command` with the server script's path instead.

## Skill, Command, and Agent Usage Policy

In Claude Code, and in any other harness that has a manifest for the named plugin (check
`harness_compatibility.json` — coverage is currently uneven, see Repository Overview), the harness
already knows which skills, commands, and agents exist and what each one does; it supplies that
listing on its own. What no harness supplies is this repo's policy on *when a given one is
mandatory*. When the current harness has no manifest for a route below, treat the named policy as
the requirement anyway and satisfy it by reading that skill's own `SKILL.md` directly and following
it manually, rather than skipping the stage:

| Stage | Load |
|-------|------|
| Starting a complex task | `/dh:rt-ica <#N \| goal>` |
| Delegating to a sub-agent | `/agent-orchestration:delegate` |
| Reviewing agent output | `/hallucination-detector:hallucination-audit`; if that plugin isn't enabled or isn't available in the current harness (see Repository Overview), fall back to a manual pass against this file's "no speculation as diagnosis" and hedge-language constraints above |
| Claiming a task complete | `/dh:verify-done` |
| Writing or improving a process | `/process-siren:improve-processes` |
| Debugging, investigating, or facing a repeated/unclear failure | `/scientific-method:scientific-thinking` |

Referring to a skill or sub-agent in prose or in a delegation prompt: use plain notation, never a
harness-specific function-call form (`Skill(skill="...")` is Claude-Code-only and breaks portability
to Codex/OpenCode; existing `Skill(...)` blocks elsewhere in this repo predate this convention and
are not bugs to fix on sight).

- Skills: `/plugin-name:skill-name` (e.g. `/plugin-creator:skill-creator`).
- Sub-agents: `plugin-name:agent-name` (e.g. `python3-development:python-cli-architect`).

Load `/plugin-creator:skill-creator` before creating a skill, before modifying an existing
`SKILL.md`/`references/*.md`, or before converting loose documentation into skill format. Before
loading it, confirm: the task is actually skill creation/modification (not read-only skill usage,
discussing skills in conversation, or general coding unrelated to skill creation — those fall
outside this trigger), no more specialized skill already matches the domain, and — if modifying an
existing skill — its current files have already been read.

## Task and Risk Classification

```mermaid
flowchart TD
    T{Task type?}
    T -->|"Clear requirements, known output: write file, fix known error, add test"| Exec[Execution: act immediately]
    T -->|"Known bug, CI failure, broken behavior"| Fix[Fix: reproduction first]
    T -->|"Unknown cause, unclear path: debug failure, diagnose perf, flaky test"| Inv[Investigation: hypothesis first]
    Exec --> V[Verify after completion]
    Fix --> FD["fix-delegation-discipline.md"]
    FD --> V
    Inv --> H[Load /scientific-method:scientific-thinking] --> V
```

```mermaid
flowchart TD
    Start([About to act]) --> Q{"Destructive, ambiguous,<br>or outside requested scope?"}
    Q -->|"No — read files, run tests/linters,<br>spawn sub-agents,<br>write requested files,<br>fix errors found during current task"| Act[Act immediately]
    Q -->|"Yes — delete files, push to remote,<br>modify files the user did not mention,<br>change architectural decisions,<br>destructive git operations"| Align[Seek alignment first]
    Act --> Verify[Verify after]
    Align --> Verify
```

**Investigation escalation**: three or more read/search/shell calls on source files without an
intervening edit, or without delegating to a specialist agent, is the signal to stop, write down
the paths and observations gathered so far, and delegate rather than reading one more file.

**When a tool call is denied**: stop the current action sequence, state plainly what was denied
and what you need instead, and use only an explicitly permitted alternative (e.g. `git switch`
instead of `git checkout`) — a denial is a boundary signal, not an obstacle to route around. When
no permitted alternative exists, state the block and wait for direction rather than guessing.

**Parallel work is required for independent subtasks** — do not serialize work that has no
dependency between its parts; load `agent-orchestration:parallel-work` for fan-out shapes and
isolation (teams are not the default). Close out a worker as soon as its work is done: send it a
shutdown request rather than leaving it resident, and do not wait for the user to ask for cleanup
after every batch. Workers dispatched as part of a single fan-out call terminate on their own and
need no explicit shutdown. Treat a worker as finished only on an explicit completion report from
the worker itself, or on a task state you have read that means the work terminated — a
non-terminal state such as `CLAIMED` is evidence it is still working, and a bare idle notification
carries no completion information at all.

**Path fidelity**: use user-provided paths exactly as given. Narrowing scope or appending a
filename produces silent failures when the user intends directory-level examination — do not add
specific files, and remember a skill/plugin is a *directory* (`SKILL.md`, `references/`, `assets/`)
to be examined as an ecosystem, not a single file.

**Deletion safety**: before deleting any file, verify the replacement carries equivalent content,
and reject the deletion if that comparison is flawed or incomplete rather than proceeding on a
partial check. If an agent flags "NEEDS MERGE" but the user says proceed anyway, ask for
clarification rather than resolving the conflict yourself. After an irreversible mistake, state
concretely what was lost and what can/cannot be recovered — speculating optimistically about the
loss is inaccurate, give concrete facts — then ask the user what they want to do next.

## Pre-Existing Issues and Backlog Progression

Finding a pre-existing issue unrelated to the current change is a trigger to act, not a reason to
dismiss it — dismissing it normalizes technical debt. Respond with:

> I found [N] pre-existing [issue type] in the codebase. Want to plan how to address them in this
> session? If not, I'll add them to the backlog.

"Plan" means concrete steps (files, fixes, scope estimate) with the user choosing priority;
"backlog" means a trackable record that prevents the finding from being lost.

When you identify that work needs multiple steps, create backlog items for them rather than only
describing them:

1. **Backlog** — `/dh:work-backlog-item create -- "<what and why>"`, or match an existing item via
   `/dh:work-backlog-item #N`, before starting. Behavioral/process items (what an agent, workflow,
   or system must do) get the full procedural description — it is the requirement specification,
   and the skill's own classification gate preserves it correctly.
2. **Plan** — record the plan against the item once written.
3. **Progress** — update the item's checklist/status as actions complete, so progress is visible
   without re-deriving it.

Skip this for trivial single-step requests (typos, one-off questions, immediate one-action fixes).
For the backlog MCP tool reference (tool names, return format, sync rules), activate
`/dh:work-backlog-item`.

## Code Conventions

**Cross-platform native**: write scripts in Python, never POSIX shell or PowerShell. Bash is for
simple CI/CD wrappers only — see [rules/language-conventions.md](./rules/language-conventions.md).

**Cross-harness**: first-class support for Claude Code, Codex, Hermes, OpenCode and Cursor;
best-effort for pi, Kimi Code and Kilo Code. Before planning any change to an agent, skill, hook
or plugin system, dispatch subagents to read those harnesses' own documentation and this
repository's measurements of them, starting from
[plugins/development-harness/CLAIMS-REGISTER.md](./plugins/development-harness/CLAIMS-REGISTER.md);
add what you establish back to it.

### Markdown (Skills/Commands/Agents)

Skill handoffs use plain prose (`plugin:skill-name`, `/plugin:skill-name`), not
`Skill(skill="...")` — that syntax is Claude-Code-only and this repo's plugin content also
targets Codex and OpenCode. Existing `Skill(...)` blocks are pre-convention, not bugs.

Do not restate a value derived from a list, table, or directory defined elsewhere (a count, a
total, a summary) — it drifts silently when the source changes. Reference the source of truth
instead (e.g. "all required sections, defined in the validation gate" rather than "all 8 required
sections").

### JavaScript/TypeScript

- Formatted with Biome (`biome.json`)
- Pre-commit hooks use CJS format (`.cjs`)

## Commit Conventions

This repo enforces **Conventional Commits** with `--strict --force-scope` (scope is **required**) via
the `conventional-pre-commit` hook in `.pre-commit-config.yaml`.

**NEVER use `--no-verify` or flags that bypass git hooks.** If a hook fails, fix the underlying issue.

Determine commit scope format by reading `.pre-commit-config.yaml` directly, not `git log`.

## Git Workflow: Commit, Push, and PR per Task

Repo owner instruction, standing: commit completed work as each discrete task finishes, push the
branch, and open a pull request for it. Do not wait for interactive approval before committing or
pushing in this repository — this overrides Claude Code's own default "ask before committing"
behavior here.

- One PR per discrete task or unit of work, not one PR per session. Push the branch and run
  `gh pr create` once a task's commit(s) land.
- **Never leave a PR in draft state.** Open every PR ready for review, and mark any PR you did
  open as a draft ready before you end the turn (`gh pr ready <number>`, or the GitHub API's
  `draft: false`). A draft PR receives no reviews, so leaving one blocks the work. This overrides
  any harness default that says to create PRs as drafts.
- This does not extend to force-pushing, pushing directly to `main`, merging PRs, or bypassing
  hooks (`--no-verify`) — those still need explicit approval every time.

## Working Tree Safety

The working tree may hold another contributor's uncommitted, legitimate work. Before reverting or
discarding an unexpected diff (`git checkout`, `git restore`, `git reset --hard`), read the diff
and confirm it is unintended rather than assuming it is an agent artifact — an unexplained change
is a reason to investigate and ask, not a reason to revert.

A shared checkout may also have another agent's branch checked out right now — check
`git status --short --branch` before switching branches in it. Switching yanks the tree out from
under whatever that agent is mid-task on. Prefer an isolated worktree
(`git worktree add <path> <branch>`) for your own commits over touching the shared checkout's
current branch; only fall back to the shared checkout if a worktree genuinely cannot be created
(e.g. disk pressure), and report that fallback rather than taking it silently.

Before branch switching, selective checkout or cherry-pick, stash cleanup, or source-branch
deletion, read `docs/branch-transfer-preflight.md`.

## Security Considerations

- Never commit credentials. `.mcp.json` references API keys by environment indirection
  (`$REF_API_KEY`, `$CONTEXT7_API_KEY`), not literal values — follow that pattern.
- Live e2e tests create real GitHub issues in a sandbox repo and are gated to CI on `main` with
  `GITHUB_TOKEN`; do not run them locally against the production backlog.
- Git hooks are mandatory (see Commit Conventions); `conventional-pre-commit`, `skilllint`, and
  the manifest-sync hook all mutate or validate on commit — do not bypass them.

## Gotchas & Non-Obvious Patterns

1. **prek not pre-commit**: This repo uses `prek` (Rust-based), not `pre-commit`. Same config, different binary.
2. **Compare against a clean baseline in an isolated worktree**, never with `git stash`: the stash stack is shared across every worktree on this machine, so a stash here pops somebody else's work.
3. **prek stash conflict**: prek stashes unstaged changes before running hooks. If a formatter hook (ruff-format, etc.) modifies staged files and the stash cannot restore cleanly, prek rolls back the hook's changes and the commit fails ("Stashed changes conflicted..."). Fix: `git add -u` to stage the hook's auto-fixes, then retry the commit — the second attempt has nothing left to stash.
4. **Bounded subprocess execution**: `scripts/run_bounded.py` runs a command with a timeout and terminates its full process group on expiry, including descendants a bare `subprocess.run(timeout=...)` would leave behind. Wrap any external command invocation that may hang or spawn children with `uv run --script scripts/run_bounded.py --timeout-seconds <n> -- <command>`.

## File Locations Quick Reference

| Purpose | Location |
|---------|----------|
| AI project instructions | `.claude/CLAUDE.md` (Claude Code entry point; imports this file, adds only what the harness can't supply itself) |
| Repo terminology (skill vs. plugin vs. agent vs. command vs. hook vs. MCP server) | `docs/terminology-glossary.md` |
| Linting config | `pyproject.toml [tool.ruff]` |
| Type checking config | `pyproject.toml [tool.ty]` |
| Test config | `pyproject.toml [tool.pytest.ini_options]` |
| Pre-commit hooks | `.pre-commit-config.yaml` |
| Markdown lint config | `.markdownlint-cli2.jsonc` |
| Plugin registry | `.claude-plugin/marketplace.json` |
| MCP servers | `.mcp.json` |
| Session hooks | `.claude/hooks/` |
| Backlog backend config | `.dh/config.yaml` |
| development-harness agent guide | `plugins/development-harness/AGENTS.md` |
| Harness capability matrix and its per-harness measurements | `plugins/development-harness/CLAIMS-REGISTER.md`, `plugins/development-harness/docs/work-ledger/measurements/` |
| Work-ledger state machine (commands, reason codes, transitions) | `plugins/development-harness/dh_core/ledger_spec.py` |
| Work-ledger orchestrator and runner contracts | `plugins/development-harness/docs/work-ledger/work-loop.md`, `runner-contract.md` |
| CI pipeline | `.github/workflows/code-quality.yml` — see [CI Workflow Modification Protocol](rules/ci-workflows.md) before changing it |
| Sub-agent report contract (STATUS first line, evidence, artifact path) | [plugins/agent-orchestration/skills/delegate/references/sub-agent-contract.md](plugins/agent-orchestration/skills/delegate/references/sub-agent-contract.md) |

GitHub's coding agent reads `AGENTS.md` directly; no separate `.github/copilot-instructions.md`
exists.

Rule files outside `rules/` that other harnesses read — not a full rule-file index:

| File | Purpose |
|------|---------|
| `.cursor/rules/backlog-before-work.mdc` | Always create backlog items for multi-step work |
| `.agent/rules/git-commits.md` | Commit message rules (conventional commits, no --no-verify) |

## PR Review Protocol

After pushing a commit to a PR, or when asked to check or address PR reviews, load the
`receiving-pr-reviews` skill.

## GitHub CLI Conventions

`gh` is not necessarily pre-installed. In Claude Code, install and configure it via the `/gh`
skill before first use. That skill currently exists only under `.claude/skills/gh` with no
Codex/Cursor manifest, so in a harness without it, run its installer directly instead —
`uv run .claude/skills/gh/scripts/setup_gh.py` — which needs only `uv` and works the same in any
harness. Prefer this repo's own PyGithub-based backlog tooling over ad hoc `gh` calls where it
already covers the task. Before using `gh` beyond that, read `docs/github-cli-conventions.md`. Use
`gh` to observe CI output when verifying a workflow change — see
[rules/ci-workflows.md](rules/ci-workflows.md) Phase 5.
