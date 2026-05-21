<p align="center">
  <img src="./assets/hero.png" alt="The Rewrite Room" width="800" />
</p>

# the-rewrite-room

Documentation and authoring workflow router: audit docs vs code drift, sync docs after changes, optimize prompts and SKILL.md files, validate GLFM and Markdown formatting, summarize files/URLs/images with fidelity enforcement, and convert user-facing docs into Claude Code skill directories.

## Why Install This?

Documentation falls out of sync with code, CLAUDE.md files accumulate noise, SKILL.md files drift from best practices, and converting third-party docs into Claude skills requires a consistent process. This plugin routes each of those tasks to a specialist agent that knows exactly how to handle it — you describe the task, the right agent does the work.

## What You Get

### Commands

#### /rwr:audit

Audits documentation accuracy against code, syncs docs after code changes, and tracks doc
freshness.

```text
/rwr:audit <task>
```

Use when docs are out of date, code changed without doc updates, or you want to verify docs
match the current implementation.

**Examples:**

```text
/rwr:audit "check if kaizen plugin docs match the code"
/rwr:audit "sync docs after refactoring DataProcessor"
/rwr:audit "add freshness tracking to the plugin-creator docs"
```

#### /rwr:optimize

Optimizes AI-facing prompts, CLAUDE.md configurations, SKILL.md files, and agent definitions
using Anthropic prompt engineering best practices.

```text
/rwr:optimize <file>
```

Use when CLAUDE.md feels ineffective, a SKILL.md needs restructuring, or agent instructions
are ambiguous. Not for user-facing docs — use `/rwr:author` for those.

**Examples:**

```text
/rwr:optimize "plugins/plugin-creator/skills/add-doc-updater/SKILL.md"
/rwr:optimize ".claude/CLAUDE.md"
```

#### /rwr:author

Authors and validates user-facing documentation — READMEs, tutorials, API docs, GitLab Wiki
pages, and GLFM-formatted content. Also routes summarization requests for files, URLs, and
images.

```text
/rwr:author <task>
```

Use when writing human-facing docs, validating GLFM syntax, or summarizing content. Not for
AI-facing docs — use `/rwr:optimize` for those.

**Examples:**

```text
/rwr:author "summarize plugins/summarizer/skills/summarizer/SKILL.md"
/rwr:author "write a README for the kaizen plugin"
/rwr:author "validate GLFM in docs/wiki/setup.md"
```

#### /rwr:cite

Fetches a source URL, cross-references all claims against the source material, and produces
attributed content with embedded hyperlinked citations.

```text
/rwr:cite <source URL> [key points] [content type]
```

Use when creating blog posts, research summaries, or any content that requires rigorous source
attribution and credit to original creators.

**Examples:**

```text
/rwr:cite "https://docs.anthropic.com/en/docs/claude-code" "blog post about Claude Code"
/rwr:cite "https://example.com/article" "key metrics" "research summary"
```

**What it does:** Fetches the source, identifies unique insights and direct quotes, verifies
every claim against the source, then produces structured output with an executive summary,
deep dive with inline citations, key takeaways as blockquotes, and a Cited From section.

#### /rwr:doc-to-skill

Converts a user-facing documentation directory (or GitHub URL) into a Claude Code skill
directory — a `SKILL.md` with valid frontmatter plus thematically grouped `references/*.md`
files.

```text
/rwr:doc-to-skill <github-url or /path/to/docs> [output_skill_name]
```

Use when you want to turn library documentation, tool guides, or API references into
structured Claude knowledge that loads on demand.

**Examples:**

```text
/rwr:doc-to-skill "docs/my-library/" "my-library"
/rwr:doc-to-skill "https://github.com/owner/repo/tree/main/docs" "repo-skill"
/rwr:doc-to-skill "docs/fastapi/" "fastapi"
```

**What it does:** Inventories the docs directory, extracts content by document type, identifies
workflow-shaped patterns and delegates those to the `process-siren` agent, groups extracted
knowledge into themes, writes reference files, assembles a `SKILL.md`, and runs validation.
The output is a complete skill directory ready to install.

### Claude Improvements

**Audit:** When you ask Claude to check whether docs match code, Claude will delegate to a
specialist that produces evidence-based findings with file:line citations and severity
categorization — not a vague summary.

**Optimize:** When you ask Claude to improve a SKILL.md or CLAUDE.md, Claude will run the
RT-ICA pre-check gate, apply 6-step optimization, and produce a token impact report showing
what changed and why.

**Author:** When you ask Claude to write a README or summarize a file, Claude routes to the
right specialist based on target format (GitLab vs general markdown, file vs URL vs image).

**Cite:** When you ask Claude to write content from a source URL, Claude will verify claims
against the source and produce structured output with embedded hyperlinked citations rather
than paraphrased summaries without attribution.

**Doc-to-skill:** When you ask Claude to convert documentation into a skill, Claude follows a
multi-phase SOP — inventory, extraction, workflow identification, thematic grouping, writing,
and validation — producing a complete, lint-passing skill directory.

### Agents

All five agents share a canonical STATUS block output contract. Every response includes
`STATUS`, `SUMMARY`, `ARTIFACTS`, and `VALIDATION` fields.

| Agent                        | Role                                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| `rewrite-room-auditor`       | Docs vs code drift detection, post-change sync, freshness tracking                           |
| `rewrite-room-optimizer`     | AI-facing prompt and SKILL.md optimization using Anthropic best practices                    |
| `rewrite-room-author`        | User-facing docs authoring, GLFM validation, file/URL/image summarization                    |
| `rewrite-room-cite`          | Source-attributed content writing with primary source verification and hyperlinked citations |
| `rewrite-room-doc-converter` | Converts user-facing documentation directories into Claude Code skill directories            |

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add jamie-bitflight/claude_skills
```

Then install the plugin:

```bash
/plugin install rwr@jamie-bitflight-skills
```

## Usage

```text
/rwr:audit "check if kaizen plugin docs match the code"
/rwr:optimize "plugins/plugin-creator/skills/add-doc-updater/SKILL.md"
/rwr:author "summarize plugins/summarizer/skills/summarizer/SKILL.md"
/rwr:cite "https://docs.anthropic.com/en/docs/claude-code" "blog post"
/rwr:doc-to-skill "docs/my-library/" "my-library"
```

## Example: Converting Library Docs to a Skill

You have a local `docs/httpx/` directory with the httpx Python library's user guide, API
reference, and quickstart. You want Claude to have expert-level knowledge of httpx that loads
on demand.

```text
/rwr:doc-to-skill "docs/httpx/" "httpx"
```

The `rewrite-room-doc-converter` agent will:

1. Inventory `docs/httpx/` — count files by type, read the index
2. Extract content from each doc using type-appropriate patterns (API reference gets different
   treatment than a tutorial)
3. Identify workflow-shaped content (installation steps, request lifecycle) and generate
   workflow diagrams via `process-siren`
4. Group extracted knowledge into themes (authentication, async, error handling, etc.)
5. Write `plugins/httpx/skills/httpx/references/*.md` — one file per theme
6. Write `plugins/httpx/skills/httpx/SKILL.md` with frontmatter and references index
7. Run `skilllint` and frontmatter validation, report PASS/FAIL

Output: a complete skill directory at `plugins/httpx/` ready for `claude plugin validate .`

## Requirements

- Claude Code v2.0+
- For `/rwr:audit`: `development-harness` plugin installed (provides `doc-drift-auditor` and `service-docs-maintainer` agents)
- For `/rwr:optimize`: `plugin-creator` plugin installed (provides `ai-doc-optimizer`, `skill-auditor`, `skill-content-updater`, and `subagent-refactorer` agents)

  Routing by concern (plugin-creator optimization suite):
  - Optimize existing content (improve clarity, fix structure, apply Anthropic prompt engineering principles) → `plugin-creator:ai-doc-optimizer`
  - Audit quality (read-only, no writes, score against completeness categories) → `plugin-creator:skill-auditor`
  - Sync content against upstream docs (add NEW/fix STALE from live sources) → `plugin-creator:skill-content-updater`
  - Write/rewrite description field only → `/plugin-creator:write-frontmatter-description` skill directly
- For `/rwr:author` (summarization): `summarizer` plugin installed
- For `/rwr:author` (GitLab targets): `gitlab-skill` plugin installed
- For `/rwr:doc-to-skill` (workflow diagrams): `process-siren` plugin installed
- For `/rwr:author` (GLFM validation): `GITLAB_TOKEN` environment variable set

---

> **The Ancient Woe**
>
> _The weeping royal archivist whose mountain of historical scrolls has been scattered to the four winds by a careless breeze through an open window._

> **The Bard's Decree**
>
> _"A place for every parchment, and every parchment in its place! Route the decrees to the scribes, the histories to the monks, and let order reign o'er this library of madness!"_
