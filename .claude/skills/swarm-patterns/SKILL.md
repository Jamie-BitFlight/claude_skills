---
name: swarm-patterns
description: Recipes and patterns for Claude Code multi-agent swarms. Use when building parallel specialist reviews, pipeline workflows, self-organizing swarms, research-then-implement flows, plan approval gates, coordinated refactoring, or any divide-and-conquer orchestration pattern.
---

# Swarm Patterns

Orchestration recipes for multi-agent workflows in Claude Code v2.1.45.

---

## Pattern 1 -- Parallel Specialists (Leader Pattern)

Multiple specialists review code simultaneously:

```javascript
// 1. Create team
TeamCreate({ team_name: "code-review" })

// 2. Spawn specialists in parallel (single message, multiple Task calls)
Agent({
  team_name: "code-review",
  name: "security",
  subagent_type: "compound-engineering:review:security-sentinel",
  prompt: "Review the PR for security vulnerabilities. Focus on SQL injection, XSS, auth bypass. Send findings to team-lead.",
  run_in_background: true
})

Agent({
  team_name: "code-review",
  name: "performance",
  subagent_type: "compound-engineering:review:performance-oracle",
  prompt: "Review the PR for performance issues. Focus on N+1 queries, memory leaks, slow algorithms. Send findings to team-lead.",
  run_in_background: true
})

Agent({
  team_name: "code-review",
  name: "simplicity",
  subagent_type: "compound-engineering:review:code-simplicity-reviewer",
  prompt: "Review the PR for unnecessary complexity. Focus on over-engineering, premature abstraction, YAGNI violations. Send findings to team-lead.",
  run_in_background: true
})

// 3. Wait for results (messages arrive automatically)

// 4. Synthesize findings and cleanup
SendMessage({ type: "shutdown_request", recipient: "security", content: "Review complete" })
SendMessage({ type: "shutdown_request", recipient: "performance", content: "Review complete" })
SendMessage({ type: "shutdown_request", recipient: "simplicity", content: "Review complete" })
// Wait for approvals...
TeamDelete()
```

---

## Pattern 2 -- Pipeline (Sequential Dependencies)

Each stage depends on the previous:

```javascript
// 1. Create team and task pipeline
TeamCreate({ team_name: "feature-pipeline" })

TaskCreate({ subject: "Research", description: "Research best practices for the feature", activeForm: "Researching..." })
TaskCreate({ subject: "Plan", description: "Create implementation plan based on research", activeForm: "Planning..." })
TaskCreate({ subject: "Implement", description: "Implement the feature according to plan", activeForm: "Implementing..." })
TaskCreate({ subject: "Test", description: "Write and run tests for the implementation", activeForm: "Testing..." })
TaskCreate({ subject: "Review", description: "Final code review before merge", activeForm: "Reviewing..." })

// Set up sequential dependencies
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })
TaskUpdate({ taskId: "3", addBlockedBy: ["2"] })
TaskUpdate({ taskId: "4", addBlockedBy: ["3"] })
TaskUpdate({ taskId: "5", addBlockedBy: ["4"] })

// 2. Spawn workers that claim and complete tasks
Agent({
  team_name: "feature-pipeline",
  name: "researcher",
  subagent_type: "compound-engineering:research:best-practices-researcher",
  prompt: "Claim task #1, research best practices, complete it, send findings to team-lead. Then check for more work.",
  run_in_background: true
})

Agent({
  team_name: "feature-pipeline",
  name: "implementer",
  subagent_type: "general-purpose",
  prompt: "Check TaskList periodically. When task #3 unblocks, claim it and implement. Then complete and notify team-lead.",
  run_in_background: true
})

// Tasks auto-unblock as dependencies complete
```

---

## Pattern 3 -- Swarm (Self-Organizing)

Workers grab available tasks from a pool:

```javascript
// 1. Create team and task pool
TeamCreate({ team_name: "file-review-swarm" })

// Create many independent tasks (no dependencies)
// For each file: auth.rb, user.rb, api_controller.rb, payment.rb
TaskCreate({
  subject: "Review auth.rb",
  description: "Review auth.rb for security and code quality issues",
  activeForm: "Reviewing auth.rb..."
})
// ... repeat for each file

// 2. Spawn worker swarm with self-organizing prompt
Agent({
  team_name: "file-review-swarm",
  name: "worker-1",
  subagent_type: "general-purpose",
  prompt: `
    You are a swarm worker. Your job:
    1. Call TaskList to see available tasks
    2. Find a task with status 'pending' and no owner
    3. Claim it with TaskUpdate (set owner to your name)
    4. Do the work
    5. Mark it completed with TaskUpdate
    6. Send findings to team-lead via SendMessage
    7. Repeat until no tasks remain
  `,
  run_in_background: true
})

Agent({
  team_name: "file-review-swarm",
  name: "worker-2",
  subagent_type: "general-purpose",
  prompt: "[Same prompt as worker-1]",
  run_in_background: true
})

Agent({
  team_name: "file-review-swarm",
  name: "worker-3",
  subagent_type: "general-purpose",
  prompt: "[Same prompt as worker-1]",
  run_in_background: true
})

// Workers race to claim tasks, naturally load-balance
```

> **Automation tip**: The `TaskCreate` pool setup above (creating one task per file) can be generated automatically from a markdown checklist. Use `Skill(skill: "swarm-from-markdown")` to parse a `- [ ]` checklist file and emit the full `TeamCreate` + `TaskCreate` + `Agent` call sequence without writing it by hand.

---

## Pattern 4 -- Research + Implementation

Research first, then implement:

```javascript
// 1. Research phase (synchronous, returns results)
const research = await Agent({
  subagent_type: "compound-engineering:research:best-practices-researcher",
  description: "Research caching patterns",
  prompt: "Research best practices for implementing caching in Rails APIs. Include cache invalidation strategies, Redis vs Memcached, cache key design."
})

// 2. Use research to guide implementation
Agent({
  subagent_type: "general-purpose",
  description: "Implement caching",
  prompt: `
    Implement API caching based on this research:

    ${research.content}

    Focus on the user_controller.rb endpoints.
  `
})
```

---

## Pattern 5 -- Plan Approval Workflow

Require plan approval before implementation:

```javascript
// 1. Create team
TeamCreate({ team_name: "careful-work" })

// 2. Spawn architect with plan mode
Agent({
  team_name: "careful-work",
  name: "architect",
  subagent_type: "Plan",
  prompt: "Design an implementation plan for adding OAuth2 authentication",
  mode: "plan",  // Requires plan approval
  run_in_background: true
})

// 3. Wait for plan approval request
// You receive: {"type": "plan_approval_request", "from": "architect", "requestId": "plan-xxx", ...}

// 4. Review and approve/reject
SendMessage({
  type: "plan_approval_response",
  request_id: "plan-xxx",
  recipient: "architect",
  approve: true
})
// OR reject with feedback
SendMessage({
  type: "plan_approval_response",
  request_id: "plan-xxx",
  recipient: "architect",
  approve: false,
  content: "Please add rate limiting considerations"
})
```

---

## Pattern 6 -- Coordinated Multi-File Refactoring

```javascript
// 1. Create team for coordinated refactoring
TeamCreate({ team_name: "refactor-auth" })

// 2. Create tasks with clear file boundaries
TaskCreate({
  subject: "Refactor User model",
  description: "Extract authentication methods to AuthenticatableUser concern",
  activeForm: "Refactoring User model..."
})

TaskCreate({
  subject: "Refactor Session controller",
  description: "Update to use new AuthenticatableUser concern",
  activeForm: "Refactoring Sessions..."
})

TaskCreate({
  subject: "Update specs",
  description: "Update all authentication specs for new structure",
  activeForm: "Updating specs..."
})

// Dependencies: specs depend on both refactors completing
TaskUpdate({ taskId: "3", addBlockedBy: ["1", "2"] })

// 3. Spawn workers for each task
Agent({
  team_name: "refactor-auth",
  name: "model-worker",
  subagent_type: "general-purpose",
  prompt: "Claim task #1, refactor the User model, complete when done",
  run_in_background: true
})

Agent({
  team_name: "refactor-auth",
  name: "controller-worker",
  subagent_type: "general-purpose",
  prompt: "Claim task #2, refactor the Session controller, complete when done",
  run_in_background: true
})

Agent({
  team_name: "refactor-auth",
  name: "spec-worker",
  subagent_type: "general-purpose",
  prompt: "Wait for task #3 to unblock (when #1 and #2 complete), then update specs",
  run_in_background: true
})
```

> **Large-scale structural transforms**: When refactoring involves AST-level changes (renaming symbols, migrating API call-sites, enforcing new patterns across ≥10 files), use `Skill(skill: "dh:codemod-runner")` to select the right tool (comby/ast-grep/jscodeshift/ts-morph/LibCST), assess scope with `rg -l`, and verify idempotency before committing. Assign one batch per swarm worker.

---

## Complete Workflows

### Workflow 1 -- Full Code Review with Parallel Specialists

```javascript
// === STEP 1: Setup ===
TeamCreate({ team_name: "pr-review-123", description: "Reviewing PR #123" })

// === STEP 2: Spawn reviewers in parallel ===
Agent({
  team_name: "pr-review-123",
  name: "security",
  subagent_type: "compound-engineering:review:security-sentinel",
  prompt: `Review PR #123 for security vulnerabilities.

  Focus on:
  - SQL injection
  - XSS vulnerabilities
  - Authentication/authorization bypass
  - Sensitive data exposure

  When done, send your findings to team-lead using SendMessage.`,
  run_in_background: true
})

Agent({
  team_name: "pr-review-123",
  name: "perf",
  subagent_type: "compound-engineering:review:performance-oracle",
  prompt: `Review PR #123 for performance issues.

  Focus on:
  - N+1 queries
  - Missing indexes
  - Memory leaks
  - Inefficient algorithms

  Send findings to team-lead when done.`,
  run_in_background: true
})

Agent({
  team_name: "pr-review-123",
  name: "arch",
  subagent_type: "compound-engineering:review:architecture-strategist",
  prompt: `Review PR #123 for architectural concerns.

  Focus on:
  - Design pattern adherence
  - SOLID principles
  - Separation of concerns
  - Testability

  Send findings to team-lead when done.`,
  run_in_background: true
})

// === STEP 3: Monitor and collect results ===
// Messages arrive automatically -- no polling needed

// === STEP 4: Synthesize findings ===
// Combine all reviewer findings into a cohesive report

// === STEP 5: Cleanup ===
SendMessage({ type: "shutdown_request", recipient: "security", content: "Review complete" })
SendMessage({ type: "shutdown_request", recipient: "perf", content: "Review complete" })
SendMessage({ type: "shutdown_request", recipient: "arch", content: "Review complete" })
// Wait for approvals...
TeamDelete()
```

### Workflow 2 -- Research > Plan > Implement > Test Pipeline

```javascript
// === SETUP ===
TeamCreate({ team_name: "feature-oauth" })

// === CREATE PIPELINE ===
TaskCreate({ subject: "Research OAuth providers", description: "Research OAuth2 best practices and compare providers (Google, GitHub, Auth0)", activeForm: "Researching OAuth..." })
TaskCreate({ subject: "Create implementation plan", description: "Design OAuth implementation based on research findings", activeForm: "Planning..." })
TaskCreate({ subject: "Implement OAuth", description: "Implement OAuth2 authentication according to plan", activeForm: "Implementing OAuth..." })
TaskCreate({ subject: "Write tests", description: "Write comprehensive tests for OAuth implementation", activeForm: "Writing tests..." })
TaskCreate({ subject: "Final review", description: "Review complete implementation for security and quality", activeForm: "Final review..." })

// Set dependencies
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })
TaskUpdate({ taskId: "3", addBlockedBy: ["2"] })
TaskUpdate({ taskId: "4", addBlockedBy: ["3"] })
TaskUpdate({ taskId: "5", addBlockedBy: ["4"] })

// === SPAWN SPECIALIZED WORKERS ===
Agent({
  team_name: "feature-oauth",
  name: "researcher",
  subagent_type: "compound-engineering:research:best-practices-researcher",
  prompt: "Claim task #1. Research OAuth2 best practices, compare providers, document findings. Mark task complete and send summary to team-lead.",
  run_in_background: true
})

Agent({
  team_name: "feature-oauth",
  name: "planner",
  subagent_type: "Plan",
  prompt: "Wait for task #2 to unblock. Read research from task #1. Create detailed implementation plan. Mark complete and send plan to team-lead.",
  run_in_background: true
})

Agent({
  team_name: "feature-oauth",
  name: "implementer",
  subagent_type: "general-purpose",
  prompt: "Wait for task #3 to unblock. Read plan from task #2. Implement OAuth2 authentication. Mark complete when done.",
  run_in_background: true
})

Agent({
  team_name: "feature-oauth",
  name: "tester",
  subagent_type: "general-purpose",
  prompt: "Wait for task #4 to unblock. Write comprehensive tests for the OAuth implementation. Run tests. Mark complete with results.",
  run_in_background: true
})

Agent({
  team_name: "feature-oauth",
  name: "reviewer",
  subagent_type: "compound-engineering:review:security-sentinel",
  prompt: "Wait for task #5 to unblock. Review the complete OAuth implementation for security. Send final assessment to team-lead.",
  run_in_background: true
})

// Pipeline auto-progresses as each stage completes
```

### Workflow 3 -- Self-Organizing Code Review Swarm

```javascript
// === SETUP ===
TeamCreate({ team_name: "codebase-review" })

// === CREATE TASK POOL (all independent, no dependencies) ===
// For each file to review:
TaskCreate({
  subject: "Review app/models/user.rb",
  description: "Review app/models/user.rb for security vulnerabilities, code quality, and performance issues",
  activeForm: "Reviewing user.rb..."
})
// ... repeat for each file (payment.rb, users_controller.rb, etc.)

// === SPAWN WORKER SWARM ===
const swarmPrompt = `
You are a swarm worker. Your job is to continuously process available tasks.

LOOP:
1. Call TaskList() to see available tasks
2. Find a task that is:
   - status: 'pending'
   - no owner
   - not blocked
3. If found:
   - Claim it: TaskUpdate({ taskId: "X", owner: "YOUR_NAME" })
   - Start it: TaskUpdate({ taskId: "X", status: "in_progress" })
   - Do the review work
   - Complete it: TaskUpdate({ taskId: "X", status: "completed" })
   - Send findings to team-lead via SendMessage
   - Go back to step 1
4. If no tasks available:
   - Send idle notification to team-lead
   - Wait 30 seconds
   - Try again (up to 3 times)
   - If still no tasks, exit

Replace YOUR_NAME with your actual agent name from $CLAUDE_CODE_AGENT_NAME.
`

// Spawn 3 workers
Agent({ team_name: "codebase-review", name: "worker-1", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })
Agent({ team_name: "codebase-review", name: "worker-2", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })
Agent({ team_name: "codebase-review", name: "worker-3", subagent_type: "general-purpose", prompt: swarmPrompt, run_in_background: true })

// Workers self-organize: race to claim tasks, naturally load-balance
```

---

## Best Practices

### 1. Always Cleanup

Don't leave orphaned teams. Always call TeamDelete when done.

### 2. Use Meaningful Names

```javascript
// Good
name: "security-reviewer"
name: "oauth-implementer"
name: "test-writer"

// Bad
name: "worker-1"
name: "agent-2"
```

### 3. Write Clear Prompts

Tell workers exactly what to do:

```javascript
// Good
prompt: `
  1. Review app/models/user.rb for N+1 queries
  2. Check all ActiveRecord associations have proper includes
  3. Document any issues found
  4. Send findings to team-lead via SendMessage
`

// Bad
prompt: "Review the code"
```

### 4. Use Task Dependencies

Let the system manage unblocking:

```javascript
// Good: Auto-unblocking
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })

// Bad: Manual polling
"Wait until task #1 is done, check every 30 seconds..."
```

### 5. Check Messages for Results

Workers send results to your inbox. Messages arrive automatically -- no polling needed.

### 6. Handle Worker Failures

- Workers have 5-minute heartbeat timeout
- Tasks of crashed workers can be reclaimed
- Build retry logic into worker prompts

### 7. Prefer Direct Message Over Broadcast

Broadcast sends N messages for N teammates. Use SendMessage with a specific recipient for targeted communication.

### 8. Match Agent Type to Task

- **Explore** for searching/reading
- **Plan** for architecture design
- **general-purpose** for implementation
- **Specialized reviewers** for specific review types

---

## Quick Reference

### Spawn Subagent (No Team)

```javascript
Agent({ subagent_type: "Explore", description: "Find files", prompt: "..." })
```

### Spawn Teammate (With Team)

```javascript
TeamCreate({ team_name: "my-team" })
Agent({ team_name: "my-team", name: "worker", subagent_type: "general-purpose", prompt: "...", run_in_background: true })
```

### Message Teammate

```javascript
SendMessage({ type: "message", recipient: "worker-1", content: "...", summary: "Brief description" })
```

### Create Task Pipeline

```javascript
TaskCreate({ subject: "Step 1", description: "..." })
TaskCreate({ subject: "Step 2", description: "..." })
TaskUpdate({ taskId: "2", addBlockedBy: ["1"] })
```

### Shutdown Team

```javascript
SendMessage({ type: "shutdown_request", recipient: "worker-1", content: "All done" })
// Wait for approval...
TeamDelete()
```

---

## Related Skills

- Core concepts -- `Skill(skill: "swarm-primitives")`
- Spawning agents -- `Skill(skill: "swarm-spawning")`
- API reference -- `Skill(skill: "swarm-operations")`
- Checklist-to-swarm automation -- `Skill(skill: "swarm-from-markdown")`

---

SOURCE: Claude Code v2.1.45 tool descriptions (TeamCreate, SendMessage, TeamDelete, TaskCreate, TaskUpdate) -- verified 2026-02-18
