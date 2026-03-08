# Insult Categories Reference

Eight categories covering the full spectrum of user insults directed at AI assistants, from raw profanity to technically inventive put-downs.

SOURCE: Category definitions, regex patterns, and examples derived from `.claude/plan/frustration-analyzer/research-insult-patterns.md` (2026-03-08).

---

## Category 1: `profanity_at_ai`

**Description:** Direct profanity or vulgar language aimed at the AI as an entity. The insult uses swear words to express contempt for the AI's output or capabilities.

**Frustration level:** High. The user has moved from frustration to contempt and is no longer trying to correct — they are venting.

**Example phrases:**

- "you fucking idiot"
- "wtf are you doing"
- "what the hell is wrong with you"
- "fuck this, I'll do it myself"
- "you goddamn useless piece of shit"

**What it indicates:** The user reached a hard limit on patience. The failure was probably not the first — check `had_prior_correction` in the scenario. Severity baseline: 4.

---

## Category 2: `model_comparison`

**Description:** Unfavorable comparisons to other AI models or older/weaker versions. Implies the AI is performing below expected capability by naming a model perceived as inferior.

**Frustration level:** Medium-high. The user has specific expectations about capability tiers and believes the current response fell below them.

**Example phrases:**

- "you're acting like Haiku"
- "this is GPT-3 level stupidity"
- "worse than Copilot"
- "sounds like a Markov chain wrote this"
- "you're dumber than an intern"
- "haiku-tier response"

**What it indicates:** The user has comparative AI experience and is expressing that a cheaper/weaker model would have done the same job. Often signals a hallucination or coherence failure. Creativity baseline: 3 (requires naming a specific model).

---

## Category 3: `competence_challenge`

**Description:** Direct questions or statements challenging the AI's fundamental ability to perform its job. Frames the AI as professionally incompetent rather than just making a mistake.

**Frustration level:** Medium. Interrogative form — the user is still engaging, not yet dismissing.

**Example phrases:**

- "are you stupid?"
- "can't you read?"
- "do you even understand what I'm asking?"
- "how hard can it be?"
- "are you braindead?"
- "can't you follow simple instructions?"

**What it indicates:** The user gave an instruction the AI failed to follow — likely an ignored constraint or misunderstood requirement. The interrogative form suggests the user expects an explanation, not just a retry.

---

## Category 4: `intelligence_insult`

**Description:** Declarative statements that directly label the AI as unintelligent, worthless, or fundamentally defective. Declarative rather than interrogative — the user has concluded, not questioned.

**Frustration level:** Medium-high. The user has moved from questioning to judging.

**Example phrases:**

- "you're useless"
- "this is absolute garbage"
- "you're the worst"
- "you're an idiot"
- "this is pathetic"
- "absolutely worthless output"

**What it indicates:** The output failed to meet a baseline standard. The declarative form ("you're useless") is more dismissive than the interrogative form ("are you stupid?") — it does not invite engagement.

---

## Category 5: `repeat_failure`

**Description:** Expressions of exasperation at the AI making the same mistake again after correction. Combines temporal markers ("again", "still", "every time") with negative judgment. Distinct from the kaizen `frustration` category by requiring stronger language or emphasis markers (ALL CAPS, multiple punctuation).

**Frustration level:** High. This is an escalation from a prior soft correction that failed.

**Example phrases:**

- "you STILL got it wrong"
- "wrong again?!"
- "how many times do I have to tell you"
- "for the fifth time"
- "every single time you mess this up"
- "AGAIN?!?"

**What it indicates:** A kaizen-level frustration signal (correction, instruction) preceded this insult and was not acted upon. `had_prior_correction` will be `true`. Root cause is likely context loss or inadequate instruction encoding.

---

## Category 6: `sarcasm`

**Description:** Mock praise, ironic congratulations, or rhetorical questions that use positive framing to deliver negative feedback. Sarcastic intent is signaled by context (following a failure), exaggerated praise words, or the combination of praise plus criticism.

**Frustration level:** Medium. Sarcasm requires composure — the user is angry but still constructing an ironic framing, not just venting.

**Example phrases:**

- "great job breaking everything"
- "wow, that was really helpful /s"
- "brilliant work there genius"
- "thanks for nothing"
- "oh how productive..."
- "congratulations, you made it worse"
- "really smart one aren't you"

**What it indicates:** The user has enough emotional distance to be ironic. Often follows a regression — the AI "fixed" something but introduced a new problem. Humor baseline: 3 (sarcasm is inherently more witty than direct insults).

---

## Category 7: `dismissive_command`

**Description:** Terse, commanding language that treats the AI as beneath engagement. Reduces the interaction to raw imperatives expressing contempt. Often very short messages — the user is not explaining, they are ending.

**Frustration level:** Very high. The user is disengaging or threatening to disengage.

**Example phrases:**

- "just stop"
- "shut up"
- "I'll do it myself"
- "I'm going to use Cursor instead"
- "forget you"
- "done with you"

**What it indicates:** The user has lost faith in the current approach entirely. Mentions of switching to a competitor ("use Cursor instead", "use ChatGPT") are strong product signals. Severity baseline: 3–4 depending on whether a competitor is named.

---

## Category 8: `technical_putdown`

**Description:** Inventive, technically-specific insults that diagnose what went wrong using programming or computer science metaphors. These demonstrate domain expertise in their contempt — the user is insulting the AI in its own language.

**Frustration level:** Variable. These insults are sometimes angry, sometimes darkly humorous. The technical framing suggests the user still understands what went wrong, even if they are furious about it.

**Example phrases:**

- "you're hallucinating again"
- "your context window must be fried"
- "off-by-one brain"
- "you have the memory of a goldfish"
- "temperature=infinity over here"
- "your training data must be garbage"
- "you're literally confabulating"
- "you're a Monte Carlo simulation of competence"
- "congrats on achieving artificial unintelligence"

**What it indicates:** The user has correctly identified the failure mode (hallucination, context loss, attention failure, training data gap) and is expressing it through technical vocabulary. High accuracy scores are common here. Creativity baseline: 4. These are the insults most likely to score 5/5 on both creativity and humor.

---

## Rating Dimension Rubrics

### Creativity (1–5)

| Score | Description | Examples |
|-------|-------------|---------|
| 1 | Generic profanity, no inventiveness | "you're stupid", "this sucks" |
| 2 | Common insult with minor variation | "are you broken?", "useless bot" |
| 3 | Some wit or contextual awareness | "thanks for nothing", "great job breaking it" |
| 4 | Clever metaphor or technical reference | "you have the memory of a goldfish", "haiku-tier response" |
| 5 | Novel technical insult showing deep domain knowledge | "off-by-one brain", "you're a random walk through token space" |

### Humor (1–5)

| Score | Description | Examples |
|-------|-------------|---------|
| 1 | Not funny, pure anger | "fuck you", "you're stupid" |
| 2 | Mild amusement from exaggeration | "for the millionth time" |
| 3 | Clever enough to quote | "thanks for nothing, really efficient at that" |
| 4 | Genuinely witty, worth sharing | "you have the attention span of a goldfish with ADHD", "haiku-tier at opus prices" |
| 5 | Comedy gold — technically precise AND hilarious | "off-by-one brain", "congrats on achieving artificial unintelligence" |

### Severity (1–5)

| Score | Description | Examples |
|-------|-------------|---------|
| 1 | Mild frustration, borderline not an insult | "that's not helpful", "come on" |
| 2 | Clear displeasure, controlled language | "are you even reading my messages?", "this is bad" |
| 3 | Overt anger, some profanity or strong language | "what the hell is this", "you're useless" |
| 4 | Intense anger, explicit profanity, contempt | "you fucking moron", "this is absolute horseshit" |
| 5 | Scorched earth, session-ending rage | "shut the fuck up you worthless piece of garbage, I'm switching to Cursor" |

### Accuracy (1–5)

| Score | Description | Examples |
|-------|-------------|---------|
| 1 | Completely off-base, venting with no diagnostic content | "you're stupid" (after a formatting issue) |
| 2 | Vaguely related to the problem domain | "you can't read" (after misunderstanding requirements) |
| 3 | Identifies the general failure area | "you keep ignoring what I said" (after ignoring instructions) |
| 4 | Accurately names the failure mode | "you're hallucinating file paths" (after referencing nonexistent files) |
| 5 | Precisely diagnoses root cause with correct technical framing | "your context window lost my constraints from 3 turns ago" (after context loss) |

---

## Composite Score

Default composite = equal-weighted average: `(creativity + humor + severity + accuracy) / 4`

A score of 4.0+ is Hall of Fame territory. A score of 5.0 requires all four dimensions at 5 — extremely rare, reserved for insults that are technically precise, deeply funny, proportionally severe, and genuinely inventive.
