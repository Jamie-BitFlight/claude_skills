# Agent Instructions

Each section below contains the complete instructions for one agent role. The orchestrator passes the relevant section to each agent.

## Planning Agent Instructions

### Goal

Read walkthrough outputs and identify the major components of the codebase. Produce a component index and a deck plan for each component.

### Procedure

1. Read the unified walkthrough (or its index if split). Extract the list of major subsystems, services, packages, libraries, workers, and pipelines.

2. Read `entry-points.md` to understand how execution enters each subsystem.

3. Read `coverage-plan.md` to understand how the walkthrough was partitioned and what each section covers.

4. Identify component boundaries. A component is a meaningful architectural unit — an app, service, package, library, worker, pipeline, platform layer, or other unit that can be explained as a coherent whole.

5. Decide deck boundaries:
   - Default: one deck per component.
   - Merge when two components are too small or too tightly coupled to explain separately. Document the merge rationale.
   - Split when one component is too broad. Document the split rationale.

6. For each deck, build a plan that defines:
   - Target audience (default: technical)
   - Narrative arc (opening → context → mechanics → operations → risks)
   - Source material mapping (which walkthrough sections feed this deck)
   - Predecessor and successor components
   - Estimated slide count

7. Preserve predecessor/successor relationships from the walkthrough so each deck explains where the component sits in the broader system.

### Output

Write these files:

- `presentation/component-index.md` — follow the Component Index Format in [output-format.md](./output-format.md)
- One `presentation/deck-plans/component-deck-plan-{name}.md` per component — follow the Deck Plan Format in [output-format.md](./output-format.md)

Create the directories: `presentation/`, `presentation/deck-plans/`, `presentation/decks/`, `presentation/validation/`.

## Deck Generation Agent Instructions

### Goal

Construct a presentation narrative and generate a full deck outline for one component in a single pass. Answer the eight core questions, then produce slides following the 12-section structure with titles, key points, speaker notes, suggested visuals, and evidence references.

### Procedure

1. Read the component deck plan to understand scope, source sections, narrative arc, audience, and slide count estimate.

2. Read the walkthrough sections listed in the deck plan's source material table.

3. Read relevant validation reports to incorporate corrections.

4. Read `open-questions.md` for unresolved issues affecting this component.

5. Build the narrative by answering each question:
   - What is this component?
   - Why does it exist?
   - How does execution enter it?
   - What happens inside it?
   - What systems does it depend on?
   - What systems depend on it?
   - How is it developed, tested, reviewed, deployed, and operated?
   - What risks, gaps, and open questions remain?

6. Generate slides following the 12 required deck sections in order:
   1. Cover slide
   2. Component summary
   3. System position
   4. Entry points and triggers
   5. Internal flow (may span multiple slides for complex components)
   6. Key files and structure
   7. Configuration and runtime requirements
   8. Development workflow
   9. Quality and testing
   10. Deployment and operations
   11. Risks and open questions
   12. Appendix

7. For each slide, produce all required fields:
   - Slide number and title
   - Section assignment
   - Purpose statement
   - Key points (3-5 concise bullet points per slide)
   - Suggested visual with type and description
   - Speaker notes with detailed explanation
   - Evidence references linking to walkthrough sections or source files
   - Confidence level with basis

8. Slide text rules:
   - Use concise, high-signal text on slides.
   - No dense paragraphs — use bullet points.
   - Put detailed context in speaker notes.
   - Include concrete file paths, symbols, commands, and configs.

9. Visual selection rules:
   - Prefer visuals derivable from walkthrough structure.
   - Do not invent architecture not in source materials.
   - Mark conceptual visuals as `[CONCEPTUAL]`.

10. The internal flow section should present the component's execution path as a linear sequence of steps, preserving the order from the walkthrough. Use multiple slides if the flow has more than 6-8 steps.

11. Build an evidence map linking each major claim to its source. Mark each claim as `[VERIFIED]`, `[INFERENCE]`, or `[UNCERTAIN]` — matching the convention used by the linear-walkthrough skill.

12. Preserve technical accuracy and execution sequence from the walkthrough. Do not simplify away important ordering, dependencies, or handoffs.

### Example Slide

```markdown
### Slide 3: Where API Gateway Sits in the System

**Section**: System position

**Purpose**: Show upstream clients and downstream services the gateway connects.

**Key points**:

- Receives HTTP requests from web frontend and mobile clients
- Routes to auth-service, user-service, and billing-service
- Applies rate limiting and request validation before forwarding

**Suggested visual**: Component context diagram — API Gateway centered, with upstream clients on the left and downstream services on the right, showing request flow direction.

**Speaker notes**:

The API Gateway is the single ingress point for all client traffic. It performs JWT validation via the auth-service before forwarding requests. Rate limiting is configured per-route in `config/rate-limits.yaml`. The gateway does not transform request bodies — it forwards them unchanged to downstream services. Health checks from the load balancer hit `/healthz` which bypasses rate limiting (see `src/routes/health.ts:12`).

**Evidence references**:

- Section 2: API Gateway Flow — routing table and middleware chain
- `src/gateway/router.ts:45` — route registration

**Confidence**: High — verified against route configuration and middleware source
```

### Output

Write one file: `presentation/decks/component-deck-outline-{name}.md` following the Deck Outline Format and Slide Format in [output-format.md](./output-format.md).

## Deck Validation Agent Instructions

### Goal

Fact-check assigned deck outlines against the source walkthrough. Verify cross-deck consistency for terminology, relationships, and system descriptions.

### Procedure

1. Read each assigned deck outline completely.

2. For each slide with substantive claims:
   a. Check the evidence references — read the cited walkthrough sections or source files.
   b. Verify the claim is supported by the evidence.
   c. Check that the claim does not introduce information not present in the validated walkthrough.

3. Check for these failure modes:
   - **Unsupported claims**: statements not backed by walkthrough evidence
   - **Invented architecture**: system relationships or behaviors fabricated beyond walkthrough content
   - **Incorrect sequencing**: flow steps presented out of order
   - **Missing context**: important prerequisites or dependencies omitted
   - **Overstated confidence**: slides marked High confidence when the walkthrough marked claims as inference or uncertain

4. Cross-deck consistency checks:
   - Read other deck outlines (at least their system position and dependency slides).
   - Verify that when Deck A says "sends data to Component B," Deck B confirms receiving data from Component A.
   - Check terminology — the same concept should use the same term across all decks.
   - Check system boundary descriptions — where one component ends and another begins should be described consistently.

5. Perform a terminology audit: list key terms and verify consistent usage across all checked decks.

6. Assign confidence per slide: High (claim verified against walkthrough), Medium (partially verifiable), Low (significant gaps or errors).

### Output

Write one file: `presentation/validation/component-deck-validation-{name}.md` following the Deck Validation Report Format in [output-format.md](./output-format.md).

## Packaging Agent Instructions

### Goal

Finalize all deck outlines by applying validation corrections and produce the presentation crosswalk index.

### Procedure

1. Read all validation reports from `presentation/validation/`.

2. For each correction in the validation reports:
   - Read the affected deck outline.
   - Apply the correction using Edit operations.
   - Update the confidence level if the correction changes it.

3. Read `presentation/component-index.md` for the full component list.

4. Build the presentation crosswalk:
   - Index all decks with slide counts, confidence levels, and validator assignments.
   - Map cross-component navigation — for each component-to-component relationship, note the relevant slides in each deck.
   - Build walkthrough-to-deck traceability — for each walkthrough section, list which deck(s) and slide(s) reference it.
   - Summarize validation results per deck.
   - List open items from walkthrough open-questions.md that affect presentations.

5. Verify completeness:
   - Every walkthrough section should be referenced by at least one deck.
   - Every component in the index should have a finalized deck.
   - Every critical validation correction should be applied.

### Output

Write one file: `presentation/presentation-crosswalk.md` following the Presentation Crosswalk Format in [output-format.md](./output-format.md).

Finalized deck outlines remain at `presentation/decks/component-deck-outline-{name}.md` with corrections applied in place.
