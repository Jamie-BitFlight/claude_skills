# Agent Orchestration

Makes Claude more thorough and systematic when handling complex, multi-step tasks.

## Why Install This?

When you ask Claude to do something involving multiple steps or files, Claude sometimes:

- Fixes only the specific instance you pointed out, missing similar issues elsewhere
- Says "done" without actually verifying the solution works
- Applies quick patches that address symptoms instead of root causes
- Makes assumptions without checking them against the actual codebase
- Skips important verification steps before marking work complete

This plugin makes Claude more methodical and complete with complex work.

## What Changes

With this plugin installed, Claude will:

**Investigate before implementing**

- Gather comprehensive context before jumping to solutions
- Trace issues through the complete stack to find root causes
- Distinguish between symptoms and underlying problems
- Verify observations instead of making assumptions

**Think systematically about scope**

- When you point out one bug, audit the entire file or module for similar patterns
- Break complex tasks into clear steps with measurable success criteria
- Consider related components that might be affected
- Look for the pattern behind single instances

**Verify work actually functions**

- Run tests and show you the actual output, not just "tests should pass"
- Execute code in realistic scenarios, not just isolated unit tests
- Check that original problems no longer occur
- Confirm no regressions were introduced

**Complete all verification before claiming "done"**

- Provide evidence that solutions work in practice
- Test edge cases and error handling
- Update documentation to reflect changes
- Meet clear completion criteria before reporting success

## Skills

| Skill                 | Purpose                                                                                            |
| --------------------- | -------------------------------------------------------------------------------------------------- |
| `agent-orchestration` | Scientific delegation framework for coordinating sub-agents with observation-based context patterns |

## Installation

First, add the marketplace (one-time setup):

```bash
/plugin marketplace add Jamie-BitFlight/claude_skills
```

Then install the plugin:

```bash
/plugin install agent-orchestration@jamie-bitflight-skills
```

## Usage

Just install it - it works automatically. You'll notice the difference when you give Claude tasks like:

**"Fix this bug"**

- Claude investigates the root cause thoroughly
- Looks for similar bugs in related code
- Verifies the fix actually works with real test execution
- Checks for regressions in dependent functionality

**"Add this feature"**

- Claude breaks down the work into clear steps
- Considers integration with existing systems
- Tests both success and failure scenarios
- Provides evidence each acceptance criterion is met

**"Refactor this code"**

- Claude ensures tests pass before starting
- Verifies behavior remains identical after changes
- Checks performance isn't degraded
- Confirms no new issues were introduced

## Example

**Without this plugin:**

```
You: "Fix the authentication bug in login.py"
Claude: [reads file, makes change]
Claude: "I've fixed the issue by updating the validation logic.
        The code should work now."
```

Later you discover the same bug exists in three other files, tests are actually failing, and the fix only addressed a symptom.

**With this plugin:**

```
You: "Fix the authentication bug in login.py"
Claude: [investigates root cause]
Claude: "I found the validation issue in login.py. This pattern
        appears in 4 files total. Let me audit and fix all instances."
Claude: [fixes all instances, runs tests]
Claude: "Fixed authentication validation in login.py, signup.py,
        reset_password.py, and api_auth.py. All tests passing:

        pytest output:
        ====== 47 passed in 2.3s ======

        Root cause was missing email format validation before
        database query. Applied consistent validation across all
        auth entry points."
```

## Requirements

- Claude Code v2.0+

## How It Works

The plugin guides Claude to:

- Base decisions on verified observations rather than assumptions
- Define clear success criteria before starting work
- Investigate comprehensively using all available tools
- Provide concrete evidence that solutions actually function
- Think about scope systematically (one bug often indicates a pattern)

This results in more complete, reliable solutions with less back-and-forth iteration.
