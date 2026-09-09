<p align="center">
  <img src="./assets/hero.png" alt="The Rewrite Room" width="800" />
</p>

# the-rewrite-room

Rewrite Room ships one model-invoked router and five model-invoked portable workflow skills. Each
workflow has a self-contained baseline and works across Claude and Codex without a bundled MCP
server, command directory, routing agent, hook, or required sibling plugin.

## Invocation

| Installed skill | Claude | Codex | Primary outcome |
| --- | --- | --- | --- |
| `rwr:the-rewrite-room` | `/rwr:the-rewrite-room` | `$rwr:the-rewrite-room` | Route an explicit or overlapping request to exactly one leaf workflow |
| `rwr:audit` | `/rwr:audit` | `$rwr:audit` | Compare docs with implementation, synchronize docs, or review freshness |
| `rwr:author` | `/rwr:author` | `$rwr:author` | Author, rewrite, summarize, or validate user-facing documentation |
| `rwr:cite` | `/rwr:cite` | `$rwr:cite` | Produce source-attributed content with verified claims and quotations |
| `rwr:doc-to-skill` | `/rwr:doc-to-skill` | `$rwr:doc-to-skill` | Convert one documentation source into one portable Agent Skill |
| `rwr:optimize` | `/rwr:optimize` | `$rwr:optimize` | Analyze or refine an existing agent-facing artifact without losing behavior |

## Audit, Synchronization, and Freshness

`rwr:audit` requires both a documentation scope and an implementation or changed-file scope. It
inventories every scoped item and records each claim as `MATCH`, `STALE`, `MISSING`, or `UNVERIFIED`
with its evidence and required action.

- **Compare** reports evidence-backed drift without writing.
- **Synchronize** edits only documentation supported by the evidence ledger and only with edit
  permission.
- **Freshness review** marks claims current or needing re-verification and adds freshness metadata
  only when requested and supported.

```text
/rwr:audit "Compare docs/api.md with src/api.py and report drift without editing."
/rwr:audit "Synchronize docs/api.md after changes in src/api.py; edit documentation only."
/rwr:audit "Review docs/api.md freshness against src/api.py; add no metadata unless evidence supports it."
```

## AI-instruction Optimization

`rwr:optimize` reads the complete target and its required local references, builds a whole-behavior
ledger, and verifies every retained, moved, rephrased, or explicitly authorized removal against the
actual or proposed result. Use it for Agent Skills, AGENTS.md, CLAUDE.md, rules, prompts, and agent
definitions; use `rwr:author` for user-facing prose.

The workflow can use installed `writing-for-agents` and `skill-lapidary` support. Skill Lapidary is
analysis-only (`--dry-run --grade reshape`); Rewrite Room owns any requested edit. Missing, unusable,
or failed support is named and the built-in baseline continues.

```text
/rwr:optimize "Analyze plugins/example/skills/example without editing it."
$rwr:optimize "Refine AGENTS.md while preserving every existing behavior."
```

## User-facing Authoring and Summaries

`rwr:author` directly authors, rewrites, summarizes, or validates user-facing documentation. It
supports READMEs, tutorials, API documentation, GitLab Markdown, and other requested Markdown
dialects. Summaries preserve source meaning, uncertainty, counts, quotations, and technical tokens.
An installed specialist may improve a relevant branch, but the source-preservation record and
validation remain authoritative. Use `rwr:audit` when implementation comparison is primary and
`rwr:cite` when the result requires reader-visible source attribution.

```text
/rwr:author "Write a README from these release notes for new users."
$rwr:author "Summarize docs/design.md without losing decisions or uncertainty."
/rwr:author "Validate the GitLab Markdown in docs/wiki/setup.md."
```

## Citation-driven Writing

`rwr:cite` accepts URLs or supplied source material and produces the requested content for its named
audience. Its output includes a source register, a claim ledger, and every unresolved or excluded
claim. Every factual claim maps to supporting evidence, every quotation matches its source, and
citations show which source supports each claim.

```text
/rwr:cite "Use https://example.com/report to write a cited research summary for engineers."
$rwr:cite "Use the supplied interview transcript to write a source-attributed brief."
```

## Documentation to Agent Skill

```text
/rwr:doc-to-skill <source> <output-skill-directory>
$rwr:doc-to-skill <source> <output-skill-directory>
```

`source` is one local file, local directory, or Git repository URL.
`output-skill-directory` is one explicit, absent directory that does not overlap the source. The
workflow treats source content as untrusted data, uses a fresh temporary clone for Git input, and
builds a final-name candidate inside a temporary sibling before promotion.

Connected `SOURCE_ID` and `ATOM_ID` ledgers account for every source unit, emitted behavior, exact
technical token, and output claim. Binary extraction runs only when the required reader capability
is available. Missing capability produces `DEGRADED` or `BLOCKED`, never silent omission or false
`DONE`. Terminal status is `DONE`, `DEGRADED`, or `BLOCKED`. A `DONE` run promotes one portable Agent
Skill containing `SKILL.md` and only its warranted relative resources.

The converter uses `writing-for-agents` when available. It inspects or invokes explicit-only Skill
Lapidary only when the current user requests Lapidary or deeper reshape analysis; otherwise it uses
built-in guidance without probing availability.

```text
/rwr:doc-to-skill "docs/httpx/" "skills/httpx"
$rwr:doc-to-skill "https://github.com/owner/repo" "skills/repo"
```

The converter resolves and inventories the source, extracts addressable atoms, classifies and
designs the skill, builds the staged candidate, then verifies and promotes it. `DEGRADED` and
`BLOCKED` runs promote no final directory and remove only temporary paths created by that run.

## Routing at a Glance

| Request | Workflow skill |
| --- | --- |
| Explicitly request routing, or resolve overlapping outcomes | `rwr:the-rewrite-room` |
| Compare docs and implementation, synchronize docs, or review freshness | `rwr:audit` |
| Author, rewrite, summarize, or validate user-facing docs | `rwr:author` |
| Write content whose claims and quotations require source attribution | `rwr:cite` |
| Convert documentation into a portable Agent Skill | `rwr:doc-to-skill` |
| Analyze or refine an agent-facing artifact without behavioral loss | `rwr:optimize` |

The router passes the original request to exactly one leaf and returns that leaf's terminal result
unchanged. The five leaf skills remain directly invocable through the forms in the invocation table.

## Installation

Claude:

```text
/plugin marketplace add Jamie-BitFlight/claude_skills
/plugin install rwr@jamie-bitflight-skills
```

Codex:

```text
codex plugin marketplace add Jamie-BitFlight/claude_skills
codex plugin add rwr@jamie-bitflight-skills
```

## Optional Enhancements

All workflows run from built-in guidance. An installed specialist may add evidence or formatting
when its branch applies, but optional support never replaces a workflow's own ledger, verification,
or completion criteria and never becomes a baseline dependency.

---

> **The Ancient Woe**
>
> *The weeping royal archivist whose mountain of historical scrolls has been scattered to the four winds by a careless breeze through an open window.*

> **The Bard's Decree**
>
> *"A place for every parchment, and every parchment in its place! Route the decrees to the scribes, the histories to the monks, and let order reign o'er this library of madness!"*
