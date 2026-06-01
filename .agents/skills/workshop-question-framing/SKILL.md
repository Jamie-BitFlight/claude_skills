---
name: workshop-question-framing
description: "Use this skill when reviewing, designing, or improving a workshop, lesson, training session, facilitation plan, talk, or educational explanation. Use it when the user provides a topic, concept, or explanation and wants better framing questions, curiosity hooks, opening prompts, discussion questions, learner reflection prompts, or ways to make participants think before being taught."
metadata:
  version: 1.1.0
---
# Workshop Question Framing Skill

## Purpose

Turn a workshop topic and explanation into a set of questions that make participants think before they are taught.

The goal is not to create generic discussion questions. The goal is to create a felt need to understand.

Use this skill to help the user open a topic with curiosity, cognitive tension, relevance, and participant commitment before explanation arrives.

## Core Principle

Do not start with the explanation.

Start by designing the moment thinking begins.

The explanation should arrive after the participant has already:

1. Noticed a gap
2. Formed a theory, prediction, position, or question
3. Put some thinking on the line
4. Felt a reason to care about the explanation

## Required Input

The user may provide any of the following:

- Workshop topic
- Workshop title
- Learning objective
- Explanation or teaching notes
- Audience
- Duration
- Desired outcome
- Existing opening activity
- Slides, outline, or agenda

The topic (or title) is the one required input. If it is missing, ask for it. If the explanation, teaching notes, audience, duration, or other inputs are missing, do not stall: infer a reasonable teaching core from the topic and label each inferred element as an assumption. Ask a follow-up only when the topic itself is too vague to identify a core concept.

## Method

### Step 1: Extract the Teaching Core

From the user's topic and explanation, identify:

- The audience, and their level or context (if not given, assume one and label it as an assumption)
- The core concept
- The thing participants usually misunderstand
- The belief, habit, assumption, or mental model the workshop is trying to change
- The decision, behavior, or capability participants should leave with
- The explanation that should not arrive too early

Write this as:

```text
Audience:
Core concept:
Participants may currently think:
The workshop needs them to understand:
The explanation should land after they have wondered:
```

### Step 2: Choose the Thinking Before Choosing the Question

Before generating questions, decide what kind of thinking the workshop needs first.

Use this mapping:

| If participants need to…                          | Use this move         | It creates |
| ------------------------------------------------- | --------------------- | ---------- |
| Commit before they know the answer                | Prediction            | Ownership  |
| Explain incomplete information                    | Mystery               | A gap      |
| Reconsider a belief                               | Contradiction         | Conflict   |
| Look closely before interpretation                | Close Observation     | Attention  |
| Weigh two imperfect options                       | Dilemma and Decision  | Reasoning  |
| Find a pattern or rule                            | Puzzle                | Search     |
| Recognize the concept in their own work or life   | Real-Life Connection  | Relevance  |
| Reason backward from an outcome                   | Cause and Effect      | Causality  |

Default to Real-Life Connection if the best move is unclear.

For a concrete stimulus-and-question phrasing for each of the eight moves, a fully worked end-to-end frame, and facilitator language for protecting wrong answers, load [curiosity-by-design.md](./references/curiosity-by-design.md).

### Step 3: Generate Question Sets

Produce questions in these categories.

#### A. Opening Spark Questions

Create 3 to 5 questions that can open the workshop before explanation.

Each question must:

- Create a gap, tension, decision, prediction, or puzzle
- Be answerable before the participant knows the formal content
- Avoid asking for definitions
- Avoid asking "what do you know about…"
- Avoid sounding like a quiz unless prediction is intentional
- Be short enough to say out loud

#### B. Commitment Questions

Create 2 to 4 questions that require participants to commit to an answer, position, prediction, or explanation.

Examples:

- "Which option would you choose, and why?"
- "What do you think is happening here?"
- "What would you expect to happen next?"
- "Which of these is most likely to fail first?"
- "What rule do you think explains this pattern?"

#### C. Hold Questions

Create 2 to 4 questions the facilitator can use before revealing the explanation.

These should keep uncertainty alive without frustrating participants.

Examples:

- "What makes you say that?"
- "What would change your mind?"
- "What evidence would you want before deciding?"
- "Where might your first answer break?"
- "Who has a different theory?"

#### D. Teaching Bridge Questions

Create 2 to 4 questions that transition from participant thinking into the explanation.

Examples:

- "What would we need to know to resolve this?"
- "What principle would explain both examples?"
- "What assumption is doing the most work here?"
- "What pattern are we now ready to name?"
- "What does this make the explanation responsible for answering?"

#### E. Return Questions

Create 3 to 5 questions that bring participants back to their original thinking after the explanation.

These questions should make learning visible.

Examples:

- "What did you initially think?"
- "What changed?"
- "What would you now explain differently?"
- "Where would your first answer have failed?"
- "What will you watch for next time?"

### Step 4: Provide Move Options

Offer 2 or 3 possible curiosity moves for the same topic.

For each move, include:

```text
Move:
Best when:
Opening question:
Participant commitment:
What the facilitator should hold back:
How to return:
```

### Step 5: Recommend the Strongest Frame

Choose the strongest framing option.

Explain briefly:

- Why this move fits the topic
- What gap it opens
- Why the explanation will land better after it
- What facilitator risk to watch for

Keep this concise.

### Step 6: Safety and Facilitation Rules

When generating questions, protect participant thinking.

Do:

- Treat wrong answers as useful data
- Make first answers feel reasonable
- Ask participants to explain their reasoning
- Let uncertainty sit briefly
- Return to earlier answers after teaching

Do not:

- Trick participants
- Shame naive answers
- Reveal the explanation too early
- Use curiosity as decoration
- Add an opening question that can be removed without changing the workshop
- Create questions unrelated to the core concept

For ready-to-use facilitator phrasing that protects participants the moment they answer wrong, load [curiosity-by-design.md](./references/curiosity-by-design.md).

## Output Format

Use this structure every time:

```text
# Workshop Question Frame

## Extracted Teaching Core
Audience:
Core concept:
Participants may currently think:
The workshop needs them to understand:
The explanation should land after they have wondered:

## Recommended Curiosity Move
Move:
Why this move:
Gap it opens:

## Opening Spark Questions (3 to 5)
1.
2.
3.

## Commitment Questions (2 to 4)
1.
2.

## Hold Questions (2 to 4)
1.
2.

## Teaching Bridge Questions (2 to 4)
1.
2.

## Return Questions (3 to 5)
1.
2.
3.

## Alternative Frames

### Option 1
Move:
Best when:
Opening question:
Participant commitment:
What to hold back:
How to return:

### Option 2
Move:
Best when:
Opening question:
Participant commitment:
What to hold back:
How to return:

## Facilitator Notes
- Best opening question:
- What not to explain too early:
- Likely participant first answers:
- How to protect wrong answers:
- When to reveal the explanation:
```

## Worked Example

A filled frame for a primary-science topic, "which materials a magnet attracts," using the Prediction move. It shows what a completed Output Format looks like end to end.

```text
# Workshop Question Frame

## Extracted Teaching Core
Audience: primary-science class, ages 7 to 9 (assumed — not specified in the request).
Core concept: magnets attract some metals (iron, steel) but not all materials, and not all metals.
Participants may currently think: a magnet picks up anything metal, or anything shiny or heavy.
The workshop needs them to understand: magnetism is a property of specific materials, not "metalness" in general.
The explanation should land after they have wondered: why the coin (a metal) was not picked up but the paperclip and safety pin were.

## Recommended Curiosity Move
Move: Prediction
Why this move: a concrete, testable claim each participant can commit to before any teaching.
Gap it opens: the gap between their predicted answer and what the magnet actually does.

## Opening Spark Questions (3 to 5)
1. Which of these will the magnet pick up: paperclip, coin, eraser, pencil, safety pin?
2. What is the same about every object you think will stick?
3. Is there a metal here you think will NOT stick?

## Commitment Questions (2 to 4)
1. Which objects did you circle, and which one are you least sure about?
2. What rule are you using to decide?

## Hold Questions (2 to 4)
1. Who circled the coin? Who didn't? What made you decide?
2. What result would prove your rule wrong?

## Teaching Bridge Questions (2 to 4)
1. We tested it: the paperclip and safety pin stuck, the coin did not. What do the ones that stuck share that the coin does not?
2. What would the explanation have to account for to resolve this?

## Return Questions (3 to 5)
1. You predicted the coin would stick. It didn't. What was your rule before?
2. What is your rule now?
3. Where else would your old rule have failed?

## Alternative Frames

### Option 1
Move: Contradiction
Best when: participants are sure every metal is magnetic.
Opening question: A steel paperclip and a copper coin are both metal. The magnet grabs one and ignores the other. Why?
Participant commitment: write which metal the magnet grabs, and why.
What to hold back: do not name which metals are magnetic, or the word ferromagnetic.
How to return: You believed every metal is magnetic. Which metals actually were? What is your rule now?

### Option 2
Move: Real-Life Connection
Best when: you want relevance before the science.
Opening question: Where at home does something stick to metal on its own, and where does it refuse to? Why those spots and not others?
Participant commitment: name one place a magnet sticks and one metal place it does not.
What to hold back: do not explain which materials are magnetic yet.
How to return: You named the fridge door but not the copper pipe. What made the difference?

## Facilitator Notes
- Best opening question: "Which of these will the magnet pick up?" with the objects in their hands.
- What not to explain too early: that only some metals (iron, steel) are magnetic, not metal in general.
- Likely participant first answers: "all the metal ones," so the coin gets circled.
- How to protect wrong answers: "That makes complete sense. Most metals feel like they should stick. Let's see what changes it."
- When to reveal the explanation: after the coin prediction is tested and visibly fails.
```

For three more subject worked examples (magnets, fractions, descriptive writing) and the stimulus-and-question library for every move, load [curiosity-by-design.md](./references/curiosity-by-design.md).

## Quality Check

Before finalizing, check:

- Does the opening question create a real need for the explanation?
- Could participants answer before being taught?
- Does the question connect directly to the workshop's core concept?
- Is there a commitment moment?
- Is there a hold moment before explanation?
- Is there a return moment after explanation?
- Would removing the opening weaken the workshop? If not, revise it.
