---
name: multi-source-synthesis
description: Combines multiple summaries into coherent synthesis. Activates when user requests combine these summaries, synthesize results, merge findings, or multi-source synthesis. This is the reduce step after individual sources have been summarized. Enforces deduplication, conflict surfacing, confidence scoring across sources, and attribution to all sources.
---

# Multi-Source Synthesis

Combine multiple summaries into a single coherent synthesis with proper attribution, deduplication, and conflict handling.

## When to Use This Skill

The model MUST activate this skill when:

- User requests: "combine these summaries", "synthesize results", "merge findings"
- Multiple sources have been individually summarized and need integration
- User asks to "pull together" or "integrate" information from multiple sources
- This is the "reduce" step after the "map" step (individual summarization)

## Prerequisites

Before applying this skill, the model MUST ensure:

1. Each source has been individually summarized using the summarizer skill
2. Each individual summary followed Rule 1 (Read Before Summarizing) and Rule 2 (Extract Before Abstracting) from [Fidelity Rules](../summarizer/references/fidelity-rules.md)
3. Each summary follows the structured format from [Structured Summary](../summarizer/templates/structured.md)
4. Source attribution is present in each individual summary

## Synthesis Workflow

The model MUST follow these steps in order:

### Step 1: Deduplicate

Merge identical or overlapping information from different sources:

**Rules**:

- If the same information appears in multiple sources, merge into a single statement and cite ALL sources
- Use the most complete version of the information among the sources
- Do NOT drop any source citations during merging
- If two sources say essentially the same thing with different wording, use the clearer or more precise wording
- Preserve exact numbers and specifics (see [Fidelity Rules](../summarizer/references/fidelity-rules.md) Rule 3)

**Example**:

```text
BEFORE DEDUPLICATION:
- Source A: "API rate limit is 100 requests per minute"
- Source B: "Rate limiting enforced at 100 req/min per key"

AFTER DEDUPLICATION:
- API rate limit is 100 requests per minute per key (sources: A, B)
```

**Deduplication Decision Matrix**:

| Situation | Action |
|-----------|--------|
| Same info, different sources | Merge, cite all sources, use most complete version |
| Same topic, different conclusions | Keep both, surface conflict explicitly |
| Different aspects of same topic | Keep separate, group under same theme cluster |
| Different people/viewpoints | Keep separate, attribute to each source |

### Step 2: Cluster by Theme

Group related findings by topic or theme, NOT by source:

**Rules**:

- Organize information by conceptual theme, not by which source it came from
- Each cluster should answer a specific question or cover a specific subtopic
- Findings from multiple sources should be integrated within each cluster
- Avoid patterns like "Source A says..., Source B says..." unless explicitly comparing viewpoints

**Example structure**:

```markdown
## Authentication Methods

The API supports JWT authentication (sources: A, C) and OAuth 2.0 (source: B). JWT tokens expire after 24 hours (source: A), while OAuth tokens are configurable per client (source: B).
```

### Step 3: Rank Clusters

Order clusters by relevance to the user's query or task:

**Rules**:

- Lead with the most important information (BLUF - Bottom Line Up Front)
- If user query is specific, rank clusters by how directly they answer the query
- If user query is broad, rank by significance or impact
- Consider dependencies: foundational concepts before advanced details

### Step 4: Assess Confidence Across Sources

Calculate confidence for each synthesized claim based on source agreement:

**Confidence Scoring Rules**:

| Source Profile | Confidence Level |
|----------------|------------------|
| Multiple fresh authoritative sources agree | High |
| Single authoritative source, recent | Medium-High |
| Multiple sources but somewhat dated | Medium |
| Single source or informal source | Medium-Low |
| Old data, conflicting sources, or ambiguous | Low |

**The model MUST**:

- Include confidence level in the synthesis frontmatter
- Add confidence notes explaining the assessment
- Surface low-confidence claims explicitly in the Uncertain section

**Confidence calculation factors** (from [Fidelity Rules](../summarizer/references/fidelity-rules.md) Rule 6):

- **Freshness**: How recent is the source? Dated information reduces confidence
- **Authority**: Official docs > community posts > informal sources
- **Agreement**: Multiple sources agreeing increases confidence
- **Completeness**: Partial or truncated sources reduce confidence

### Step 5: Synthesize

Produce a narrative synthesis with proper attribution:

**Rules**:

- Use the structured output format from [Structured Summary](../summarizer/templates/structured.md)
- Set `source_type: multi-source` in frontmatter
- List all source paths in `source_path` as a YAML list
- Attribute claims to their sources inline: `(source: A)` or `(sources: A, B, C)`
- Do NOT add information not present in any source
- Do NOT resolve conflicts by picking one version without stating the choice

**Attribution format**:

```markdown
JWT tokens expire after 24 hours (source: API Documentation v2.3). However, the Developer Guide states tokens expire after 12 hours. This discrepancy requires clarification.
```

### Step 6: Format Based on Result Count

Choose detail level based on the number of distinct findings after deduplication:

| Result Count | Strategy | Format |
|--------------|----------|--------|
| Small (1-5 findings) | Present each finding with full detail | Bulleted list with inline attribution |
| Medium (6-15 findings) | Group by theme, provide detail within each theme | Themed sections with subsections |
| Large (16+ findings) | High-level summary + offer drill-down | Executive summary + detailed sections |

**Small result set example**:

```markdown
## Summary

Four key capabilities were identified:

- JWT authentication with 24-hour token expiration (source: API Docs)
- Rate limiting at 100 requests/min per API key (sources: API Docs, Developer Guide)
- WebSocket support for real-time updates (source: Developer Guide)
- Webhook notifications for asynchronous events (source: Integration Guide)
```

**Large result set example**:

```markdown
## Summary

The synthesis covers 23 distinct API capabilities across 5 categories: authentication, rate limiting, real-time features, data formats, and error handling.

### Authentication (5 findings)

[Detailed subsection with attributions...]

### Rate Limiting (4 findings)

[Detailed subsection with attributions...]

[Additional sections...]

See "What Was Found" section for complete enumeration with source references.
```

## Conflict Handling

When sources disagree, the model MUST surface conflicts explicitly:

**Rules**:

- NEVER silently pick one version when sources conflict
- State both versions with their sources
- Add the conflict to the Uncertain section
- If one source is clearly more authoritative or recent, note that but present both
- Recommend verification or clarification to the user

**Conflict pattern**:

```markdown
## Uncertain

- Token expiration time: API Documentation v2.3 states 24 hours, but Developer Guide v1.8 states 12 hours. The API Documentation is more recent (2026-01-15 vs 2025-11-03), but both are official sources. Recommend testing or contacting support for clarification.
```

## Multi-Source Output Format

Use the structured format from [Structured Summary](../summarizer/templates/structured.md) with these multi-source specifics:

**YAML frontmatter**:

```yaml
---
source_type: multi-source
source_path:
  - /path/to/source-a.md
  - https://example.com/source-b
  - /path/to/source-c.pdf
summarized_at: "2026-02-06T14:32:00Z"
method: hybrid
word_count_source: null
word_count_summary: 847
compression_ratio: null
confidence: medium
confidence_notes: "Three sources from 2025-2026, all authoritative. One minor conflict on token expiration requires verification."
---
```

**Body sections** (all required):

1. **Summary** - The synthesized narrative
2. **What Was Found** - Deduplicated findings with multi-source attributions
3. **What Was NOT Found** - Items searched across all sources but absent
4. **Uncertain** - Conflicts, ambiguities, items requiring clarification
5. **Sources** - Complete list with access dates

## Team Coordination Mode

When this skill is invoked after a team-based summarization (teammates instead of subagents), the synthesis workflow is the same but the input format differs:

### Input: Teammate Messages vs Subagent Returns

| Orchestration | Input to Synthesis |
|---|---|
| Subagents | Summary text returned directly from Agent tool calls |
| Teammates | Findings delivered via Teammate inbox messages to the leader |

### Cross-Checking During Summarization

In team mode, teammates message each other directly when they discover overlapping or contradictory information. This means some deduplication and conflict detection happens *during* the map step rather than only in this reduce step.

The leader MUST still run the full synthesis workflow (Steps 1-6) on the collected findings. Teammate cross-checking reduces but does not eliminate the need for post-hoc deduplication and conflict handling.

### Leader Responsibilities

1. Collect all teammate findings from the inbox
2. Run the synthesis workflow (Steps 1-6) on the collected findings
3. Request shutdown for all teammates after synthesis is complete
4. Cleanup the team

SOURCE: Team coordination pattern from [Claude Code agent teams](https://code.claude.com/docs/en/agent-teams.md) (accessed 2026-02-06); see `agent-orchestration:parallel-work`. Swarm pattern (self-organizing workers with shared task list) applied to multi-source summarization.

## Output Rendering

1. **Read template** - Load the template file at `../summarizer/templates/{format_id}.md` (default: `structured`). The template defines the schema, required sections, and fidelity constraints for the selected format.
2. **Render** - Produce output following the template's Schema section. Use the template's Example as a reference for structure and style.
3. **Verify fidelity** - Confirm the output satisfies the template's Fidelity Constraints and all applicable [Fidelity Rules](../summarizer/references/fidelity-rules.md).

## Anti-Patterns

The model MUST NOT:

- List results source-by-source instead of clustering by theme
- Bury the answer under methodology descriptions
- Present uncertain information with the same confidence as well-supported facts
- Silently resolve conflicts by picking one version
- Drop source citations during deduplication
- Re-summarize the individual summaries (violates [Fidelity Rules](../summarizer/references/fidelity-rules.md) Rule 5)
- Upgrade "not found in any source" to "doesn't exist"
- Omit the confidence assessment
- Fail to distinguish between single-source and multi-source agreement

## Sources

This skill is adapted from Anthropic's knowledge-synthesis skill in the knowledge-work-plugins repository (accessed 2026-02-06). Synthesis workflow steps, confidence scoring methodology, and result set size strategies are derived from that source.
