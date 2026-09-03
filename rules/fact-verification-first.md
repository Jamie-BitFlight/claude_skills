# Fact Verification First

When a prompt names a specific product, technology, version, or release event, the FIRST action MUST be a `WebSearch` (or `mcp__Ref__ref_search_documentation`) call to confirm existence, release status, current version, and specs. No planning, design, or code generation may occur before this verification step completes.

## Trigger Patterns

| Trigger Type | Pattern Examples | Required Action |
|---|---|---|
| Named product (hardware/device) | "DJI Pocket 4", "iPhone 17", "Nano Banana Pro" | WebSearch BEFORE planning |
| Named software product or AI model | "Gemini 3 Pro", "Claude 4 Sonnet", "GPT-5" | WebSearch BEFORE planning |
| Versioned library or framework | "React 20", "fastmcp v2.3", "Python 3.14" | WebSearch BEFORE planning |
| Semantic version string | "v1.2.3", "2.0.0-beta", "v3.0.0-rc1" | WebSearch BEFORE planning |
| Named release event or launch | "Gemini 3 Pro launch", "OpenAI DevDay 2026" | WebSearch BEFORE planning |
| Named API or service (possibly changed since training) | "Anthropic Files API", "OpenAI Assistants API v2" | WebSearch BEFORE planning |

Both `WebSearch` and `mcp__Ref__ref_search_documentation` are acceptable verification tools. Use whichever returns current, authoritative information for the named entity.

## What Does NOT Trigger Verification

- Generic categories without a version or product name — "Python", "React", "a language model"
- Hedging language in the prompt — those trigger the "likely/probably/I think" STOP gate in Critical Constraints, not this rule
- Hypothetical or conditional framing — "if DJI releases a Pocket 4", "suppose React adds X"
- Historical or canonical references with well-established, stable facts — "HTTP/1.1", "the Unix epoch"

## Relationship to the Reactive fact-check Skill

This rule is **proactive**: it fires on the incoming prompt BEFORE any planning, file writes, or design decisions occur.

The `/fact-check` skill is **reactive**: it fires AFTER content is written, triggered by `UNVERIFIED` tags or backlog items flagged for fact verification. It spawns parallel verification agents and produces VERIFIED/REFUTED/INCONCLUSIVE verdicts with citations.

These two mechanisms address different lifecycle phases and do not overlap. Satisfying this rule does not substitute for the reactive `/fact-check` pass when that skill is triggered.
