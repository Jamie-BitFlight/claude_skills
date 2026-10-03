# Improvement Proposals: GitDiagram

**Research entry**: ./research/mcp-ecosystem/gitdiagram.md
**Generated**: 2026-10-02
**Patterns assessed**: 8
**Backlog items created**: 0 (1 high-confidence proposal qualified; `mcp__plugin_dh_backlog__backlog_add` failed — see Improvement 1)
**Deferred (low confidence)**: 2
**Skipped (already covered or tracked)**: 5

---

## Improvement 1: Syntax-check every committed Mermaid block in a hook or CI job

**Source pattern**: "Mermaid Compilation (`compileDiagramGraph` in `graph.ts`) — Deterministic AST-to-Mermaid transpiler with total text escaping and GitHub-only link enforcement. Uses test-only parser in `mermaid-validator.ts` to validate output" (Technical Architecture → Generation Pipeline, step 4; referenced from Relevance → Applications, "Architecture diagram rendering via Mermaid")
**Local system**: `.pre-commit-config.yaml`, `.claude/skills/mermaid-js/` (directory), `plugins/development-harness/scripts/enumerate_scope.py`
**Absence evidence**:
`git grep -n -i "mermaid\|mmdc" -- .pre-commit-config.yaml .github/workflows/ pyproject.toml package.json` -> 0 matches;
`git grep -il "mmdc\|mermaid-cli\|@mermaid-js/parser\|mermaid.parse" -- plugins/ .claude/skills/ .claude/agents/ scripts/` -> 0 matches;
`grep -ril mermaid` over the installed `skilllint` package source (`uvx skilllint@latest`, the repo's skill-validation hook) -> 0 matches;
`git grep -il "mermaid" -- '*.py' '*.cjs' '*.js' '*.ts'` -> 2 files, neither validates syntax (`enumerate_scope.py` extracts `.md` paths from node labels; `notify-investigation-complete.cjs` is a hook notifier)
**Confidence**: High
**Impact**: Medium
**Backlog**: Not created — `mcp__plugin_dh_backlog__backlog_add` returned `GraphQL is unavailable in this environment` (backlog_list failed identically). Duplicate check done by paging all 2,959 issues through the REST endpoint `repos/Jamie-BitFlight/claude_skills/issues?state=all`: no title covers Mermaid syntax validation (nearest: #3244 auto-disclose large diagrams, #3773 Mermaid authority remediation — body checked, no syntax validation). Create when the backlog server can reach its backend; full description is in the sections below.

### Current state

`git grep -c '```mermaid' -- '*.md'` counts 578 Mermaid fences across 190 tracked Markdown files.
Mermaid flowcharts are the main control-flow notation in SKILL.md and agent files, and agents write
most of them. No pre-commit hook and no CI workflow parses them. `skilllint` checks frontmatter and
structure only. `.claude/skills/mermaid-js/` (README.md, QUICK_REFERENCE.md, COOKBOOK.md,
DIAGRAM_INDEX.md, mermaid-diagram-reference.md) documents syntax but has no validation step. A
malformed block shows up only as a GitHub render error, or never if the only reader is an agent
reading the source. The number of currently invalid blocks has not been measured.

### Target state

A pre-commit hook or CI step parses every changed ```mermaid fence. When a block does not parse, it
fails and reports the file path, the line where the fence starts, and the parser's error message.
GitDiagram's equivalent is a parser-based check over generated Mermaid. Choosing the parser and
whether the check runs as a hook or in CI is grooming work, bounded by
`rules/language-conventions.md`.

### Measurable signal

- Stage a SKILL.md with a deliberately malformed ```mermaid block. The commit or CI job fails, and its output names that file and line.
- `git grep -n -i "mermaid" -- .pre-commit-config.yaml .github/workflows/` returns at least one match for the validation step.
- One full run over all tracked Markdown reports a baseline count of invalid blocks.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Add the GitDiagram remote MCP server (`https://gitdiagram.com/mcp`) as a project connector (Applications, "MCP server for codebase analysis") | low | `.mcp.json` holds only `Ref-local` and `context7-local`; `git grep -il gitdiagram` over `plugins/ .claude/ rules/ docs/ AGENTS.md .mcp.json` -> 0 matches, so the server is absent. The entry says `get_repository_diagram` "never starts generation": it returns only diagrams already cached in GitDiagram's public R2 namespace (7-day lifecycle), with a 120 calls/hour per-network limit. Local repository analysis already runs through `.claude/skills/linear-walkthrough/SKILL.md` against a clone. No failure mode or demonstrated need was found; raising confidence needs a recorded task where cross-repo architecture context was missing and a clone was not workable. |
| Deterministically drop evidence citations to files the model was not shown, using a SOURCE INDEX (Technical Architecture step 2–3: "Evidence citations are dropped for files the model wasn't shown") applied to walkthrough generation | medium | `.claude/skills/linear-walkthrough/SKILL.md` Phase 3 runs LLM validators that look for "broken references" (lines 66–78), so the check exists but is model-judged rather than deterministic. Not confirmed: whether `references/agent-instructions.md` or any script already checks cited paths mechanically. Also overlaps open #4023 ("enforce source-grounded manual hypothetical walkthrough contracts"); read #4023's body before proposing. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| AST-to-Mermaid compiler with total escaping and GitHub-only link enforcement (Applications, mermaid bullet, the compiler half) | Incompatible with this repo: nothing here generates Mermaid from code (`git grep -ilE "flowchart (TD\|LR)\|graph (TD\|LR)" -- '*.py'` -> 0 matches). Diagrams are written by hand or by agents. The validation half of the same passage became Improvement 1. |
| AI-guided diagram generation pipeline (Applications) | The entry marks it out of scope (domain-specific to codebase analysis). |
| Streamed SSE explanations alongside generated content (Patterns Worth Adopting) | The entry marks Change: none. This repo's MCP servers are tool servers, and none of them streams a narrative next to an artifact, so the pattern has nothing to attach to. The quoted goal line exists at `docs/mcp-architecture-analysis.md:7`. |
| Deterministic graph validation and repair-in-place (Patterns Worth Adopting) | Already covered. `.claude/agents/research-curator.md` Phase 1c / re-run Repo Anchor Pass (lines 51, 66, 141) re-checks each cited path and rewrites items whose anchor no longer resolves. |
| Explainer video generation with AI narration (Integration Opportunities) | The entry marks it out of scope; 0 matches for "explainer video" and "narrated" per the entry's own git grep. |
