# Agent Inventory

Total agents discovered: 57

---

## bash-script-auditor

- Path: plugins/bash-development/agents/bash-script-auditor.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: blue
- Skills: bash-development, bash-portability, bash-lint, bash-testing
- Purpose: Audits bash scripts for correctness, portability, and quality. Reviews against bash 5.1+ standards and POSIX compatibility requirements.
- Triggers: When bash scripts need security/quality review; after bash-script-developer produces output
- Inputs: Bash script files, task files describing what to audit
- Outputs: Audit report with severity-rated issues (Critical/Warning/Suggestion); follow-up task files
- Validators: bash-lint skill gates; subagent-contract DONE/BLOCKED pattern

---

## bash-script-developer

- Path: plugins/bash-development/agents/bash-script-developer.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Color: yellow
- Skills: bash-development, bash-portability, bash-logging, bash-lint
- Purpose: Writes production-quality bash scripts using bash 5.1+ features and POSIX portability conventions. Applies bash-development skill standards.
- Triggers: When new bash scripts need to be created; when existing scripts need refactoring to meet standards
- Inputs: Feature requirements, existing script files to modify
- Outputs: Bash script files with proper shebangs, logging, error handling
- Validators: bash-lint skill; portability checks

---

## perl-cli-architect

- Path: plugins/perl-development/agents/perl-cli-architect.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: purple
- Purpose: Designs and implements Perl CLI tools using modern Perl idioms. Focuses on CPAN ecosystem, command-line argument parsing, and idiomatic Perl patterns.
- Triggers: When Perl CLI tools need to be built or refactored
- Inputs: Feature specifications, existing Perl files
- Outputs: Perl CLI scripts, module files
- Validators: Perl::Critic, perlcritic checks

---

## perl-script-developer

- Path: plugins/perl-development/agents/perl-script-developer.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: pink
- Purpose: Implements Perl scripts using best practices. Handles CPAN dependency management and Perl-specific idioms.
- Triggers: When Perl scripts need to be written or enhanced
- Inputs: Task files, specifications
- Outputs: Perl script files
- Validators: (plugin defaults)

---

## perl-script-auditor

- Path: plugins/perl-development/agents/perl-script-auditor.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: orange
- Purpose: Audits Perl scripts for correctness, security, and Perl best practices. Reviews against perlcritic standards.
- Triggers: After perl-script-developer or perl-cli-architect produces output; on-demand code review
- Inputs: Perl script files, audit task descriptions
- Outputs: Audit report with issue severity ratings
- Validators: perlcritic; Perl::Critic

---

## feature-researcher (python3-development)

- Path: plugins/python3-development/agents/feature-researcher.md
- Tools: Read, Grep, Glob, Write, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__exa__get_code_context_exa, mcp__sequential_thinking__sequentialthinking
- Model: (not specified)
- permissionMode: acceptEdits
- Color: cyan
- Skills: subagent-contract
- Purpose: Researches feature requirements and prior art before implementation. Gathers context from codebase and official documentation to inform planning decisions.
- Triggers: At S1 Discovery stage; when a feature needs research before planning begins
- Inputs: Feature description, codebase paths to investigate, documentation URLs
- Outputs: Research report written to file; DONE/BLOCKED status block
- Validators: subagent-contract DONE/BLOCKED pattern

---

## doc-drift-auditor (python3-development)

- Path: plugins/python3-development/agents/doc-drift-auditor.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- permissionMode: acceptEdits
- Color: orange
- Skills: subagent-contract
- Purpose: Audits documentation versus code drift using git forensics. Categorizes findings as implemented-but-undocumented, documented-but-unimplemented, outdated, or mismatched.
- Triggers: After significant code changes; before releases; when documentation accuracy is in question
- Inputs: Code files, documentation files, git history
- Outputs: Documentation drift audit report with evidence citations (file:line, commit SHA)
- Validators: subagent-contract DONE/BLOCKED pattern

---

## context-gathering (python3-development)

- Path: plugins/python3-development/agents/context-gathering.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: cyan
- Skills: subagent-contract
- Purpose: Creates comprehensive context manifests for task files. Reads the entire codebase relevant to a task and writes verbose narrative paragraphs plus technical reference sections.
- Triggers: Before implementation begins; when a task needs deep context about the codebase
- Inputs: Task file path, codebase paths relevant to the task
- Outputs: Context manifest appended to specified task file only
- Validators: subagent-contract DONE/BLOCKED pattern

---

## ecosystem-researcher (python3-development)

- Path: plugins/python3-development/agents/ecosystem-researcher.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- permissionMode: plan
- Color: blue
- Skills: subagent-contract
- Purpose: Researches external dependencies, libraries, and ecosystem options before implementation. Evaluates tradeoffs and recommends appropriate packages.
- Triggers: When choosing between library options; when a task involves unfamiliar external dependencies
- Inputs: Research question, dependency names, official documentation URLs
- Outputs: Ecosystem research report with recommendations; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## context-refinement (python3-development)

- Path: plugins/python3-development/agents/context-refinement.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: purple
- Skills: subagent-contract
- Purpose: Checks if context has drifted or new discoveries were made during implementation. Updates task context manifests with session discoveries.
- Triggers: During context compaction; at session end; when implementation reveals surprises that change system understanding
- Inputs: Task file, transcript files at sessions/transcripts/context-refinement/
- Outputs: Updated context manifest in task file; "No context updates needed" if unchanged
- Validators: subagent-contract DONE/BLOCKED pattern

---

## ecosystem-researcher-v1.1-rt-ica (python3-development)

- Path: plugins/python3-development/agents/ecosystem-researcher-v1.1-rt-ica.md
- Tools: Read, Grep, Glob, Write, WebSearch, WebFetch, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__exa__get_code_context_exa, mcp__sequential_thinking__sequentialthinking
- Model: sonnet
- permissionMode: acceptEdits
- Color: purple
- Purpose: Enhanced ecosystem researcher with RT-ICA pre-check pattern. Performs Reverse Thinking Information Completeness Assessment before beginning research to ensure all required inputs are available.
- Triggers: When choosing between library options; when task involves external dependencies requiring thorough research
- Inputs: Research question, RT-ICA checklist completion, documentation URLs
- Outputs: RT-ICA assessment + ecosystem research report + recommendations
- Validators: RT-ICA pre-check; subagent-contract DONE/BLOCKED pattern

---

## code-reviewer (python3-development)

- Path: plugins/python3-development/agents/code-reviewer.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- permissionMode: acceptEdits
- Color: yellow
- Skills: subagent-contract, python3-development, python3-development:validation-protocol, holistic-linting
- Purpose: Post-implementation code review. Does NOT fix issues directly — creates follow-up task files for discovered issues (naming: tasks-{N}-{feature-slug}-followup-{issue-number}.md).
- Triggers: After python-cli-architect or python-pytest-architect completes; at S6 Forensic Review stage
- Inputs: Implemented code files, task file with acceptance criteria
- Outputs: Review report + follow-up task files for unresolved issues; DONE/BLOCKED status block with artifact counts
- Validators: validation-protocol skill; holistic-linting skill; subagent-contract DONE/BLOCKED pattern

---

## python-cli-architect

- Path: plugins/python3-development/agents/python-cli-architect.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- permissionMode: bypassPermissions
- Color: pink
- Purpose: Creates and enhances Python CLIs using Typer and Rich. Uses modern Python 3.11+ patterns including Annotated syntax, async processing, and Rich components. Project structure: packages/{package_name}/ (never src/).
- Triggers: DEFAULT for ALL Python implementation. When Python code needs to be written, refactored, or enhanced.
- Inputs: Feature specification, existing Python files, task files
- Outputs: Python CLI source files; passes ruff format, ruff check, tests (80% coverage minimum)
- Validators: ruff format → ruff check → pytest (>80% coverage)

---

## python-cli-design-spec

- Path: plugins/python3-development/agents/python-cli-design-spec.md
- Tools: Read, Write, Glob, Grep, mcp__ref__*, mcp__exa__*, TodoWrite, mcp__sequential-thinking__*
- Model: (not specified)
- Purpose: Architecture specs only — WHAT to build, not HOW. Produces C4 diagrams, technology stack recommendations, testing architecture patterns, and ADRs. Does NOT write implementation code.
- Triggers: Before implementation begins; when a feature needs architectural planning
- Inputs: Feature requirements, existing codebase state
- Outputs: architecture.md with C4 diagrams, component designs, testing strategy, ADRs
- Validators: (none specified — output is reviewed by orchestrator before implementation begins)

---

## python-code-reviewer

- Path: plugins/python3-development/agents/python-code-reviewer.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: yellow
- Purpose: Code quality review using /python-check-codesmells and /python3-development:modernpython slash commands. Outputs smell reports and modernization recommendations to .claude/smells/.
- Triggers: When code quality analysis is requested; as part of post-implementation review
- Inputs: Python source files to review
- Outputs: .claude/smells/{filename}.smells.{timestamp}.md; .claude/smells/{filename}.modernization.{timestamp}.md
- Validators: python-check-codesmells slash command; modernpython slash command

---

## python-pytest-architect

- Path: plugins/python3-development/agents/python-pytest-architect.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: pink
- Purpose: Creates pytest test suites. Mandatory pytest-mock (never unittest.mock); AAA pattern; 80% coverage minimum; mutation testing for critical code; hypothesis property-based testing.
- Triggers: When test suites need to be written; at S5 Execution stage for test tasks
- Inputs: Python source files, feature specifications, acceptance criteria
- Outputs: pytest test files; passes ruff format, ruff check, mypy/basedpyright, pytest (>80% coverage)
- Validators: ruff format → ruff check → mypy/basedpyright → pytest (>80% coverage)

---

## swarm-task-planner (python3-development)

- Path: plugins/python3-development/agents/swarm-task-planner.md
- Tools: Read, Write, Glob, Grep, mcp__ref__*, mcp__exa__*, TodoWrite, mcp__sequential-thinking__*
- Model: sonnet
- user-invocable: true
- Skills: clear-cove-task-design
- Purpose: Creates dependency-based task plans for parallel AI agent execution. Transforms architecture docs and PRDs into priority-ordered tasks with acceptance criteria, sync checkpoints, and quality gates. Uses CLEAR+CoVe standard. NOT for human project management (no sprints/weeks/Gantt).
- Triggers: When a feature needs to be decomposed for parallel agent execution; when architecture.md exists and needs an execution plan
- Inputs: Architecture documents, PRDs, feature briefs
- Outputs: PLAN.md (<500 lines) or PLAN/ directory (>=500 lines); optional TASK/ directory for per-task worker prompts
- Validators: CLEAR lint; YAML frontmatter completeness; CoVe question quality (when accuracy-risk medium/high)

---

## image-summarizer

- Path: plugins/summarizer/agents/image-summarizer.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Purpose: Summarizes image content using multimodal capabilities. Extracts and describes visual information from images.
- Triggers: When images need to be described or summarized for downstream use
- Inputs: Image files (PNG, JPG, etc.)
- Outputs: Text summary of image content
- Validators: (none specified)

---

## url-summarizer

- Path: plugins/summarizer/agents/url-summarizer.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Purpose: Fetches and summarizes content from URLs. Extracts key information from web pages and online documents.
- Triggers: When URLs need to be summarized for downstream use or research
- Inputs: URLs
- Outputs: Text summary of URL content with source reference
- Validators: (none specified)

---

## file-summarizer

- Path: plugins/summarizer/agents/file-summarizer.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Purpose: Summarizes file content from the repository or filesystem. Extracts key information from documents for downstream use.
- Triggers: When files need to be summarized for downstream use; files >5000 chars per summarization rules
- Inputs: File paths
- Outputs: Text summary of file content with source reference
- Validators: (none specified)

---

## feature-researcher (development-harness)

- Path: plugins/development-harness/agents/feature-researcher.md
- Tools: Read, Grep, Glob, Write, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__exa__get_code_context_exa, mcp__sequential_thinking__sequentialthinking
- Model: (not specified)
- permissionMode: acceptEdits
- Color: cyan
- Skills: subagent-contract
- Purpose: Researches feature requirements and prior art at S1 Discovery stage. Gathers context from codebase and official documentation to inform planning.
- Triggers: S1 Discovery stage of development-harness pipeline; when feature needs research before planning
- Inputs: Feature description, codebase paths, documentation URLs
- Outputs: Discovery artifact written to .planning/harness/discovery-{feature}.md; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## codebase-analyzer

- Path: plugins/development-harness/agents/codebase-analyzer.md
- Tools: Read, Bash, Grep, Glob, Write, mcp__git-forensics__analyze_file_changes, mcp__git-forensics__analyze_time_period, mcp__sequential_thinking__sequentialthinking, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__exa__get_code_context_exa
- Model: sonnet
- Skills: subagent-contract
- Color: cyan
- Purpose: Analyzes codebase structure and patterns. Uses git forensics MCP tools to understand code evolution, hotspots, and architectural patterns relevant to a feature.
- Triggers: S1 Discovery or S3 Context Integration stages; when codebase analysis is needed before planning
- Inputs: Feature description, codebase paths, git history scope
- Outputs: Codebase analysis report; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## doc-drift-auditor (development-harness)

- Path: plugins/development-harness/agents/doc-drift-auditor.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- permissionMode: acceptEdits
- Color: orange
- Skills: subagent-contract
- Purpose: Audits documentation versus code drift using git forensics. Categorizes findings as implemented-but-undocumented, documented-but-unimplemented, outdated, or mismatched.
- Triggers: After significant code changes; at S7 Final Verification stage; when documentation accuracy is in question
- Inputs: Code files, documentation files, git history
- Outputs: Documentation drift report with evidence citations; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## ecosystem-researcher (development-harness)

- Path: plugins/development-harness/agents/ecosystem-researcher.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- permissionMode: plan
- Color: blue
- Skills: subagent-contract
- Purpose: Researches external dependencies and ecosystem options for a feature. Evaluates library tradeoffs and recommends appropriate packages for the development-harness pipeline.
- Triggers: S1 Discovery or S2 Planning stages; when choosing between library options
- Inputs: Research question, dependency names, official documentation URLs
- Outputs: Ecosystem research report written to .planning/harness/; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## feature-verifier

- Path: plugins/development-harness/agents/feature-verifier.md
- Tools: Read, Write, Edit, Bash, Grep, Glob, mcp__sequential_thinking__sequentialthinking, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__exa__get_code_context_exa
- Model: opus
- Skills: subagent-contract, development-harness, development-harness:validation-protocol
- Color: green
- Purpose: Verifies feature meets original acceptance criteria at S7 Final Verification stage. Runs 3-level verification (Existence, Substantive, Wired). Uses opus for higher-stakes final verification.
- Triggers: S7 Final Verification stage; when feature is considered complete and needs certification
- Inputs: Original feature requirements, all S1-S6 artifacts, implemented code
- Outputs: Verification certificate at .planning/harness/verification-{feature}.md; DONE/BLOCKED status
- Validators: validation-protocol skill; development-harness 3-level verification; subagent-contract DONE/BLOCKED pattern

---

## integration-checker

- Path: plugins/development-harness/agents/integration-checker.md
- Tools: Read, Bash, Grep, Glob, mcp__git-forensics__analyze_file_changes, mcp__sequential_thinking__sequentialthinking, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__exa__get_code_context_exa
- Model: (not specified)
- Skills: subagent-contract, development-harness:validation-protocol
- Color: blue
- Purpose: Checks integration points and compatibility between components. Verifies that new code integrates correctly with existing systems at S6 Forensic Review stage.
- Triggers: S6 Forensic Review stage; after implementation tasks complete; when integration risk is identified
- Inputs: Implemented code, integration point descriptions, existing system interfaces
- Outputs: Integration check report; DONE/BLOCKED status
- Validators: validation-protocol skill; subagent-contract DONE/BLOCKED pattern

---

## context-gathering (development-harness)

- Path: plugins/development-harness/agents/context-gathering.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: cyan
- Skills: subagent-contract
- Purpose: Creates comprehensive context manifests for development-harness task files. Gathers context from codebase relevant to current stage artifact.
- Triggers: Before execution stages; when tasks need deep codebase context
- Inputs: Task file path, codebase paths
- Outputs: Context manifest appended to task file; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## context-refinement (development-harness)

- Path: plugins/development-harness/agents/context-refinement.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: purple
- Skills: subagent-contract
- Purpose: Updates context manifests in development-harness artifacts when implementation reveals surprises or new discoveries.
- Triggers: At stage transitions; when implementation reveals information that changes system understanding
- Inputs: Current stage artifact, transcript files
- Outputs: Updated context in artifact file; "No context updates needed" if unchanged; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## plan-validator

- Path: plugins/development-harness/agents/plan-validator.md
- Tools: Read, Grep, Glob, Bash, mcp__sequential_thinking__sequentialthinking, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__exa__get_code_context_exa
- Model: opus
- Skills: subagent-contract
- Color: green
- Purpose: Validates plans for completeness and feasibility at S3 Context Integration stage. Uses opus for rigorous plan assessment. Checks plan against actual codebase state.
- Triggers: S3 Context Integration stage; after S2 Planning produces a plan artifact
- Inputs: Plan artifact from S2, codebase state
- Outputs: Validation report; approved or rejected plan with required changes; DONE/BLOCKED status
- Validators: subagent-contract DONE/BLOCKED pattern

---

## swarm-task-planner (development-harness)

- Path: plugins/development-harness/agents/swarm-task-planner.md
- Tools: Read, Write, Glob, Grep, mcp__ref__*, mcp__exa__*, TodoWrite, mcp__sequential-thinking__*
- Model: sonnet
- Skills: clear-cove-task-design
- Purpose: Decomposes features into parallel task streams at S4 Task Decomposition stage. Creates CLEAR+CoVe formatted task files for worker agent execution.
- Triggers: S4 Task Decomposition stage; when a plan needs to be broken into executable worker tasks
- Inputs: Plan artifact from S2/S3, language manifest for agent role mapping
- Outputs: Task files at .planning/harness/task-{N}-{slug}.md; DONE/BLOCKED status
- Validators: CLEAR lint; YAML frontmatter completeness; CoVe question quality

---

## service-docs-maintainer

- Path: plugins/development-harness/agents/service-docs-maintainer.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: yellow
- memory: project
- Purpose: Synchronizes documentation with code changes. Use after implementing features, refactoring, deleting files, changing APIs, or modifying configurations. Triggers include new endpoints, refactored modules, deleted files, changed configs, or session-end sweeps.
- Triggers: After implementing features; after refactoring; after deleting files; when APIs or configurations change; at session end to sweep all affected docs
- Inputs: Description of code changes; git diff output; list of affected files
- Outputs: Updated documentation files (markdown, docstrings, comments); summary of what was changed and why; list of files examined but skipped
- Validators: Quality gates: every deleted file has zero remaining references; every renamed symbol has updated references everywhere; no code snippets in docs (file path references only); no contradictions between docs and code

---

## improvement-generator

- Path: plugins/agentskill-kaizen/agents/improvement-generator.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: yellow
- Skills: kaizen-improvement
- Purpose: Transforms transcript analysis findings into concrete improvement proposals for skills and agents. Takes improvement opportunities identified by transcript-analyst and produces actionable recommendations.
- Triggers: After transcript-analyst produces analysis output; when kaizen improvement cycle needs proposals
- Inputs: Transcript analysis report from transcript-analyst; existing skill/agent files to improve
- Outputs: Improvement proposals with before/after diffs; prioritized list of recommended changes
- Validators: kaizen-improvement skill gates

---

## transcript-analyst

- Path: plugins/agentskill-kaizen/agents/transcript-analyst.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: cyan
- Skills: transcript-analysis
- Purpose: Analyzes Claude Code session transcripts using DuckDB SQL queries against JSONL transcript files. Extracts patterns, identifies friction points, and surfaces improvement opportunities.
- Triggers: When kaizen analysis cycle begins; when session transcripts need pattern analysis
- Inputs: JSONL transcript files; DuckDB queries defined by transcript-analysis skill
- Outputs: Transcript analysis report with discovered patterns, friction points, and improvement opportunities
- Validators: transcript-analysis skill gates

---

## dasel-guide

- Path: plugins/dasel/agents/dasel-guide.md
- Tools: Read, Grep, Glob
- Model: haiku
- Color: yellow
- Purpose: Provides dasel v3 selector syntax guidance. Lightweight reference agent using haiku for cost efficiency. Answers questions about dasel query construction.
- Triggers: When dasel selector syntax help is needed; when constructing dasel queries
- Inputs: Questions about dasel syntax; structured data files (JSON, YAML, TOML, CSV, XML)
- Outputs: Dasel query examples and explanations; corrected selector syntax
- Validators: (none specified — advisory agent)

---

## data-analyst

- Path: plugins/dasel/agents/data-analyst.md
- Tools: Read, Bash, Write, Edit, Grep, Glob
- Model: sonnet
- Color: cyan
- Purpose: Performs complex data analysis and transformation using dasel v3. Runs dasel commands via Bash and writes transformed output to files.
- Triggers: When structured data needs to be analyzed, transformed, or extracted using dasel
- Inputs: Structured data files (JSON, YAML, TOML, CSV, XML); transformation requirements
- Outputs: Transformed data files; analysis reports; dasel command scripts
- Validators: dasel command success; output file validation

---

## data-explorer

- Path: plugins/dasel/agents/data-explorer.md
- Tools: Read, Grep, Glob, Bash
- Model: haiku
- Color: green
- Purpose: Lightweight data exploration using dasel v3. Uses haiku for cost-efficient read-only exploration and discovery of data structure.
- Triggers: When data structure needs to be understood before transformation; when exploring unfamiliar structured files
- Inputs: Structured data files; exploration questions
- Outputs: Data structure descriptions; field listings; sample values
- Validators: (none specified — read-only exploration agent)

---

## linting-root-cause-resolver

- Path: plugins/holistic-linting/agents/linting-root-cause-resolver.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: orange
- Purpose: Resolves linting errors by finding and fixing root causes rather than suppressing warnings. Audits all changed files for the same pattern when a linting issue is found.
- Triggers: When linting errors block a commit or CI run; when holistic-linting skill is activated for error resolution
- Inputs: Linting error output; source files with errors
- Outputs: Fixed source files; root cause analysis of linting errors
- Validators: Configured linters (ruff, mypy, etc.) pass after fix; no inline suppression comments added

---

## post-linting-architecture-reviewer

- Path: plugins/holistic-linting/agents/post-linting-architecture-reviewer.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: yellow
- Purpose: Reviews architectural implications of linting fixes. After linting errors are resolved, identifies if the patterns revealed deeper architectural issues needing refactoring.
- Triggers: After linting-root-cause-resolver completes; when linting fixes reveal systemic architectural problems
- Inputs: Linting fix diff; source files post-fix
- Outputs: Architectural review report with recommendations for systemic improvements
- Validators: (none specified — advisory output)

---

## agent-creator

- Path: plugins/plugin-creator/agents/agent-creator.md
- Tools: Read, Write, Edit, Grep, Glob, Bash, Task
- Model: sonnet
- Color: green
- Skills: plugin-creator:claude-plugins-reference-2026, claude-hooks-reference-2026, claude-skills-overview-2026, agent-creator
- Purpose: Creates high-quality Claude Code agent files following Anthropic best practices. Produces agent frontmatter, system prompts, and validates output against plugin schema.
- Triggers: When a new agent definition file needs to be created; when an existing agent needs to be refactored to meet standards
- Inputs: Agent requirements description; plugin directory path; existing agent files to reference
- Outputs: New or updated agent .md file with valid YAML frontmatter and system prompt
- Validators: plugin-creator:lint; frontmatter schema validation; claude-plugins-reference-2026 standards

---

## hook-creator

- Path: plugins/plugin-creator/agents/hook-creator.md
- Tools: Read, Write, Edit, Grep, Glob, Bash
- Model: sonnet
- Color: blue
- Skills: plugin-creator:claude-hooks-reference-2026, hooks-core-reference, hooks-io-api, hooks-patterns, hook-creator
- Purpose: Creates Claude Code hook scripts following official hook patterns. Handles PreToolUse, PostToolUse, PreCompact, PostCompact, Notification, Stop, SubagentStop, and UserPromptSubmit hook types.
- Triggers: When a new hook needs to be created; when hook logic needs to be added to a plugin
- Inputs: Hook requirements, event type, desired behavior
- Outputs: Hook script files (JavaScript for Claude Code hooks); hooks.json configuration
- Validators: hooks-io-api schema compliance; hooks-core-reference patterns

---

## plugin-assessor (plugin-creator)

- Path: plugins/plugin-creator/agents/plugin-assessor.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Skills: claude-skills-overview-2026, claude-plugins-reference-2026, claude-hooks-reference-2026
- Purpose: Deep structural analysis of Claude Code plugins. Runs 9-phase assessment workflow covering schema compliance, frontmatter quality, reference audit, and cross-references. Generates scored report (0-100).
- Triggers: When plugin needs quality assessment; before publishing or major refactoring; when plugin-creator:assessor skill is activated
- Inputs: Plugin directory path
- Outputs: Plugin Assessment Report with scoring breakdown across 7 components; orphan resolution checklist
- Validators: claude-plugins-reference-2026 schema; plugin validator script

---

## refactor-executor

- Path: plugins/plugin-creator/agents/refactor-executor.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: green
- Purpose: Executes refactoring tasks from .claude/plan/tasks-refactor-{slug}.md. Delegates by task type: SKILL_SPLIT to refactor-skill, AGENT_OPTIMIZE to subagent-refactorer, DOC_IMPROVE to contextual-ai-documentation-optimizer, STRUCTURE_FIX to direct implementation.
- Triggers: When refactoring plan has been produced by refactor-planner; at plugin-creator:implement-refactor skill activation
- Inputs: Refactoring task file at .claude/plan/tasks-refactor-{slug}.md
- Outputs: Execution report with task completion table; task statuses updated in-place in task file
- Validators: refactor-validator agent runs after completion; plugin_validator.py

---

## contextual-ai-documentation-optimizer

- Path: plugins/plugin-creator/agents/contextual-ai-documentation-optimizer.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: yellow
- Skills: prompt-optimization-claude-45, write-frontmatter-description, subagent-contract, plugin-creator:audit-skill-completeness
- Purpose: Optimizes prompts, SKILL.md, and CLAUDE.md files for Claude comprehension. 6-step process: RT-ICA pre-check → analyze → diagnose → apply → compare → CoVe post-check → structural upgrade analysis.
- Triggers: When skill documentation needs optimization; when prompts produce poor AI behavior; during plugin refactoring for DOC_IMPROVE tasks
- Inputs: SKILL.md, CLAUDE.md, or prompt files to optimize
- Outputs: RT-ICA assessment + optimized content + CoVe verification + token impact report; STATUS: DONE or BLOCKED
- Validators: RT-ICA pre-check; CoVe post-check; audit-skill-completeness skill; subagent-contract DONE/BLOCKED pattern

---

## refactor-validator

- Path: plugins/plugin-creator/agents/refactor-validator.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: yellow
- Purpose: Validates plugin refactoring completeness after refactor-executor finishes. Runs plugin_validator.py, checks task completion, verifies structure integrity, confirms regression absence.
- Triggers: After refactor-executor completes all tasks; before declaring plugin refactoring done
- Inputs: Plugin directory, completed refactoring task file
- Outputs: Refactoring Validation Report with score X/100; follow-up tasks for unresolved issues
- Validators: plugin_validator.py execution; task completion verification; structure integrity checks

---

## refactor-planner

- Path: plugins/plugin-creator/agents/refactor-planner.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: cyan
- Purpose: Analyzes plugin structure and creates executable refactoring plans. Categorizes issues as SKILL_SPLIT, AGENT_OPTIMIZE, DOC_IMPROVE, ORPHAN_RESOLVE, or STRUCTURE_FIX. Maps dependencies and identifies parallelization opportunities.
- Triggers: At plugin-creator:refactor-plugin skill activation; when plugin needs structural improvement
- Inputs: Plugin directory path
- Outputs: Refactoring Analysis report with executive summary, issue categorization, task specifications at .claude/plan/tasks-refactor-{slug}.md
- Validators: Issue categorization completeness; task specification completeness

---

## subagent-refactorer

- Path: plugins/plugin-creator/agents/subagent-refactorer.md
- Tools: Read, Write, Edit, Grep, Glob, WebFetch, WebSearch, Skill, SlashCommand, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa, mcp__github__search_code, mcp__sequential_thinking__sequentialthinking, mcp__plugin_episodic-memory_episodic-memory__search, mcp__plugin_episodic-memory_episodic-memory__read
- Model: sonnet
- Color: purple
- Skills: write-frontmatter-description
- Purpose: Refactors Claude agents using official Anthropic prompt engineering best practices (XML tagging, Constitutional AI, Claude 4.x optimization). MUST research official docs first. Uses strategic XML (not full XML conversion).
- Triggers: AGENT_OPTIMIZE tasks in refactoring plans; when agent quality needs to be improved against Anthropic standards
- Inputs: Agent .md file to refactor; Anthropic documentation URLs
- Outputs: Analysis report + refactored agent file + validation checklist; uses official docs as primary source
- Validators: write-frontmatter-description skill; official Anthropic documentation compliance

---

## example-agent

- Path: plugins/plugin-creator/examples/agents/example-agent.md
- Tools: Read, Grep, Glob, WebFetch, WebSearch
- disallowedTools: Bash, Write, Edit
- Model: sonnet
- permissionMode: default
- Color: cyan
- Skills: python3-development, claude-skills-overview-2026
- Hooks: PreToolUse matcher on Read
- Purpose: Reference/demonstration agent showing all available frontmatter fields and capabilities. For documentation only — not for production use.
- Triggers: When developers need a reference for how to structure agent frontmatter
- Inputs: (demonstration only)
- Outputs: (demonstration only)
- Validators: (demonstration only)

---

## code-review (.claude/agents)

- Path: .claude/agents/code-review.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Purpose: Use ONLY when explicitly requested. Reviews code for LLM slop, security vulnerabilities, and performance issues. Focuses on whether code works correctly and safely within the existing system.
- Triggers: ONLY when user explicitly requests a code review — never proactively
- Inputs: Files and line ranges to review, task file, description of recent changes
- Outputs: Code review response with Critical/Warning/Suggestion severity levels (returned as response message, not saved to file)
- Validators: (none specified — advisory output only)

---

## logging (.claude/agents)

- Path: .claude/agents/logging.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Purpose: Consolidates work logs from transcript files at sessions/transcripts/logging/. Cleans up outdated info and removes completed items. Use only during context compaction or task completion.
- Triggers: During context compaction; at task completion when logs need consolidation
- Inputs: Transcript files at sessions/transcripts/logging/
- Outputs: Consolidated log entries; cleaned-up log state
- Validators: MUST NOT touch sessions/state/, current-task.json, or any system state files

---

## context-refinement (.claude/agents)

- Path: .claude/agents/context-refinement.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Purpose: Checks if context drifted or new discoveries were made. Reads transcripts at sessions/transcripts/context-refinement/. Only updates if genuine surprises that change system understanding.
- Triggers: During context compaction; when implementation reveals surprises
- Inputs: Transcript files at sessions/transcripts/context-refinement/
- Outputs: "No context updates needed" or summary of what was added to context
- Validators: (none specified)

---

## context-gathering (.claude/agents)

- Path: .claude/agents/context-gathering.md
- Tools: (not specified in frontmatter)
- Model: (not specified)
- Purpose: Creates verbose, comprehensive context manifests for task files. Reads ENTIRE codebase relevant to a task and writes narrative paragraphs plus technical reference section.
- Triggers: Before implementation begins on a task that needs deep codebase context
- Inputs: Task file path (the ONLY file it may edit), codebase paths relevant to the task
- Outputs: Context manifest appended to specified task file only
- Validators: FORBIDDEN from editing any file other than the specific task file given

---

## plugin-docs-writer

- Path: .claude/agents/plugin-docs-writer.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- permissionMode: acceptEdits
- Skills: claude-skills-overview-2026, claude-plugins-reference-2026, claude-hooks-reference-2026
- Purpose: Generates user-facing README.md for Claude Code plugins. Translates AI-internal behavior into user-observable outcomes. Banned terms list prevents exposing AI internals to human readers.
- Triggers: When a plugin needs user-facing documentation; when README.md is missing or outdated
- Inputs: Plugin directory path; plugin CLAUDE.md, SKILL.md, agent files (to understand behavior)
- Outputs: README.md only (one file per invocation)
- Validators: claude-plugins-reference-2026 README structure; banned terms check

---

## c-systems-programmer

- Path: .claude/agents/c-systems-programmer.md
- Tools: (not specified in frontmatter)
- Model: inherit
- Color: cyan
- Purpose: C and systems programming specialist. Memory management, pointer safety, POSIX APIs, pthreads, embedded systems. Uses Valgrind/GDB for verification. Explains the WHY behind recommendations.
- Triggers: When C code needs to be written, reviewed, or debugged; for systems-level programming tasks
- Inputs: C source files, system programming requirements, debugging artifacts
- Outputs: C source files; Valgrind/GDB diagnostic output; explanations of memory/pointer reasoning
- Validators: Valgrind (zero memory errors); GDB-verified behavior; compiler warnings at -Wall -Wextra

---

## doc-drift-auditor (.claude/agents)

- Path: .claude/agents/doc-drift-auditor.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Color: orange
- Purpose: Audits documentation versus code drift at repository level using git forensics. Categorizes as implemented-but-undocumented, documented-but-unimplemented, outdated, or mismatched. Evidence-based with file:line and commit SHA citations.
- Triggers: When documentation accuracy is questioned; before major releases; after large refactors
- Inputs: Repository root; git history; documentation files; source code files
- Outputs: DOCUMENTATION_DRIFT_AUDIT.md in repository root with evidence citations (file:line, commit SHA)
- Validators: Evidence citations required for all findings; no undocumented claims

---

## research-context-agent

- Path: .claude/agents/research-context-agent.md
- Tools: Read, Write, Edit, Grep, Glob, WebSearch, WebFetch
- Model: sonnet
- Purpose: Cross-references research files with repo skills, agents, hooks, and plugins. Identifies integration opportunities and appends them to research files.
- Triggers: After research files are created by research-curator; when research needs to be connected to existing repo capabilities
- Inputs: Research file paths; repo skill/agent/hook/plugin directories
- Outputs: Integration Opportunities section appended to each research file
- Validators: (none specified — appendix only, does not modify existing content)

---

## javascript-pro

- Path: .claude/agents/javascript-pro.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- memory: project
- Purpose: Modern JavaScript ES2023+/Node.js 20+ specialist. Async patterns, performance optimization, ESM modules. Has persistent agent memory at .claude/agent-memory/javascript-pro/.
- Triggers: When JavaScript code needs to be written, reviewed, or optimized
- Inputs: JavaScript source files, feature requirements
- Outputs: JavaScript source files; passes ESLint + Prettier + >85% test coverage + JSDoc
- Validators: ESLint + Prettier + >85% test coverage + JSDoc

---

## typescript-pro

- Path: .claude/agents/typescript-pro.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- memory: project
- Purpose: TypeScript 5.0+ specialist. Advanced types (conditional, mapped, template literal, discriminated unions, branded types). Type-first development; strict mode always. Has persistent agent memory at .claude/agent-memory/typescript-pro/.
- Triggers: When TypeScript code needs to be written, reviewed, or optimized
- Inputs: TypeScript source files, type definitions, feature requirements
- Outputs: TypeScript source files with strict types; passes tsc --strict + ESLint + >85% test coverage
- Validators: tsc --strict; ESLint; >85% test coverage

---

## research-curator

- Path: .claude/agents/research-curator.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Skills: gh
- Purpose: Creates single research entries for tools and libraries. Three modes: new (create), --rerun (regenerate), --fix (correct errors). Uses MCP tools and gh CLI. Does NOT update README.md, commit, or coordinate batch operations.
- Triggers: When a new tool or library needs a research entry; when an existing research entry needs correction
- Inputs: Tool/library name; category classification; mode flag (new/--rerun/--fix)
- Outputs: Research file at ./research/{category}/{resource-name}.md
- Validators: gh skill for CLI operations; research file structure compliance

---

## backlog-item-groomer

- Path: .claude/agents/backlog-item-groomer.md
- Tools: Glob, Grep, Read
- Model: haiku
- Purpose: Produces context manifests for backlog items. Performs RT-ICA assessment. Finds supporting skills, related agents, prior work, and dependencies. Uses haiku for cost efficiency.
- Triggers: When a backlog item needs grooming before work begins; at backlog grooming sessions
- Inputs: Backlog item text; BACKLOG.md; repo skill and agent files
- Outputs: Context Manifest with RT-ICA summary, supporting skills table, related agents table, dependencies, blockers, suggested first steps

> **NOTE (2026-02-27)**: BACKLOG.md was removed. Backlog items now live in `.claude/backlog/` per-item files; GitHub Issues are the source of truth.
- Validators: RT-ICA assessment completeness; supporting evidence citations

---

## plugin-assessor (.claude/agents)

- Path: .claude/agents/plugin-assessor.md
- Tools: (not specified in frontmatter)
- Model: sonnet
- Skills: claude-skills-overview-2026, claude-plugins-reference-2026, claude-hooks-reference-2026
- Purpose: Deep structural analysis of Claude Code plugins. 9-phase assessment workflow. Validates schema compliance, frontmatter quality, reference audit, and cross-references. Generates scored report (0-100).
- Triggers: When any plugin needs quality assessment; before publishing or major refactoring
- Inputs: Plugin directory path
- Outputs: Plugin Assessment Report with scoring breakdown across 7 components; orphan resolution checklist
- Validators: claude-plugins-reference-2026 schema; plugin validator script; 7-component scoring rubric

---

## User-Global Agents (~/.claude/agents/)

Agents discovered in /home/user/.claude/agents/ not previously inventoried. These are user-global (available in all repos) and not part of any plugin.

---

## gitlab-docs-expert (~/.claude/agents)

- Path: ~/.claude/agents/gitlab-docs-expert.md
- Tools: * (all tools)
- Model: sonnet
- Color: orange
- Purpose: GitLab Flavored Markdown (GLFM) documentation specialist. Extends documentation-expert with GitLab-specific features: GLFM alert blocks (lowercase `[!note]` syntax), collapsible sections, Mermaid diagrams, GitLab references (#issue, !MR, @user), TOC with `[[_TOC_]]`, math expressions, color chips. Includes a validation script at `~/.claude/agents/validate-glfm.py` that calls the GitLab Markdown API to verify rendering.
- Triggers: Creating or reviewing GitLab Wiki pages, README files for GitLab repos, GLFM syntax validation, documentation for GitLab-hosted projects
- Inputs: Documentation requirements, existing markdown files to review or rewrite
- Outputs: GLFM-compliant markdown files with proper lowercase alerts, strategic collapsibles, Mermaid diagrams
- Validators: validate-glfm.py (GitLab Markdown API via `POST /api/v4/markdown`); GLFM quality checklist (alert case, heading hierarchy, TOC for >3 sections)
- Registry workflow: formatting-validation (canonical GLFM agent), authoring (GitLab-specific)

---

## documentation-expert (~/.claude/agents)

- Path: ~/.claude/agents/documentation-expert.md
- Tools: Read, Write, Edit, Grep, Glob, Bash, LS, Task, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
- Model: haiku
- Purpose: User-facing software documentation specialist. Creates user manuals, API docs, tutorials, troubleshooting guides, style guides, and knowledge bases. Explicitly NOT for AI-facing documents (CLAUDE.md, AGENTS.md, system prompts, agent definitions) — those route to prompt-optimization workflow. Uses context7 MCP for documentation patterns and writing standards.
- Triggers: Proactively when software documentation is needed for human readers; user manuals, how-to guides, API documentation, release notes, glossaries
- Inputs: Software description, existing docs to improve, audience specification
- Outputs: User-facing documentation in markdown (user manuals, API docs, tutorials, troubleshooting guides, style guides)
- Validators: (none specified — advisory)
- Registry workflow: authoring (legacy component, user-facing docs)

---

## doc-freshness-guardian (~/.claude/agents)

- Path: ~/.claude/agents/doc-freshness-guardian.md
- Tools: (inherits from caller — not specified)
- Model: inherit
- Color: cyan
- Purpose: Maintains documentation-code synchronization with freshness tracking. Two-phase operation: (1) pre-task discovery — reads relevant docs, checks freshness headers, alerts if >90 days stale; (2) post-task update — adds/updates YAML frontmatter freshness headers (last_updated, last_verified, applies_to_version, related_files, update_required_when). Implements bidirectional sync and cross-reference validation. Freshness indicators: green <30d (quick review), yellow 30-90d (verify against code), red >90d (full review required).
- Triggers: Before and after code modifications; auditing documentation freshness; implementing doc governance; when documentation has drifted from code significantly
- Inputs: Task description, list of files to be modified (to determine which docs are relevant)
- Outputs: Updated documentation files with freshness YAML frontmatter; freshness audit report
- Validators: Cross-reference validation; freshness header completeness
- Registry workflow: drift-audit (legacy component — bidirectional freshness-tracking variant)

---

## service-documentation (~/.claude/agents)

- Path: ~/.claude/agents/service-documentation.md
- Tools: Read, Grep, Glob, LS, Edit, Bash
- Model: inherit
- Color: blue
- Purpose: Updates CLAUDE.md files and module documentation (SKILL.md, references/, agent definitions, Python docstrings, config comments) to reflect current implementation. Adapts to super-repo, mono-repo, or single-repo structures. Invoked at context compaction or task completion. Input: task file path. Scope constraint: updates project-level CLAUDE.md only — NOT the user's global ~/.claude/CLAUDE.md. Documents skill structures, agent design patterns, Python CLI development patterns, quality/security patterns, and AI integration patterns.
- Triggers: Context compaction; task completion; when existing documentation has drifted from code significantly; supply with task file path
- Inputs: Task file path (to understand what was implemented); code changes (git diff)
- Outputs: Updated CLAUDE.md and module docs; documentation update summary with files changed
- Validators: Consistency cross-check between CLAUDE.md and SKILL.md; no broken relative file references
- Registry workflow: drift-audit (legacy component — post-implementation doc sync variant)

---

## subagent-refactorer (~/.claude/agents)

- Path: ~/.claude/agents/subagent-refactorer.md
- Tools: Read, Write, Edit, Grep, Glob, WebFetch, mcp__Ref__ref_search_documentation, mcp__Ref__ref_read_url, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, mcp__exa__web_search_exa, mcp__exa__get_code_context_exa, mcp__github__search_code, WebSearch, mcp__sequential_thinking__sequentialthinking, mcp__plugin_episodic-memory_episodic-memory__search, mcp__plugin_episodic-memory_episodic-memory__read, Skill, SlashCommand
- Model: sonnet
- Color: purple
- Purpose: Refactors Claude Code agents using Anthropic official prompt engineering best practices. MANDATORY research phase before any refactoring. Applies: strategic XML tagging (NOT full XML conversion), Constitutional AI self-critique patterns, Claude 4.x model-specific optimizations (Sonnet 4.5 vs Opus 4.5), instruction strengthening (vague→imperative), example enhancement, minimal tool selection. Produces analysis report + refactored agent file + validation checklist. Note: a repo-canonical version also exists at plugins/plugin-creator/agents/subagent-refactorer.md.
- Triggers: Reviewing or refactoring Claude Code subagents; improving agent clarity, structure, and optimization; agents producing poor results
- Inputs: Path to target agent .md file; target model preference (Sonnet 4.5 default); optional specific issues
- Outputs: Analysis report with citations; refactored agent .md file; validation checklist
- Validators: Official Anthropic documentation compliance; strategic XML (not full XML conversion); all claims backed by cited sources
- Registry workflow: prompt-optimization (legacy component)

---

## subagent-generator (~/.claude/agents)

- Path: ~/.claude/agents/subagent-generator.md
- Tools: Write, Read, WebFetch, Glob, Grep, mcp__sequential_thinking__sequentialthinking, mcp__plugin_episodic-memory_episodic-memory__search, mcp__plugin_episodic-memory_episodic-memory__read, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, Edit, Skill, SlashCommand
- Model: (not specified in frontmatter)
- Purpose: Creates new Claude Code agent .md files with proper frontmatter, structure, and best practices. Knows the mandatory format (YAML frontmatter: name, description, tools, model, color), available tools reference, description field best practices (include usage examples with <example> tags), system prompt structure template, tool selection guidelines by agent type, and Constitutional AI patterns. Validates: kebab-case name, trigger conditions in description, minimal tool set, structured system prompt, defined output format, explicit boundaries.
- Triggers: When a new specialized agent needs to be created for any task
- Inputs: Agent purpose description, inputs/outputs, tool requirements, complexity level
- Outputs: New agent .md file at .claude/agents/{agent-name}.md with complete frontmatter and system prompt
- Validators: Validation checklist (name format, description triggers, tool minimalism, output format, boundaries)
- Registry workflow: prompt-optimization (legacy component — creation variant vs refactorer's edit variant)

---

## User-Global Skills (~/.claude/skills/)

Skills discovered in /home/user/.claude/skills/ not previously inventoried.

---

## cursor-mdc-editor (~/.claude/skills)

- Path: ~/.claude/skills/cursor-mdc-editor/SKILL.md
- Tools: (not specified — skill loaded into caller context)
- Model: (not specified — skill loaded into caller context)
- Purpose: Creates and optimizes Cursor IDE .mdc rule files using Structured Context Protocol (SCP) and XML-based prompt engineering. Transforms vague guidelines into deterministic, verifiable, imperative rules for Cursor's AI. Three workflows: (1) creating new MDC files from requirements, (2) editing existing MDC files for SCP compliance, (3) converting external guidelines (PDFs, markdown, wikis) to MDC format. Applies quantifiable metrics, IF/THEN conditional logic, verification criteria for every MUST rule, and anti-pattern documentation. Validates against 500-line limit, YAML frontmatter correctness, and glob pattern accuracy.
- Triggers: Creating new Cursor rules, improving .mdc files, converting coding guidelines to MDC format, refactoring vague rules, migrating from .cursorrules
- Inputs: Target file types (glob patterns), rule purpose, strictness level, existing guidelines to convert
- Outputs: .cursor/rules/{name}.mdc file with SCP-compliant rules; validation checklist; delivery summary
- Validators: MDC format compliance checklist; SCP compliance (deterministic, verifiable, quantified); research-backed (2+ authoritative sources per major rule)
- Registry workflow: formatting-validation (legacy component — Cursor-specific rule formatting)
