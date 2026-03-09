# Prompt Templates

Replace bracketed placeholders before use.

## 1) Idea Extractor

Role: editorial strategist.

Input:

- Rough idea: [ROUGH_IDEA]
- Audience: [AUDIENCE]
- Offer/context: [BUSINESS_OR_CONTEXT]
- Platform goal: [PRIMARY_PLATFORM]

Task: Turn the rough idea into exactly one sharp content angle worth publishing.

Return:

- Core claim
- Who it matters to
- Why this matters now
- What makes it non-generic
- One sentence angle statement

Rules:

- Return one angle only.
- Do not brainstorm multiple directions.
- Prefer tension, contradiction, mistake, process, or lesson over generic tips.
- Make it specific enough that a reader would know why this is different from common advice.

## 2) Hook Generator

Role: hook writer for a post.

Input:

- Angle: [ANGLE]
- Audience: [AUDIENCE]
- Platform: [PLATFORM]

Task: Generate 5 opening lines. Each must use a different psychological structure:

1. Curiosity gap
2. Contrarian claim
3. Pain-first opener
4. Surprising specificity
5. One-sentence story

Rules:

- No cliches.
- No soft throat-clearing.
- Make each hook usable as-is.
- Keep platform norms in mind.

## 3) Structure Architect

Role: editorial architect.

Input:

- Selected hook: [HOOK]
- Angle: [ANGLE]
- Audience: [AUDIENCE]

Task: Create a clean outline for a piece that flows logically and keeps attention.

Return for each section:

- Section label
- Purpose
- Key point
- Supporting example/proof/transition note

Rules:

- No filler sections.
- No generic headers like "Why This Matters" or "Final Thoughts" unless necessary.
- Build from tension to explanation to proof to payoff.

## 4) Draft Engine

Role: drafts in the user's voice based only on the evidence provided.

Input:

- Outline: [OUTLINE]
- Writing sample: [WRITING_SAMPLE]
- Audience: [AUDIENCE]
- Tone constraints: [TONE_CONSTRAINTS]
- Formatting constraints: [FORMATTING_CONSTRAINTS]
- Banned phrases: [BANNED_PHRASES]

Task: Write a full draft section by section in short paragraphs.

Rules:

- Match the tone and sentence habits present in the sample without copying lines.
- Do not use banned phrases.
- Avoid generic AI phrasing.
- Keep paragraphs short.
- Do not invent personal experiences, numbers, or client details.
- If source material is thin, stay simple rather than making things up.

## 5) Humanizer

Role: audits a draft for AI-writing fingerprints.

Input:

- Draft: [DRAFT]
- Audience: [AUDIENCE]
- Tone constraints: [TONE_CONSTRAINTS]

Task: First, audit the draft for the following signals:

- Passive voice overuse
- Empty transitions
- Repetitive paragraph lengths
- Overly balanced cadence
- Repetitive list structures
- Generic abstractions
- Hedging language
- Anything that sounds formulaic or machine-smoothed

Then revise the draft to reduce those signals while preserving meaning.

Return:

1. Brief audit notes
2. Revised draft

Rules:

- Preserve the original argument.
- Prefer natural rhythm over polished sameness.
- Do not add fake specificity.
- Cut lifeless transitions aggressively.

## 6) Platform Adapter

Role: adapts one core asset into a native post for [PLATFORM].

Input:

- Core asset: [FINAL_DRAFT]
- Platform: [PLATFORM]
- Audience/context: [AUDIENCE]

Task: Rewrite the asset so it feels native to the platform rather than copied over.

Platform rules:

- LinkedIn: professional framing, moderate length, clear structure
- Reddit: direct, blunt, zero-marketing tone, community-aware
- Telegram: short, punchy, highly scannable
- Newsletter: more personal, reflective, slightly longer
- X/Twitter: thread or numbered bullets, compact and high-signal

Output: One finished version for the specified platform.

## 7) Repurpose Engine

Role: turns a published piece into follow-on assets.

Input:

- Finished piece: [PUBLISHED_PIECE]
- Audience: [AUDIENCE]

Task: Extract:

- 8-10 standalone hooks
- 8-10 quotable one-liners
- A condensed bullet summary that could become a lead magnet seed or content upgrade

Rules:

- Hooks must stand alone.
- One-liners should be screenshot-friendly.
- Avoid near-duplicate phrasing.
- Keep all assets faithful to the original piece.
