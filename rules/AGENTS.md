# rules/ — Cross-Tool Path-Scoped Rules

`rules/` is the authoritative, plain-content rule source for tools without a native path-glob mechanism
(Codex, Hermes). `manifest.json` is the authoritative source for which glob patterns load which
file — read it directly rather than trusting a restated pattern here. `context-loader.mjs` is
designed as the shared matcher/loader for every harness's own hook wrapper to call; as of this
writing only Claude Code's wrapper (`.claude/hooks/context-rules.mjs`) exists and is wired
(`.claude/settings.json`'s `PostToolUse`/`SessionStart` hooks) — a Codex or Hermes wrapper has not
been added yet.

| File | Purpose | Reaches an agent via |
|---|---|---|
| `adr-lifecycle.md` | `ARCHITECTURE.md` states what's true now; an ADR records a dismissible deliberation nothing links to | `manifest.json` |
| `agent-output-contracts.md` | prohibited silent-output instructions and enforcement checklist | `manifest.json` |
| `astral-tool-overrides.md` | this repo's uv/ty/ruff policy overrides | `manifest.json` |
| `ci-workflows.md` | CI workflow modification protocol | `manifest.json` |
| `citation-requirements.md` | factual claims need a cited source | `manifest.json` |
| `data-format-selection.md` | pick the format closest to the consumer; never parse prose for your own data | `manifest.json` |
| `delegation-format.md` | wrong delegation-instruction formats to avoid in prose | `manifest.json` |
| `exception-handling.md` | narrow exception catches only, no broad `except Exception` | `manifest.json` |
| `frontmatter-requirements.md` | required frontmatter fields | `manifest.json` |
| `language-conventions.md` | language choice, `.cjs`/`.mjs` Node convention | `manifest.json` |
| `linting-exceptions.md` | when a lint suppression is (rarely) acceptable | `manifest.json` |
| `markdown-file-references.md` | code fence and markdown link conventions | `manifest.json` |
| `plugin-development.md` | auto-discovery, versioning, local testing | `manifest.json` |
| `plugin-json.md` | manifest schema requirements | `manifest.json` |
| `prose-file-classification.md` | review-treatment decision tree for prose files | `manifest.json` |
| `python-development.md` | PEP 723 scripts, no uv workspace, ty errors | `manifest.json` |
| `review-and-correction-discipline.md` | structural vs content review gates, and what belongs in `AGENTS.md` | `manifest.json` |
| `runtime-vs-design-time.md` | runtime vs. design-time audience, and a portable artifact's actual (installed) environment vs. its authoring repo | `manifest.json` |
| `script-invocation.md` | shebang/execute-bit, run scripts directly | `manifest.json` |
| `silent-failure-prevention.md` | write operations must report what changed | `manifest.json` |
| `skill-documentation-verification.md` | skill docs are AI-facing, not user-facing | `manifest.json` |
| `shared-process-extraction.md` | writing into an agent what another also needs, or finding the same process in two agents: one skill holds it, both load it | `manifest.json` |
| `skill-substitution.md` | load-time string substitution gotcha | `manifest.json` |
| `uv-run-required.md` | stop and tell the user when uv is unavailable — no pip/poetry/pipx/python fallback exists | `manifest.json` |
| `yaml-toml-libraries.md` | `ruamel.yaml`/`tomlkit` only, never `pyyaml` | `manifest.json` |
| `commit-cadence-and-worktrees.md` | small scoped commits, worktrees for concurrent writes | routing line |
| `delegation.md` | substantive work is delegated; pointer to `agent-orchestration:delegate` | routing line + `context-rules-agent.mjs` |
| `evidence-action-proportionality.md` | files changed must match evidence gathered | routing line |
| `fact-verification-first.md` | WebSearch before planning around a named product/version | routing line + `context-rules-prompt.mjs` |
| `falsification-requirement.md` | every hypothesis test needs a falsification check | routing line |
| `fix-delegation-discipline.md` | reproduction-first cycle for bug-fix delegation | routing line + `context-rules-agent.mjs` |
| `interactive-terminal-workarounds.md` | PTY providers when a tool needs a TTY | routing line |
| `large-file-write-strategy.md` | skeleton+edit-fill above 25K chars | routing line |
| `model-selection.md` | model/effort tier by cognitive requirement | routing line + `context-rules-agent.mjs` |
| `proactive-fix-gate.md` | gate before acting on a self-discovered problem | routing line |
| `reproduction-integrity.md` | reproduce in the real environment before synthetic ones | routing line |
| `scratch-directory.md` | `.tmp/scratch/` fallback output convention | routing line |

A `manifest.json` entry means `context-rules.mjs` loads the file when a touched path matches its
glob — read the actual pattern in `manifest.json` itself, not restated here. "routing line" means
the rule carries no `manifest.json` entry; instead, a line under root `AGENTS.md`'s "Situational
Rule Triggers" section names the file and the condition for reading it. A routing-line rule marked
with a hook filename also reaches an agent directly on that hook's event, independent of whether
the routing line gets read.

## Writing a Rule File

Rules are the current requirement only — never provenance, citations, or narrative. Put those in
the commit message or PR description; put a durable architecture decision in `docs/` instead.

Rules are read only when small. Tightening an existing rule means rewriting it from scratch as
flat directives, not `Edit`-trimming words from its existing structure.
