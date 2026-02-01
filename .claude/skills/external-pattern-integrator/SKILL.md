---
description: 'Integrate patterns from external sources (URLs or files) into local skills, agents, and plugins. Triggers on comparing external agent definitions against local equivalents, extracting best practices from frameworks like GSD or BMAD-METHOD, enhancing local skills with external patterns, or ensuring interoperability with external tool ecosystems.'
argument-hint: '<url-or-file> [url-or-file...]'
user-invocable: true
---

# External Pattern Integrator

Systematically analyze external agent/skill definitions and integrate their strengths into local skills while maintaining workflow coherence.

## Arguments

$ARGUMENTS

## Workflow Overview

```text
Phase 1: Parallel Candidate Mapping
├── For each external source (concurrent):
│   ├── Fetch/read the external file
│   ├── Analyze its purpose and patterns
│   └── Scan local files for candidates (frontmatter only)
└── Output: Tracking document with source → candidates mapping

Phase 2: Contextual Enhancement (concurrent per source)
├── Understand local file's workflow context FIRST
├── Compare against external patterns
├── Identify enhancements that fit the workflow stage
├── Add external artifact recognition for interoperability
└── Edit files with coordinated changes

Phase 3: Validation
└── Run linting on all modified files
```

## Phase 1: Parallel Candidate Mapping

### Step 1.1: Create Tracking Document

Create a tracking file at `.claude/external-pattern-integration-{date}.md`:

```markdown
# External Pattern Integration

**Date**: {YYYY-MM-DD}
**Sources**: {list of URLs/files from arguments}
**Status**: IN_PROGRESS

## Source Analysis

### Source 1: {URL or path}

**Purpose**: {What this external agent/skill does}
**Key Patterns**:
- {Pattern 1}
- {Pattern 2}

**Local Candidates** (by frontmatter similarity):
| Local File | Similarity Reason | Priority |
|------------|-------------------|----------|
| {path} | {why it matches} | {High/Medium/Low} |

### Source 2: {URL or path}
...
```

### Step 1.2: Fetch External Sources

For each URL/file in $ARGUMENTS:

**If URL**: Use WebFetch or curl to download to `/tmp/external-pattern-{slug}.md`
**If local file**: Read directly

### Step 1.3: Analyze External Source

For each external source, extract:

1. **Purpose**: What problem does it solve?
2. **Key Patterns**: What techniques does it use?
3. **Artifact Files**: What files does it create/read? (for interoperability)
4. **Workflow Stage**: Where in a development workflow does it fit?

### Step 1.4: Scan Local Candidates

Scan these locations for candidates (frontmatter only, not full files):

```text
plugins/*/skills/*/SKILL.md
plugins/*/agents/*.md
.claude/skills/*/SKILL.md
.claude/agents/*.md
```

Match by:

- Similar purpose (from description field)
- Similar workflow stage
- Overlapping functionality

**Priority Assignment**:

- **High**: Direct functional overlap (same workflow stage, similar purpose)
- **Medium**: Adjacent functionality (related workflow stage)
- **Low**: Tangential (shared patterns but different purpose)

### Step 1.5: Deduplicate Candidates

If a local file appears as candidate for multiple external sources:

1. Assign to the BEST match (highest similarity)
2. Note secondary matches for cross-reference during enhancement

## Phase 2: Contextual Enhancement

Run concurrently for each external source. For each candidate local file:

### Step 2.1: Understand Workflow Context

BEFORE comparing, determine:

1. **Is this file part of a multi-file workflow?**

   - Check for references to other skills/agents in the file
   - Check if other files reference this one
   - Look for phase indicators (discovery → planning → implementation → verification)

2. **What stage of the workflow is this file for?**

   - Discovery/Research (gathering context)
   - Planning (creating specs, acceptance criteria)
   - Implementation (writing code)
   - Verification (testing, validation)
   - Orchestration (coordinating other agents)

3. **What are the upstream/downstream dependencies?**
   - What artifacts does this file expect as input?
   - What artifacts does this file produce?

### Step 2.2: Compare and Identify Enhancements

Read the full external source and full local file. Identify:

| Enhancement Type     | Description                                   | Fits Current Stage? |
| -------------------- | --------------------------------------------- | ------------------- |
| Missing pattern      | External has X, local lacks it                | Yes/No              |
| Stronger guidance    | External has better instructions for Y        | Yes/No              |
| Better structure     | External organizes Z more clearly             | Yes/No              |
| Artifact recognition | External creates files local should recognize | Yes/No              |

**Critical Rule**: Only recommend enhancements that fit the file's workflow stage. If an enhancement belongs in a different stage, note which file should receive it instead.

### Step 2.3: Add External Artifact Recognition

For interoperability, add a section to context-gathering skills:

```markdown
## External Framework Artifacts

<external_artifacts>

When gathering context, also check for these artifacts from external frameworks:

**Get Shit Done (GSD)**:
- `STATE.md` - Current project state and progress
- `ROADMAP.md` - Feature roadmap and planning
- `codebase-map.md` - Generated codebase structure
- `research-*.md` - Research documents
- `plan-*.md` - Execution plans

**BMAD-METHOD**:
- `*.agent.yaml` - Agent definitions
- `workflows/*.md` - Workflow definitions
- `party-mode-session.md` - Multi-agent collaboration notes

If found, incorporate their context into discovery.

</external_artifacts>
```

### Step 2.4: Coordinate Cross-File Changes

If enhancements affect multiple files in a workflow:

1. List all affected files
2. Determine the order of changes (upstream before downstream)
3. Ensure consistency (same terminology, compatible artifacts)
4. Make changes atomically (all or none)

### Step 2.5: Apply Enhancements

Edit local files with:

- Clear section markers for new content
- Source attribution: `SOURCE: Adapted from {external source URL/path}`
- Preserved existing functionality (additive changes preferred)

## Phase 3: Validation

### Step 3.1: Run Linting

```bash
uv run prek run --files {all modified files}
```

Fix any issues before proceeding.

### Step 3.2: Update Tracking Document

Update the tracking file with:

```markdown
## Results

**Files Modified**:
| File | Enhancements Applied | Source |
|------|---------------------|--------|
| {path} | {what was added} | {external source} |

**Deferred Enhancements** (didn't fit current files):
| Enhancement | Reason Deferred | Suggested Location |
|-------------|-----------------|-------------------|
| {pattern} | {why} | {where it should go} |

**Status**: COMPLETE
```

### Step 3.3: Add Deferred Items to Backlog

If there are deferred enhancements, add them to `.claude/BACKLOG.md`:

1. Read the current backlog file
2. For each deferred enhancement, add an entry under the appropriate priority:
   - **P1 (Should Have)**: Patterns that would significantly improve workflows
   - **P2 (Could Have)**: Nice-to-have patterns or minor improvements
   - **Ideas**: Patterns worth exploring but unclear fit

Entry format:

```markdown
### {Enhancement title}

**Source**: [{tracking-document}]({path-to-tracking-document})
**Added**: {YYYY-MM-DD}
**Description**: {What needs to be done}
**Patterns from**: {external-source-name}
**Suggested location**: {path/to/file.md}
```

3. Update the summary counts in the backlog
4. Note in tracking document: "Deferred items added to `.claude/BACKLOG.md`"

### Step 3.4: Commit Changes

Stage and commit with message:

```text
feat(skills): integrate patterns from {source names}

Enhancements:
- {file1}: {what was added}
- {file2}: {what was added}

Sources:
- {URL1}
- {URL2}
```

## Success Criteria

- [ ] All external sources fetched and analyzed
- [ ] Tracking document created with candidate mapping
- [ ] Workflow context understood before making changes
- [ ] Enhancements fit the file's workflow stage
- [ ] Cross-file changes coordinated
- [ ] External artifact recognition added for interoperability
- [ ] All modified files pass linting
- [ ] Deferred enhancements added to `.claude/BACKLOG.md` with priority
- [ ] Changes committed with source attribution

## Example Usage

```text
User: /external-pattern-integrator https://github.com/glittercowboy/get-shit-done/blob/main/agents/gsd-codebase-mapper.md
```
