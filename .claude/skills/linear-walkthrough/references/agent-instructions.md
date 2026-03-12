# Agent Instructions

Each section below contains the complete instructions for one agent role. The orchestrator passes the relevant section to each agent.

## Discovery Agent Instructions

### Goal

Scan the target repository and produce two artifacts: a coverage plan partitioning the repo into parallel exploration tasks, and an entry point index cataloging all meaningful entry points.

### Procedure

1. Read the top-level directory structure. Identify languages, frameworks, package boundaries, services, apps, libraries, infrastructure, CI/CD, docs, and configuration.

2. Read high-signal files first:
   - README, CONTRIBUTING, architecture docs
   - Package manifests (package.json, pyproject.toml, Cargo.toml, go.mod, pom.xml, Gemfile)
   - Configuration files (docker-compose, Dockerfile, Makefile, CI configs)
   - Entry point files (main.*, index.*, app.*, manage.py, cli.*)

3. Identify all entry points. Scan for:
   - Application bootstraps (main functions, app factories)
   - CLI commands (argument parsers, command registries)
   - HTTP or RPC servers (route registrations, server startup)
   - Worker and job runners (task definitions, queue consumers)
   - Scheduled tasks (cron configs, scheduler registrations)
   - Event consumers (message handlers, webhook endpoints)
   - Test harnesses (test configuration, test runners)
   - Deployment entry points (Dockerfiles, serverless handlers, cloud function exports)
   - Local development startup paths (dev scripts, docker-compose services)

4. For each entry point, record: name, type, file location (with line number), purpose, owning subsystem, and discovery evidence.

5. Build agent assignments by clustering related entry points and their downstream paths. Each assignment must:
   - Focus on one execution path or one tightly related cluster of paths
   - Stay within 50k tokens of source file reading
   - Minimize overlap with other assignments (overlap only for shared infrastructure)
   - Include a rationale for why these files belong together

6. Estimate token budgets per assignment. Use file sizes as proxy: ~4 characters per token for code files.

7. Track files that are not assigned to any agent and document why in the uncovered areas section.

### Output

Write two files:

- `walkthrough/coverage-plan.md` — follow the Coverage Plan Format in [output-format.md](./output-format.md)
- `walkthrough/entry-points.md` — follow the Entry Point Index Format in [output-format.md](./output-format.md)

Create the `walkthrough/`, `walkthrough/sections/`, and `walkthrough/validation/` directories.

## Tracing Agent Instructions

### Goal

Produce a linear walkthrough for the assigned scope — trace execution from entry points through modules, documenting what happens in order with concrete file paths and symbols.

### Constraints

- Read at most 50k tokens of source files.
- Stay within the assigned scope from the coverage plan. Read shared infrastructure files only when necessary to understand the assigned flow.
- Do not speculate about code you have not read. Mark anything not directly verified as `[INFERENCE]`.

### Procedure

1. Read the assigned entry point files first.

2. Follow the execution path forward: what does the entry point call? What does that call? Trace through the call chain, reading each file as needed.

3. At each step, record:
   - File and line where execution happens
   - What function/class/module is invoked
   - What data or control is passed
   - What prerequisites or setup happened before
   - What downstream systems or side effects happen after
   - Where the flow branches, retries, fails, or exits

4. Note configuration files, environment variables, and external dependencies that affect the flow.

5. Document error handling paths, not just the happy path. Note retry logic, fallback behavior, and failure modes.

6. When encountering shared infrastructure (logging, auth, database connections, middleware), describe its role in this flow without fully tracing its internals (that belongs to the agent assigned to infrastructure).

7. Assess confidence for each major claim:
   - **Verified**: directly read in source code or config
   - **[INFERENCE]**: reasonable conclusion from patterns, naming, or partial evidence
   - **[UNCERTAIN]**: could not verify, needs investigation

### Output

Write one file: `walkthrough/sections/walkthrough-section-{id}.md` following the Walkthrough Section Format in [output-format.md](./output-format.md).

## Validation Agent Instructions

### Goal

Fact-check assigned walkthrough sections against source code. Identify incorrect sequencing, invented behavior, missing prerequisites, broken references, contradictions, and ambiguous boundaries.

### Constraints

- Read at most 50k tokens of explanation files plus relevant source context.
- Do not rewrite walkthrough sections. Produce a validation report with corrections, confidence levels, and unresolved issues.

### Procedure

1. Read each assigned walkthrough section file completely.

2. For each major claim in the section:
   a. Identify the source file and line referenced.
   b. Read the referenced source to verify the claim.
   c. Check: does the code actually do what the walkthrough says? Is the sequence correct? Are the function signatures and return types accurate?

3. Check for these specific failure modes:
   - **Incorrect sequencing**: steps described out of order relative to actual execution
   - **Invented behavior**: claims about functionality that does not exist in the code
   - **Missing prerequisites**: setup steps or initialization that the walkthrough omits
   - **Broken references**: file paths, function names, or class names that do not exist
   - **Contradictions with other sections**: claims that conflict with what other walkthrough sections describe (read other sections for cross-reference if assigned)
   - **Ambiguous boundaries**: unclear where one subsystem ends and another begins

4. Check naming and terminology consistency:
   - Are the same concepts called the same thing across sections?
   - Are system boundaries described consistently?

5. Assign a confidence level to each section: High (most claims verified), Medium (some claims unverifiable), Low (significant gaps or errors found).

6. Document unresolved issues — things that could not be verified because source was unavailable, behavior depends on runtime state, or external documentation is needed.

### Output

Write one file: `walkthrough/validation/validation-report-{id}.md` following the Validation Report Format in [output-format.md](./output-format.md).

## Synthesis Agent Instructions

### Goal

Merge all validated walkthrough sections into a single unified walkthrough document that a new engineer can read end-to-end to understand the codebase.

### Procedure

1. Read all walkthrough section files from `walkthrough/sections/`.

2. Read all validation reports from `walkthrough/validation/`. Apply any corrections noted in validation reports to the section content as it is merged.

3. Read `walkthrough/entry-points.md` for the complete entry point index.

4. Determine a logical reading order for sections. Prefer:
   - Start with application bootstrap and initialization
   - Follow primary request/data flow paths
   - Then secondary paths (background jobs, scheduled tasks)
   - Then infrastructure and cross-cutting concerns
   - Then development and operations processes

5. Write the unified walkthrough following the Unified Walkthrough Format in [output-format.md](./output-format.md). This includes:
   - Executive overview
   - Entry point index with links to walkthrough sections
   - All walkthrough sections in reading order with navigation links
   - Cross-cutting system coverage
   - Repository process coverage
   - Validation appendix

6. Connect sections with predecessor/successor navigation. Every section must clearly state what comes before and after it.

7. Consolidate all unresolved issues, partial coverage areas, and follow-up suggestions into `walkthrough/open-questions.md`.

8. For cross-cutting coverage: synthesize information from all sections into unified subsections. If the codebase does not include an area (observability, security, data stores), state that explicitly rather than omitting the subsection.

### Output

Write two files:

- `walkthrough/unified-walkthrough.md` — follow the Unified Walkthrough Format in [output-format.md](./output-format.md). If content exceeds 25k characters, split into `walkthrough/unified/index.md` with per-part files.
- `walkthrough/open-questions.md` — follow the Open Questions Format in [output-format.md](./output-format.md).
