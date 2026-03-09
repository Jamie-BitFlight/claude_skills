---
name: seven-prompt-content-engine
description: Walk a user from one rough content idea to a finished post, platform-adapted variants, and repurposed follow-on assets using a 7-step sequential prompting workflow. Use when the user wants help turning a half-formed idea, frustration, story, or client situation into publishable content quickly and consistently.
---

# Seven Prompt Content Engine

## Purpose

Runs a fixed 7-step sequential pipeline that converts a rough idea into a finished, platform-adapted content asset plus standalone repurposed outputs. Each step consumes the prior step's output. Do not skip steps unless the user explicitly provides the missing upstream material.

## When to Use

Invoke this skill when the user wants to:

- Turn a rough thought, frustration, client situation, or lesson into a finished post
- Build a repeatable content system with consistent structure
- Generate hooks, outlines, drafts, and platform variants in one pass
- Reduce blank-page time with a guided process
- Make AI writing sound more human
- Repurpose one piece into many standalone assets

Do not invoke this skill when the user only wants:

- Proofreading or light editing with no process
- Generic brainstorming with multiple broad options returned
- A one-off rewrite with no repeatable framework

## Core Operating Rules

- Keep the chain linear — output of each step is the input for the next
- Default to one strong angle in Step 1; never return a menu of broad topics
- Preserve the user's audience, offer, and lived experience whenever known
- Prefer specificity over polish in early steps (Steps 1–3)
- In Step 4, match only voice constraints the user explicitly provides; do not claim perfect voice-matching
- In Step 5, audit for detectable AI patterns, not just grammar
- In Step 6, adapt natively per platform; do not copy-paste the same text across destinations
- In Step 7, extract assets that stand alone without the original piece
- If the user provides a URL to a writing sample or source material, read it before drafting
- Pause after any step if the user asks to revise; otherwise continue through the full chain

## Intake

Collect or infer before starting:

| Input | Required | Notes |
|-------|----------|-------|
| Rough idea / frustration / client situation / lesson / observation | Required | Core material for Step 1 |
| Target audience | Required | Shapes angle, voice, platform fit |
| Desired platform or primary destination | Required | Drives Step 6 |
| Offer / business context | Optional | Sharpens angle specificity in Step 1 |
| Writing sample | Optional | Used in Step 4 for voice matching |
| Banned phrases / tone constraints / formatting constraints | Optional | Applied in Steps 4 and 5 |

If some items are missing, proceed with the rough idea and clearly label assumptions before Step 1 output.

## Output Format

For each step:

1. State the step name and number
2. Show the exact input being used for that step
3. Produce output in a copyable code block
4. Note briefly what carries forward to the next step
5. Label all assumptions separately when intake was incomplete
6. Do not include email subject lines unless explicitly requested

## Step 1 — Idea Extractor

Goal: Convert a messy idea into one sharp, specific content angle.

Input: rough topic, frustration, story, client situation, insight, or half-formed thought.

Output: exactly one angle with all four components:

- Core claim
- Who it matters to
- Why it is interesting now
- What makes it non-generic

Constraints:

- One angle only — no menus of options
- Avoid broad educational framing ("here's how X works")
- Favor tension, contrast, process reveal, mistake, or hard-earned lesson as the angle type

## Step 2 — Hook Generator

Goal: Generate multiple opening lines from the chosen angle.

Output: 5 hooks using these five structures, one each:

1. Curiosity gap
2. Contrarian claim
3. Pain-first opener
4. Surprising specificity or stat-like framing
5. One-sentence story

Constraints:

- No soft intros ("In today's post...", "Have you ever wondered...")
- No clichés
- Each hook must sound plausible for the target platform

## Step 3 — Structure Architect

Goal: Create a tight outline that earns attention and carries the argument.

Input: selected hook from Step 2 plus the angle from Step 1.

Output: clean outline with only necessary sections. Per section include:

- Section purpose
- Key point
- Proof, example, or transition note

Constraints:

- No filler headers
- Exclude "Why This Matters" or "Final Thoughts" unless genuinely required by the argument
- Section sequence: tension → explanation → proof → payoff

## Step 4 — Draft Engine

Goal: Turn the outline into a draft that approximates the user's voice.

Input: outline from Step 3, user writing sample (if available), voice constraints and banned phrases.

Output: full draft in short paragraphs.

Constraints:

- Match observed tone only from evidence the user provided; never fabricate voice characteristics
- Avoid over-explaining — trust the reader
- Avoid stock AI phrasing ("It's worth noting that...", "Delve into...", "In conclusion...")
- Respect all banned phrases and formatting rules the user stated

## Step 5 — Humanizer

Goal: Audit and revise the draft to remove AI-signaling patterns.

Required audit categories — check each explicitly:

- Passive voice overuse
- Empty transitions ("Additionally...", "Furthermore...", "Moreover...")
- Repetitive paragraph lengths
- Symmetrical list cadence (all bullets same length)
- Overly balanced sentence rhythm
- Generic abstractions without lived detail
- Hedging that weakens conviction ("might", "could potentially", "it seems")
- Fake specificity or invented numbers not grounded in user's material

Output in two parts:

1. Concise audit listing detected issues per category
2. Revised draft with those patterns reduced

Constraints:

- Preserve meaning and voice
- Prefer uneven but natural rhythm over artificial smoothness
- Add concrete detail only if grounded in the user's source material

## Step 6 — Platform Adapter

Goal: Convert the core asset into platform-native variants.

Supported platforms: LinkedIn, Reddit, Telegram, newsletter, X/Twitter thread.

Output: one version per platform requested by the user.

Per-platform constraints:

- LinkedIn — professional framing, moderate length, clear paragraph breaks for readability
- Reddit — direct, blunt, community-aware tone, no marketing sheen or self-promotion framing
- Telegram — compressed, punchy, mobile-friendly; remove long preamble
- Newsletter — more personal and reflective; allow longer sentences and narrative warmth
- X/Twitter thread — break into concise numbered posts or bullets; strong open post, strong close post

## Step 7 — Repurpose Engine

Goal: Create follow-on assets from the finished piece.

Output:

- 8–10 standalone hooks (each works without reading the original piece)
- 8–10 quotable one-liners (screenshot-friendly length and format)
- Condensed bullet summary usable as lead magnet seed or content upgrade

Constraints:

- Each hook must be self-contained — no references to "the post" or "as mentioned above"
- One-liners must fit a single screenshot without truncation
- Summary must be dense, clear, and reusable as a standalone asset

## Prompt Templates

Use the templates in [./references/prompt-templates.md](./references/prompt-templates.md).


## Quality Checklist

Show this checklist to the user before finalizing any full pipeline run:

- [ ] The angle is singular and specific
- [ ] The hook matches the angle
- [ ] The outline has no filler sections
- [ ] The draft reflects actual source material provided by the user
- [ ] The humanizer pass removed detectable AI patterns
- [ ] Each platform version feels native to that platform
- [ ] Repurposed assets are distinct, not paraphrase duplicates of each other
