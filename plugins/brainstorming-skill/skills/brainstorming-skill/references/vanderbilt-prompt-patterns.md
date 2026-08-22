# Vanderbilt University Prompt Pattern Catalog

**Source:** [A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT](https://www.dre.vanderbilt.edu/~schmidt/PDF/prompt-patterns.pdf)

**Authors:** Jules White, Quchen Fu, Sam Hays, Michael Sandborn, Carlos Olea, Henry Gilbert, Ashraf Elnashar, Jesse Spencer-Smith, and Douglas C. Schmidt

**Institution:** Department of Computer Science, Vanderbilt University

**Publication:** February 2023 | arXiv:2302.11382

---

## Overview

This comprehensive catalog documents prompt patterns as reusable solutions to common problems in Large Language Model (LLM) interactions. Drawing direct parallels to software design patterns in computer science, the research establishes that prompt engineering is a systematic discipline with documented, reproducible techniques for improving LLM output quality and reliability.

The catalog addresses a critical gap in LLM usage: while practitioners frequently discover effective prompting techniques, these discoveries are rarely formalized or shared systematically. By cataloging patterns, the research enables knowledge transfer and consistent application of proven strategies.

---

## Theoretical Framework

### Fundamental Principles

**LLMs as Pattern Predictors:** Large Language Models are fundamentally trained to predict the next word based on preceding context. This architecture makes them inherently pattern-dependent systems where structured input reliably produces structured output.

**Pattern Analogy to Software:** Just as software design patterns (Gang of Four) provide reusable solutions to recurring design problems in code architecture, prompt patterns provide reusable solutions to recurring challenges in LLM interaction and output generation.

**Fundamental Contextual Statements:** The research introduces "Fundamental Contextual Statements" as the core structural approach—moving beyond formal grammars to capture the essential concepts that make patterns effective with conversational AI systems.

### Why Prompt Patterns Matter

Prompts function as **instructions given to an LLM to**:

- Enforce specific rules and constraints
- Automate processes and workflows
- Ensure particular qualities and quantities of generated output
- Guide model behavior toward desired objectives

By formalizing patterns, practitioners can:

1. **Replicate success** - Consistently apply techniques proven to work
2. **Combine patterns** - Layer multiple patterns for sophisticated behavior
3. **Transfer knowledge** - Share and learn from documented solutions
4. **Improve discipline** - Elevate prompt engineering from ad-hoc to systematic practice

---

## The 15 Core Prompt Patterns

### Category 1: Input Modification Patterns

#### 1. **Persona Pattern**

**Definition:** Assign the LLM a specific role, identity, or perspective to shape response generation.

**Structure:** "Act as [role]" + task description

**Application:** Grants the model a specific identity to determine what types of output to generate and which details to emphasize.

**Example:**

- "Act as a cybersecurity expert and analyze this system breach"
- "Respond as a software architect evaluating this design proposal"
- "You are a creative writing teacher grading this essay"

**Effectiveness:** The persona pattern anchors the model's behavior to domain-specific knowledge, expertise levels, and communication styles.

**Variations:**

- Single persona: One specific role
- Comparative personas: Multiple experts evaluating same topic
- Audience personas: Tailoring to specific listener expertise levels

---

#### 2. **Audience Persona Pattern**

**Definition:** Specify the target audience to tailor complexity, terminology, and perspective.

**Structure:** "Explain [concept] to [audience type/expertise level]"

**Application:** Adjusts response sophistication, vocabulary, and conceptual frameworks to match audience understanding.

**Example:**

- "Explain blockchain technology as if to a 10-year-old"
- "Explain supply chain logistics as if to Genghis Khan"
- "Describe quantum computing for someone with no physics background"

**Effectiveness:** Dramatically improves accessibility and comprehension by matching explanation to listener knowledge.

**Use Cases:**

- Educational content creation
- Executive summaries vs. technical documentation
- Cross-domain communication
- Accessibility considerations

---

#### 3. **Meta Language Creation Pattern**

**Definition:** Establish custom notation, symbols, or shorthand phrases with explicit meanings for repeated use.

**Structure:** Define notation → use consistently throughout interaction

**Application:** Creates domain-specific language for efficiency and precision in specialized contexts.

**Example:**

- Define: "variations(X)" = "provide ten alternatives of X"
- Define: "impact(X)" = "explain consequences across three contexts: business, technical, user experience"
- Define: "PRO/CON(X)" = "list five advantages and five disadvantages with explanations"

**Effectiveness:** Reduces prompt length in iterative interactions and eliminates ambiguity about intent.

**Benefits:**

- Shortens subsequent prompts significantly
- Prevents misinterpretation through consistent notation
- Accelerates multi-turn conversations
- Documents context and intent explicitly

---

### Category 2: Interaction Flow Patterns

#### 4. **Flipped Interaction Pattern**

**Definition:** Reverse traditional roles—have the LLM ask clarifying questions instead of the user providing all context upfront.

**Structure:** "Ask me questions until you have enough information to [objective]"

**Application:** Guides information gathering through structured dialogue, ensuring comprehensive context capture.

**Example:**

- "Ask me questions to diagnose why my internet connection is slow"
- "What do you need to know about my project before recommending a technology stack?"
- "Ask clarifying questions to help me refine my business idea"

**Effectiveness:** Extracts needed information more efficiently than users attempting to anticipate all relevant details.

**Use Cases:**

- Diagnostic questioning (troubleshooting, medical, technical)
- Requirements gathering (software, product management)
- Interview and research processes
- Progressive information disclosure

**Process:**

1. User states objective
2. LLM generates targeted questions
3. User provides answers
4. LLM either provides solution or asks follow-up questions
5. Repeat until sufficient information gathered

---

#### 5. **Question Refinement Pattern**

**Definition:** Request that the LLM improve questions before answering them, elevating question quality and response accuracy.

**Structure:** "Improve this question before answering: [question]"

**Application:** Captures better-formed questions that are more likely to elicit accurate, useful responses.

**Example:**

- "Refine this question: 'Who is the greatest basketball player of all time?' before answering"
- Improvement: "Considering peak performance level, championships, consistency across eras, and era-adjusted stats, which NBA player demonstrates the highest combination of these factors?"

**Effectiveness:** Moves questions from subjective to more objective framing, accounting for nuance and context.

**Benefits:**

- Surfaces assumptions in original question
- Adds necessary qualifiers and context
- Produces more precise, answerable questions
- Reduces response ambiguity

---

#### 6. **Cognitive Verifier Pattern**

**Definition:** Generate supporting questions, answer them, then synthesize into comprehensive final answer.

**Structure:**

1. State objective/question
2. "Generate questions that would help answer this"
3. LLM answers supporting questions
4. LLM synthesizes comprehensive answer

**Application:** Builds multi-faceted answers through systematic questioning, improving depth and completeness.

**Example - Recipe Context:**

- Initial ask: "Create a recipe for lasagna"
- Supporting questions generated:
  - What ingredients are available?
  - What equipment is accessible?
  - What dietary restrictions apply?
  - What time constraints exist?
  - What skill level is the cook?
- Answers incorporated into customized, comprehensive recipe

**Effectiveness:** Produces better-reasoned, more thorough responses by forcing structured thinking.

**Benefits:**

- Ensures comprehensive coverage of relevant factors
- Reduces oversights and missing context
- Produces more nuanced, detailed outputs
- Creates reasoning transparency (showing question→answer chain)

---

### Category 3: Output Format and Customization

#### 7. **Template Pattern**

**Definition:** Provide a specific output format with labeled placeholders to enforce consistent structure.

**Structure:** Supply format template → LLM fills placeholders

**Application:** Ensures responses follow exact formatting requirements and include all necessary components.

**Example - Workout Format:**

```
EXERCISE: [name]
REPS @ SETS: [reps × sets]
MUSCLE GROUPS: [primary and secondary]
DIFFICULTY: [beginner/intermediate/advanced]
FORM NOTES: [key form cues]
```

**Example - Product Review Template:**

```
PRODUCT: [name]
RATING: [1-5 stars]
PROS: [list benefits]
CONS: [list drawbacks]
RECOMMENDATION: [who should buy]
PRICE VALUE: [how price compares to value]
```

**Effectiveness:** Guarantees consistent structure, complete information coverage, and machine-parseable output.

**Use Cases:**

- Data extraction and standardization
- Structured reporting
- Content templating (emails, proposals, documentation)
- Ensuring specific required sections

---

#### 8. **Recipe Pattern**

**Definition:** Provide some initial steps and ask for a complete sequence with gaps filled in logically.

**Structure:** "Here are some steps: [step1], [step2]... Complete the full sequence"

**Application:** Leverages LLM knowledge to create comprehensive procedures from partial frameworks.

**Example - Home Buying Process:** Given steps: "Make an offer" and "Close on the property" Complete sequence generates:

1. Get pre-approved for mortgage
2. Find a real estate agent
3. Search for properties
4. Make an offer
5. Home inspection
6. Appraisal
7. Final walkthrough
8. Sign closing documents
9. Close on the property
10. Get keys and move in

**Effectiveness:** Produces logical, sequentially organized procedures with essential steps contextualized.

**Benefits:**

- Fills knowledge gaps with domain expertise
- Ensures logical sequence and dependencies
- Captures often-forgotten intermediate steps
- Creates step-appropriate detail levels

---

#### 9. **Alternative Approaches Pattern**

**Definition:** Request multiple solutions to the same problem with pros/cons analysis for comparison.

**Structure:** "Provide [N] different approaches to [problem] with pros and cons for each"

**Application:** Evaluates different strategies, implementation approaches, or perspectives.

**Example:**

- "Show me 3 ways to structure this React component with pros/cons"
- "What are 5 approaches to reducing project costs, each with tradeoffs?"
- "Provide different versions of this prompt with their strengths and weaknesses"

**Effectiveness:** Illuminates decision factors and tradeoffs, enabling informed choices.

**Use Cases:**

- Design decisions (architecture, UX, technical implementation)
- Problem-solving with multiple valid solutions
- Cost-benefit analysis
- Strategy evaluation
- Prompt iteration and optimization

---

### Category 4: Content Control and Extraction

#### 10. **Ask for Input Pattern**

**Definition:** Explicitly request specific information types or data structures the LLM needs for completion.

**Structure:** "To [objective], please provide: [list specific information needs]"

**Application:** Establishes clear input expectations and guides user in providing complete context.

**Example:**

- "To summarize these emails, please provide: [the email chain], [summary length preference], [focus areas: decisions/action items/timeline]"
- "To generate a project timeline, I need: [project scope], [resource availability], [dependency constraints], [milestone dates]"

**Effectiveness:** Ensures users provide necessary information upfront rather than iterating on missing context.

**Benefits:**

- Reduces back-and-forth clarifications
- Prevents incomplete or misguided outputs
- Sets clear collaboration expectations
- Saves time by getting right information immediately

---

#### 11. **Menu Actions Pattern**

**Definition:** Map specific commands or phrases to specific actions/responses, creating command-driven interaction.

**Structure:**

```
"[COMMAND1]" → [action]
"[COMMAND2]" → [action]
```

**Application:** Creates predictable, command-driven behavior for structured interactions.

**Example - Shopping List Assistant:**

- `"add ITEM"` → Adds ITEM to shopping list
- `"remove ITEM"` → Deletes ITEM
- `"show list"` → Displays current list
- `"suggest meals"` → Recommends recipes using listed items

**Effectiveness:** Establishes consistent command semantics that don't require repeated explanation.

**Use Cases:**

- Interactive assistants and chatbots
- Task management systems
- Shopping/inventory management
- Structured workflows
- API-like interactions with LLMs

**Benefits:**

- Predictable, consistent behavior
- Reduces ambiguity about intent
- Enables complex workflows through simple commands
- Creates intuitive interaction patterns

---

#### 12. **Semantic Filter Pattern**

**Definition:** Specify content categories or types to remove from information, extracting through exclusion.

**Structure:** "Provide [information] excluding [categories to remove]"

**Application:** Filters information by removing irrelevant, redundant, or unwanted content categories.

**Example:**

- "Summarize this report excluding budget figures and proprietary metrics"
- "Extract technical requirements, excluding implementation details and cost considerations"
- "List product features, removing redundant items and excluding cosmetic-only features"

**Effectiveness:** Isolates relevant information through strategic exclusion rather than inclusion lists.

**Use Cases:**

- Information extraction and filtering
- Privacy-aware data handling (removing sensitive categories)
- Cost analysis (excluding low-impact factors)
- Requirements clarification (removing implementation details)

**Benefits:**

- Often easier to exclude than enumerate inclusions
- Handles edge cases naturally
- Reduces information overload
- Focuses output on specific concerns

---

### Category 5: Verification and Quality Assurance

#### 13. **Fact Check List Pattern**

**Definition:** Generate a list of verifiable facts and position strategically (typically end of response) for human verification.

**Structure:** Request response + add "Generate a fact-check list" step

**Application:** Enables systematic verification of factual accuracy in LLM outputs.

**Example:** After generating response about historical event:

```
FACT-CHECK LIST:
□ [Specific verifiable fact 1]
□ [Specific verifiable fact 2]
□ [Specific verifiable fact 3]
```

**Effectiveness:** Makes factual claims explicit and checkable, supporting human verification workflows.

**Use Cases:**

- Research and academic writing
- Journalism and reporting
- Technical documentation with factual claims
- Any context where accuracy is critical

**Benefits:**

- Creates explicit verification targets
- Separates verifiable facts from opinion/analysis
- Supports collaborative accuracy checking
- Documents assumptions that should be verified

---

#### 14. **Tail Generation Pattern**

**Definition:** Repeat available options or prompt for next action at response conclusion to maintain conversation flow.

**Structure:** End response with: "Next options: [A], [B], [C]" or "What would you like to explore next?"

**Application:** Sustains engagement and guides users toward natural next steps in multi-turn interactions.

**Example - Outline Expansion:**

```
I. Introduction
   A. Context (expanded)
II. Main Section
   B. Key concepts (ready to expand)
   C. Examples (ready to expand)
```

"Which section would you like me to expand next: B or C?"

**Effectiveness:** Keeps conversation flowing naturally without users having to determine next steps.

**Use Cases:**

- Document and outline development
- Interactive learning and tutoring
- Progressive information disclosure
- Exploratory dialogue

**Benefits:**

- Reduces friction in multi-turn interactions
- Guides users toward productive next steps
- Maintains context and continuity
- Creates natural conversation flow

---

### Category 6: Complex Reasoning and Problem-Solving

#### 15. **Game Play Pattern**

**Definition:** Frame task as a game with explicit rules, constraints, and objectives to engage problem-solving.

**Structure:** Define game (setting, rules, objectives, winning conditions) → Play through interaction

**Application:** Leverages game mechanics to structure learning, exploration, and problem-solving.

**Example - Language Discovery Game:**

```
GAME: Cave Exploration
SETTING: Ancient cave with inscribed symbols
RULES:
- Each response reveals new chamber with clues
- Decipher language rules from context
- Progress deeper by demonstrating understanding
OBJECTIVE: Decode the complete language system
WINNING CONDITION: Correctly translate provided text
```

**Effectiveness:** Transforms abstract tasks into engaging, structured problem-solving with clear progression.

**Use Cases:**

- Language learning and teaching
- Logic puzzle and reasoning exercises
- Creative writing and worldbuilding
- Exploratory learning
- Constraint-based problem solving

**Benefits:**

- Increases engagement and motivation
- Provides structure and clear progress indicators
- Enables iterative learning through failure/retry
- Makes abstract concepts concrete

---

## Advanced Techniques: Combining Patterns

The research demonstrates that maximum effectiveness often comes from strategically combining multiple patterns:

### Example: Multi-Pattern Customer Service Bot

**Combined Patterns:**

1. **Flipped Interaction** - Bot asks questions to diagnose customer issue
2. **Menu Actions** - Customer uses commands like "escalate" or "cancel"
3. **Template Pattern** - Responses follow consistent troubleshooting format
4. **Fact Check List** - Technical solutions include verification steps

### Example: Educational Content Generator

**Combined Patterns:**

1. **Audience Persona** - Target specific educational level
2. **Recipe Pattern** - Build lesson structure
3. **Alternative Approaches** - Provide multiple teaching methods
4. **Template Pattern** - Format for consistency
5. **Tail Generation** - Suggest next learning modules

### Example: Complex Problem Analysis

**Combined Patterns:**

1. **Cognitive Verifier** - Generate supporting questions
2. **Alternative Approaches** - Explore multiple solutions
3. **Fact Check List** - Verify assumptions and claims
4. **Template Pattern** - Structure final recommendation

---

## Research Findings and Implications

### Key Contributions to Prompt Engineering Discipline

1. **Formalization of Practice:** Patterns move prompt engineering from ad-hoc discovery to systematic, reusable practice
2. **Knowledge Transfer:** Documented patterns enable practitioners to leverage community expertise
3. **Design Composition:** Multiple patterns can be combined for complex behavior, similar to software design patterns
4. **Measurable Improvement:** Specific pattern applications produce predictable, measurable improvements in output quality

### Effectiveness Characteristics

The research identifies that effective patterns share these characteristics:

- **Explicit Structure:** Clear instructions about what the LLM should do
- **Contextual Grounding:** "Fundamental Contextual Statements" that capture why patterns work
- **Composability:** Patterns combine well without conflicts
- **Predictability:** Same pattern produces consistent results across contexts
- **Discoverability:** Users can learn to recognize which pattern applies to their needs

---

## Practical Application Guidelines

### When to Use Each Pattern Category

**Input Modification (Patterns 1-3):**

- Use to shape model behavior and perspective
- Combine multiple for complex role requirements
- Most effective when persona details are specific

**Interaction Flow (Patterns 4-6):**

- Use to improve information gathering and question quality
- Combine for iterative, multi-turn dialogues
- Most effective for collaborative problem-solving

**Output Format (Patterns 7-9):**

- Use when specific structure or format is required
- Combine to handle complex information organization
- Most effective for reproducible, consistent output

**Content Control (Patterns 10-12):**

- Use to extract specific information or structure interaction
- Combine for sophisticated filtering and command systems
- Most effective for data extraction and structured workflows

**Verification (Patterns 13-14):**

- Use to support quality assurance and accuracy checking
- Combine with other patterns for comprehensive reliability
- Most effective when accuracy is critical

**Problem-Solving (Pattern 15):**

- Use to engage creative thinking and iterative exploration
- Combine with other patterns for learning frameworks
- Most effective for educational and discovery contexts

---

## Connection to Brainstorming Skills

The Vanderbilt patterns are foundational to effective brainstorming because they:

1. **Structure Creative Thinking:** Patterns like Cognitive Verifier and Alternative Approaches directly support brainstorming by organizing thought processes
2. **Enable Ideation Capture:** Template and Menu Actions patterns capture and organize brainstorming outputs
3. **Facilitate Exploration:** Game Play and Flipped Interaction patterns explore solution spaces systematically
4. **Synthesize Ideas:** Recipe and Meta Language patterns help organize and communicate brainstormed concepts

---

## Resources

- **Official Vanderbilt Prompt Patterns Portal:** <https://www.vanderbilt.edu/generative-ai/prompt-patterns/>
- **Free Coursera Course:** "Prompt Engineering for ChatGPT" by Jules White (Vanderbilt University)
- **Research Paper:** "A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT" (arXiv:2302.11382)
- **Related Research:** "Prompt Patterns for Structured Data Extraction from Unstructured Text" (Vanderbilt)

---

## References

White, J., Fu, Q., Hays, S., Sandborn, M., Olea, C., Gilbert, H., Elnashar, A., Spencer-Smith, J., & Schmidt, D. C. (2023). A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT. _arXiv preprint arXiv:2302.11382_.

Department of Computer Science, Vanderbilt University. (2023). Prompt Patterns. Retrieved from <https://www.vanderbilt.edu/generative-ai/prompt-patterns/>

---

**Last Updated:** 2025-11-05 **Source Verification:** Verified against Hillside Conference Proceedings (2023) and official Vanderbilt University resources
