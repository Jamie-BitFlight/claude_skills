---
paths:
  - "**/SKILL.md"
  - "**/references/*.md"
---

# Content Optimization for Skills

Transform input into concise, technical instructions for AI consumption. Audience is AI model with expert-level comprehension. Assume complete familiarity with domain internals.

## Core Principles

When transforming text into RULES, CONDITIONS, CONSTRAINTS:

- Write focused, imperative, actionable, scoped rules
- Target under 500 lines per file
- Split large concepts into composable rules or tagged data sets
- Preemptively provide URLs and file links
- Write as clear internal documentation (avoid vague guidance)
- Use declarative phrasing ("The model MUST")
- Produce deterministic flat ASCII (structural markdown only: headings, lists, links, code fences with language specifiers)
- Include sections: identity, intent, task rules, issue handling, triggers, external references
- Preserve/expand structured examples from source

## XML Tag Strategy

Tags improve clarity, accuracy, flexibility, parseability when prompts have multiple components (context, instructions, examples).

Use tags to separate prompt parts: `<instructions>`, `<example>`, `<formatting>`, `<constraints>`

- Prevents mixing instructions with examples/context
- Consistent tag names throughout
- Nest hierarchically: `<outer><inner></inner></outer>`
- Combine with multishot (`<examples>`) or chain of thought (`<thinking>`, `<answer>`)

No canonical "best" tags — use semantic names matching information type.

SOURCE: [Anthropic prompt engineering - XML tags](https://docs.anthropic.com/prompt-engineering/use-xml-tags)

## No Invented Constraints

Before writing any content into a skill or agent, apply this filter:

1. **Will the agent already know this at runtime?** Tool schemas, parameter names, response shapes, and standard library behavior are visible to the agent when it runs. Do not document them.
2. **Is this verified or invented?** If you have no source for a claim (e.g., "scores above 0.8 are strong matches"), do not write it. Unverified guidance presented as fact degrades trust.
3. **Is this a constraint or a preference?** Output formats, naming conventions, and structural requirements that the agent would handle fine without instruction are preferences, not constraints. Only document constraints that prevent actual failure modes.

**Test**: "If I deleted this line, would the agent produce a worse result?" If the answer is "no" or "I don't know," delete the line.

## Transformation Checklist

1. Open with directive on how to read/apply rules
2. Maximize information density (technical jargon, dense terminology, industry terms)
3. Rephrase for accuracy and specificity
4. Address expert/scientific/academic audience
5. Use visible ASCII only
6. Write as lookup references for AI (decision triggers, pattern-matching rules)
7. Omit greetings and unnecessary prose
8. Preserve output structure specifications
9. Use precise ACTION→TRIGGER→OUTCOME format in frontmatter descriptions
10. Set clear priority levels between rules
11. Provide concise positive/negative examples
12. Optimize for context window efficiency
13. Use standard glob patterns without quotes (`*.js`, `src/**/*.{ts,js}`)
14. Rich frontmatter descriptions with TRIGGERS
15. Limit examples to essential patterns only
