# rules/ — Cross-Tool Path-Scoped Rules

Plain-content mirror of `.claude/rules/*.md` for tools without a native path-glob mechanism
(Codex, Hermes). `manifest.json` is the authoritative source for which glob patterns load which
file — read it directly rather than trusting a restated pattern here. `context-loader.mjs` is
designed as the shared matcher/loader for every harness's own hook wrapper to call; as of this
writing only Claude Code's wrapper (`.claude/hooks/context-rules.mjs`) exists and is wired
(`.claude/settings.json`'s `PostToolUse`/`SessionStart` hooks) — a Codex or Hermes wrapper has not
been added yet.

| File | Loads when editing... |
|---|---|
| `agent-output-contracts.md` | agent-definition files — prohibited silent-output instructions and enforcement checklist |
| `astral-tool-overrides.md` | Python files, `pyproject.toml`, `uv.lock` — this repo's uv/ty/ruff policy overrides |
| `ci-workflows.md` | `.github/workflows/*.yml` — CI workflow modification protocol |
| `citation-requirements.md` | SKILL.md/agents/commands/CLAUDE.md — factual claims need a cited source |
| `delegation-format.md` | SKILL.md/agents/commands/references — wrong delegation-instruction formats to avoid in prose |
| `exception-handling.md` | Python/TS/JS — narrow exception catches only, no broad `except Exception` |
| `frontmatter-requirements.md` | SKILL.md/agents/commands — required frontmatter fields |
| `language-conventions.md` | scripts/, `.claude/hooks/`, Python files — language choice, `.cjs`/`.mjs` Node convention |
| `linting-exceptions.md` | Python files, `pyproject.toml` — when a lint suppression is (rarely) acceptable |
| `markdown-file-references.md` | any `.md` — code fence and markdown link conventions |
| `plugin-development.md` | `plugins/**`, `.claude-plugin/**` — auto-discovery, versioning, local testing |
| `plugin-json.md` | `plugin.json` — manifest schema requirements |
| `prose-file-classification.md` | any `.md` — review-treatment decision tree for prose files |
| `python-development.md` | Python files, `pyproject.toml`, `uv.lock` — PEP 723 scripts, no uv workspace, ty errors |
| `review-and-correction-discipline.md` | SKILL.md/agents/commands/CLAUDE.md — structural vs content review gates |
| `runtime-vs-design-time.md` | SKILL.md/references/agents/commands/CLAUDE.md/AGENTS.md — runtime vs. design-time audience, and a portable artifact's actual (installed) environment vs. its authoring repo |
| `script-invocation.md` | scripts/, `.claude/hooks/` — shebang/execute-bit, run scripts directly |
| `silent-failure-prevention.md` | Python/TS/JS — write operations must report what changed |
| `skill-content-optimization.md` | SKILL.md, references/*.md — load skill-creator before editing skills |
| `skill-documentation-verification.md` | SKILL.md, references/*.md — skill docs are AI-facing, not user-facing |
| `skill-substitution.md` | SKILL.md — load-time string substitution gotcha |
| `uv-run-fallback.md` | scripts/, Python files, `.claude/hooks/` — uv run fallback when uv unavailable |
| `yaml-toml-libraries.md` | Python files — `ruamel.yaml`/`tomlkit` only, never `pyyaml` |
| `commit-cadence-and-worktrees.md` | any file (always-on) — small scoped commits, worktrees for concurrent writes |
| `delegation.md` | any file (always-on) — substantive work is delegated; pointer to `agent-orchestration:delegate` and the sub-agent contract |
| `evidence-action-proportionality.md` | any file (always-on) — files changed must match evidence gathered |
| `fact-verification-first.md` | any file (always-on) — WebSearch before planning around a named product/version |
| `falsification-requirement.md` | any file (always-on) — every hypothesis test needs a falsification check |
| `fix-delegation-discipline.md` | any file (always-on) — reproduction-first cycle for bug-fix delegation |
| `interactive-terminal-workarounds.md` | any file (always-on) — PTY providers when a tool needs a TTY |
| `large-file-write-strategy.md` | any file (always-on) — skeleton+edit-fill above 25K chars |
| `model-selection.md` | any file (always-on) — model/effort tier by cognitive requirement |
| `proactive-fix-gate.md` | any file (always-on) — gate before acting on a self-discovered problem |
| `reproduction-integrity.md` | any file (always-on) — reproduce in the real environment before synthetic ones |
| `scratch-directory.md` | any file (always-on) — `.tmp/scratch/` fallback output convention |

`match: "*"` in `manifest.json` means always-on: it fires on the first file touch of a session,
same dedup rules as any other entry. Every `.claude/rules/*.md` file is now migrated — a file with
no `paths:` frontmatter there became an always-on entry here instead of being skipped.

## Writing a Rule File

Rules are the current requirement only — never provenance, citations, or narrative. Put those in
the commit message or PR description; put a durable architecture decision in `docs/` instead.

Rules are read only when small. Tightening an existing rule means rewriting it from scratch as
flat directives, not `Edit`-trimming words from its existing structure.
