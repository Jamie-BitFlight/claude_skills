# Example CLAUDE.md: Boris Cherny's Configuration

Real-world CLAUDE.md file demonstrating effective prompt optimization patterns. This example shows strong use of structured headings, numbered principles, actionable instructions, and positive framing.

SOURCE: Boris Cherny (@leadgenman), shared publicly on social media (2026-03-06)

---

## Full Example

```markdown
## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update tasks/lessons.md with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes -- don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -- then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management
1. **Plan First**: Write plan to tasks/todo.md with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to tasks/todo.md
6. **Capture Lessons**: Update tasks/lessons.md after corrections

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Only touch what's necessary. No side effects with new bugs.
```

---

## Analysis: What This Example Does Well

### Structured Headings with Numbered Subsections

Each workflow principle gets its own numbered heading under `## Workflow Orchestration`. This creates a scannable hierarchy that Claude can reference by number ("following principle 4, I'll verify before marking complete").

### Actionable Bullet Points

Every bullet is a concrete instruction, not a vague aspiration:

| Vague (avoided) | Concrete (used) |
|---|---|
| "Plan carefully" | "Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)" |
| "Use agents wisely" | "One task per subagent for focused execution" |
| "Be thorough" | "Run tests, check logs, demonstrate correctness" |

### Balanced Guidance

Principle 5 ("Demand Elegance") explicitly includes a scope limiter: "Skip this for simple, obvious fixes -- don't over-engineer." This prevents Claude from over-applying the rule, which is a common failure mode when instructions lack boundary conditions.

### Self-Referential Learning Loop

Principle 3 creates a feedback mechanism: corrections from the user are captured in `tasks/lessons.md` and reviewed at session start. This is an effective pattern for projects with recurring sessions.

### Positive Framing with Strategic Prohibitions

The file uses mostly positive framing ("Use subagents liberally", "Write detailed specs upfront") but deploys prohibitions strategically where absolute boundaries matter ("Never mark a task complete without proving it works"). This follows the optimization principle: use positive framing by default, reserve prohibitions for hard constraints.

### Bold Keywords in Task Management

The `## Task Management` section uses `**bold**` keywords at the start of each step ("**Plan First**", "**Verify Plan**"). This creates visual anchors that improve scannability for both humans and Claude.

---

## Patterns Worth Adopting

1. **Numbered workflow principles** -- creates a referenceable framework ("per principle 4...")
2. **Scope limiters on broad rules** -- prevents over-application
3. **Session-persistent learning files** -- `tasks/lessons.md` pattern for cross-session improvement
4. **Verification as a named principle** -- elevates testing from afterthought to core workflow step
5. **Autonomous action bias** -- "just fix it" framing reduces unnecessary back-and-forth
6. **Three-word principle names** -- "Plan Mode Default", "Simplicity First" -- memorable and referenceable
