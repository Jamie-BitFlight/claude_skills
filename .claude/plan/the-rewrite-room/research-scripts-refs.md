# Scripts, References, Templates & Research Inventory

## Scripts

### plugin_validator.py
- Path: plugins/plugin-creator/scripts/plugin_validator.py
- Language: Python (PEP 723)
- Invocation: `uv run plugins/plugin-creator/scripts/plugin_validator.py <path> [--fix] [--check] [--verbose] [--no-color]`
- Purpose: Comprehensive plugin validation with token-based complexity measurement. Validates frontmatter schema (skills, agents, commands), plugin structure, skill complexity via tiktoken, internal links, and progressive disclosure structure.
- Inputs: Path to plugin directory, individual SKILL.md, agent .md, or command .md file; flags --fix, --check, --verbose, --no-color
- Outputs: Validation report with error codes; auto-fixes YAML arrays to comma-separated strings, multiline descriptions, unquoted colons, removes name: from plugin skills
- Validators: YES — primary plugin validation tool; token thresholds TOKEN_WARNING_THRESHOLD (SK006) and TOKEN_ERROR_THRESHOLD (SK007) defined as constants within the script

### validate_frontmatter.py
- Path: plugins/plugin-creator/scripts/validate_frontmatter.py
- Language: Python (PEP 723)
- Invocation: `uv run plugins/plugin-creator/scripts/validate_frontmatter.py <path>`
- Purpose: Validate and fix YAML frontmatter in Claude Code capability files (SKILL.md, agent .md). Subset of plugin_validator.py focused on frontmatter only.
- Inputs: Path to markdown file or directory
- Outputs: Validation report, optional auto-fix of frontmatter issues
- Validators: YES

### normalize_frontmatter.py
- Path: plugins/plugin-creator/scripts/normalize_frontmatter.py
- Language: Python (PEP 723)
- Invocation: `uv run plugins/plugin-creator/scripts/normalize_frontmatter.py <path>`
- Purpose: Normalize YAML frontmatter quoting by round-tripping through ruamel.yaml. Removes unnecessary quotes, preserves file body verbatim.
- Inputs: Path to markdown file or directory containing frontmatter
- Outputs: Normalized markdown files (in-place)
- Validators: NO — normalizer/formatter only

### Retired tool-format fixer
- Historical purpose: The deleted `fix_tool_formats.py` script scanned Claude capability files and converted YAML or JSON tool lists to comma-separated strings.
- Status: Removed after runtime-specific tool formats replaced the blanket conversion rule. This entry records the former inventory item; there is no current executable or invocation.

### auto_sync_manifests.py
- Path: plugins/plugin-creator/scripts/auto_sync_manifests.py
- Language: Python (stdlib only, no PEP 723 deps)
- Invocation: `uv run plugins/plugin-creator/scripts/auto_sync_manifests.py` (pre-commit mode) or `--reconcile [--dry-run]` (reconcile mode)
- Purpose: Maintain plugin.json and marketplace.json automatically. Pre-commit mode detects CRUD operations on staged changes and bumps semantic versions. Reconcile mode does full filesystem scan for drift detection.
- Inputs: Git staged changes (pre-commit mode) or full filesystem (reconcile mode)
- Outputs: Updated plugin.json and marketplace.json with correct component lists and bumped versions; auto-staged for commit
- Validators: YES — manifest sync and drift detection

### frontmatter_utils.py
- Path: plugins/plugin-creator/scripts/frontmatter_utils.py
- Language: Python (shared utility module, not executable)
- Invocation: Imported as module: `from frontmatter_utils import load_frontmatter, dump_frontmatter`
- Purpose: Shared frontmatter utilities backed by ruamel.yaml. Provides load/dump for YAML frontmatter files with round-trip handler that preserves formatting and only adds quotes where syntax demands them.
- Inputs: File path or string containing YAML frontmatter
- Outputs: Parsed Post objects; serialized frontmatter strings; in-place file updates
- Validators: NO — shared utility library

### create_plugin.py
- Path: plugins/plugin-creator/scripts/create_plugin.py
- Language: Python (PEP 723)
- Invocation: `uv run plugins/plugin-creator/scripts/create_plugin.py`
- Purpose: Interactive plugin scaffolding. Creates .claude-plugin/ directory with plugin.json, optional skills/ and agents/ directories, template files for each component type.
- Inputs: Interactive prompts (plugin name, description, author)
- Outputs: Scaffolded plugin directory structure with validated plugin.json
- Validators: NO — scaffold/creation tool; runs claude plugin validate internally

### validate_glfm.py
- Path: plugins/gitlab-skill/skills/gitlab-skill/scripts/validate_glfm.py
- Language: Python (PEP 723, requires httpx)
- Invocation: `./validate_glfm.py --file <path>` or `./validate_glfm.py --markdown "# Text"`
- Purpose: Validate GitLab Flavored Markdown rendering by calling the GitLab markdown API. Confirms GLFM-specific syntax (alerts, collapsibles) renders correctly before committing.
- Inputs: --file <path> to a markdown file, or --markdown "string" for inline validation; GITLAB_TOKEN from environment
- Outputs: Rendered HTML output or validation errors from GitLab API
- Validators: YES

### sync_gitlab_docs.py
- Path: plugins/gitlab-skill/skills/gitlab-skill/scripts/sync_gitlab_docs.py
- Language: Python (PEP 723, requires httpx, ruamel.yaml)
- Invocation: `uv run plugins/gitlab-skill/skills/gitlab-skill/scripts/sync_gitlab_docs.py [--force]`
- Purpose: Download and update GitLab CI documentation from official repository. Downloads archive, validates extraction, transforms links, removes Hugo shortcodes, generates file tree index, atomically replaces existing documentation.
- Inputs: None (fetches from GitLab's official repo); --force bypasses cooldown
- Outputs: Updated local GitLab CI documentation in skill's references directory
- Validators: NO — documentation synchronizer

### get_gitlab_context.py / gitlab_context.py
- Path: plugins/gitlab-skill/skills/gitlab-skill/scripts/get_gitlab_context.py and gitlab_context.py
- Language: Python (stdlib only)
- Invocation: Used as dynamic injection context script by the skill
- Purpose: Get GitLab CI/CD context for dynamic injection. Runs glab commands to extract current project state for skill context.
- Inputs: Current git repo (reads .gitlab-ci.yml)
- Outputs: JSON context for skill injection
- Validators: NO — context extraction

### file_metrics.py
- Path: plugins/summarizer/scripts/file_metrics.py
- Language: Python (stdlib only, no external deps)
- Invocation: `python file_metrics.py <file_path> [--excerpt-lines N] [--json]`
- Purpose: Cross-platform file metrics for summarization strategy selection. Provides word count, line count, character count, file type detection, and excerpt extraction.
- Inputs: File path; optional --excerpt-lines N, --json flag
- Outputs: Human-readable metrics (default) or JSON object with all metrics
- Validators: NO — metrics extraction tool

### lint_orchestrator.py
- Path: plugins/holistic-linting/skills/holistic-linting/scripts/lint_orchestrator.py
- Language: Python (PEP 723, requires typer)
- Invocation: `uv run plugins/holistic-linting/skills/holistic-linting/scripts/lint_orchestrator.py [files...]`
- Purpose: Run project linters based on CLAUDE.md LINTERS configuration. Reads LINTERS section from CLAUDE.md, matches file patterns to tools, executes formatters and linters in correct order with aggregated results.
- Inputs: File paths (optional); reads CLAUDE.md LINTERS section for tool configuration
- Outputs: Aggregated lint results with pass/fail per tool
- Validators: YES — linting orchestrator

### discover_linters.py
- Path: plugins/holistic-linting/skills/holistic-linting/scripts/discover_linters.py
- Language: Python (PEP 723, requires typer, tomlkit, ruamel.yaml)
- Invocation: `uv run plugins/holistic-linting/skills/holistic-linting/scripts/discover_linters.py`
- Purpose: Discover project linters by scanning configuration files (pyproject.toml, .pre-commit-config.yaml, etc.) and generate a standardized LINTERS section for CLAUDE.md.
- Inputs: None (scans current project)
- Outputs: LINTERS section text for insertion into CLAUDE.md
- Validators: NO — discovery and documentation generator

### detect_hook_tool.py
- Path: plugins/holistic-linting/skills/holistic-linting/scripts/detect_hook_tool.py
- Language: Python (stdlib only)
- Invocation: `python detect_hook_tool.py`
- Purpose: Detect and run git hook tool (prek or pre-commit). Reads .git/hooks/pre-commit to determine which tool generated it; falls back to prek.
- Inputs: None (reads .git/hooks/pre-commit)
- Outputs: Detected tool name (prek or pre-commit)
- Validators: NO — tool detection utility

### validate_pep723.py
- Path: plugins/python3-development/scripts/validate_pep723.py
- Language: Python (PEP 723, requires typer)
- Invocation: `uv run plugins/python3-development/scripts/validate_pep723.py <path> [--fix]`
- Purpose: Validate Python shebang compliance using 4-rule decision system. Checks PEP 723 compliance, execute bits, and provides auto-fix capabilities.
- Inputs: Path to Python script file or directory
- Outputs: Validation report; auto-fix corrects shebang and PEP 723 metadata if --fix specified
- Validators: YES

### split_task_file.py
- Path: plugins/python3-development/scripts/split_task_file.py
- Language: Python (PEP 723, requires typer, ruamel.yaml)
- Invocation: `uv run plugins/python3-development/scripts/split_task_file.py <input-file> [output-directory]`
- Purpose: Split multi-task markdown file into one-task-per-file directory structure. Converts YAML frontmatter or legacy markdown task format into individual task files.
- Inputs: Path to multi-task markdown file; optional output directory
- Outputs: Directory of individual task files, one per task
- Validators: NO — format transformation tool

### migrate_task_format.py
- Path: plugins/python3-development/scripts/migrate_task_format.py
- Language: Python (PEP 723, requires typer, ruamel.yaml)
- Invocation: `uv run plugins/python3-development/scripts/migrate_task_format.py <path> [--dry-run]`
- Purpose: Migrate task files from markdown format to YAML frontmatter format, preserving all metadata and content.
- Inputs: Path to task file or directory; --dry-run flag
- Outputs: Converted task files in YAML frontmatter format
- Validators: NO — format migration tool

### sync_uv_releases.py
- Path: plugins/python3-development/skills/uv/scripts/sync_uv_releases.py
- Language: Python (PEP 723, requires typer, httpx)
- Invocation: `uv run plugins/python3-development/skills/uv/scripts/sync_uv_releases.py [--force]`
- Purpose: Fetch uv release notes from GitHub Releases API and update SKILL.md documentation. Identifies releases newer than last recorded version, categorizes changes, updates Version Information section.
- Inputs: None (queries GitHub API for astral-sh/uv releases); --force bypasses cooldown
- Outputs: Updated Version Information section in uv SKILL.md
- Validators: NO — documentation updater

### sentiment-score.py
- Path: plugins/agentskill-kaizen/scripts/sentiment-score.py
- Language: Python (PEP 723, requires duckdb, typer, vaderSentiment)
- Invocation: `uv run plugins/agentskill-kaizen/scripts/sentiment-score.py <jsonl-path> [--output CSV]`
- Purpose: Score sentiment of user messages in Claude Code JSONL session transcripts. Runs VADER sentiment analysis on user-authored messages and outputs CSV of per-message scores for time-series analysis.
- Inputs: Path to JSONL session transcript file(s); optional --output for CSV path
- Outputs: CSV with per-message sentiment scores; persists to DuckDB
- Validators: NO — analysis tool

### package_skill.py
- Path: plugins/plugin-creator/skills/skill-creator/scripts/package_skill.py
- Language: Python (stdlib)
- Invocation: `python package_skill.py <path/to/skill-folder> [output-directory]`
- Purpose: Create a distributable .skill file of a skill folder.
- Inputs: Path to skill directory; optional output directory
- Outputs: .skill archive file in output directory
- Validators: NO — packaging tool (note: CLAUDE.md says do not package skills for local use)

### init_skill.py
- Path: plugins/plugin-creator/skills/skill-creator/scripts/init_skill.py
- Language: Python (stdlib)
- Invocation: `init_skill.py <skill-name> --path <path>`
- Purpose: Create a new skill from template at the specified path.
- Inputs: Skill name; --path for destination directory
- Outputs: Scaffolded skill directory with SKILL.md template
- Validators: NO — scaffold tool

### quick_validate.py
- Path: plugins/plugin-creator/skills/skill-creator/scripts/quick_validate.py
- Language: Python (requires ruamel.yaml; no PEP 723 block)
- Invocation: `python quick_validate.py <skill-path>`
- Purpose: Minimal quick validation script for skills. Lighter alternative to plugin_validator.py.
- Inputs: Path to skill SKILL.md or directory
- Outputs: Pass/fail validation result
- Validators: YES — lightweight validator

### install_agents.py
- Path: plugins/holistic-linting/skills/holistic-linting/scripts/install_agents.py
- Language: Python
- Invocation: `python install_agents.py`
- Purpose: Install linting-related agents (inferred from context; docstring not captured)
- Inputs: Not captured
- Outputs: Installed agent files
- Validators: NO

---

## Reference Files

### glfm-syntax.md
- Path: plugins/gitlab-skill/skills/gitlab-skill/references/glfm-syntax.md
- Topic: Complete GitLab Flavored Markdown syntax reference with alert block syntax, collapsible rules, common mistakes, and best practices
- Linked From: gitlab-skill SKILL.md

### pipeline-optimization.md
- Path: plugins/gitlab-skill/skills/gitlab-skill/references/pipeline-optimization.md
- Topic: GitLab CI pipeline optimization patterns
- Linked From: gitlab-skill SKILL.md

### common-patterns.md
- Path: plugins/gitlab-skill/skills/gitlab-skill/references/common-patterns.md
- Topic: Common GitLab CI/CD patterns and examples
- Linked From: gitlab-skill SKILL.md

### gitlab-ci-local-guide.md
- Path: plugins/gitlab-skill/skills/gitlab-skill/references/gitlab-ci-local-guide.md
- Topic: Guide for running GitLab CI locally with gitlab-ci-local tool
- Linked From: gitlab-skill SKILL.md

### doc-updater-template.md
- Path: plugins/plugin-creator/skills/add-doc-updater/references/doc-updater-template.md
- Topic: Workflow template for adding automated documentation updater to skills. Covers workflow phases from load → architect → code review → quality gates → testing → integration. Uses mermaid flowchart.
- Linked From: add-doc-updater SKILL.md

### output-patterns.md
- Path: plugins/plugin-creator/skills/skill-creator/references/output-patterns.md
- Topic: Patterns for producing consistent output from skills — template pattern, strict vs flexible, format specifications. Covers string substitutions and dynamic context injection.
- Linked From: skill-creator SKILL.md

### workflows.md
- Path: plugins/plugin-creator/skills/skill-creator/references/workflows.md
- Topic: Workflow patterns for multi-step skill processes — sequential workflows, parameterized steps, dynamic context injection via backtick commands.
- Linked From: skill-creator SKILL.md

### skill-completeness-checklist.md
- Path: plugins/plugin-creator/skills/audit-skill-completeness/references/skill-completeness-checklist.md
- Topic: Checklist for evaluating whether a skill provides everything an AI agent needs. Covers preparation, context injection, execution protocol, output format, quality gates. Derived from Anthropic's official skills repository patterns.
- Linked From: audit-skill-completeness SKILL.md

### agent-templates.md
- Path: plugins/plugin-creator/skills/agent-creator/references/agent-templates.md
- Topic: Templates for creating Claude Code agents with different role archetypes
- Linked From: agent-creator SKILL.md

### agent-examples.md
- Path: plugins/plugin-creator/skills/agent-creator/references/agent-examples.md
- Topic: Examples of well-formed agent files for reference during creation
- Linked From: agent-creator SKILL.md

### agent-schema.md
- Path: plugins/plugin-creator/skills/agent-creator/references/agent-schema.md
- Topic: Schema reference for agent frontmatter fields (name, description, model, tools, etc.)
- Linked From: agent-creator SKILL.md

### memory-reference.md
- Path: plugins/plugin-creator/skills/memory-and-rules/references/memory-reference.md
- Topic: Reference for Claude Code memory system — MEMORY.md format, project vs user memory, persistence patterns
- Linked From: memory-and-rules SKILL.md

### permissions-reference.md
- Path: plugins/plugin-creator/skills/permissions/references/permissions-reference.md
- Topic: Reference for Claude Code permission modes and tool restrictions
- Linked From: permissions SKILL.md

### workflow-diagram.md
- Path: plugins/plugin-creator/skills/plugin-creator/references/workflow-diagram.md
- Topic: Mermaid workflow diagram for the plugin-creator orchestration process
- Linked From: plugin-creator SKILL.md

### fidelity-rules.md
- Path: plugins/summarizer/skills/summarizer/references/fidelity-rules.md
- Topic: Rules governing all summarization operations. Covers three failure modes (hallucinated content, lossy summary chains, speculation as observation) and five rules: Read Before Summarizing, No Re-Summarization, Exact Counts, Source References, Relay Agent Output.
- Linked From: summarizer SKILL.md

### pre-existing-issues-protocol.md
- Path: plugins/holistic-linting/skills/holistic-linting/references/pre-existing-issues-protocol.md
- Topic: Protocol for handling pre-existing linting issues discovered during sessions
- Linked From: holistic-linting SKILL.md

### improvement-templates.md
- Path: plugins/agentskill-kaizen/skills/kaizen-improvement/references/improvement-templates.md
- Topic: Templates for kaizen improvement proposals derived from transcript analysis
- Linked From: kaizen-improvement SKILL.md

### duckdb-queries.md
- Path: plugins/agentskill-kaizen/skills/transcript-analysis/references/duckdb-queries.md
- Topic: DuckDB query patterns for analyzing Claude Code session transcript data
- Linked From: transcript-analysis SKILL.md

### jsonl-schema.md
- Path: plugins/agentskill-kaizen/skills/transcript-analysis/references/jsonl-schema.md
- Topic: Schema reference for Claude Code JSONL session transcript format
- Linked From: transcript-analysis SKILL.md

### hook-patterns.md
- Path: plugins/agentskill-kaizen/skills/kaizen-improvement/references/hook-patterns.md
- Topic: Patterns for Claude Code hooks as improvement targets
- Linked From: kaizen-improvement SKILL.md

### extraction-patterns.md
- Path: plugins/agentskill-kaizen/skills/meta-inspector/references/extraction-patterns.md
- Topic: Patterns for extracting structured data from Claude Code transcripts
- Linked From: meta-inspector SKILL.md

### type-safety-mypy.md
- Path: plugins/python3-development/skills/python3-development/references/type-safety-mypy.md
- Topic: Type safety patterns using mypy for Python development
- Linked From: python3-development SKILL.md

### exception-handling.md
- Path: plugins/python3-development/skills/python3-development/references/exception-handling.md
- Topic: Exception handling patterns and fail-fast principles for Python
- Linked From: python3-development SKILL.md

### modernization-guide.md
- Path: plugins/python3-development/skills/modernpython/references/modernization-guide.md
- Topic: Guide for modernizing Python code to contemporary standards
- Linked From: modernpython SKILL.md

### cli_reference.md (uv)
- Path: plugins/python3-development/skills/uv/references/cli_reference.md
- Topic: Complete uv CLI command reference
- Linked From: uv SKILL.md

### troubleshooting.md (uv)
- Path: plugins/python3-development/skills/uv/references/troubleshooting.md
- Topic: uv troubleshooting patterns and common errors
- Linked From: uv SKILL.md

### configuration.md (uv)
- Path: plugins/python3-development/skills/uv/references/configuration.md
- Topic: uv configuration options and pyproject.toml integration
- Linked From: uv SKILL.md

### pre-commit-official-docs.md
- Path: plugins/python3-development/skills/pre-commit/references/pre-commit-official-docs.md
- Topic: Official pre-commit documentation reference for hook configuration
- Linked From: pre-commit SKILL.md

### markdown-template.md
- Path: plugins/python3-development/skills/pypi-readme-creator/references/markdown-template.md
- Topic: Markdown template for PyPI README files
- Linked From: pypi-readme-creator SKILL.md

### agent-orchestration references
- Path: plugins/agent-orchestration/skills/agent-orchestration/references/accessing_online_resources.md
- Topic: Patterns for accessing online resources from agent context
- Linked From: agent-orchestration SKILL.md

- Path: plugins/agent-orchestration/skills/agent-orchestration/references/ecosystem-context-patterns.md
- Topic: Patterns for gathering ecosystem context during orchestration
- Linked From: agent-orchestration SKILL.md

### autonomous-refinement-loop-research.md
- Path: plugins/plugin-creator/skills/arl/references/autonomous-refinement-loop-research.md
- Topic: Research on autonomous refinement loop patterns for AI skill improvement
- Linked From: arl SKILL.md

### research-foundations.md
- Path: plugins/verification-gate/skills/verification-gate/references/research-foundations.md
- Topic: Research foundations for verification gate patterns
- Linked From: verification-gate SKILL.md

### failure-patterns.md
- Path: plugins/verification-gate/skills/verification-gate/references/failure-patterns.md
- Topic: Documented failure patterns that the verification gate is designed to catch
- Linked From: verification-gate SKILL.md

---

## Templates

### structured.md
- Path: plugins/summarizer/skills/summarizer/templates/structured.md
- Purpose: Default summarizer output format. Defines required sections (Summary, What Was Found, What Was NOT Found, Uncertain, Sources) and YAML frontmatter metadata fields (source_type, source_path, summarized_at, method, word counts, compression_ratio, confidence, confidence_notes).

### bullets.md
- Path: plugins/summarizer/skills/summarizer/templates/bullets.md
- Purpose: Bullets format template for summarizer output. Requires Key Findings section with inline source references, Not Found section, Uncertain section, and footer with Source/Confidence/access date.

### tldr.md
- Path: plugins/summarizer/skills/summarizer/templates/tldr.md
- Purpose: TL;DR summarizer format. Requires 2-4 sentence paragraph and footer. Low confidence summaries must state so explicitly.

### json.md
- Path: plugins/summarizer/skills/summarizer/templates/json.md
- Purpose: JSON summarizer output format. Requires valid JSON with keys: metadata, summary, findings (with source_ref per item), not_found, uncertain, sources.

### table.md
- Path: plugins/summarizer/skills/summarizer/templates/table.md
- Purpose: Markdown table summarizer format. Requires Finding/Detail/Source/Status columns; Status values must be exactly: Found, Not Found, or Uncertain.

### outline.md
- Path: plugins/summarizer/skills/summarizer/templates/outline.md
- Purpose: Hierarchical outline summarizer format. Mirrors source structure with Not Found and Uncertain sections.

### command-template.md
- Path: plugins/python3-development/commands/development/templates/command-template.md
- Purpose: Template for creating new Claude Code commands in python3-development plugin context.

### feature-task-template.md
- Path: plugins/python3-development/commands/development/templates/feature-task-template.md
- Purpose: Template for feature task files following python3-development workflow conventions.

### test-checklist.md
- Path: plugins/python3-development/commands/testing/templates/test-checklist.md
- Purpose: Checklist template for test planning and validation in python3-development.

### language-manifest-template.md
- Path: plugins/development-harness/templates/language-manifest-template.md
- Purpose: Template for language manifest files defining development harness language configuration.

### sam-task-template.md
- Path: plugins/python3-development/templates/sam-task-template.md
- Purpose: Stateless Agent Methodology (SAM) task template for python3-development workflow tasks.

---

## Research Files

### research/documentation-tools

Files found:
- research/documentation-tools/gitdocify.md
- research/documentation-tools/living-architecture.md

Key content summary:
- **gitdocify.md** (researched 2026-01-31): GitDocify is a commercial SaaS tool that generates README documentation for GitHub repositories using AI. Freemium model, connects GitHub account, outputs professionally formatted READMEs. Hosted on Vercel/Supabase.
- **living-architecture.md** (researched 2026-02-20): Open-source tool (Apache-2.0) by Nick Tune that extracts operational flow-based architecture from code as living documentation using the Rivière schema. Language-agnostic, visualizes operation flows (UI → API → UseCase → DomainOp → Event → EventHandler), includes extraction/modeling/querying/visualization with AI-assisted workflows.

### All Research Directories

```text
research/
├── agent-frameworks/        (agno, ai-agents-frameworks, bmad-method, ra-aid, superpowers, get-shit-done, liteagents, micro-agent)
├── agent-infrastructure/    (plano, zeroclaw)
├── ai-design-tools/         (google-stitch, hedra)
├── ai-observability/        (logfire)
├── ai-research-tools/       (notebooklm, the-unwind-ai)
├── ai-writing-tools/        (type-ai)
├── api-frameworks/          (fastapi, tornado)
├── async-libraries/         (anyio, trio)
├── code-auditing/           (hound)
├── coding-agents/           (openhands, pilot)
├── context-management/      (claude-mem, microsoft-graphrag, local-memory)
├── data-infrastructure/     (tinybird)
├── developer-tooling/       (plannotator, makefile-tutorial)
├── developer-tools/         (git-cliff, repomix, animejs, orbstack, copier-astral, grepai, traycer, niteni, yume, claude-conductor, jscpd, loguru, github-cli, jirajs, kythe, lopaka, claude-quickstarts, claude-openocd-spi-dump, vert)
├── documentation-tools/     (gitdocify, living-architecture)
├── installer-tools/         (installanywhere-specs-collection)
├── llm-infrastructure/      (tensorzero)
├── low-code-platforms/      (tooljet)
├── mcp-ecosystem/           (narsil-mcp, octocode-mcp, docs-mcp-server, mcpjam, mimir-mcp, retio-pagemap, perplexity-mcp-server, browsermcp-mcp)
├── ml-infrastructure/       (ray)
├── python-runtimes/         (rustpython)
├── research-agent-patterns/ (orchestrator-agent-creation-guide, compound-engineering-plugin, claw-loop, github-patterns, ollama-subagents-web-search-claude-code, tinyclaw)
├── rust-python-bindings/    (pyo3)
├── skill-generation-tools/  (skill-seekers, hmohamed-claude-code-plugins, claude-night-market, skillkit, mcpskills-cli, human-compiler, clawhub, codex-skills, claude-skillz, softaworks-agent-toolkit, vercel-labs-skills)
└── task-management/         (claude-task-master)
```

---

## Hooks

### SubagentStop (summarizer)
- Path: plugins/summarizer/hooks/hooks.json
- Matcher: None (applies to all subagents; validates only summarizer agent output via conditional check at end of prompt)
- Purpose: Validate summarizer sub-agent output against the active format template. Identifies format from task parameters (defaults to 'structured'), checks format-specific required sections and fields, checks universal fidelity violations (vague quantifiers, search-limit-as-negative, missing confidence, unsourced content). Returns `{"ok": true}` or `{"ok": false, "reason": "..."}`.
- Event: SubagentStop
- Type: prompt (context-aware LLM validation)
- Timeout: 30 seconds

### SessionStart (dasel)
- Path: plugins/dasel/hooks/hooks.json
- Matcher: None
- Purpose: Check dasel installation status at session start. Runs Node.js script to detect whether dasel binary is available and report status to the session context.
- Event: SessionStart
- Type: command
- Command: `node "${CLAUDE_PLUGIN_ROOT}/hooks/session-start-dasel-check.cjs"`
- Timeout: 10 seconds
