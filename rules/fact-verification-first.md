# Fact Verification First

When a prompt names a specific product, technology, version, or release event, verification MUST be a `WebSearch` (or `mcp__Ref-local__ref_search_documentation`) call to confirm existence, release status, current version, and specs. No planning, design, or code generation may occur before this verification step completes.

## Trigger Patterns

| Trigger Type | Pattern Examples |
|---|---|
| Named product (hardware/device) | "DJI Pocket 4", "iPhone 17", "Nano Banana Pro" |
| Named software product or AI model | "Gemini 3 Pro", "Claude Sonnet 5", "GPT-5" |
| Versioned library or framework | "React 20", "fastmcp v2.3", "Python 3.14" |
| Semantic version string | "v1.2.3", "2.0.0-beta", "v3.0.0-rc1" |
| Named release event or launch | "Gemini 3 Pro launch", "OpenAI DevDay 2026" |
| Named API or service (possibly changed since training) | "Anthropic Files API", "OpenAI Assistants API v2" |

## What Does NOT Trigger Verification

- Generic categories without a version or product name — "Python", "React", "a language model"
- Hedging language in the prompt — those trigger the hedging-language stop rule in AGENTS.md's Identity and Working Norms section (`- Output containing "likely", "probably", or "I think"...`), not this rule
- Hypothetical or conditional framing — "if DJI releases a Pocket 4", "suppose React adds X"
- Historical or canonical references with well-established, stable facts — "HTTP/1.1", "the Unix epoch"

Satisfying this rule does not substitute for the reactive `/fact-check` pass when that skill is triggered.
