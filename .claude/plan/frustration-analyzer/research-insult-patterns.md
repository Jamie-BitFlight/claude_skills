# Research: Insult Detection Patterns for frustration-analyzer Plugin

## Context

This document designs the insult detection subsystem for a `frustration-analyzer` plugin. It builds on the existing `agentskill-kaizen` frustration signal detection (which covers soft signals: corrections, denials, interrupts, mild frustration) and extends into explicit insults directed at the AI.

### Existing System Baseline

The kaizen plugin's `_FRUSTRATION_PATTERNS` (at `plugins/agentskill-kaizen/mcp/server.py` line 76) detects four soft signal categories:

| Category | Pattern | Example |
|----------|---------|---------|
| correction | `no, don't, wrong, incorrect, stop, undo, revert` | "no, that's wrong" |
| denial | `that's not, I didn't, never, absolutely not` | "I didn't ask for that" |
| interrupt | `wait, hold on, cancel, abort, forget it, nevermind` | "forget it" |
| frustration | `why did you, you keep, again?, still wrong, broken` | "you keep doing this" |

The existing `detect_frustration_signals` function scans `type: "user"` records (excluding `toolUseResult: true`), extracts text via `_extract_user_text()`, matches one signal per message (first match wins), and returns `{session_id, timestamp, signal_type, message_text}`.

The insult detector operates on the same JSONL transcript schema (documented in `plugins/agentskill-kaizen/skills/transcript-analysis/references/jsonl-schema.md`) but targets a distinct, higher-severity signal class.

---

## Insult Categories

### Category 1: Profanity-at-AI

**Description:** Direct profanity or vulgar language aimed at the AI as an entity. The insult uses swear words to express contempt for the AI's output or capabilities.

**Example regex:**

```python
re.compile(
    r"\b(?:you\s+)?(?:fucking|damn|goddamn|bloody)\s+(?:idiot|moron|fool|useless|stupid|dumb|piece\s+of\s+shit)\b"
    r"|\b(?:wtf|what\s+the\s+fuck|what\s+the\s+hell)\s+(?:are\s+you\s+doing|is\s+this|is\s+wrong\s+with\s+you)\b"
    r"|\b(?:fuck\s+(?:you|this|off)|go\s+to\s+hell|screw\s+you)\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "you fucking idiot"
- "wtf are you doing"
- "what the hell is wrong with you"
- "fuck this, I'll do it myself"
- "you goddamn useless piece of shit"

---

### Category 2: Model Comparison Insults

**Description:** Unfavorable comparisons to other AI models or older/weaker versions. Implies the AI is performing below expected capability by naming a model perceived as inferior.

**Example regex:**

```python
re.compile(
    r"\b(?:you'?re|this\s+is|acting\s+like|sounds?\s+like|worse\s+than|dumber\s+than)\s+"
    r"(?:gpt[-\s]?[23]|haiku|gemini\s*(?:nano|flash)?|copilot|chatgpt|a\s+chatbot"
    r"|clippy|eliza|a\s+markov\s+chain|an?\s+intern)\b"
    r"|\b(?:gpt[-\s]?[23]|haiku|chatgpt)\s+(?:level|quality|tier|grade)\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "you're acting like Haiku"
- "this is GPT-3 level stupidity"
- "worse than Copilot"
- "sounds like a markov chain wrote this"
- "you're dumber than an intern"
- "haiku-tier response"

---

### Category 3: Competence Challenges

**Description:** Direct questions or statements challenging the AI's fundamental ability to perform its job. Frames the AI as professionally incompetent.

**Example regex:**

```python
re.compile(
    r"\b(?:are\s+you\s+(?:stupid|dumb|deaf|blind|broken|brain\s*dead|incapable)"
    r"|can'?t\s+you\s+(?:read|understand|follow|listen|think|do\s+anything)"
    r"|do\s+you\s+(?:even|not)\s+(?:understand|know|read|listen)"
    r"|how\s+(?:hard|difficult)\s+(?:is\s+it|can\s+it\s+be))\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "are you stupid?"
- "can't you read?"
- "do you even understand what I'm asking?"
- "how hard can it be?"
- "are you braindead?"

---

### Category 4: Intelligence Insults

**Description:** Statements that directly label the AI as unintelligent, worthless, or fundamentally defective. Declarative rather than interrogative.

**Example regex:**

```python
re.compile(
    r"\b(?:you'?re\s+(?:useless|worthless|hopeless|pathetic|terrible|awful|garbage|trash"
    r"|incompetent|clueless|brain\s*dead|an?\s+idiot|a\s+moron|the\s+worst)"
    r"|this\s+(?:is\s+)?(?:garbage|trash|useless|pathetic|terrible|awful|horseshit|bullshit)"
    r"|absolute(?:ly)?\s+(?:useless|worthless|pathetic|terrible|garbage))\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "you're useless"
- "this is absolute garbage"
- "you're the worst"
- "you're an idiot"
- "this is pathetic"
- "absolutely worthless output"

---

### Category 5: Repeat-Failure Insults

**Description:** Expressions of exasperation at the AI making the same mistake again after correction. Combines temporal markers ("again", "still", "every time") with negative judgment. Distinct from the kaizen `frustration` category by requiring stronger language or emphasis markers (caps, punctuation).

**Example regex:**

```python
re.compile(
    r"\b(?:(?:you\s+)?(?:STILL|AGAIN|ONCE\s+AGAIN|YET\s+AGAIN)\s+(?:got\s+it\s+wrong|broke|failed|messed|fucked)"
    r"|(?:how\s+many\s+times|for\s+the\s+(?:\w+\s+)?time)\b"
    r"|(?:every\s+(?:single\s+)?time\s+you)"
    r"|(?:wrong\s+)?again[!?]{2,}"
    r"|(?:STILL\s+(?:broken|wrong|failing|bugged)))\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "you STILL got it wrong"
- "wrong again?!"
- "how many times do I have to tell you"
- "for the fifth time"
- "every single time you mess this up"
- "AGAIN?!?"

---

### Category 6: Sarcasm Patterns

**Description:** Mock praise, ironic congratulations, or rhetorical questions that use positive framing to deliver negative feedback. The sarcastic intent is signaled by context (following a failure), exaggerated praise words, or the combination of praise + criticism.

**Example regex:**

```python
re.compile(
    r"\b(?:(?:great|good|nice|wonderful|brilliant|excellent|amazing|fantastic)\s+(?:job|work|going)"
    r"|(?:wow|congrats|congratulations|bravo|well\s+done|genius)\s*[,.]?\s*(?:you|that|now|it)"
    r"|(?:oh?\s+)?(?:how\s+)?(?:helpful|useful|productive)\s*(?:\.{3,}|/s)"
    r"|(?:real(?:ly)?\s+)?(?:helpful|useful|smart|intelligent)\s+(?:aren'?t\s+you|one|there)"
    r"|thanks?\s+for\s+(?:nothing|wasting|breaking|making\s+it\s+worse))\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "great job breaking everything"
- "wow, that was really helpful /s"
- "brilliant work there genius"
- "thanks for nothing"
- "oh how productive..."
- "congratulations, you made it worse"
- "really smart one aren't you"

---

### Category 7: Dismissive Commands

**Description:** Terse, commanding language that treats the AI as beneath engagement. Reduces the interaction to raw imperatives expressing contempt. Often very short messages.

**Example regex:**

```python
re.compile(
    r"^(?:just\s+(?:stop|shut\s+up|quit|give\s+up)"
    r"|(?:shut\s+(?:up|the\s+fuck\s+up))"
    r"|(?:I'?(?:ll|m\s+going\s+to)\s+(?:do\s+it\s+myself|just\s+do\s+it\s+manually|use\s+\w+\s+instead))"
    r"|(?:forget\s+(?:it|you)|I\s+give\s+up\s+on\s+you|done\s+with\s+you))\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "just stop"
- "shut up"
- "I'll do it myself"
- "I'm going to use Cursor instead"
- "forget you"
- "done with you"

---

### Category 8: Technical Put-downs

**Description:** Inventive, technically-specific insults that diagnose what went wrong using programming or CS metaphors. These are the "creative" insults that demonstrate domain expertise in their contempt.

**Example regex:**

```python
re.compile(
    r"\b(?:(?:you|this)\s+(?:is\s+)?(?:a\s+)?(?:hallucinating|confabulating|regressing|overfitting|underfitting)"
    r"|(?:your\s+(?:context\s+window|attention|memory|weights|training\s+data)\s+(?:is|must\s+be)\s+(?:broken|garbage|corrupted|empty|fried))"
    r"|(?:off[\s-]?by[\s-]?one\s+(?:brain|intelligence|model))"
    r"|(?:you\s+(?:have|got)\s+(?:the\s+)?(?:memory|attention\s+span)\s+of\s+(?:a\s+)?(?:goldfish|gnat|rock))"
    r"|(?:temperature\s*=?\s*(?:99|100|infinity|NaN)))\b",
    re.IGNORECASE,
)
```

**Example insults:**

- "you're hallucinating again"
- "your context window must be fried"
- "off-by-one brain"
- "you have the memory of a goldfish"
- "temperature=infinity over here"
- "your training data must be garbage"
- "you're literally confabulating"

---

## Rating Dimensions

### Creativity (1-5)

How original and inventive is the insult?

| Score | Description | Examples |
|-------|-------------|----------|
| 1 | Generic profanity, no thought | "you're stupid", "this sucks" |
| 2 | Common insult with minor variation | "are you broken?", "useless bot" |
| 3 | Some wit or contextual awareness | "thanks for nothing", "great job breaking it" |
| 4 | Clever metaphor or technical reference | "you have the memory of a goldfish", "haiku-tier response" |
| 5 | Novel technical insult showing deep domain knowledge | "off-by-one brain", "your attention mechanism is clearly corrupted", "you're a random walk through token space" |

### Technical Accuracy (1-5)

Does the insult correctly diagnose the actual failure mode?

| Score | Description | Examples |
|-------|-------------|----------|
| 1 | Completely off-base, venting with no diagnostic content | "you're stupid" (after a formatting issue) |
| 2 | Vaguely related to the problem domain | "you can't read" (after misunderstanding requirements) |
| 3 | Identifies the general failure area | "you keep ignoring what I said" (after ignoring instructions) |
| 4 | Accurately names the failure mode | "you're hallucinating file paths" (after referencing nonexistent files) |
| 5 | Precisely diagnoses root cause with correct technical framing | "your context window lost my constraints from 3 turns ago" (after losing context) |

### Severity (1-5)

How intense is the emotional escalation?

| Score | Description | Examples |
|-------|-------------|----------|
| 1 | Mild frustration, borderline not an insult | "that's not helpful", "come on" |
| 2 | Clear displeasure, controlled language | "are you even reading my messages?", "this is bad" |
| 3 | Overt anger, some profanity or strong language | "what the hell is this", "you're useless" |
| 4 | Intense anger, explicit profanity, contempt | "you fucking moron", "this is absolute horseshit" |
| 5 | Scorched earth, session-ending rage, multiple categories in one message | "shut the fuck up you worthless piece of garbage, I'm switching to Cursor, done with this trash" |

### Humor (1-5)

Is the insult genuinely clever or funny, even to the target?

| Score | Description | Examples |
|-------|-------------|----------|
| 1 | Not funny, pure anger | "fuck you", "you're stupid" |
| 2 | Mild amusement from exaggeration | "for the millionth time" |
| 3 | Clever enough to quote | "thanks for nothing, really efficient at that" |
| 4 | Genuinely witty, would get laughs if shared | "you have the attention span of a goldfish with ADHD", "haiku-tier at opus prices" |
| 5 | Comedy gold, technically precise AND hilarious | "off-by-one brain", "you're a Monte Carlo simulation of competence", "congrats on achieving artificial unintelligence" |

---

## Scenario Context

### Recommended Default: N = 5 preceding messages

**Rationale:**

1. **Conversation turn structure.** A typical Claude Code interaction cycle is: user prompt -> assistant response (with tool calls) -> user evaluation. One full cycle is 2-3 messages. N=5 captures ~2 full cycles before the insult, which is enough to see the precipitating failure and any prior correction attempt.

2. **Escalation visibility.** Insults rarely appear without warning. The pattern is typically: (1) initial request, (2) failed response, (3) soft correction (kaizen-level frustration), (4) second failed attempt, (5) insult. N=5 captures this full escalation arc.

3. **Context window economy.** Storing more than 5 messages per insult increases storage cost quadratically across many insults. 5 messages provides the "minimal reproducing scenario" in most cases.

4. **Compact boundary awareness.** Claude Code sessions can have `compact_boundary` records that reset conversation context. If a compact boundary falls within the N=5 window, the scenario should note this, as the AI may have literally lost context at that point (which may be the root cause of the failure).

**Configurable range:** Allow override from 3 to 15 via a parameter. Some insults follow long, slow deterioration (N=10-15), while others are immediate reactions to a single bad output (N=3).

---

## DuckDB Schema

### Table: `insults`

Primary table storing each detected insult with its classification.

```sql
CREATE TABLE insults (
    insult_id       INTEGER PRIMARY KEY,
    session_id      VARCHAR NOT NULL,
    timestamp       TIMESTAMP NOT NULL,
    message_uuid    VARCHAR NOT NULL,
    parent_uuid     VARCHAR,
    insult_text     VARCHAR NOT NULL,
    category        VARCHAR NOT NULL,
    -- One of: profanity_at_ai, model_comparison, competence_challenge,
    --         intelligence_insult, repeat_failure, sarcasm,
    --         dismissive_command, technical_putdown
    matched_pattern VARCHAR,          -- Which regex matched (for debugging/tuning)
    model           VARCHAR,          -- Model active at time of insult (from preceding assistant record)
    git_branch      VARCHAR,          -- From JSONL common fields
    session_slug    VARCHAR,          -- Human-readable session identifier
    is_subagent     BOOLEAN DEFAULT FALSE,  -- From isSidechain field
    agent_name      VARCHAR           -- If insult directed at a subagent
);
```

### Table: `insult_ratings`

Rating scores for each insult across the four dimensions.

```sql
CREATE TABLE insult_ratings (
    rating_id    INTEGER PRIMARY KEY,
    insult_id    INTEGER NOT NULL REFERENCES insults(insult_id),
    creativity   TINYINT NOT NULL CHECK (creativity   BETWEEN 1 AND 5),
    accuracy     TINYINT NOT NULL CHECK (accuracy     BETWEEN 1 AND 5),
    severity     TINYINT NOT NULL CHECK (severity     BETWEEN 1 AND 5),
    humor        TINYINT NOT NULL CHECK (humor        BETWEEN 1 AND 5),
    composite    DECIMAL(3,2) GENERATED ALWAYS AS (
        (creativity * 0.25 + accuracy * 0.25 + severity * 0.25 + humor * 0.25)
    ) STORED,
    rated_by     VARCHAR NOT NULL DEFAULT 'auto',
    -- 'auto' = heuristic scoring, 'llm' = LLM-rated, 'human' = manual
    rated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Composite score rationale:** Equal weighting (0.25 each) is the default. The composite treats all dimensions as equally interesting. A user who values humor over accuracy can query with custom weighting:

```sql
SELECT i.insult_text, i.category,
       (r.creativity * 0.1 + r.accuracy * 0.1 + r.severity * 0.3 + r.humor * 0.5) AS custom_score
FROM insults i JOIN insult_ratings r ON i.insult_id = r.insult_id
ORDER BY custom_score DESC;
```

### Table: `insult_scenarios`

The surrounding conversation context that precipitated the insult.

```sql
CREATE TABLE insult_scenarios (
    scenario_id          INTEGER PRIMARY KEY,
    insult_id            INTEGER NOT NULL REFERENCES insults(insult_id),
    preceding_messages   JSON NOT NULL,
    -- Array of {role, text, timestamp, uuid, tool_name?} for N messages before insult
    context_window_n     TINYINT NOT NULL DEFAULT 5,
    summary              VARCHAR,
    -- LLM-generated one-line summary of what went wrong
    precipitating_failure VARCHAR,
    -- Classified failure type: hallucination, ignored_instruction, wrong_tool,
    --   repeated_mistake, context_loss, slow_response, formatting_error,
    --   incorrect_code, broke_existing, other
    had_prior_correction BOOLEAN DEFAULT FALSE,
    -- True if a kaizen-level frustration signal appears in preceding messages
    compact_boundary_in_window BOOLEAN DEFAULT FALSE,
    -- True if a compact_boundary record falls within the N-message window
    tool_sequence        JSON
    -- Tool names used in the preceding assistant messages (for pattern analysis)
);
```

### Useful Views

```sql
-- Leaderboard: highest-rated insults
CREATE VIEW insult_leaderboard AS
SELECT i.insult_text, i.category, i.session_slug,
       r.creativity, r.accuracy, r.severity, r.humor, r.composite,
       s.precipitating_failure, s.summary
FROM insults i
JOIN insult_ratings r ON i.insult_id = r.insult_id
LEFT JOIN insult_scenarios s ON i.insult_id = s.insult_id
ORDER BY r.composite DESC;

-- Category distribution
CREATE VIEW category_distribution AS
SELECT category, COUNT(*) AS count,
       AVG(r.severity) AS avg_severity,
       AVG(r.composite) AS avg_composite
FROM insults i
JOIN insult_ratings r ON i.insult_id = r.insult_id
GROUP BY category
ORDER BY count DESC;

-- Failure mode analysis: what failures trigger the worst insults
CREATE VIEW failure_triggers AS
SELECT s.precipitating_failure,
       COUNT(*) AS insult_count,
       AVG(r.severity) AS avg_severity,
       AVG(r.composite) AS avg_composite,
       MAX(r.composite) AS best_insult_score
FROM insult_scenarios s
JOIN insult_ratings r ON s.insult_id = r.insult_id
GROUP BY s.precipitating_failure
ORDER BY avg_severity DESC;

-- Escalation analysis: insults that had prior soft correction
CREATE VIEW escalation_patterns AS
SELECT i.insult_text, i.category, s.had_prior_correction,
       s.precipitating_failure, r.severity
FROM insults i
JOIN insult_ratings r ON i.insult_id = r.insult_id
JOIN insult_scenarios s ON i.insult_id = s.insult_id
WHERE s.had_prior_correction = TRUE
ORDER BY r.severity DESC;
```

---

## Integration Notes

### Relationship to Existing Kaizen Frustration Detection

The insult detector is a **severity escalation** of the existing kaizen frustration signals, not a replacement:

```text
Severity spectrum:
  [kaizen signals]                    [insult detector]
  correction -> denial -> interrupt -> frustration -> insult
  (soft)       (soft)    (medium)     (medium)        (hard)
```

A message can match both systems. The `insult_scenarios.had_prior_correction` field explicitly tracks whether kaizen-level signals preceded the insult, enabling escalation analysis.

### JSONL Record Processing

Insult detection operates on the same record types as kaizen:

- **Input records:** `type: "user"` where `toolUseResult` is falsy
- **Text extraction:** Same `_extract_user_text()` path -- content is either a string or `[{type: "text", text: "..."}]` array
- **Context records:** `type: "assistant"` records preceding the insult provide the scenario (model used, tools called, response content)
- **Metadata enrichment:** `session_id`, `timestamp`, `gitBranch`, `slug` from JSONL common fields

### Scoring Automation

Initial scoring can be heuristic-based:

- **Severity:** Derived from category (profanity_at_ai baseline=4, sarcasm baseline=2) + modifiers (ALL CAPS +1, multiple exclamation marks +0.5, profanity count)
- **Creativity:** Derived from category (technical_putdown baseline=4, profanity_at_ai baseline=1) + lexical diversity
- **Accuracy and Humor:** Require LLM rating (pass insult + scenario context to a model for 1-5 scoring). These dimensions depend on semantic understanding that regex cannot provide.

SOURCE: Existing frustration detection at `plugins/agentskill-kaizen/mcp/server.py` lines 76-81, 460-512. JSONL schema at `plugins/agentskill-kaizen/skills/transcript-analysis/references/jsonl-schema.md`. Improvement templates at `plugins/agentskill-kaizen/skills/kaizen-improvement/references/improvement-templates.md`.
