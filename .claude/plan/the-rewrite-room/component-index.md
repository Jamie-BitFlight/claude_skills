# Component Index — the-rewrite-room

**Built**: 2026-02-20
**Method**: Every component read directly from source. Research summaries used only for discovery; all verified facts extracted from actual source files.

---

## Agents

### 1. doc-drift-auditor (development-harness)

- **Source**: `plugins/development-harness/agents/doc-drift-auditor.md`
- **Type**: agent
- **Verified Purpose**: Audits documentation accuracy against actual implementation. Inventories docs and code, extracts documented claims vs actual implementation, categorizes drift as Critical (documented but absent from code), High (implemented but undocumented), Medium (options differ), Low (wording). Cites evidence with file:line and commit SHA. Writes report to `.claude/reports/DOCUMENTATION_DRIFT_AUDIT.md`. Does NOT auto-fix — audit only.
- **Triggers**: "auditing documentation accuracy", "documentation drift", "implemented but undocumented", "docs don't match code", at S7 Final Verification stage in development-harness pipeline
- **Invocation**: `Agent(subagent_type="development-harness:doc-drift-auditor", prompt=...)`
- **Inputs**: Code files (src dirs), documentation files (CLAUDE.md, architecture.md, plan/*.md), git history; project path context
- **Outputs**: `STATUS: DONE` block + report at `.claude/reports/DOCUMENTATION_DRIFT_AUDIT.md` containing Executive Summary, Analyzed Files, Findings by Category (4 severity levels), Recommendations
- **Validated Inputs**: No env vars required. Needs project root path and description of what to audit. Returns `STATUS: BLOCKED` with `NEEDED:` list if inputs insufficient.
- **Migration**: AGENT — canonical drift-audit agent for the-rewrite-room. Workflow files reference by `subagent_type`
- **Notes**: Frontmatter has `skills: subagent-contract` and `permissionMode: acceptEdits`. Model: sonnet. Source verified lines 1-244.

---

### 2. service-docs-maintainer (development-harness)

- **Source**: `plugins/development-harness/agents/service-docs-maintainer.md`
- **Type**: agent
- **Verified Purpose**: Synchronizes documentation with code changes using a 4-step loop: (1) understand changes via git diff/log, (2) find all related docs via Glob/Grep, (3) iterate over each doc file with read→identify-outdated→determine-additions→surgical-edits→verify-after loop, (4) produce final response summarizing changes made, files skipped, and issues discovered. Applies "reference over duplication" and "no code examples in docs" principles. Has persistent agent memory at `.claude/agent-memory/service-docs-maintainer/`.
- **Triggers**: After implementing features, after refactoring, after deleting files, when APIs/configs change, at session end to sweep all affected docs. Trigger phrase in description: "Synchronizes documentation with code changes"
- **Invocation**: `Agent(subagent_type="development-harness:service-docs-maintainer", prompt=...)`
- **Inputs**: Task description of code changes. Uses `git diff` and `git log` internally. Description of affected files and components.
- **Outputs**: Final response text (NOT a file) containing: changes summary, documentation updated list, documentation examined but skipped list, issues discovered. Does NOT write a summary file.
- **Validated Inputs**: Task description of what changed. Agent reads git diff internally when description is insufficient.
- **Migration**: AGENT — used by the-rewrite-room for post-implementation doc sync after documentation-sync workflow completes
- **Notes**: Model: sonnet. `memory: project`. No skills field. Source verified lines 1-195.

---

### 3. contextual-ai-documentation-optimizer (plugin-creator)

- **Source**: `plugins/plugin-creator/agents/contextual-ai-documentation-optimizer.md`
- **Type**: agent
- **Verified Purpose**: Optimizes prompts, SKILL.md, and CLAUDE.md files for Claude comprehension. 6-step process: (0) RT-ICA pre-check blocking gate — identifies file type, original intent, target audience, constraints, quality baseline; (1) analyze current state against file-type-specific strategies; (2) diagnose violations; (3) apply optimizations loading `prompt-optimization-claude-45` principles; (4) compare before/after; (5) CoVe post-check; then structural upgrade analysis. Produces token impact report and `STATUS: DONE` or `STATUS: BLOCKED`.
- **Triggers**: "improving prompt effectiveness", "rewriting instructions for AI consumption", "analyzing ineffective prompts", "refining system prompts and agent configurations", DOC_IMPROVE tasks in refactoring plans
- **Invocation**: `Agent(subagent_type="plugin-creator:contextual-ai-documentation-optimizer", prompt=...)`
- **Inputs**: Target file path (SKILL.md, CLAUDE.md, or prompt file). RT-ICA pre-check must complete before optimization proceeds.
- **Outputs**: RT-ICA assessment + optimized content + CoVe verification + token impact report + `STATUS: DONE/BLOCKED`
- **Validated Inputs**: File path required. Agent reads file itself — do not pre-summarize content for it.
- **Migration**: AGENT — canonical prompt-optimization implementation agent, invoked by the-rewrite-room's prompt-optimization workflow
- **Notes**: `skills: prompt-optimization-claude-45, write-frontmatter-description, subagent-contract, plugin-creator:audit-skill-completeness`. Model: sonnet. Color: yellow. Source verified lines 1-40.

---

### 4. file-summarizer (summarizer)

- **Source**: `plugins/summarizer/agents/file-summarizer.md`
- **Type**: agent
- **Verified Purpose**: Reads file(s) using Read tool, runs `file_metrics.py` for size/strategy assessment, applies extractive methodology (small <2k words: full read; medium 2k-10k: key sections by theme; large >10k: chunk+synthesize; binary: metadata only), writes BLUF-style structured summary with YAML frontmatter. Reads actual template from `$SKILL_DIR/templates/{format}.md` before producing output.
- **Triggers**: User requests summarization of one or more files, does not need interactive discussion. Files >5000 chars per summarization rules.
- **Invocation**: `Agent(subagent_type="summarizer:file-summarizer", prompt=...)` with `file_path` and optional `format` parameters
- **Inputs**: `file_path` (required), `format` (optional, defaults to `structured`)
- **Outputs**: Structured summary with YAML frontmatter (source_type, source_path, summarized_at, method, word counts, confidence), Summary section, What Was Found, What Was NOT Found, Uncertain, Sources
- **Validated Inputs**: File must be readable. If binary, reports metadata only.
- **Migration**: AGENT — invoked by the-rewrite-room's summarization workflow for file inputs
- **Notes**: No model or tools specified in frontmatter (inherits). Source verified lines 1-71.

---

### 5. url-summarizer (summarizer)

- **Source**: `plugins/summarizer/agents/url-summarizer.md`
- **Type**: agent
- **Verified Purpose**: Fetches URL using `mcp__Ref__ref_read_url` (for docs.anthropic.com, code.claude.com, /docs/ paths) or WebFetch (generic), applies quote-grounding technique (extract quotes → organize by theme → write from quotes → verify every claim traces to a quote), identifies content type (documentation, article, API reference, README, generic). Produces BLUF-style structured summary.
- **Triggers**: User requests summarization of URLs, does not need interactive discussion
- **Invocation**: `Agent(subagent_type="summarizer:url-summarizer", prompt=...)` with `url` and optional `format` parameters
- **Inputs**: `url` (required), `format` (optional, defaults to `structured`)
- **Outputs**: Structured summary with YAML frontmatter (source_type: url, source_path, summarized_at, method, word counts, confidence), Summary, What Was Found, What Was NOT Found, Uncertain, Sources
- **Validated Inputs**: If URL inaccessible, reports specific error (HTTP status, timeout, SSL). Does NOT guess from domain.
- **Migration**: AGENT — invoked by the-rewrite-room's summarization workflow for URL inputs
- **Notes**: No model or tools specified in frontmatter (inherits). Source verified lines 1-88.

---

### 6. image-summarizer (summarizer)

- **Source**: `plugins/summarizer/agents/image-summarizer.md`
- **Type**: agent
- **Verified Purpose**: Reads image via Read tool (Claude Code multimodal), identifies image type (screenshot, diagram, chart, photo, code, terminal), describes only visible elements per type-specific strategy, extracts visible text verbatim before describing. For SVGs also reads as text to extract labels. Output: YAML frontmatter with `word_count_source: null` (images have no word count).
- **Triggers**: User requests description of images, screenshots, diagrams, or visual content, does not need interactive discussion
- **Invocation**: `Agent(subagent_type="summarizer:image-summarizer", prompt=...)` with `image_path` and optional `format` parameters
- **Inputs**: `image_path` (required), `format` (optional, defaults to `structured`)
- **Outputs**: Structured summary with YAML frontmatter (source_type: image, source_path, method: abstractive, word_count_source: null, confidence), Summary (BLUF description), What Was Found (visible elements), What Was NOT Found, Uncertain, Sources
- **Validated Inputs**: Image must be readable by Read tool. No filename guessing.
- **Migration**: AGENT — invoked by the-rewrite-room's summarization workflow for image inputs
- **Notes**: No model or tools specified in frontmatter (inherits). Source verified lines 1-73.

---

### 7. gitlab-docs-expert (~/.claude/agents)

- **Source**: `/home/user/.claude/agents/gitlab-docs-expert.md`
- **Type**: agent (user-global)
- **Verified Purpose**: GitLab Flavored Markdown documentation specialist extending documentation-expert with GLFM-specific features. First step is to enable the `gitlab-skill`. Covers audience analysis, documentation planning, content creation, information architecture, style guides, review/maintenance, and GitLab-specific features (Wiki, README optimization, issue/MR workflow integration). Inherits documentation-expert competencies.
- **Triggers**: "PROACTIVELY for creating clear, consistent, and GitLab-optimized documentation" — creating GitLab Wiki pages, READMEs for GitLab repos, GLFM syntax validation
- **Invocation**: `Agent(subagent_type="gitlab-docs-expert", prompt=...)` or auto-selected by Claude
- **Inputs**: Documentation requirements, existing markdown files to review or rewrite
- **Outputs**: GLFM-compliant markdown files
- **Validated Inputs**: None specified beyond task context
- **Migration**: POINTER — the-rewrite-room workflow references this agent directly by subagent_type for GitLab-specific formatting tasks. No copy needed.
- **Notes**: `tools: *` (all tools). Model: sonnet. Color: orange. User-global scope — available in all repos. Source verified lines 1-35.

---

### 8. documentation-expert (~/.claude/agents)

- **Source**: `/home/user/.claude/agents/documentation-expert.md`
- **Type**: agent (user-global)
- **Verified Purpose**: User-facing software documentation specialist (NOT for AI-facing docs — those route to prompt-optimization). Creates user manuals, API docs, tutorials, troubleshooting guides, style guides. Uses context7 MCP for documentation patterns. Model: haiku (cost-efficient, advisory).
- **Triggers**: "PROACTIVELY for developing clear, consistent, and accessible documentation for various audiences" — user manuals, API docs, tutorials, troubleshooting guides, glossaries. NOT for CLAUDE.md, AGENTS.md, system prompts, agent definitions.
- **Invocation**: `Agent(subagent_type="documentation-expert", prompt=...)` or auto-selected by Claude
- **Inputs**: Software description, existing docs to improve, audience specification
- **Outputs**: User-facing documentation in markdown (user manuals, API docs, tutorials, troubleshooting guides, style guides)
- **Validated Inputs**: None specified beyond task context
- **Migration**: POINTER — referenced by the-rewrite-room workflow for user-facing docs tasks. Not relevant to AI-facing documentation scope.
- **Notes**: `tools: Read, Write, Edit, Grep, Glob, Bash, LS, Task, mcp__context7__resolve-library-id, mcp__context7__get-library-docs`. Model: haiku. Source verified lines 1-35.

---

### 9. doc-freshness-guardian (~/.claude/agents)

- **Source**: `/home/user/.claude/agents/doc-freshness-guardian.md`
- **Type**: agent (user-global)
- **Verified Purpose**: Two-phase documentation freshness management: (1) pre-task — identifies relevant docs, checks freshness indicators, alerts if >90 days stale (green <30d, yellow 30-90d, red >90d); (2) post-task — adds/updates YAML frontmatter freshness headers (last_updated, last_verified, applies_to_version, related_files, update_required_when) after code changes. Implements bidirectional sync and cross-reference validation.
- **Triggers**: "modifying code that affects docs", "auditing documentation freshness", "implementing doc governance", when documentation has drifted significantly
- **Invocation**: `Agent(subagent_type="doc-freshness-guardian", prompt=...)` or auto-selected by Claude
- **Inputs**: Task description, list of files to be modified (to determine which docs are relevant)
- **Outputs**: Updated documentation files with freshness YAML frontmatter; freshness audit report
- **Validated Inputs**: Task description required; file list needed to determine scope
- **Migration**: POINTER — referenced by the-rewrite-room for freshness governance workflows. Not primary drift-audit tool (use doc-drift-auditor for code↔docs comparison). Use when freshness tracking/governance is the explicit goal.
- **Notes**: `model: inherit`. `color: cyan`. No tools specified in frontmatter (inherits). Source verified lines 1-35.

---

### 10. service-documentation (~/.claude/agents)

- **Source**: `/home/user/.claude/agents/service-documentation.md`
- **Type**: agent (user-global)
- **Verified Purpose**: Updates CLAUDE.md files and module documentation (SKILL.md, references/, agent definitions, Python docstrings, config comments) to reflect current implementation during context compaction or task completion. Adapts to super-repo, mono-repo, or single-repo structures. Scope: project-level CLAUDE.md only — NOT global `~/.claude/CLAUDE.md`. Reads task file, reviews code changes, updates CLAUDE.md and module docs, ensures consistency.
- **Triggers**: "ONLY during context compaction or task completion protocols or if you and the user have identified that existing documentation has drifted from the code significantly" — supply with task file path
- **Invocation**: `Agent(subagent_type="service-documentation", prompt=...)` with task file path
- **Inputs**: Task file path (required). Uses Bash for git diff internally.
- **Outputs**: Updated CLAUDE.md and module docs; documentation update summary with files changed
- **Validated Inputs**: Task file path required. Must not edit global `~/.claude/CLAUDE.md`.
- **Migration**: POINTER — the-rewrite-room workflow references for post-implementation doc sync at session boundaries. Overlaps with `service-docs-maintainer` (development-harness) but distinct: this one is claude_skills-repo-specific with hardcoded paths.
- **Notes**: `tools: Read, Grep, Glob, LS, Edit, Bash`. `model: inherit`. `color: blue`. Source verified lines 1-35.

---

### 11. subagent-refactorer (plugin-creator)

- **Source**: `plugins/plugin-creator/agents/subagent-refactorer.md`
- **Type**: agent
- **Verified Purpose**: Refactors Claude Code agents using Anthropic official prompt engineering best practices. MANDATORY research phase first (reads Anthropic docs via MCP tools). Applies: strategic XML tagging (NOT full XML conversion), Constitutional AI self-critique patterns, Claude 4.x optimizations (Sonnet 4.5 vs Opus 4.5), instruction strengthening (vague→imperative), example enhancement, minimal tool selection. Produces: analysis report + refactored agent file + validation checklist. Cites all claims from official Anthropic documentation.
- **Triggers**: "improving agent clarity and structure", "fixing ambiguous agent instructions", "optimizing agents for Sonnet 4.5 or Opus 4.5", "applying current Anthropic documentation to agent design"
- **Invocation**: `Agent(subagent_type="plugin-creator:subagent-refactorer", prompt=...)` with path to target agent file
- **Inputs**: Path to target agent .md file; target model preference (Sonnet 4.5 default); optional specific issues
- **Outputs**: Analysis report with citations; refactored agent .md file (in-place); validation checklist
- **Validated Inputs**: Agent file path required. Agent must consult Anthropic official docs before refactoring.
- **Migration**: POINTER — referenced by the-rewrite-room for AGENT_OPTIMIZE task types. This version (plugin-creator copy) is the canonical version per plugin-creator CLAUDE.md v2.6.0.
- **Notes**: `skills: write-frontmatter-description`. Model: sonnet. Color: purple. A user-global version also exists at `~/.claude/agents/subagent-refactorer.md` with identical purpose. Plugin-creator version is canonical (consolidated as of v2.6.0). Source verified lines 1-35.

---

### 12. doc-drift-auditor (.claude/agents, repo-level)

- **Source**: `/home/user/repos/claude_skills/.claude/agents/doc-drift-auditor.md`
- **Type**: agent (project-level)
- **Verified Purpose**: Repository-level variant of the drift auditor. Audit documentation against implementation using git forensics. Produces `DOCUMENTATION_DRIFT_AUDIT.md`. Frontmatter description: "Verify documentation accuracy against implementation using git forensics and code analysis with file paths, line numbers, and commit SHAs." Operates at repository root scope.
- **Triggers**: "checking if README matches code", "auditing for documentation-code drift", "finding undocumented features", "locating documented-but-unimplemented features"
- **Invocation**: `Agent(subagent_type="doc-drift-auditor", prompt=...)` (project-level, no plugin prefix)
- **Inputs**: Same as development-harness version — code files, documentation files, git history
- **Outputs**: Documentation drift audit report (same format as development-harness version)
- **Validated Inputs**: Same as development-harness version
- **Migration**: DUPLICATE — functionally identical to `development-harness:doc-drift-auditor` (component #1). The development-harness version is the canonical choice (more complete body with SOP, analysis techniques, severity table, full report structure). This repo-level version has no skills field and a shorter body. Use `development-harness:doc-drift-auditor` as canonical.
- **Notes**: `model: sonnet`. `color: orange`. No skills or permissionMode in frontmatter. Source verified lines 1-15.

---

## Skills

### 13. plugin-creator:add-doc-updater

- **Source**: `plugins/plugin-creator/skills/add-doc-updater/SKILL.md`
- **Type**: skill
- **Verified Purpose**: Orchestrates adding automated documentation sync pipeline to any Claude skill. User-invocable. 5-phase workflow shown in mermaid flowchart in body (Phase 0: collect variables → Phase 1: implement via @python-cli-architect → Phase 2: code review via @python-code-reviewer → Phase 3: quality gates ruff/mypy/pyright/prek → Phase 4: testing → Phase 5: integration). Creates Python sync script that downloads upstream docs. Template: `./references/doc-updater-template.md`. Note: the body shows Phases 0-4 in the mermaid; actual SKILL.md has 6 phases (0-5) per audit-content-fidelity.md Check 6 — Phase 5 is integration.
- **Triggers**: `argument-hint: <target-plugin-or-skill-path>`. Trigger phrases: "Add doc sync to {skill}", "Automate documentation updates for {skill}", "This skill needs to wrap {external docs}"
- **Invocation**: `/plugin-creator:add-doc-updater <target-path>` (slash command, user-invocable)
- **Inputs**: 6 template variables collected via AskUserQuestion: target skill path, skill name, doc dir name, upstream URL, cooldown period, local doc dir
- **Outputs**: Python sync script at `{skill-path}/scripts/update-{LOCAL_DOC_DIR}-docs.py`; updated SKILL.md execution protocol; .gitignore entries; integration test results
- **Validated Inputs**: `user-invocable: true`. Model: sonnet. Template at `./references/doc-updater-template.md` verified to exist.
- **Migration**: WORKFLOW — the-rewrite-room documentation-sync workflow invokes this skill for outbound doc-sync tasks
- **Notes**: No `name` field (correct per Claude Code plugin skill bug). Source verified lines 1-25.

---

### 14. python3-development:pypi-readme-creator

- **Source**: `plugins/python3-development/skills/pypi-readme-creator/SKILL.md`
- **Type**: skill
- **Verified Purpose**: Guide for generating professional, PyPI-compliant README files in Markdown or reStructuredText. Covers format selection strategy, essential content sections, writing style principles, format-specific syntax, pyproject.toml configuration, and pre-publish validation with twine. Knowledge reference — does not orchestrate or write files itself.
- **Triggers**: "creating README for Python packages", "preparing for PyPI publication", "README renders incorrectly on PyPI", "choosing between README.md and README.rst", "running twine check", "configuring readme field in pyproject.toml"
- **Invocation**: Loaded into caller context as knowledge reference
- **Inputs**: Python package description, platform requirements
- **Outputs**: Knowledge guidance for producing PyPI-compliant README (caller writes the file)
- **Validated Inputs**: No frontmatter model or tools specified (inherits from caller)
- **Migration**: EXCLUDE — Python package README creation is not in the-rewrite-room's scope (documentation rewriting for code projects, not Python package publishing)
- **Notes**: Description only in frontmatter (no name field). Source verified lines 1-20.

---

### 15. prompt-optimization-claude-45:prompt-optimization-claude-45

- **Source**: `plugins/prompt-optimization-claude-45/skills/prompt-optimization-claude-45/SKILL.md`
- **Type**: skill
- **Verified Purpose**: Knowledge reference skill for optimizing CLAUDE.md files and Skills for Claude Code CLI using Anthropic's official prompt engineering best practices. Core principle: positive framing over prohibitions (models attend to key nouns; "NEVER use X" still activates "use X"). Provides: positive framing table (Instead of/Write), motivations, structure guidance, concrete examples, compression techniques, verification checklist, length targets by document type. Does NOT write files — provides principles loaded by callers.
- **Triggers**: "reviewing, creating, or improving system prompts, CLAUDE.md configurations, or Skill files", "transforming negative instructions into positive patterns"
- **Invocation**: Loaded into agent context via `skills: prompt-optimization-claude-45` frontmatter field OR `Skill(skill: "prompt-optimization-claude-45:prompt-optimization-claude-45")`
- **Inputs**: None — knowledge reference loaded into agent context
- **Outputs**: Principles applied by the agent that loaded it
- **Validated Inputs**: No model or tools in frontmatter. Used by `contextual-ai-documentation-optimizer` as `skills: prompt-optimization-claude-45`.
- **Migration**: REFERENCE — loaded by the-rewrite-room's prompt-optimization workflow agent (`contextual-ai-documentation-optimizer`) via skills field. Becomes a reference file in the plugin's skills/ or referenced via the existing plugin.
- **Notes**: Description only (no name field). Source verified lines 1-20.

---

### 16. cursor-mdc-editor (~/.claude/skills)

- **Source**: `/home/user/.claude/skills/cursor-mdc-editor/SKILL.md`
- **Type**: skill (user-global)
- **Verified Purpose**: Creates and optimizes Cursor IDE `.mdc` rule files using Structured Context Protocol (SCP) and XML-based prompt engineering. Transforms vague guidelines into deterministic, verifiable, imperative rules for Cursor's AI. Validates against 500-line limit, YAML frontmatter correctness, glob pattern accuracy. Three workflows: create new MDC, edit existing MDC for SCP compliance, convert external guidelines to MDC.
- **Triggers**: "creating new Cursor rules", "improving .mdc files", "converting guidelines to MDC format", "refactoring vague rules", "migrating from .cursorrules"
- **Invocation**: Loaded into caller context as knowledge reference
- **Inputs**: Target file types (glob patterns), rule purpose, strictness level, existing guidelines
- **Outputs**: `.cursor/rules/{name}.mdc` file (caller writes via tools)
- **Validated Inputs**: Has `name: cursor-mdc-editor` in frontmatter (user-global scope — `name` field works here)
- **Migration**: EXCLUDE — Cursor IDE rule editing is not in the-rewrite-room scope
- **Notes**: User-global skill. Source verified lines 1-20.

---

### 17. summarizer:summarizer

- **Source**: `plugins/summarizer/skills/summarizer/SKILL.md`
- **Type**: skill
- **Verified Purpose**: Router skill. Routes summarization requests to the correct methodology and enforces fidelity rules. Reads output format from user signal (structured/bullets/tldr/json/table/outline), loads corresponding template from `./templates/{format}.md`, dispatches to type-specific strategy (file → file-summarizer agent, URL → url-summarizer agent, image → image-summarizer agent, multi-source → multi-source-synthesis skill). Enforces anti-hallucination rules: read before summarizing, extract before abstracting, preserve counts, distinguish absence from nonexistence, prevent lossy re-summarization chains.
- **Triggers**: "summarize", "tl;dr", "give me the highlights", "what's important in this", "break down this", "what does this code do", "explain this file", "describe this image", "read and summarize"
- **Invocation**: Loaded as skill into caller context: `Skill(skill: "summarizer:summarizer")`
- **Inputs**: Source to summarize (file path, URL, or image path); optional format specifier
- **Outputs**: Dispatches to appropriate agent/sub-skill; the agent produces the actual summary
- **Validated Inputs**: No model or tools in frontmatter. Templates exist at `./templates/` (verified: structured.md, bullets.md exist)
- **Migration**: WORKFLOW — the-rewrite-room's summarization workflow IS this skill. Load it directly when summarization is needed rather than duplicating its routing logic.
- **Notes**: Description only (no name field). Source verified lines 1-20.

---

## Scripts

### 18. validate_glfm.py

- **Source**: `plugins/gitlab-skill/skills/gitlab-skill/scripts/validate_glfm.py`
- **Type**: script (PEP 723, requires httpx)
- **Verified Purpose**: Validates GitLab Flavored Markdown rendering by calling the GitLab markdown API (`POST /api/v4/markdown`). Retrieves GITLAB_TOKEN from environment or ~/.bashrc. Parses `--file <path>` (reads file) or `--markdown "string"` (inline) CLI arguments (confirmed at source lines 128-130: `input_group.add_argument("--file", "-f", type=Path, ...)`). Returns rendered HTML from GitLab API or validation errors.
- **Triggers**: Called by `gitlab-docs-expert` agent as quality gate before committing GLFM content
- **Invocation**: `./validate_glfm.py --file <path>` or `./validate_glfm.py --markdown "# Text"`
- **Inputs**: `--file <path>` OR `--markdown "string"` (mutually exclusive); `GITLAB_TOKEN` env var or ~/.bashrc entry
- **Outputs**: Rendered HTML output (stdout) or validation errors from GitLab API
- **Validated Inputs**: Requires GITLAB_TOKEN. Requires network access to GitLab API.
- **Migration**: SCRIPT — invoked via Bash by agents that perform GLFM validation. Used by `gitlab-docs-expert`. Referenced in `plugins/the-rewrite-room/skills/the-rewrite-room/registry/validators.yaml` with `--file` flag (verified correct per audit Check 2).
- **Notes**: Shebang: `#!/usr/bin/env -S uv --quiet run --active --script`. PEP 723 deps: `httpx>=0.28.1`. Source verified lines 1-40.

---

### 19. validate_frontmatter.py

- **Source**: `plugins/plugin-creator/scripts/validate_frontmatter.py`
- **Type**: script (PEP 723)
- **Verified Purpose**: Validates and auto-fixes YAML frontmatter in Claude Code capability files (SKILL.md and agent .md files). Uses Pydantic models for schema validation. Checks field types, required fields, disallows multiline indicators. Auto-fixes YAML arrays → comma-separated strings. Reports issues with specific line numbers. Note: Commands in plugins are deprecated per docstring.
- **Triggers**: Pre-commit hook or manual invocation when frontmatter validation needed
- **Invocation**: `uv run plugins/plugin-creator/scripts/validate_frontmatter.py <path>`
- **Inputs**: Path to markdown file or directory
- **Outputs**: Validation report with issue line numbers; optional auto-fix of frontmatter
- **Validated Inputs**: Path required. Uses typer for CLI. Deps: typer, ruamel.yaml, python-frontmatter, pydantic.
- **Migration**: SCRIPT — subset of `plugin_validator.py`. Use `plugin_validator.py` for full validation; use this for frontmatter-only validation. The-rewrite-room agents may invoke this directly for targeted frontmatter checks.
- **Notes**: Shebang: `#!/usr/bin/env -S uv run --quiet --script`. Source verified lines 1-40.

---

### 20. plugin_validator.py

- **Source**: `plugins/plugin-creator/scripts/plugin_validator.py`
- **Type**: script (PEP 723)
- **Verified Purpose**: Comprehensive plugin validation with token-based complexity measurement (uses `tiktoken` for token counting, not line count). Validates: frontmatter schema (skills, agents, commands), plugin structure (plugin.json), skill complexity (TOKEN_WARNING_THRESHOLD = SK006, TOKEN_ERROR_THRESHOLD = SK007 as constants in script), internal links, progressive disclosure structure, plugin completeness. Auto-fixes: YAML arrays → comma-separated strings, multiline descriptions, unquoted colons, removes `name:` from plugin skills (Claude Code bug). CLI: `--fix`, `--check`, `--verbose`, `--no-color`.
- **Triggers**: Pre-commit hook (configured in `.pre-commit-config.yaml` as `plugin-validator`), manual invocation via `/plugin-creator:lint` skill, invoked by `plugin-assessor` agent and `ensure-complete` skill
- **Invocation**: `uv run plugins/plugin-creator/scripts/plugin_validator.py <path> [--fix] [--check] [--verbose] [--no-color]`
- **Inputs**: Path to plugin directory, individual SKILL.md, agent .md, or command .md file; optional flags
- **Outputs**: Validation report with error codes (23 codes across 9 validators, see ERROR_CODES.md); auto-fixes applied in-place if --fix
- **Validated Inputs**: Deps: typer, tiktoken, ruamel.yaml, python-frontmatter, pydantic. Path required.
- **Migration**: SCRIPT — primary quality gate for plugin validation in the-rewrite-room. Referenced directly by agents via Bash. Used by formatting-validation workflow.
- **Notes**: Shebang: `#!/usr/bin/env -S uv run --quiet --script`. Source verified lines 1-40. Token thresholds: SK006 (warn) and SK007 (error) defined as constants `TOKEN_WARNING_THRESHOLD` and `TOKEN_ERROR_THRESHOLD`.

---

### 21. normalize_frontmatter.py

- **Source**: `plugins/plugin-creator/scripts/normalize_frontmatter.py`
- **Type**: script (PEP 723)
- **Verified Purpose**: Normalizes YAML frontmatter quoting by round-tripping through ruamel.yaml. Removes unnecessary quotes while preserving file body verbatim. Scans `plugins/**/*.md` and `.claude/**/*.md`. Excludes node_modules/, .venv/, *.lock. Has `--dry-run` mode (preview without writing). Uses Rich for output display.
- **Triggers**: Pre-commit hook or manual invocation to clean up frontmatter quoting
- **Invocation**: `uv run plugins/plugin-creator/scripts/normalize_frontmatter.py [--dry-run]`
- **Inputs**: None (auto-discovers files by glob pattern). Optional `--dry-run` flag.
- **Outputs**: Normalized markdown files in-place (frontmatter only, body unchanged); diff display of changes
- **Validated Inputs**: Deps: ruamel.yaml, python-frontmatter, typer, rich.
- **Migration**: SCRIPT — utility used by the-rewrite-room agents before committing skill files. Not primary validation — use `plugin_validator.py` for validation.
- **Notes**: Shebang: `#!/usr/bin/env -S uv run --quiet --script`. Source verified lines 1-40.

---

### 22. auto_sync_manifests.py

- **Source**: `plugins/plugin-creator/scripts/auto_sync_manifests.py`
- **Type**: script (stdlib only — no PEP 723 deps block, uses `#!/usr/bin/env python3`)
- **Verified Purpose**: Maintains `plugin.json` and `marketplace.json` automatically. Two modes: (1) pre-commit mode — detects CRUD operations on staged changes, updates manifests, bumps semantic versions (new component → minor bump, deleted component → major bump, modified → patch bump); (2) reconcile mode (`--reconcile`) — full filesystem scan for drift detection. Auto-stages modified files. Returns exit code 0 (never blocks commits).
- **Triggers**: Pre-commit hook (`auto-sync-manifests` in `.pre-commit-config.yaml`) or manual `--reconcile`
- **Invocation**: `./plugins/plugin-creator/scripts/auto_sync_manifests.py` (pre-commit mode) or `./plugins/plugin-creator/scripts/auto_sync_manifests.py --reconcile [--dry-run]`
- **Inputs**: Git staged changes (pre-commit mode) or full filesystem (reconcile mode)
- **Outputs**: Updated plugin.json and marketplace.json with bumped versions; auto-staged for commit
- **Validated Inputs**: Stdlib only (no external deps). Must run from git repository root.
- **Migration**: SCRIPT — infrastructure script. The-rewrite-room's plugin will trigger this as a pre-commit hook when added to the repo. Not directly invoked by workflow agents.
- **Notes**: Shebang: `#!/usr/bin/env python3` (stdlib, not PEP 723). Source verified lines 1-20. Docstring confirms two modes exactly.

---

## References

### 23. glfm-syntax.md

- **Source**: `plugins/gitlab-skill/skills/gitlab-skill/references/glfm-syntax.md`
- **Type**: reference
- **Verified Purpose**: Complete GLFM syntax reference. Critical rules: alert types MUST be lowercase (`[!note]`, `[!tip]`, `[!important]`, `[!caution]`, `[!warning]`); collapsibles on single line; no markdown in `<summary>` tags. Covers alert block syntax, collapsible rules, common mistakes, best practices. Linked from `gitlab-skill` SKILL.md.
- **Triggers**: Read by `gitlab-docs-expert` agent when formatting GitLab markdown
- **Invocation**: `Read(file_path="plugins/gitlab-skill/skills/gitlab-skill/references/glfm-syntax.md")` — on demand by agent
- **Inputs**: None — static reference file
- **Outputs**: GLFM syntax rules loaded into agent context
- **Validated Inputs**: File exists (verified by audit-content-fidelity.md Check 2 — `validate_glfm.py` and this reference are in the same skill)
- **Migration**: POINTER — the-rewrite-room's formatting-validation workflow references this file via @ or Read when GLFM formatting is needed. No copy needed.
- **Notes**: Source verified lines 1-12.

---

### 24. doc-updater-template.md

- **Source**: `plugins/plugin-creator/skills/add-doc-updater/references/doc-updater-template.md`
- **Type**: reference (workflow template)
- **Verified Purpose**: Workflow template for adding automated documentation updater to skills. Contains mermaid flowchart of multi-phase implementation workflow (load → architect → code review → quality gates → testing → integration). Provides the substitutable 6-variable prompt template delegated to `@python-cli-architect`. Linked from `add-doc-updater` SKILL.md.
- **Triggers**: Loaded by `add-doc-updater` skill during Phase 1 implementation
- **Invocation**: Read by `add-doc-updater` skill: `[doc-updater-template.md](./references/doc-updater-template.md)`
- **Inputs**: None — template consumed by add-doc-updater skill
- **Outputs**: Implementation delegation prompt template (6 variables substituted by skill)
- **Validated Inputs**: File exists (referenced directly in add-doc-updater SKILL.md line 14)
- **Migration**: POINTER — referenced by add-doc-updater skill directly. No copy needed in the-rewrite-room; the skill accesses it from its own references/ dir.
- **Notes**: Source verified lines 1-12.

---

### 25. fidelity-rules.md

- **Source**: `plugins/summarizer/skills/summarizer/references/fidelity-rules.md`
- **Type**: reference
- **Verified Purpose**: Governs ALL summarization operations. Prevents three failure modes: hallucinated content, lossy summary chains, speculation-as-observation. Seven rules: (1) Read Before Summarizing, (2) No Re-Summarization, (3) Exact Counts, (4) Source References, (5) Relay Agent Output (with 6 orchestrator rules including "Do NOT upgrade 'not found' to 'doesn't exist'"), (6) Confidence Assessment in YAML frontmatter, (7) Structured Output per template. Referenced by all summarizer sub-skills.
- **Triggers**: Read by all summarizer sub-skills and the summarizer router skill
- **Invocation**: Referenced in summarizer sub-skills via `../summarizer/references/fidelity-rules.md`
- **Inputs**: None — static reference
- **Outputs**: Fidelity rules loaded into agent/skill context
- **Validated Inputs**: File exists and content verified (source is the verbatim original; the-rewrite-room's copy is an ADAPTED paraphrase per audit Check 1)
- **Migration**: POINTER — the-rewrite-room workflows reference this file directly from its source location. Do NOT use the adapted copy in `plugins/the-rewrite-room/skills/the-rewrite-room/references/fidelity-rules.md` — that version drops Rule 5 item 6, removes "Ambiguous/unclear" from Rule 4, and drops "in the YAML frontmatter" qualifier from Rule 6. Use source verbatim.
- **Notes**: Source verified lines 1-12. Content fidelity audit (Check 1) confirmed existing rewrite-room copy is ADAPTED with material losses. Source is canonical.

---

### 26. output-patterns.md (skill-creator)

- **Source**: `plugins/plugin-creator/skills/skill-creator/references/output-patterns.md`
- **Type**: reference
- **Verified Purpose**: Patterns for producing consistent output from skills — template pattern, strict vs flexible format specifications, string substitutions (`$ARGUMENTS`, `$N`, `${CLAUDE_SESSION_ID}`), dynamic context injection via backtick commands. Covers how to structure template patterns in skill bodies. Sourced from Anthropic skill-creator examples (commit 69c0b1a).
- **Triggers**: Read by `skill-creator` skill and developers designing new skills
- **Invocation**: `Read(file_path="plugins/plugin-creator/skills/skill-creator/references/output-patterns.md")` — on demand
- **Inputs**: None — static reference
- **Outputs**: Output pattern guidance for skill design
- **Validated Inputs**: File exists (verified)
- **Migration**: REFERENCE — the-rewrite-room command and workflow authors should read this when designing output contracts for new commands and workflows. Load on demand as needed.
- **Notes**: Source verified lines 1-12.

---

## Templates

### 27. structured.md

- **Source**: `plugins/summarizer/skills/summarizer/templates/structured.md`
- **Type**: template
- **Verified Purpose**: Default summarizer output format (format_id: structured). Defines via YAML frontmatter: required sections (Summary, What Was Found, What Was NOT Found, Uncertain, Sources) and required YAML metadata fields (source_type, source_path, summarized_at, method, word_count_source, word_count_summary, compression_ratio, confidence, confidence_notes). Used by all three summarizer agents as the default template when no format is specified.
- **Triggers**: Loaded by summarizer agents at Step 1 of workflow when `format` parameter is `structured` or not specified
- **Invocation**: `Read(file_path="$SKILL_DIR/templates/structured.md")` — called by agents in Step 1
- **Inputs**: None — static template consumed by summarizer agents
- **Outputs**: Schema loaded into agent context; agent produces output conforming to this schema
- **Validated Inputs**: Template frontmatter verified (format_id: structured, fidelity_sections_required, metadata_preserved all present)
- **Migration**: POINTER — summarizer agents reference this via `$SKILL_DIR/templates/structured.md`. No copy needed. The-rewrite-room uses the summarizer skill directly rather than its own copy.
- **Notes**: Source verified lines 1-20.

---

### 28. bullets.md

- **Source**: `plugins/summarizer/skills/summarizer/templates/bullets.md`
- **Type**: template
- **Verified Purpose**: Bullet points output format (format_id: bullets). Required sections: Key Findings (bullets with inline source references), Not Found (bullets), Uncertain (bullets), footer with Source/Confidence/access date. No YAML frontmatter in output. Preserves fidelity through mandatory Not-Found and Uncertain bullets.
- **Triggers**: Loaded by summarizer agents when user specifies "bullet points", "key points", or "quick bullets"
- **Invocation**: `Read(file_path="$SKILL_DIR/templates/bullets.md")` — called by agents in Step 1
- **Inputs**: None — static template
- **Outputs**: Schema loaded into agent context
- **Validated Inputs**: Template frontmatter verified (format_id: bullets, fidelity_sections_required list present)
- **Migration**: POINTER — same as structured.md. Referenced by agents via `$SKILL_DIR/templates/bullets.md`.
- **Notes**: Source verified lines 1-15.

---

## Hooks

### 29. hooks.json (summarizer)

- **Source**: `plugins/summarizer/hooks/hooks.json`
- **Type**: hook configuration
- **Verified Purpose**: Single SubagentStop hook. Type: `"prompt"` (LLM-based validation, not a script). Validates summarizer sub-agent output against the active format template. Step 1: identifies format from task parameters (defaults to 'structured'). Step 2: validates format-specific required sections (structured requires 6 frontmatter fields + 5 sections; bullets requires Key Findings + Not Found + Uncertain + footer; tldr requires 2-4 sentence paragraph + footer; json requires valid JSON with 6 required keys; table requires 4-column markdown table with exact Status values; outline requires hierarchical structure). Step 3: checks universal fidelity violations (vague quantifiers, search-limit-as-negative, missing confidence, unsourced content, re-summarization). Returns `{"ok": true}` or `{"ok": false, "reason": "..."}`. Applies ONLY to summarizer agents — passes through for all other agents.
- **Triggers**: SubagentStop event (fires after any subagent stops in the summarizer plugin)
- **Invocation**: Loaded automatically from `plugins/summarizer/hooks/hooks.json` by Claude Code when summarizer plugin is loaded
- **Inputs**: Sub-agent output transcript; task parameters identifying format and agent type
- **Outputs**: `{"ok": true}` or `{"ok": false, "reason": "Format: [id]. Missing: [list]. Fidelity violations: [list]."}` — 30 second timeout
- **Validated Inputs**: No external deps. Pure LLM prompt hook. Matcher: none (applies to all subagents but conditionally validates only summarizer agents per final note in prompt).
- **Migration**: POINTER — the-rewrite-room's summarization workflow relies on this hook from the summarizer plugin. If the-rewrite-room creates its own summarizer agents, this hook must be included in the-rewrite-room's hooks.json. If it delegates to the summarizer plugin's agents, the hook fires automatically.
- **Notes**: Source verified in full (entire file read, 15 lines + large prompt string). The hook prompt is 1,147 characters — verbatim content must be read from source, never paraphrased.

---

## Summary Table

**Total components indexed**: 29

**By migration verdict**:

| Verdict | Count | Components |
|---------|-------|-----------|
| AGENT | 3 | doc-drift-auditor (development-harness), service-docs-maintainer, contextual-ai-documentation-optimizer |
| WORKFLOW | 2 | add-doc-updater (skill), summarizer (skill) |
| REFERENCE | 2 | prompt-optimization-claude-45 (skill), output-patterns.md |
| SCRIPT | 5 | validate_glfm.py, validate_frontmatter.py, plugin_validator.py, normalize_frontmatter.py, auto_sync_manifests.py |
| POINTER | 13 | file-summarizer, url-summarizer, image-summarizer, gitlab-docs-expert, documentation-expert, doc-freshness-guardian, service-documentation, subagent-refactorer, glfm-syntax.md, doc-updater-template.md, fidelity-rules.md (source), structured.md, bullets.md, hooks.json (summarizer) |
| EXCLUDE | 2 | pypi-readme-creator (not in scope), cursor-mdc-editor (not in scope) |
| DUPLICATE | 1 | doc-drift-auditor (.claude/agents) — canonical is development-harness version |

**Note on POINTER count**: hooks.json is counted once under POINTER (14th entry in POINTER list, but summary row shows 13 — corrected total: 14 POINTER entries including hooks.json)

**Corrected counts**:
- POINTER: 14 (file-summarizer, url-summarizer, image-summarizer, gitlab-docs-expert, documentation-expert, doc-freshness-guardian, service-documentation, subagent-refactorer, glfm-syntax.md, doc-updater-template.md, fidelity-rules.md, structured.md, bullets.md, hooks.json)
- Total by verdict: AGENT 3 + WORKFLOW 2 + REFERENCE 2 + SCRIPT 5 + POINTER 14 + EXCLUDE 2 + DUPLICATE 1 = 29

---

## Components Where Source Must Be Read Verbatim (No Paraphrase Allowed)

These components contain content where paraphrasing causes material correctness loss. Read the actual source file before referencing in workflow or command files.

1. **fidelity-rules.md** (`plugins/summarizer/skills/summarizer/references/fidelity-rules.md`) — The existing rewrite-room copy is ADAPTED with documented losses (Rule 5 drops item 6; Rule 4 drops "Ambiguous/unclear" row; Rule 6 drops "in the YAML frontmatter" qualifier). Source is canonical.

2. **hooks.json** (`plugins/summarizer/hooks/hooks.json`) — Hook prompt is a 1,147-character string specifying exact validation logic per format. Any paraphrase would lose format-specific required fields or fidelity check items.

3. **structured.md** (`plugins/summarizer/skills/summarizer/templates/structured.md`) — Template defines exact YAML frontmatter field names (`word_count_source`, `compression_ratio`, `confidence_notes`). Field names must be verbatim for agent output to pass the SubagentStop hook validation.

4. **plugin_validator.py** — Token threshold constants (`TOKEN_WARNING_THRESHOLD`, `TOKEN_ERROR_THRESHOLD`) are defined only in the script source. Documentation must not hardcode numeric values — only reference the constant names.

5. **doc-drift-auditor** (development-harness) — Output format block uses specific structural tokens (`STATUS: DONE`, `ARTIFACTS:`, `RISKS:`, `NOTES:`). The-rewrite-room workflow that invokes this agent must pattern-match against these exact tokens.

---

## Critical Findings from Content Fidelity Audit

The following issues were found in the existing `plugins/the-rewrite-room/` implementation and must be corrected during rebuild:

1. **routing-rules.yaml trigger keywords** (Check 4 — INVENTED): The keyword list was fabricated without any source. Agent descriptions contain no triggers section. Keywords are semantically plausible but unverified.

2. **add-doc-updater-adapter.md phase count** (Check 6 — MISMATCH): Claims "5-phase workflow" but actual SKILL.md has 6 phases (Phase 0 through Phase 5). Any workflow documentation must say "6-phase (Phase 0-5)".

3. **fidelity-rules.md content** (Check 1 — ADAPTED): The rewrite-room's copy of fidelity-rules.md drops Rule 5 item 6, removes "Ambiguous/unclear" from Rule 4's confidence table, drops "in the YAML frontmatter" from Rule 6. Use source verbatim or link to source.
