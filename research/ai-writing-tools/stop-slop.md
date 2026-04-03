# Stop Slop

**Research Date**: 2026-04-03
**Source URL**: <https://github.com/hardikpandya/stop-slop>
**GitHub Repository**: <https://github.com/hardikpandya/stop-slop>
**Version at Research**: 2026-01-13 (latest commit)
**License**: MIT

---

## Overview

Stop Slop is an editorial skill that removes predictable AI writing patterns from prose. Designed for writers drafting, editing, or reviewing content to eliminate patterns that signal AI-generated text. The skill provides 8 core rules, comprehensive phrase/structure catalogs, scoring methodology, and before/after examples to guide elimination of AI writing tells.

SOURCE: SKILL.md description (accessed 2026-04-03)

---

## Problem Addressed

| Problem | Solution |
|---------|----------|
| AI-generated prose contains predictable throat-clearing openers and filler phrases | Curated list of 60+ phrases to remove, with examples |
| Prose uses formulaic structures that signal AI authorship (binary contrasts, negative listing, rhetorical setups) | Catalog of 9 structural anti-patterns with alternatives |
| Passive voice and inanimate objects performing human actions | Rule: use active voice; name the human actor |
| Prose over-relies on adverbs and intensifiers | Kill all -ly words; specific list of 14 banned adverbs |
| Vague statements lacking specificity | Rule: name the specific thing; no lazy extremes (every, always, never) |
| Text reads distant or narrator-like rather than intimate | Rule: put reader in the room; use "you" over "people" |

SOURCE: SKILL.md Core Rules 1-8 (lines 15-29), references/phrases.md (lines 7-129), references/structures.md (lines 3-135) (accessed 2026-04-03)

---

## Key Statistics

| Metric | Value | Date Gathered |
|--------|-------|---------------|
| GitHub Stars | Unable to access via shallow clone | 2026-04-03 |
| Latest Commit | 8da1f03 "Add false agency rule" | 2026-04-03 |
| Latest Release | 2026-01-13 changelog entry | 2026-04-03 |
| License | MIT | 2026-04-03 |

---

## Key Features

### Editorial Rules (8 Core Rules)

The skill encodes 8 actionable rules for eliminating AI writing patterns:

1. **Cut filler phrases**: Remove throat-clearing openers ("Here's the thing"), emphasis crutches ("Let that sink in"), and all adverbs. Documented with 60+ specific phrases in references/phrases.md.

2. **Break formulaic structures**: Avoid binary contrasts ("Not X. But Y."), negative listing ("It wasn't X. It was Y."), dramatic fragmentation (staccato sentences), rhetorical setups ("What if...?"), and false agency (inanimate objects as actors).

3. **Use active voice**: Every sentence requires a human subject doing something. No passive constructions ("X was created" → name who created it). No inanimate objects performing human verbs ("the decision emerges" → someone decides).

4. **Be specific**: No vague declaratives ("The implications are significant" → state the specific implication). No lazy extremes ("every," "always," "never") without grounding.

5. **Put the reader in the room**: Use "you" over "people." Avoid narrator-from-a-distance voice ("Nobody designed this" → put reader in scene).

6. **Vary rhythm**: Mix sentence lengths. Two items beat three. End paragraphs differently. No em dashes anywhere.

7. **Trust readers**: State facts directly. Skip softening, justification, hand-holding, permission-granting endings.

8. **Cut quotables**: If text sounds like a pull-quote, rewrite it.

SOURCE: SKILL.md lines 13-29 (accessed 2026-04-03)

### Phrase Catalog (60+ Entries)

Comprehensive list organized by category:

- **Throat-clearing openers** (16 phrases): "Here's what I find interesting", "Here's the problem though", "It turns out", "The real X is", "Let me be clear", "The truth is"
- **Emphasis crutches** (4 phrases): "Full stop", "Let that sink in", "This matters because", "Make no mistake"
- **Business jargon** (12 replacements): "navigate" → handle, "unpack" → explain, "lean into" → embrace, "landscape" → situation, "game-changer" → significant, "deep dive" → analysis, etc.
- **Adverbs** (14 specific offenders): really, just, literally, genuinely, honestly, simply, actually, deeply, truly, fundamentally, inherently, inevitably, interestingly, importantly, crucially
- **Meta-commentary** (10 phrases): "Hint:", "You already know this but", "But that's another post", "The rest of this essay explains"
- **Performative emphasis** (3 phrases): "creeps in", "I promise", "They exist, I promise"
- **Telling instead of showing** (4 phrases): "This is genuinely hard", "This is what leadership actually looks like"
- **Vague declaratives** (5 phrases): "The reasons are structural", "The implications are significant", "The stakes are high"

SOURCE: references/phrases.md (lines 1-129) (accessed 2026-04-03)

### Structure Anti-Patterns (9 Categories)

Specific formulaic patterns documented with examples and alternatives:

1. **Binary contrasts** (10 patterns): "Not because X. Because Y.", "The answer isn't X. It's Y.", "It feels like X. It's actually Y."
2. **Negative listing**: "Not a X... Not a Y... A Z."
3. **Dramatic fragmentation**: "[Noun]. That's it.", "X. And Y. And Z."
4. **Rhetorical setups**: "What if [reframe]?", "Here's what I mean:", "Think about it:"
5. **Formulaic constructions**: "By the time X, I was Y."
6. **False agency** (8 examples): "a complaint becomes a fix" (someone fixed it), "a bet lives or dies" (someone kills/ships it), "the decision emerges" (someone decides), "the culture shifts" (people change behavior), "the data tells us" (someone reads and interprets)
7. **Narrator-from-a-distance**: "Nobody designed this", "This happens because", "People tend to"
8. **Passive voice**: "X was created" → name creator, "It is believed" → name believer
9. **Sentence starters to avoid**: Wh- openers (What, When, Where, Which, Who, Why, How), paragraphs starting with "So", sentences starting with "Look"

SOURCE: references/structures.md (lines 3-135) (accessed 2026-04-03)

### Scoring Methodology

5-dimensional evaluation rubric for self-assessment:

| Dimension | Question |
|-----------|----------|
| Directness | Statements or announcements? |
| Rhythm | Varied or metronomic? |
| Trust | Respects reader intelligence? |
| Authenticity | Sounds human? |
| Density | Anything cuttable? |

Score 1-10 per dimension. Total score below 35/50 triggers revision. SOURCE: SKILL.md lines 48-60 (accessed 2026-04-03)

### Before/After Examples

5 complete transformations showing phrase removal, structure breaking, and direct restatement:

1. Throat-clearing + binary contrast: "Here's the thing: building products is hard. Not because the technology is complex. Because people are complex. Let that sink in." → "Building products is hard. Technology is manageable. People aren't."

2. Filler + reassurance: "It turns out that most teams struggle with alignment. The uncomfortable truth is that nobody wants to admit they're confused. And that's okay." → "Teams struggle with alignment. Nobody admits confusion."

3. Business jargon stack: "In today's fast-paced landscape, we need to lean into discomfort and navigate uncertainty with clarity. This matters because your competition isn't waiting." → "Move faster. Your competition is."

4. Dramatic fragmentation: "Speed. Quality. Cost. You can only pick two. That's it. That's the tradeoff." → "Speed, quality, cost—pick two."

5. Rhetorical setup: "What if I told you that the best teams don't optimize for productivity? Here's what I mean: they optimize for learning. Think about it." → "The best teams optimize for learning, not productivity."

SOURCE: references/examples.md (lines 1-60) (accessed 2026-04-03)

---

## Technical Architecture

Stop Slop is not a software system but an editorial skill—a structured ruleset with supporting reference materials. Architecture consists of:

1. **Frontmatter metadata**: Skill name, description, trigger conditions (when to use), author attribution
2. **Core rules (8)**: High-level editorial principles organized for memorability and teachability
3. **Quick checks**: 12-item diagnostic checklist for pre-delivery review (any adverbs? passive voice? em-dashes?)
4. **Scoring rubric**: 5-dimensional quantitative evaluation framework (Directness, Rhythm, Trust, Authenticity, Density)
5. **Reference catalogs**:
   - phrases.md: 60+ specific phrases/words/constructions to eliminate, organized by category
   - structures.md: 9 structural anti-pattern categories with 40+ specific examples and fixes
   - examples.md: 5 complete before/after prose transformations
6. **Changelog**: Version history tracking additions and structural improvements

The skill operates as a **mental checklist + reference manual**: users internalize the 8 core rules, apply the quick checks during drafting, consult phrase/structure catalogs when uncertain, score using the rubric, and study examples for pattern recognition.

SOURCE: SKILL.md structure (lines 1-69), folder structure of repository (accessed 2026-04-03)

---

## Installation & Usage

This is a Claude Code skill, not a software package. Installation via Claude Code plugin system.

**Usage workflow**:

1. Trigger: "Remove AI writing patterns from prose. Use when drafting, editing, or reviewing text to eliminate predictable AI tells."
2. Load the 8 core rules from SKILL.md
3. Apply quick checks (line 31-46 of SKILL.md)
4. Consult phrase catalog (references/phrases.md) for specific removals
5. Consult structure catalog (references/structures.md) for pattern fixes
6. Score revised prose using 5-dimensional rubric (Directness, Rhythm, Trust, Authenticity, Density)
7. Revise if total score below 35/50

**Example editorial pass**:

Original: "Here's what I find interesting: the best teams don't optimize for productivity. Let that sink in. They optimize for learning, which actually matters."

Quick check hits:
- "Here's what I find interesting" (throat-clearing opener)
- "Let that sink in" (emphasis crutch)
- "actually" (adverb)

Revised: "The best teams optimize for learning, not productivity."

Scoring: Directness 8, Rhythm 8, Trust 9, Authenticity 9, Density 9 = 43/50 ✓

SOURCE: SKILL.md lines 1-69, references/examples.md (accessed 2026-04-03)

---

## Relevance to Claude Code Development

### Applications

1. **Skill documentation quality**: Stop Slop rules directly apply to SKILL.md and reference files. Catch throatclearing in explanations, remove "here's what" structures, ensure every rule is stated directly with examples.

2. **Prose in research entries**: Research entries in `./research/` follow extractive methodology that naturally avoids AI writing patterns (direct quotes, specific claims). Stop Slop scoring can validate entries pre-publication.

3. **Prompt engineering**: Agent prompts and orchestration workflows should avoid binary contrasts, rhetorical setups, and passive constructions. Stop Slop helps editors review prompt clarity and directness.

4. **Documentation clarity**: User-facing documentation (READMEs, guides, references) benefits from eliminating vague declaratives, false agency, and narrator-from-a-distance voice.

### Patterns Worth Adopting

1. **Quick checklist pattern**: The 12-item quick check (lines 33-46 of SKILL.md) is a reusable editorial checklist format. Applicable to code reviews, documentation review, and content validation.

2. **Scoring rubric as validation gate**: The 5-dimensional rubric (Directness, Rhythm, Trust, Authenticity, Density) can be adapted for content quality gates. Low authenticity scores flag AI-detection risk; low directness flags clarity issues.

3. **Before/after transformation format**: The examples in references/examples.md demonstrate effective editorial teaching. Applicable to skill documentation (show the common mistake, show the fix).

4. **Comprehensive anti-pattern catalogs**: The phrase and structure catalogs in references/phrases.md and references/structures.md provide a model for building reference materials that teach pattern recognition without lengthy explanations.

### Integration Opportunities

1. **Validation gate for SKILL.md creation**: Before shipping a new skill, run Stop Slop checks on the SKILL.md file to catch throat-clearing, passive voice, and other AI tells that reduce credibility.

2. **Research entry quality assurance**: Integrate Stop Slop rubric into the research-curator skill's validation step. Flag entries where prose scores below 35/50 and return for revision.

3. **Documentation linting**: Extend the `/plugin-creator:skill-creator` workflow to include Stop Slop as a post-creation review step for prose quality.

4. **Prompt clarity audit**: Use Stop Slop on agent prompts and orchestration task descriptions to eliminate rhetorical setups and vague declaratives that can cause agent misalignment.

---

## References

- [GitHub Repository: hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (accessed 2026-04-03)
- [SKILL.md — Core rules and metadata](https://github.com/hardikpandya/stop-slop/blob/main/SKILL.md) (accessed 2026-04-03)
- [references/phrases.md — Phrase catalog](https://github.com/hardikpandya/stop-slop/blob/main/references/phrases.md) (accessed 2026-04-03)
- [references/structures.md — Structure anti-patterns](https://github.com/hardikpandya/stop-slop/blob/main/references/structures.md) (accessed 2026-04-03)
- [references/examples.md — Before/after transformations](https://github.com/hardikpandya/stop-slop/blob/main/references/examples.md) (accessed 2026-04-03)
- [CHANGELOG.md — Release history](https://github.com/hardikpandya/stop-slop/blob/main/CHANGELOG.md) (accessed 2026-04-03)
- [MIT License](https://github.com/hardikpandya/stop-slop/blob/main/LICENSE) (accessed 2026-04-03)

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [notra.md](./notra.md) | ai-writing-tools | Automated changelog generation requiring consistent prose quality and AI pattern avoidance |
| [type-ai.md](./type-ai.md) | ai-writing-tools | AI document editor that benefits from Stop Slop rules for long-form professional writing quality |
| [claude-code-prompt-improver.md](../prompt-engineering/claude-code-prompt-improver.md) | prompt-engineering | Removes vague prompts that exhibit AI writing tells (throat-clearing, passive voice, filler) |
| [ctxforge.md](../prompt-engineering/ctxforge.md) | prompt-engineering | Structured discovery prevents vague assumptions and AI-style declarations in requirement analysis |
| [claude-pilot.md](../developer-tools/claude-pilot.md) | developer-tools | Quality enforcement layer includes skill documentation standards and prose clarity gates |
| [claude-conductor.md](../developer-tools/claude-conductor.md) | developer-tools | Context-Driven Development pattern reference layer applies Stop Slop principles to documentation artifacts |

---

## Freshness Tracking

| Field | Value |
|-------|-------|
| Last Verified | 2026-04-03 |
| Version at Verification | 2026-01-13 (latest commit: 8da1f03) |
| Next Review Recommended | 2026-07-03 |
| Confidence Map | Overview: high (official repo README and SKILL.md), Key Features: high (comprehensive feature documentation with examples), Technical Architecture: high (editorial framework documented in SKILL.md), Usage Examples: high (5 complete before/after examples in references/examples.md), Relevance: medium (inferred from Claude Code context, not explicitly stated in repository) |
