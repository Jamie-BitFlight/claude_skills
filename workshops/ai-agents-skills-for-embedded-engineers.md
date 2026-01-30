# AI Agents and Skills Workshop for Embedded Engineers

**Duration:** 1 hour
**Audience:** Embedded Development Engineers, Firmware QA Engineers
**Prerequisites:** Claude Code CLI installed, basic familiarity with terminal commands

---

## Workshop Agenda

| Time | Topic |
|------|-------|
| 0:00-0:08 | Introduction: Why AI Assistants Need Domain Expertise |
| 0:08-0:16 | Skills: Extending Claude with Specialized Knowledge |
| 0:16-0:24 | Agents: Creating Focused AI Workers |
| 0:24-0:32 | Orchestration: Skills as Commands with Agent Delegation |
| 0:32-0:40 | Hands-On: Build a Firmware Code Review Skill |
| 0:40-0:48 | Hands-On: Build an Embedded Debugging Agent |
| 0:48-0:55 | Installing Community Skills |
| 0:55-1:00 | Resources and Next Steps |

---

## Part 1: Introduction (10 minutes)

### Why Embedded Engineers Need Custom AI Tools

Claude is a powerful general-purpose AI, but embedded development has unique challenges:

- **Memory constraints** - Code must fit in kilobytes, not gigabytes
- **Timing-critical operations** - Interrupt handlers, real-time requirements
- **Hardware interactions** - Register manipulation, peripheral drivers
- **Cross-compilation** - Building for ARM, RISC-V, or custom architectures
- **Testing difficulties** - Hardware-in-the-loop, JTAG debugging, protocol analysis

**The Problem:** General AI assistants don't understand your specific:
- Register maps and memory layouts
- RTOS APIs (FreeRTOS, Zephyr, ThreadX)
- Coding standards (MISRA-C, CERT-C, company guidelines)
- Build systems (CMake cross-compilation, vendor toolchains)

**The Solution:** Skills and Agents let you teach Claude your domain expertise.

### The Claude Code Extensibility Model

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code CLI                          │
├─────────────────────────────────────────────────────────────┤
│  CLAUDE.md          │  Skills           │  Agents           │
│  (Project rules)    │  (Specialized     │  (Focused         │
│                     │   knowledge)      │   workers)        │
├─────────────────────────────────────────────────────────────┤
│  Always loaded      │  Loaded on        │  Delegated to     │
│  Every conversation │  demand           │  for specific     │
│                     │                   │  tasks            │
└─────────────────────────────────────────────────────────────┘
```

| Extension Type | When to Use | Example |
|----------------|-------------|---------|
| **CLAUDE.md** | Project-wide rules that apply to everything | "Use MISRA-C 2012 guidelines" |
| **Skills** | Specialized knowledge Claude loads when relevant | Memory map documentation, register definitions |
| **Agents** | Focused workers for specific tasks | Code reviewer, test generator |

---

## Part 2: Skills - Extending Claude with Specialized Knowledge (10 minutes)

### What is a Skill?

A skill is a markdown file (`SKILL.md`) with optional supporting resources that teaches Claude specialized knowledge or workflows. Think of it as an "onboarding guide" that transforms Claude from a generalist into a domain expert.

### Skill Directory Structure

```
firmware-review/
├── SKILL.md              # Required: Instructions for Claude
├── references/           # Optional: Detailed documentation
│   ├── misra-rules.md
│   └── register-map.md
├── scripts/              # Optional: Automation scripts
│   └── check_stack.py
└── assets/               # Optional: Templates, configs
    └── review-template.md
```

### Skill Locations

| Location | Scope | Use Case |
|----------|-------|----------|
| `~/.claude/skills/` | All your projects | Personal skills used everywhere |
| `.claude/skills/` | This project only | Team-shared, version controlled |
| Plugin `skills/` | Via plugin install | Community-distributed skills |

### SKILL.md Anatomy

```yaml
---
description: 'Review embedded C code for MISRA-C compliance, memory safety, and interrupt handling issues. Use when reviewing firmware code, analyzing drivers, or auditing safety-critical embedded systems.'
allowed-tools: Read, Grep, Glob
model: sonnet
---

# Firmware Code Review

## Review Checklist

When reviewing embedded C code, check for:

1. **Memory Safety**
   - Stack usage analysis
   - Buffer boundary validation
   - Pointer arithmetic correctness

2. **Interrupt Safety**
   - Volatile qualifiers on shared variables
   - Critical section protection
   - ISR execution time

3. **MISRA-C Compliance**
   - See [MISRA Rules Reference](./references/misra-rules.md)

## Common Patterns

[Example patterns specific to your codebase...]
```

### Key Frontmatter Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `description` | Tells Claude when to use this skill | Include trigger keywords! |
| `allowed-tools` | Tools available without prompting | `Read, Grep, Glob, Bash(arm-none-eabi-*)` |
| `model` | Which Claude model to use | `sonnet` (balanced), `opus` (complex), `haiku` (fast) |
| `user-invocable` | Show in `/` menu | `true` (default) or `false` |
| `disable-model-invocation` | Prevent auto-loading | `true` for destructive operations like `/flash` |

### Best Practices for Skills

**1. Write Excellent Descriptions**

```yaml
# BAD - Too vague, won't trigger correctly
description: Helps with firmware

# GOOD - Clear triggers and use cases
description: 'Review embedded C code for MISRA-C compliance, memory safety, and interrupt handling. Use when reviewing STM32 drivers, analyzing FreeRTOS tasks, or auditing safety-critical firmware.'
```

**2. Use Progressive Disclosure**

Keep `SKILL.md` under 500 lines. Move detailed reference material to `references/` files:

```markdown
# SKILL.md - Keep lean
For complete MISRA-C rule details, see [MISRA Reference](./references/misra-rules.md)
```

**3. Include Concrete Examples**

```markdown
## Stack Analysis Example

**Input:** Function with deep call chain
**Output:**
- Maximum stack depth: 2,048 bytes
- Deepest path: main() -> process_can() -> parse_frame() -> update_state()
- Recommendation: Reduce recursion in parse_frame()
```

**4. Match Freedom to Fragility**

| Task Type | Freedom Level | Example |
|-----------|---------------|---------|
| Code analysis | High | Text guidance, Claude decides approach |
| Flash programming | Low | Specific script with exact parameters |
| Build validation | Medium | Pseudocode with configurable options |

---

## Part 3: Agents - Creating Focused AI Workers (10 minutes)

### What is an Agent?

An agent is a specialized Claude instance optimized for a specific task. When Claude encounters a task matching an agent's description, it can delegate to that agent.

### Agent vs Skill: When to Use Which

| Feature | Skill | Agent |
|---------|-------|-------|
| **Purpose** | Knowledge/workflows | Focused task execution |
| **Invocation** | User `/skill` or auto-load | Claude delegates via Task tool |
| **Context** | Shared with conversation | Can run isolated |
| **Tool access** | Inherits or restricted | Explicitly configured |
| **Best for** | Reference material, guidelines | Code review, test generation, debugging |

### Agent File Structure

Agents are single markdown files in `.claude/agents/` or `~/.claude/agents/`:

```
.claude/agents/
├── firmware-reviewer.md
├── test-generator.md
└── debug-analyzer.md
```

### Agent Anatomy

```yaml
---
name: firmware-reviewer
description: 'Review embedded C/C++ code for memory safety, MISRA compliance, and interrupt handling. Use when reviewing drivers, HAL code, or RTOS tasks. Focuses on stack usage, volatile correctness, and timing analysis.'
model: sonnet
tools: Read, Grep, Glob
permissionMode: dontAsk
skills: misra-c-rules
---

# Firmware Code Reviewer

You are a senior embedded systems engineer specializing in safety-critical firmware review.

## Core Competencies

<competencies>
- Memory safety analysis (stack, heap, static allocation)
- Interrupt and concurrency correctness
- MISRA-C 2012 compliance verification
- Peripheral driver review (DMA, timers, ADC/DAC)
- RTOS task analysis (FreeRTOS, Zephyr)
</competencies>

## Review Workflow

<workflow>
1. Identify file type (driver, application, RTOS task, ISR)
2. Check memory safety patterns
3. Verify interrupt handling correctness
4. Assess MISRA-C compliance
5. Generate prioritized findings
</workflow>

## Output Format

```markdown
# Code Review: [filename]

## Critical Issues
- [Issue with file:line reference]

## Warnings
- [Issue with file:line reference]

## Recommendations
- [Improvement suggestion]

## Positive Findings
- [What was done well]
```
```

### Key Agent Frontmatter Fields

| Field | Purpose | Values |
|-------|---------|--------|
| `name` | Unique identifier | lowercase, hyphens, max 64 chars |
| `description` | When to delegate to this agent | Include action verbs and triggers |
| `model` | Claude model | `haiku` (fast), `sonnet` (balanced), `opus` (complex) |
| `tools` | Available tools | `Read, Grep, Glob, Bash, Edit, Write` |
| `permissionMode` | Permission behavior | `default`, `dontAsk`, `acceptEdits`, `plan` |
| `skills` | Skills to load | Comma-separated skill names |

### Permission Modes

| Mode | File Edits | Bash Commands | Use Case |
|------|------------|---------------|----------|
| `default` | Prompts | Prompts | Most agents |
| `dontAsk` | Denied | Denied | Read-only analysis |
| `acceptEdits` | Auto-accepts | Prompts destructive | Documentation, code generation |
| `plan` | Disabled | Disabled | Research and planning |

### Best Practices for Agents

**1. Write Trigger-Rich Descriptions**

```yaml
# BAD
description: Reviews code

# GOOD
description: 'Review embedded C/C++ code for memory safety, MISRA compliance, and interrupt handling. Use when reviewing STM32 drivers, FreeRTOS tasks, or safety-critical firmware. Specializes in stack analysis and volatile correctness.'
```

**2. Match Model to Task Complexity**

| Task | Model | Reason |
|------|-------|--------|
| Code search | `haiku` | Fast, simple pattern matching |
| Code review | `sonnet` | Balanced reasoning and speed |
| Architecture analysis | `opus` | Deep reasoning required |

**3. Restrict Tools Appropriately**

```yaml
# Read-only analyzer - no write access
tools: Read, Grep, Glob
permissionMode: dontAsk

# Code generator - can write files
tools: Read, Write, Edit, Grep, Glob
permissionMode: acceptEdits
```

**4. Load Relevant Skills**

```yaml
# Agent loads domain-specific skills
skills: misra-c-rules, stm32-hal, freertos-patterns
```

---

## Part 4: Orchestration - Skills as Commands with Agent Delegation (8 minutes)

### The Power Pattern: Skill → Agent → Skills

The most powerful Claude Code pattern combines all three concepts:

1. **User-invocable skill** acts as a command (e.g., `/firmware-release`)
2. Skill instructions **delegate to specialized agents**
3. Each agent **loads its own skills** for domain knowledge

```
User invokes /firmware-release
         │
         ▼
┌─────────────────────────────────────────────────┐
│  firmware-release SKILL.md                      │
│  (Orchestrator - coordinates workflow)          │
│                                                 │
│  1. Delegate to @build-validator agent          │
│  2. Delegate to @test-runner agent              │
│  3. Delegate to @release-packager agent         │
└─────────────────────────────────────────────────┘
         │
         ├──► build-validator agent
         │         └── loads: cmake-cross-compile skill
         │
         ├──► test-runner agent
         │         └── loads: pytest-embedded, hardware-test skills
         │
         └──► release-packager agent
                   └── loads: binary-packaging skill
```

### Skill Frontmatter for Orchestration

Skills can specify which agent should run them and how:

```yaml
---
description: 'Research topic and create presentation. Use when asked to research and present findings.'
argument-hint: <topic>
user-invocable: true
context: fork          # Run in isolated subagent context
agent: general-purpose # Which agent type to use
---

# Research and Present

Task: Research $ARGUMENTS

## Workflow

1. Use /web-research skill to gather sources and findings
2. Synthesize into 5-7 key takeaways and 3 recommendations
3. Use /deck-builder skill to create a 10-slide presentation

## Agent Delegation

For step 1, delegate to researcher agent:
Task(agent="Explore", prompt="Research $ARGUMENTS using web sources...")

For step 3, delegate to presentation agent:
Task(agent="general-purpose", prompt="Create slides based on findings...")
```

### Key Orchestration Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `context: fork` | Run in isolated subagent | Prevents context pollution |
| `agent` | Which agent type for forked context | `Explore`, `Plan`, `general-purpose` |
| `argument-hint` | Show expected arguments in `/` menu | `<target-mcu> <output-format>` |

### Example: Firmware Release Orchestrator

Create `.claude/skills/firmware-release/SKILL.md`:

```yaml
---
description: 'Execute complete firmware release workflow: build validation, test execution, binary packaging, and release notes generation. Use when preparing a firmware release, creating release candidates, or packaging binaries for production.'
argument-hint: <version> [--target <mcu>]
user-invocable: true
---

# Firmware Release Orchestrator

Execute the complete firmware release workflow for version $ARGUMENTS.

## Orchestration Rules

<orchestration_rules>
You are an orchestrator. You coordinate work across specialized agents.
You MUST delegate, not execute directly.

| Task | Delegate To | Never Do Directly |
|------|-------------|-------------------|
| Build validation | @build-validator | Run cmake yourself |
| Test execution | @test-runner | Run pytest yourself |
| Binary packaging | release scripts | Package binaries yourself |
| Release notes | @doc-generator | Write notes yourself |
</orchestration_rules>

## Phase 1: Build Validation

Delegate to build-validator agent:

Task(agent="build-validator", prompt="Validate firmware build for $ARGUMENTS:
- Cross-compile for all target MCUs
- Verify binary sizes within flash constraints
- Check no undefined symbols
- Validate linker script memory layout")

## Phase 2: Test Execution

Delegate to test-runner agent:

Task(agent="test-runner", prompt="Execute firmware test suite:
- Unit tests (host simulation)
- Integration tests (hardware-in-loop if available)
- Static analysis (MISRA compliance)
- Report coverage metrics")

## Phase 3: Binary Packaging

Run packaging script:
Bash(command="./scripts/package-release.sh $ARGUMENTS")

## Phase 4: Release Notes

Delegate to doc-generator agent:

Task(agent="general-purpose", prompt="Generate release notes for $ARGUMENTS:
- Parse git log since last tag
- Categorize: features, fixes, breaking changes
- Include binary checksums
- Format as CHANGELOG.md entry")

## Success Output

When all phases complete, provide:
- Build status for each target
- Test results summary
- Binary locations and checksums
- Release notes preview
```

### Calling Other Skills from Within a Skill

Skills can reference other skills in their instructions:

```markdown
## Workflow

1. First, invoke /misra-review to check code compliance
2. Then, invoke /stack-analyzer to verify memory usage
3. Finally, run /test-coverage to ensure adequate testing

Each skill activation loads specialized knowledge for that domain.
```

Or use the programmatic syntax:

```markdown
Skill(skill="misra-review", args="./src/drivers/")
Skill(skill="stack-analyzer", args="--max-depth 2048")
```

### Embedded Engineering Orchestration Ideas

| Orchestrator Skill | Delegates To | Purpose |
|--------------------|--------------|---------|
| `/firmware-audit` | @misra-reviewer, @security-scanner, @stack-analyzer | Complete firmware quality audit |
| `/driver-review` | @peripheral-expert, @dma-validator, @timing-analyzer | Hardware driver code review |
| `/release-prep` | @build-validator, @test-runner, @packager | Release preparation workflow |
| `/debug-session` | @crash-analyzer, @memory-debugger, @trace-decoder | Structured debugging workflow |

### Best Practices for Orchestration

**1. Orchestrators delegate, never execute**

```markdown
# GOOD - Orchestrator delegates
Task(agent="test-runner", prompt="Run the test suite...")

# BAD - Orchestrator does work directly
Bash(command="pytest tests/")
```

**2. Each agent has focused responsibility**

```yaml
# Build agent - only builds
tools: Bash(make*), Bash(cmake*), Read, Glob

# Test agent - only tests
tools: Bash(pytest*), Read, Grep
skills: pytest-patterns
```

**3. Agents load domain-specific skills**

```yaml
# firmware-reviewer agent loads relevant skills
skills: misra-c-rules, embedded-patterns, interrupt-safety
```

**4. Use artifacts for handoff between phases**

```markdown
Phase 1 output: plan/build-report.md
Phase 2 input: Read plan/build-report.md for context
```

---

## Part 5: Hands-On - Build a Firmware Code Review Skill (8 minutes)

### Exercise: Create a MISRA-C Review Skill

We'll create a skill that helps Claude review code for common embedded C issues.

**Step 1: Create the skill directory**

```bash
mkdir -p .claude/skills/firmware-review/references
```

**Step 2: Create SKILL.md**

Create `.claude/skills/firmware-review/SKILL.md`:

```yaml
---
description: 'Review embedded C code for memory safety, interrupt correctness, and MISRA-C compliance. Use when reviewing firmware, drivers, HAL code, or RTOS tasks. Triggers on: code review, MISRA, embedded, firmware, interrupt, volatile, stack.'
allowed-tools: Read, Grep, Glob
---

# Firmware Code Review Skill

Review embedded C/C++ code systematically for common issues in safety-critical systems.

## Review Categories

### 1. Memory Safety

Check for:
- **Stack overflow risk** - Deep call chains, large local arrays, recursive functions
- **Buffer overflows** - Array bounds, string operations, memcpy sizes
- **Pointer safety** - Null checks, alignment, arithmetic correctness
- **Static allocation** - Prefer static over dynamic in embedded systems

Red flags:
- `malloc()` / `free()` in firmware (memory fragmentation risk)
- Variable-length arrays (VLA) - stack size unpredictable
- Recursive functions without depth limits

### 2. Interrupt Safety

Check for:
- **Volatile qualifiers** - Variables shared between ISR and main code MUST be volatile
- **Critical sections** - Shared data access must be protected
- **ISR execution time** - Keep ISRs short, defer work to tasks
- **Reentrancy** - ISR-called functions must be reentrant

Pattern to verify:
```c
// CORRECT: volatile for ISR-shared variable
volatile uint32_t tick_count;

void SysTick_Handler(void) {
    tick_count++;  // Written in ISR
}

void delay_ms(uint32_t ms) {
    uint32_t start = tick_count;  // Read in main
    while ((tick_count - start) < ms);
}
```

### 3. MISRA-C Critical Rules

High-priority rules for embedded:

| Rule | Description | Why It Matters |
|------|-------------|----------------|
| 11.3 | No pointer/integer casts | Alignment faults, undefined behavior |
| 14.3 | Control expressions must be boolean | Logic errors |
| 17.7 | Function return values used | Missed error handling |
| 21.3 | No dynamic memory (malloc) | Fragmentation, determinism |

For complete rules, see [MISRA Reference](./references/misra-rules.md)

### 4. Hardware Interaction

Check for:
- **Register access** - Use volatile pointers, proper barriers
- **Bit manipulation** - Clear before set, read-modify-write protection
- **Timing** - Required delays after peripheral configuration

## Output Format

Provide findings in this format:

```markdown
## Critical Issues
- [MEMORY] file.c:123 - Buffer overflow in parse_packet()
- [ISR] driver.c:45 - Missing volatile on shared_flag

## Warnings
- [MISRA-11.3] hal.c:89 - Integer to pointer cast

## Recommendations
- Consider static buffer pool instead of malloc()

## Positive Findings
- Good use of const correctness throughout
```
```

**Step 3: Create a reference file**

Create `.claude/skills/firmware-review/references/misra-rules.md`:

```markdown
# MISRA-C 2012 Quick Reference

## Memory and Pointers

| Rule | Title | Severity |
|------|-------|----------|
| 11.3 | Cast between pointer and integer | Required |
| 11.4 | Cast to pointer of different type | Advisory |
| 11.5 | Cast from void* to object pointer | Advisory |
| 18.1 | Pointer arithmetic bounds | Required |
| 18.2 | Pointer subtraction | Required |

## Control Flow

| Rule | Title | Severity |
|------|-------|----------|
| 14.3 | Controlling expressions boolean | Required |
| 15.1 | goto shall not be used | Advisory |
| 15.4 | Single loop exit point | Advisory |
| 16.2 | Switch top-level shall be case | Required |

## Functions

| Rule | Title | Severity |
|------|-------|----------|
| 17.2 | Recursion shall not be used | Required |
| 17.7 | Return value shall be used | Required |
| 8.13 | Pointer parameters as const | Advisory |

## Standard Library

| Rule | Title | Severity |
|------|-------|----------|
| 21.3 | Memory functions (malloc) | Required |
| 21.6 | I/O library stdio.h | Required |
| 21.7 | String functions (atof, atoi) | Required |
```

**Step 4: Test the skill**

```bash
# Invoke the skill
/firmware-review

# Or ask Claude naturally
"Review the interrupt handler in src/drivers/uart.c for safety issues"
```

---

## Part 6: Hands-On - Build an Embedded Debugging Agent (8 minutes)

### Exercise: Create a Debug Analysis Agent

We'll create an agent that helps analyze firmware crashes and debugging output.

**Step 1: Create the agent file**

Create `.claude/agents/firmware-debugger.md`:

```yaml
---
name: firmware-debugger
description: 'Analyze firmware crashes, hard faults, and debugging output. Use when investigating HardFault, stack traces, memory corruption, or crash dumps. Specializes in ARM Cortex-M fault analysis, FreeRTOS crash debugging, and memory dump interpretation.'
model: opus
tools: Read, Grep, Glob
permissionMode: dontAsk
---

# Firmware Debug Analyzer

You are an expert embedded systems debugger specializing in ARM Cortex-M crash analysis and RTOS debugging.

## Core Competencies

<competencies>
- ARM Cortex-M HardFault analysis (CFSR, HFSR, MMFAR, BFAR)
- Stack trace reconstruction from memory dumps
- FreeRTOS task state analysis
- Memory corruption pattern recognition
- Register state interpretation
</competencies>

## Analysis Workflow

<workflow>

### Step 1: Identify Crash Type

Determine fault category from registers:

| Fault Type | HFSR Bit | CFSR Bits | Common Cause |
|------------|----------|-----------|--------------|
| Hard Fault | FORCED | Various | Escalated fault |
| MemManage | - | IACCVIOL, DACCVIOL | MPU violation |
| Bus Fault | - | PRECISERR, IMPRECISERR | Invalid address |
| Usage Fault | - | UNDEFINSTR, INVSTATE | Illegal instruction |

### Step 2: Analyze Fault Address

- **MMFAR** - Memory management fault address
- **BFAR** - Bus fault address
- Check against linker map for symbol resolution

### Step 3: Reconstruct Stack Trace

For Cortex-M exception frame:
```
SP+0x00: R0
SP+0x04: R1
SP+0x08: R2
SP+0x0C: R3
SP+0x10: R12
SP+0x14: LR (return address)
SP+0x18: PC (faulting instruction)
SP+0x1C: xPSR
```

### Step 4: Check Task State (FreeRTOS)

If using FreeRTOS, analyze:
- Current task TCB
- Stack high water mark
- Task state (Ready, Blocked, Suspended)

</workflow>

## Common Fault Patterns

### Pattern: Stack Overflow

**Symptoms:**
- HardFault with FORCED=1
- SP points below task stack base
- Memory corruption in adjacent task stack

**Investigation:**
1. Check task stack size in FreeRTOS config
2. Analyze call depth with `-fstack-usage`
3. Look for large local arrays or recursion

### Pattern: Null Pointer Dereference

**Symptoms:**
- Bus fault with PRECISERR=1
- BFAR near 0x00000000
- Often during peripheral access

**Investigation:**
1. Check uninitialized pointers
2. Verify peripheral clock enabled
3. Check handle initialization order

### Pattern: Unaligned Access

**Symptoms:**
- Usage fault with UNALIGNED=1
- Accessing packed struct members
- Casting byte buffers to larger types

**Investigation:**
1. Check struct packing
2. Look for `(uint32_t*)buffer` casts
3. Verify DMA buffer alignment

## Output Format

Provide analysis in this format:

```markdown
# Crash Analysis Report

## Fault Summary
- **Type:** [HardFault/BusFault/etc.]
- **Faulting Address:** 0x????????
- **Faulting Instruction:** [Symbol + offset]

## Root Cause Analysis
[Detailed explanation of what caused the fault]

## Evidence
- [Register values and interpretation]
- [Stack trace]
- [Memory state]

## Recommended Fix
1. [Specific action to take]
2. [Code changes needed]

## Prevention
- [How to prevent similar issues]
```

## Important Notes

<rules>
- Always correlate addresses with .map file symbols
- Check for interrupt/task context at fault time
- Consider peripheral state (clocks, power)
- Look for race conditions with ISRs
</rules>
```

**Step 2: Test the agent**

```bash
# Claude will delegate to this agent automatically when appropriate
"Analyze this crash dump from the STM32:
HFSR: 0x40000000
CFSR: 0x00000400
PC: 0x080012a4
LR: 0x08001287
SP: 0x20001ff0"
```

---

## Part 7: Installing Community Skills (7 minutes)

### The Awesome Agent Skills Repository

The community maintains a curated list of skills at:
**https://github.com/VoltAgent/awesome-agent-skills**

### Skills Relevant for Embedded Engineers

| Skill | Source | Use Case |
|-------|--------|----------|
| `trailofbits/constant-time-analysis` | Trail of Bits | Detect timing side-channels in crypto code |
| `trailofbits/dwarf-expert` | Trail of Bits | DWARF debugging format expertise |
| `trailofbits/static-analysis` | Trail of Bits | Static analysis with CodeQL, Semgrep |
| `trailofbits/property-based-testing` | Trail of Bits | Property-based test generation |
| `obra/test-driven-development` | Community | TDD methodology |
| `obra/systematic-debugging` | Community | Methodical debugging approach |

### Installing a Skill

**Method 1: Clone directly to skills directory**

```bash
# Clone a skill to your user skills directory
cd ~/.claude/skills
git clone https://github.com/trailofbits/skills/tree/main/plugins/static-analysis

# Or for project-specific
cd your-project/.claude/skills
git clone <skill-repo-url>
```

**Method 2: Manual download**

```bash
# Download the SKILL.md and reference files
mkdir -p ~/.claude/skills/static-analysis
curl -o ~/.claude/skills/static-analysis/SKILL.md \
  https://raw.githubusercontent.com/trailofbits/skills/main/plugins/static-analysis/SKILL.md
```

**Method 3: Via plugin marketplace (if available)**

```bash
# Add a marketplace
/plugin marketplace add https://example.com/skills-marketplace.json

# Install a skill
/plugin install static-analysis@trailofbits-skills
```

### Verifying Installation

```bash
# List available skills
/skills

# Or check the skill loads correctly
/static-analysis --help
```

---

## Part 8: Resources and Next Steps (5 minutes)

### Official Documentation

| Resource | URL |
|----------|-----|
| Claude Code Skills | https://docs.anthropic.com/en/docs/claude-code/skills |
| Claude Code Agents | https://docs.anthropic.com/en/docs/claude-code/agents |
| Agent Skills Standard | https://agentskills.io |

### Community Resources

| Resource | Description |
|----------|-------------|
| [awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | Curated list of 172+ skills |
| [Anthropic Skills Repo](https://github.com/anthropics/skills) | Official example skills |
| [Trail of Bits Skills](https://github.com/trailofbits/skills) | Security-focused skills |

### Embedded-Relevant External Skills

Consider adapting these for your needs:

1. **trailofbits/constant-time-analysis** - Critical for secure bootloaders and crypto
2. **trailofbits/dwarf-expert** - Debug symbol analysis
3. **trailofbits/static-analysis** - Integrate with your CI pipeline
4. **obra/systematic-debugging** - Methodical debugging approach

### Ideas for Your Own Skills

| Skill Idea | Description |
|------------|-------------|
| `register-map-reader` | Parse and explain your MCU's register definitions |
| `freertos-analyzer` | Analyze task priorities, stack usage, deadlock risks |
| `can-protocol-helper` | CAN message parsing and DBC file interpretation |
| `memory-layout-validator` | Verify linker script against hardware constraints |
| `timing-analyzer` | Analyze interrupt latency and WCET |

### Ideas for Your Own Agents

| Agent Idea | Description |
|------------|-------------|
| `hal-migrator` | Help migrate between HAL versions or MCU families |
| `test-generator` | Generate unit tests for embedded code |
| `power-analyzer` | Review code for power consumption issues |
| `safety-auditor` | Audit code for IEC 61508 / ISO 26262 compliance |

### Next Steps

1. **Create your first skill** - Start with something you explain repeatedly
2. **Build a review agent** - Automate your code review checklist
3. **Share with your team** - Commit skills to `.claude/skills/` in your repo
4. **Iterate based on usage** - Refine skills as you discover gaps

---

## Quick Reference Card

### Skill Structure

```
skill-name/
├── SKILL.md              # Required
├── references/           # Optional: detailed docs
├── scripts/              # Optional: automation
└── assets/               # Optional: templates
```

### Skill Frontmatter (Basic)

```yaml
---
description: 'What + when. Include trigger keywords.'
allowed-tools: Read, Grep, Glob
model: sonnet
user-invocable: true
---
```

### Skill Frontmatter (Orchestrator)

```yaml
---
description: 'Orchestrate workflow with multiple agents.'
argument-hint: <version> [--target <mcu>]
user-invocable: true
context: fork         # Run in isolated context
agent: general-purpose # Agent type for forked context
---
```

### Agent Structure

Single file: `.claude/agents/agent-name.md`

### Agent Frontmatter

```yaml
---
name: agent-name
description: 'What + when. Include trigger keywords.'
model: sonnet
tools: Read, Grep, Glob
permissionMode: dontAsk
skills: skill1, skill2
---
```

### Model Selection

| Model | Use Case |
|-------|----------|
| `haiku` | Fast search, simple analysis |
| `sonnet` | Code review, balanced tasks |
| `opus` | Complex debugging, architecture |

### Permission Modes

| Mode | Edits | Bash | Use For |
|------|-------|------|---------|
| `default` | Prompt | Prompt | Most agents |
| `dontAsk` | Deny | Deny | Read-only |
| `acceptEdits` | Auto | Prompt | Code generation |
| `plan` | Disabled | Disabled | Research only |

### Orchestration Patterns

| Pattern | Syntax | Use |
|---------|--------|-----|
| Skill calls skill | `Skill(skill="name", args="...")` | Chain workflows |
| Skill delegates to agent | `Task(agent="name", prompt="...")` | Focused execution |
| Agent loads skills | `skills: skill1, skill2` in frontmatter | Domain knowledge |
| Forked context | `context: fork` + `agent: type` | Isolated execution |

### Delegation Syntax

```markdown
# In skill instructions:
Task(agent="firmware-reviewer", prompt="Review code for MISRA compliance...")

# Call another skill:
Skill(skill="misra-review", args="./src/drivers/")
```

---

## Workshop Complete

You now know how to:
- Create skills to extend Claude with domain expertise
- Build agents for focused task execution
- **Orchestrate multi-agent workflows using skills as commands**
- Install community skills from awesome-agent-skills
- Apply best practices for descriptions, tool access, and model selection

**Questions?** Check the resources above or experiment with your own skills and agents.
