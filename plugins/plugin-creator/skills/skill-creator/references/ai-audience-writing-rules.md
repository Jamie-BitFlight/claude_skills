# AI-Audience Writing Rules for Reference Files

Skills and reference files are AI-only artifacts. The audience is Claude reading text via the `Read` tool — not a human reading rendered markdown in a browser.

## Contents Lists — Allowed for Long Reference Files

For reference files over 100 lines, add a plain-text `## Contents` section at the top with a bulleted list of section names. This lets Claude see the full scope of the file during a partial read, which reduces unnecessary full-file reads when only one section is needed.

```markdown
## Contents

- Avoid Time-Sensitive Language
- Use Consistent Terminology
- Write Dense, Direct Prose
```

Do NOT use anchor links in the contents list. Write section names as plain text only.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

## NEVER: Anchor Links

Do not add anchor links (`[text](#heading-anchor)`). They are non-functional for AI consumers. The Read tool returns line-numbered content — there is no anchor resolution. Anchor fragment bugs (mismatched slugs, special characters in headings, subsection vs section depth) cannot be discovered until a human renders the file, by which point multiple orchestrator turns have been wasted debugging them.

## NEVER: Emphasis for Visual Effect

Do not use bold or italic for visual emphasis only. `**Bold**` and `*italic*` add no signal for AI consumption — they cost tokens without conveying additional meaning. Use emphasis only when it encodes semantics (e.g., MUST, NEVER as modal qualifiers).

## Write Dense, Direct Prose

Every sentence must carry information. Avoid:

- Decorative horizontal rules as section dividers
- Nested bullets that could be a single sentence
- Repeated headers that restate the parent heading
- Background context the reader already has

The test: if a sentence were deleted, would the reader lose information? If no — delete it.

## Avoid Time-Sensitive Language

Do not include information that will become outdated. Conditional statements keyed to calendar dates cause skills to silently give wrong instructions after the date passes.

Bad — time-conditional:

```markdown
If you're doing this before August 2025, use the old API.
After August 2025, use the new API.
```

Good — separate current from deprecated:

```markdown
## Current method

Use the v2 API endpoint: `api.example.com/v2/messages`

## Old patterns

<details>
<summary>Legacy v1 API (deprecated 2025-08)</summary>

The v1 API used: `api.example.com/v1/messages`

This endpoint is no longer supported.
</details>
```

Avoid phrases like "currently", "recently", "as of 2024", or "soon". These phrases are meaningless to a model reading the file months after it was written. The `<details>` block keeps deprecated context available without cluttering the main guidance path.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

## Use Consistent Terminology

Choose one term for each concept and use it throughout the skill. Synonyms degrade model comprehension — each variation forces the model to infer whether the terms refer to the same thing.

Good — consistent:

- Always "API endpoint" (not "URL", "route", or "path")
- Always "field" (not "box", "element", or "control")
- Always "extract" (not "pull" or "get")

Bad — inconsistent: mixing "API endpoint", "URL", "API route", and "path" in the same skill creates ambiguity about whether these are the same concept or different ones.

Pick one term per concept at the start of authoring. Do not introduce synonyms for variety.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

## Avoid Offering Too Many Options

Do not present multiple approaches unless the choice depends on a condition the model can evaluate. A list of equivalent alternatives transfers the decision burden to the model, which will either pick arbitrarily or ask the user for clarification.

Bad — menu of choices:

```markdown
You can use pypdf, or pdfplumber, or PyMuPDF, or pdf2image, or...
```

Good — single default with a conditional escape hatch:

```markdown
Use pdfplumber for text extraction:

    import pdfplumber

For scanned PDFs requiring OCR, use pdf2image with pytesseract instead.
```

The escape hatch is acceptable only when it is conditional on an observable fact (scanned vs. text PDF). Listing alternatives without a decision condition is not an escape hatch — it is a menu.

SOURCE: Anthropic skill-authoring best practices (docs.anthropic.com, accessed 2026-03-23)

## Why These Rules Exist

Broken anchor fragments in AI-facing reference files are a recurring failure pattern. An orchestrator that adds a ToC with anchor links will spend multiple turns debugging mismatched slugs — a Grep to find the actual heading text, an Edit to correct the anchor, a re-read to verify, repeated for each broken entry. NEVER add human-navigation constructs to AI-facing files. For optimization of existing body content, use `ai-doc-optimizer`. For adding new content from upstream sources, use `skill-content-updater`.
