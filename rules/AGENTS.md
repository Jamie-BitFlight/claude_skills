# rules/ — Cross-Tool Path-Scoped Rules

Plain-content mirror of `.claude/rules/*.md` for tools without a native path-glob mechanism
(Codex, Hermes). `manifest.json` is the authoritative source for which glob patterns load which
file — read it directly rather than trusting a restated pattern here. `context-loader.mjs` is the
shared matcher/loader every harness's own hook wrapper calls.

| File | Loads when editing... |
|---|---|
| `agent-output-contracts.md` | agent/command/reference files — every agent must emit explicit terminal output |
| `astral-tool-overrides.md` | Python files, `pyproject.toml`, `uv.lock` — this repo's uv/ty/ruff policy overrides |
| `ci-workflows.md` | `.github/workflows/*.yml` — CI workflow modification protocol |
| `citation-requirements.md` | SKILL.md/agents/commands/CLAUDE.md — factual claims need a cited source |
| `delegation-format.md` | SKILL.md/agents/commands/references — canonical delegation-instruction format |
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
| `script-invocation.md` | scripts/, `.claude/hooks/` — shebang/execute-bit, run scripts directly |
| `silent-failure-prevention.md` | Python/TS/JS — write operations must report what changed |
| `skill-content-optimization.md` | SKILL.md, references/*.md — load skill-creator before editing skills |
| `skill-documentation-verification.md` | SKILL.md, references/*.md — skill docs are AI-facing, not user-facing |
| `skill-substitution.md` | SKILL.md — load-time string substitution gotcha |
| `uv-run-fallback.md` | scripts/, Python files, `.claude/hooks/` — uv run fallback when uv unavailable |
| `yaml-toml-libraries.md` | Python files — `ruamel.yaml`/`tomlkit` only, never `pyyaml` |

A file with no `paths:` frontmatter in `.claude/rules/` was never migrated here — it loads some
other way (always-on, or referenced directly) and has no glob-triggered equivalent.
