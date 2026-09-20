# rules/ — Cross-Tool Path-Scoped Rules

`rules/` is the authoritative, plain-content rule source for tools without a native path-glob mechanism
(Codex, Hermes). `manifest.json` is the authoritative source for which glob patterns load which
file — read it directly rather than trusting a restated pattern here. `context-loader.mjs` is
designed as the shared matcher/loader for every harness's own hook wrapper to call; as of this
writing only Claude Code's wrapper (`.claude/hooks/context-rules.mjs`) exists and is wired
(`.claude/settings.json`'s `PostToolUse`/`SessionStart` hooks) — a Codex or Hermes wrapper has not
been added yet.

| File | Purpose |
|---|---|
| `adr-lifecycle.md` | `ARCHITECTURE.md` states what's true now; an ADR records a dismissible deliberation nothing links to |
| `agent-output-contracts.md` | prohibited silent-output instructions and enforcement checklist |
| `astral-tool-overrides.md` | this repo's uv/ty/ruff policy overrides |
| `ci-workflows.md` | CI workflow modification protocol |
| `citation-requirements.md` | factual claims need a cited source |
| `data-format-selection.md` | pick the format closest to the consumer; never parse prose for your own data |
| `delegation-format.md` | wrong delegation-instruction formats to avoid in prose |
| `exception-handling.md` | narrow exception catches only, no broad `except Exception` |
| `frontmatter-requirements.md` | required frontmatter fields |
| `language-conventions.md` | language choice, `.cjs`/`.mjs` Node convention |
| `linting-exceptions.md` | when a lint suppression is (rarely) acceptable |
| `markdown-file-references.md` | code fence and markdown link conventions |
| `plugin-development.md` | auto-discovery, versioning, local testing |
| `plugin-json.md` | manifest schema requirements |
| `prose-file-classification.md` | review-treatment decision tree for prose files |
| `python-development.md` | PEP 723 scripts, no uv workspace, ty errors |
| `review-and-correction-discipline.md` | structural vs content review gates, and what belongs in `AGENTS.md` |
| `runtime-vs-design-time.md` | runtime vs. design-time audience, and a portable artifact's actual (installed) environment vs. its authoring repo |
| `script-invocation.md` | shebang/execute-bit, run scripts directly |
| `silent-failure-prevention.md` | write operations must report what changed |
| `skill-content-optimization.md` | load skill-creator before editing skills |
| `skill-documentation-verification.md` | skill docs are AI-facing, not user-facing |
| `shared-process-extraction.md` | writing into an agent what another also needs, or finding the same process in two agents: one skill holds it, both load it |
| `skill-substitution.md` | load-time string substitution gotcha |
| `uv-run-fallback.md` | uv run fallback when uv unavailable |
| `yaml-toml-libraries.md` | `ruamel.yaml`/`tomlkit` only, never `pyyaml` |
| `commit-cadence-and-worktrees.md` | small scoped commits, worktrees for concurrent writes |
| `delegation.md` | substantive work is delegated; pointer to `agent-orchestration:delegate` and the sub-agent contract |
| `evidence-action-proportionality.md` | files changed must match evidence gathered |
| `fact-verification-first.md` | WebSearch before planning around a named product/version |
| `falsification-requirement.md` | every hypothesis test needs a falsification check |
| `fix-delegation-discipline.md` | reproduction-first cycle for bug-fix delegation |
| `interactive-terminal-workarounds.md` | PTY providers when a tool needs a TTY |
| `large-file-write-strategy.md` | skeleton+edit-fill above 25K chars |
| `model-selection.md` | model/effort tier by cognitive requirement |
| `proactive-fix-gate.md` | gate before acting on a self-discovered problem |
| `reproduction-integrity.md` | reproduce in the real environment before synthetic ones |
| `scratch-directory.md` | `.tmp/scratch/` fallback output convention |

`match: "*"` in `manifest.json` means always-on: it fires on the first file touch of a session
(and, for `delegation.md`, `fix-delegation-discipline.md`, and `model-selection.md`, also on the
first `Agent` tool call, via `.claude/hooks/context-rules-agent.mjs`'s hardcoded list), same dedup
rules as any other entry.

## Writing a Rule File

Rules are the current requirement only — never provenance, citations, or narrative. Put those in
the commit message or PR description; put a durable architecture decision in `docs/` instead.

Rules are read only when small. Tightening an existing rule means rewriting it from scratch as
flat directives, not `Edit`-trimming words from its existing structure.
