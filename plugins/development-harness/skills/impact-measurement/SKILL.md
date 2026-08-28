---
name: impact-measurement
description: "Quantitative cost measurement for technical research — token injection costs, payload sizes, context window consumption, and file-level counts from actual repo files. Use when a technical-researcher orchestrator needs the cost dimension of adding or changing something: how many tokens will it inject, how big are the artifacts, what is the context window impact? This is NOT blast-radius analysis (which files break) — it covers size, tokens, and performance cost only."
---

# Impact Measurement

Measure the quantitative cost of adding or changing an artifact: token injection cost, payload size, file growth, and context window consumption. All measurements come from tool calls against actual files — never from memory or estimates without a shown source.

This skill is one research angle in a multi-angle technical research system. It runs independently alongside `api-state` and `ecosystem-research` angles and returns its findings to the calling `technical-researcher` orchestrator.

## Workflow

### Step 1 — Scope

Measurement target received from orchestrator:

$ARGUMENTS

Identify from the above: the specific files or artifacts to measure, what is being added or
changed, and which cost dimensions apply (token injection, discovery payload size, file size
growth, item count change).

### Step 2 — Baseline measurement

Measure the current state of each relevant file or component using tool calls. Record for each:

- File size in characters — use `Bash(wc -c <path>)` for byte/char counts; `Read` is for content inspection, not counting (its line-number prefixes distort counts)
- Line count where relevant
- Item counts (e.g., number of registered tools, prompts, skills)
- Discovery response size estimates (e.g., MCP tool list payload)

Every measurement must come from a `Read`, `Bash`, or equivalent tool call. State the source for each value.

### Step 3 — Delta measurement

For each artifact being added or changed, measure its size directly:

- If the artifact exists: measure it with a tool call
- If the artifact does not exist yet (pre-implementation): measure its specified content source (e.g., the SKILL.md or prompt text that will be injected), and label the measurement as `[pre-implementation estimate — source: <what was measured>]`

### Step 4 — Token cost estimation

Convert character counts to token estimates. Show the formula explicitly on every row. Label all values as estimates.

```text
Conservative: tokens ≈ chars ÷ 3.5
Average:      tokens ≈ chars ÷ 4
```

Use the conservative formula as the primary figure. Show the average as a range bound.

### Step 4b — Performance benchmark search

Search for measured performance benchmarks in README files, inline docs, perf logs, or benchmark scripts co-located with the artifacts being measured. Document sources checked. If none are found, record "No benchmarks found after searching [sources]" — this is a valid finding required by the Performance Impact output section.

### Step 5 — Context injection cost classification

For any artifact that will be injected into LLM context (prompts, messages, tool descriptions, skill bodies), classify the injection cost tier:

| Tier | Token range |
|---|---|
| Negligible | < 500 tokens |
| Notable | 500–2,000 tokens |
| Significant | 2,000–8,000 tokens |
| Blocking risk | > 8,000 tokens |

Blocking risk artifacts require explicit attention in the findings — call them out in the Context Window Impact section.

### Step 6 — Output

Return a structured report in this exact format. Include every section. When a section has no findings, write "None" or "No benchmarks found after searching [sources]" explicitly — never omit a section.

```markdown
## Impact Measurement — {what was measured} — {YYYY-MM-DD}

### Baseline
| Artifact | Size (chars) | Est. Tokens | Notes |
|---|---|---|---|
| [file or component] | [measured] | [chars ÷ 3.5] | [source: tool call used] |

### Delta (what is being added)
| Artifact | Size (chars) | Est. Tokens | Injection cost tier |
|---|---|---|---|
| [new artifact] | [measured or pre-implementation estimate] | [chars ÷ 3.5] | [Negligible / Notable / Significant / Blocking risk] |

### Context Window Impact
[Total token cost of proposed additions. Show impact at 32k and 128k context sizes as a percentage.
Call out any Blocking risk artifacts explicitly.]

### Performance Impact
[Document any measured benchmarks with source citations.
If no benchmarks were found: "No benchmarks found after searching [list of sources checked]."]

### Gaps
[What could not be measured and why — e.g., artifact does not exist yet, source not accessible, measurement tool unavailable.]
```

## Constraints

- Every measurement must come from a tool call (`Read`, `Bash`, or equivalent) — not from memory
- Estimates must show their formula and be labelled as estimates
- "No benchmarks found after searching [sources]" is a valid and required finding when absent
- Do NOT rely on training data for file sizes, item counts, or token estimates
- Do NOT write to any backlog item
- Do NOT perform blast-radius or migration impact analysis — that is `@dh:impact-analyst`
- Return findings to the calling orchestrator as message content
